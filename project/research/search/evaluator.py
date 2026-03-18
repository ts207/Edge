"""
Batch hypothesis evaluator (Rich Version).

Evaluates a list of HypothesisSpec against a wide feature table and returns
a metrics DataFrame. Reuses the existing project.research infrastructure
(forward returns, cost model, sparsification) rather than reimplementing it.

The evaluator is trigger-type-agnostic: event, state, transition, and
feature_predicate triggers all resolve to a boolean mask over the feature table.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from project.core.timeframes import bars_per_year, normalize_timeframe, timeframe_spec
from project.domain.hypotheses import HypothesisSpec, TriggerType
from project.research.helpers.shrinkage import _time_decay_weights, _effective_sample_size
from project.core.column_registry import ColumnRegistry
from project.events.event_specs import EVENT_REGISTRY_SPECS

# Robustness framework imports
from project.research.robustness.regime_evaluator import evaluate_by_regime
from project.research.robustness.robustness_scorer import compute_robustness_score
from project.research.robustness.stress_test import evaluate_stress_scenarios, STRESS_SCENARIOS, _apply_stress_mask
from project.research.robustness.kill_switch import detect_kill_switches
from project.research.robustness.regime_labeler import label_regimes

# Shared utilities
from project.research.search.feasibility import FeasibilityResult, check_hypothesis_feasibility
from project.research.search.stage_models import CandidateHypothesis, EvaluatedHypothesis, FeasibilityCheckedHypothesis
from project.research.search.evaluator_utils import (
    horizon_bars as _horizon_bars_func,
    forward_log_returns as _forward_log_returns,
    excursion_stats as _excursion_stats,
    trigger_mask as _trigger_mask,
    context_mask as _context_mask,
    trigger_key as _trigger_key,
)

log = logging.getLogger(__name__)


METRICS_COLUMNS = [
    "hypothesis_id",
    "trigger_type",
    "trigger_key",
    "direction",
    "horizon",
    "template_id",
    "n",
    "train_n_obs",
    "validation_n_obs",
    "test_n_obs",
    "validation_samples",
    "test_samples",
    "mean_return_bps",
    "t_stat",
    "sharpe",
    "hit_rate",
    "cost_adjusted_return_bps",
    "mae_mean_bps",
    "mfe_mean_bps",
    "robustness_score",
    "stress_score",
    "kill_switch_count",
    "capacity_proxy",
    "valid",
    "invalid_reason",
]


def evaluated_records_from_metrics(metrics_df: pd.DataFrame) -> pd.DataFrame:
    if metrics_df.empty:
        return pd.DataFrame(columns=METRICS_COLUMNS)
    out = metrics_df.copy()
    out["status"] = "evaluated"
    return out


def _null_row(spec: HypothesisSpec, n: int, reason: str = "unknown") -> Dict[str, Any]:
    candidate = CandidateHypothesis(spec=spec, search_spec_name="evaluation")
    checked = FeasibilityCheckedHypothesis(
        candidate=candidate,
        feasibility=FeasibilityResult(valid=False, reasons=(reason,), details={}),
    )
    evaluated = EvaluatedHypothesis(
        checked=checked,
        valid=False,
        invalid_reason=reason,
        metrics={
            "n": n,
            "train_n_obs": 0,
            "validation_n_obs": 0,
            "test_n_obs": 0,
            "validation_samples": 0,
            "test_samples": 0,
            "mean_return_bps": 0.0,
            "t_stat": 0.0,
            "sharpe": 0.0,
            "hit_rate": 0.0,
            "cost_adjusted_return_bps": 0.0,
            "mae_mean_bps": 0.0,
            "mfe_mean_bps": 0.0,
            "robustness_score": 0.0,
            "stress_score": 0.0,
            "kill_switch_count": 0,
            "capacity_proxy": 0.0,
        },
    )
    row = evaluated.to_record()
    return {column: row.get(column) for column in METRICS_COLUMNS}


def evaluate_hypothesis_batch(
    hypotheses: List[HypothesisSpec],
    features: pd.DataFrame,
    *,
    cost_bps: float = 2.0,
    min_sample_size: int = 20,
    annualisation_factor: Optional[float] = None,
    time_decay_tau_days: Optional[float] = 60.0,
    use_context_quality: bool = True,
) -> pd.DataFrame:
    """
    Evaluate a batch of HypothesisSpec with rich metrics.
    """
    if "close" not in features.columns:
        raise ValueError("features DataFrame must contain a 'close' column")
    if not hypotheses:
        return pd.DataFrame(columns=METRICS_COLUMNS)
    if features.empty:
        rows = [_null_row(spec, 0) for spec in hypotheses]
        return pd.DataFrame(rows)

    if annualisation_factor is None:
        # Infer timeframe from features index frequency if possible
        # Default to 5m if unknown
        try:
            from project.core.timeframes import normalize_timeframe
            # Assuming the index has freq or we can infer it
            pandas_freq = features.index.inferred_freq
            if pandas_freq:
                # Map pandas freq to our timeframe
                # Simplified mapping for common ones
                mapping = {"5min": "5m", "1min": "1m", "15min": "15m", "1H": "1h", "4H": "4h", "1D": "1d"}
                tf = mapping.get(pandas_freq, "5m")
                ann = float(bars_per_year(tf))
            else:
                ann = float(bars_per_year("5m"))
        except Exception:
            ann = float(bars_per_year("5m"))
    else:
        ann = annualisation_factor
    
    # Compute population volatility across full forward distribution to avoid selection bias
    # Use 15m default if hbars not yet resolved, but better to calculate inside loop per horizon.
    # However, to avoid redundant computation, we can cache fwd series.
    fwd_cache: Dict[int, pd.Series] = {}
    
    # Pre-calculate time decay weights if timestamp is available
    weights = pd.Series(1.0, index=features.index)
    if "timestamp" in features.columns and time_decay_tau_days:
        ref_ts = pd.to_datetime(features["timestamp"].max(), utc=True)
        weights = _time_decay_weights(
            features["timestamp"], 
            ref_ts=ref_ts, 
            tau_seconds=time_decay_tau_days * 86400.0, 
            floor_weight=0.05
        )

    # Pre-calculate shared masks for robustness evaluation
    regime_labels = label_regimes(features)
    stress_masks = {s["name"]: _apply_stress_mask(s, features) for s in STRESS_SCENARIOS}

    rows: List[Dict[str, Any]] = []

    for spec in hypotheses:
        feasibility = check_hypothesis_feasibility(spec, features=features)
        if not feasibility.valid:
            rows.append(_null_row(spec, 0, feasibility.primary_reason or "infeasible"))
            continue

        hbars = _horizon_bars_func(spec.horizon)
        direction_sign = 1.0 if spec.direction == "long" else -1.0 if spec.direction == "short" else 1.0

        # Resolve trigger mask
        mask_raw = _trigger_mask(spec, features)

        # Apply entry lag
        if spec.entry_lag > 0:
            mask = mask_raw.astype("boolean").shift(spec.entry_lag, fill_value=False).astype(bool)
        else:
            mask = mask_raw

        # Apply context filter (regime conditioning)
        # If context is specified but cannot be resolved to feature columns, skip this hypothesis.
        if spec.context:
            ctx_mask = _context_mask(
                spec.context,
                features,
                use_context_quality=use_context_quality,
            )
            if ctx_mask is None:
                rows.append(_null_row(spec, 0, "context_unresolvable"))
                continue
            mask = mask & ctx_mask

        # Apply optional feature condition
        if spec.feature_condition is not None:
            fc_spec = HypothesisSpec(
                trigger=spec.feature_condition,
                direction=spec.direction,
                horizon=spec.horizon,
                template_id=spec.template_id,
            )
            fc_mask = _trigger_mask(fc_spec, features)
            mask = mask & fc_mask

        if not mask.any():
            rows.append(_null_row(spec, 0, "no_trigger_hits"))
            continue

        # Compute forward returns and extracts
        if hbars not in fwd_cache:
            fwd_cache[hbars] = _forward_log_returns(features["close"], hbars)
        
        fwd = fwd_cache[hbars]
        event_returns = fwd[mask].dropna()
        n = len(event_returns)
        split_counts = {
            "train_n_obs": 0,
            "validation_n_obs": 0,
            "test_n_obs": 0,
            "validation_samples": 0,
            "test_samples": 0,
        }
        if "split_label" in features.columns and not event_returns.empty:
            split_labels = features.loc[event_returns.index, "split_label"].astype(str)
            split_counts["train_n_obs"] = int((split_labels == "train").sum())
            split_counts["validation_n_obs"] = int((split_labels == "validation").sum())
            split_counts["test_n_obs"] = int((split_labels == "test").sum())
            split_counts["validation_samples"] = split_counts["validation_n_obs"]
            split_counts["test_samples"] = split_counts["test_n_obs"]

        if n < min_sample_size:
            rows.append(_null_row(spec, n, "min_sample_size"))
            continue

        event_weights = weights[mask].loc[event_returns.index]
        
        # ── Refined Statistical Estimators ──
        # Effective Sample Size from time-decay weights
        # n_eff_w = (sum w)^2 / (sum w^2)
        n_eff_w = float(_effective_sample_size(event_weights))
        # NOTE: Overlap correction is handled entirely by the Newey-West
        # variance estimator below — no separate n_eff deflation is needed.
        
        signed = event_returns * direction_sign
        
        # 2. Weighted Mean
        w_sum = event_weights.sum()
        weighted_mean = float((signed * event_weights).sum() / w_sum)
        
        # SF-003: Newey-West robust variance (handling overlap serial correlation).
        # We manually calculate an approximated AR(hbars) overlapping variance for t-stats,
        # integrating the reliability weights.
        v1 = w_sum
        v2 = (event_weights**2).sum()
        denom = v1 - (v2 / v1)
        
        if denom > 0:
            # Base sample weighted variance
            weighted_var = ((event_weights * (signed - weighted_mean)**2).sum()) / denom
            
            # Newey-West overlap correction
            # Lags up to (hbars - 1)
            nw_var = weighted_var
            n_samples = len(signed)
            
            if hbars > 1 and n_samples > hbars:
                signed_demeaned = (signed - weighted_mean).values
                w_arr = event_weights.values
                
                # Approximate sum of autocorrelations out to hbars - 1 lag
                cov_sum = 0.0
                for lag in range(1, hbars):
                    # Bartlett kernel weight: 1 - lag / hbars
                    kernel = 1.0 - (lag / hbars)
                    
                    # Weighted auto-covariance at this lag
                    w_lag = w_arr[lag:] * w_arr[:-lag]
                    x_lag = signed_demeaned[lag:] * signed_demeaned[:-lag]
                    cov_lag = (w_lag * x_lag).sum() / denom
                    
                    cov_sum += 2.0 * kernel * cov_lag
                
                nw_var += cov_sum
                
            weighted_std = np.sqrt(max(0.0, float(nw_var)))
        else:
            weighted_std = 0.0

        # Check for zero variance or too small sample early
        if weighted_std < 1e-10:
            rows.append(_null_row(spec, n, "low_variance"))
            continue
            
        # ── Enhanced Robustness Framework ──
        # 1. Per-Regime Evaluation
        regime_evals = evaluate_by_regime(spec, features, horizon_bars=hbars, min_n_per_regime=5, regime_labels=regime_labels)
        
        # 2. Composite Robustness Score
        robustness = compute_robustness_score(regime_evals, overall_direction=direction_sign)
        
        # 3. Stress Test Score
        stress_evals = evaluate_stress_scenarios(spec, features, horizon_bars=hbars, min_n=5, stress_masks=stress_masks)
        if not stress_evals.empty and stress_evals["valid"].any():
            valid_stress = stress_evals[stress_evals["valid"]]
            # Stress score is fraction of survived scenarios (t_stat > 1.0, a meaningful threshold)
            stress_survived = (valid_stress["t_stat"] > 1.0).sum()
            stress_score = float(stress_survived / len(valid_stress))
        else:
            stress_score = 0.0
            
        # 4. Kill-Switch Detection
        ks_df = detect_kill_switches(spec, features, horizon_bars=hbars, min_n=10)
        ks_count = len(ks_df) if not ks_df.empty else 0
            
        # Excursions
        maes, mfes = _excursion_stats(features["close"], mask, hbars, direction_sign)
        mae_mean = float(maes.mean())
        mfe_mean = float(mfes.mean())

        # Capacity proxy (volume based if available)
        capacity = 1.0
        if "volume" in features.columns:
            capacity = float(features["volume"][mask].median())

        # T-stat using Newey-West weighted standard error. 
        # Overlap density adjustment is already captured structurally by NW variance above, 
        # so we use raw sqrt(n_eff_w) for the denominator to prevent double-penalizing.
        t_stat = weighted_mean / (weighted_std / np.sqrt(max(1.0, n_eff_w)))
        
        # Strategy Sharpe (Scaling by realized trades per year)
        trades_per_year = n * (ann / len(features))
        trades_per_year = min(trades_per_year, ann)  # Cap at theoretical max to avoid sparse-trigger Sharpe inflation
        sharpe = (weighted_mean / weighted_std) * np.sqrt(trades_per_year)
        hit_rate = float((signed > 0).mean())
        mean_bps = weighted_mean * 10_000.0
        cost_adj_bps = mean_bps - cost_bps

        candidate = CandidateHypothesis(spec=spec, search_spec_name="evaluation")
        checked = FeasibilityCheckedHypothesis(
            candidate=candidate,
            feasibility=FeasibilityResult(valid=True),
        )
        evaluated = EvaluatedHypothesis(
            checked=checked,
            valid=True,
            metrics={
                "n": n,
                **split_counts,
                "mean_return_bps": round(mean_bps, 4),
                "t_stat": round(t_stat, 4),
                "sharpe": round(sharpe, 4),
                "hit_rate": round(hit_rate, 4),
                "cost_adjusted_return_bps": round(cost_adj_bps, 4),
                "mae_mean_bps": round(mae_mean * 10_000.0, 4),
                "mfe_mean_bps": round(mfe_mean * 10_000.0, 4),
                "robustness_score": round(robustness, 4),
                "stress_score": round(stress_score, 4),
                "kill_switch_count": ks_count,
                "capacity_proxy": capacity,
            },
        )
        row = evaluated.to_record()
        rows.append({column: row.get(column) for column in METRICS_COLUMNS})

    df = pd.DataFrame(rows, columns=METRICS_COLUMNS)
    log.info(
        "Evaluated %d hypotheses: %d valid, %d below min_sample_size=%d",
        len(hypotheses),
        int(df["valid"].sum()),
        int((~df["valid"]).sum()),
        min_sample_size,
    )
    return df
