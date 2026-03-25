from __future__ import annotations

import json
from typing import Callable, Optional

import numpy as np
import pandas as pd

from project.research import discovery
from project.research.gating import build_event_return_frame
from project.research.validation.falsification import generate_placebo_events
from project.research.validation.regime_tests import evaluate_by_regime
from project.research.validation import (
    apply_multiple_testing,
    assign_split_labels,
    assign_test_families,
    estimate_effect_from_frame,
    resolve_split_scheme,
)
from project.research.multiplicity import simes_p_value
from project.research.gating import bh_adjust


def _json_array(values: list[object]) -> str:
    return json.dumps(values, separators=(",", ":"))


def _split_labels(frame: pd.DataFrame) -> pd.Series:
    if frame.empty:
        return pd.Series(dtype=object)
    if "split_label" not in frame.columns:
        return pd.Series(["train"] * len(frame), index=frame.index, dtype=object)
    return frame["split_label"].astype(str).str.strip().str.lower()


def _evaluation_mask(split_labels: pd.Series) -> pd.Series:
    if split_labels.empty:
        return pd.Series(dtype=bool)
    evaluation_mask = split_labels.isin(["validation", "test"])
    if not bool(evaluation_mask.any()):
        evaluation_mask = split_labels != "train"
    if not bool(evaluation_mask.any()):
        evaluation_mask = pd.Series(True, index=split_labels.index)
    return evaluation_mask.astype(bool)


def _split_frame(frame: pd.DataFrame, label: str) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=list(frame.columns))
    labels = _split_labels(frame)
    return frame.loc[labels == str(label).strip().lower()].copy()


def _float_mean(frame: pd.DataFrame, column: str) -> float:
    if frame.empty or column not in frame.columns:
        return 0.0
    series = pd.to_numeric(frame[column], errors="coerce").dropna()
    return float(series.mean()) if not series.empty else 0.0


def _numeric_series(frame: pd.DataFrame, column: str, default: float = np.nan) -> pd.Series:
    if frame.empty:
        return pd.Series(dtype=float)
    if column not in frame.columns:
        return pd.Series([default] * len(frame), index=frame.index, dtype=float)
    return pd.to_numeric(frame[column], errors="coerce")


def _t_stat(frame: pd.DataFrame, column: str = "forward_return") -> float:
    if frame.empty or column not in frame.columns:
        return 0.0
    series = pd.to_numeric(frame[column], errors="coerce").dropna()
    if len(series) < 2:
        return 0.0
    std = float(series.std(ddof=1) or 0.0)
    if std <= 0.0:
        return 0.0
    return float(series.mean() / (std / np.sqrt(len(series))))


def _regime_labels(frame: pd.DataFrame) -> pd.Series:
    if frame.empty:
        return pd.Series(dtype=object)
    for column in ("regime", "vol_regime", "liquidity_state", "market_liquidity_state", "depth_state"):
        if column in frame.columns:
            values = frame[column].astype("object").where(frame[column].notna(), "unknown")
            return values.astype(str)
    return pd.Series(["unknown"] * len(frame), index=frame.index, dtype=object)


def _random_entry_events(events_df: pd.DataFrame, features_df: Optional[pd.DataFrame]) -> pd.DataFrame:
    if events_df.empty or features_df is None or features_df.empty or "timestamp" not in features_df.columns:
        return pd.DataFrame()
    sampled_ts = pd.to_datetime(features_df["timestamp"], utc=True, errors="coerce").dropna()
    sampled_ts = sampled_ts.drop_duplicates().sort_values()
    if sampled_ts.empty:
        return pd.DataFrame()
    n = min(len(events_df), len(sampled_ts))
    sampled = sampled_ts.sample(n=n, random_state=0).sort_values().reset_index(drop=True)
    out = events_df.iloc[:n].copy().reset_index(drop=True)
    if "timestamp" in out.columns:
        out["timestamp"] = sampled.values
    if "enter_ts" in out.columns:
        out["enter_ts"] = sampled.values
    return out


def _placebo_pass(observed_frame: pd.DataFrame, placebo_frame: pd.DataFrame) -> bool:
    observed = pd.to_numeric(observed_frame.get("forward_return"), errors="coerce").dropna()
    placebo = pd.to_numeric(placebo_frame.get("forward_return"), errors="coerce").dropna()
    if observed.empty or placebo.empty:
        return False
    observed_mean = float(observed.mean())
    placebo_mean = float(placebo.mean())
    observed_scale = max(abs(observed_mean) * 0.5, 1e-4)
    if np.sign(observed_mean) != 0.0 and np.sign(placebo_mean) != np.sign(observed_mean):
        return True
    return bool(abs(placebo_mean) < observed_scale)


def _build_confirmatory_evidence(
    *,
    return_frame: pd.DataFrame,
    delayed_frame: pd.DataFrame,
    shift_placebo_frame: pd.DataFrame,
    random_placebo_frame: pd.DataFrame,
    direction_placebo_frame: pd.DataFrame,
) -> dict[str, object]:
    if return_frame.empty:
        return {
            "returns_oos_combined": "[]",
            "pnl_series": "[]",
            "returns_raw": "[]",
            "costs_bps_series": "[]",
            "timestamps": "[]",
            "fold_scores": "[]",
            "validation_fold_scores": "[]",
            "regime_counts": "{}",
            "mean_train_return": 0.0,
            "mean_validation_return": 0.0,
            "mean_test_return": 0.0,
            "train_t_stat": 0.0,
            "val_t_stat": 0.0,
            "oos1_t_stat": 0.0,
            "test_t_stat": 0.0,
            "sign_consistency": 0.0,
            "stability_score": 0.0,
            "gate_stability": False,
            "gate_delay_robustness": False,
            "gate_delayed_entry_stress": False,
            "gate_regime_stability": False,
            "pass_shift_placebo": False,
            "pass_random_entry_placebo": False,
            "pass_direction_reversal_placebo": False,
            "control_pass_rate": 1.0,
        }

    labels = _split_labels(return_frame)
    eval_mask = _evaluation_mask(labels)
    eval_frame = return_frame.loc[eval_mask].copy()
    train_frame = _split_frame(return_frame, "train")
    validation_frame = _split_frame(return_frame, "validation")
    test_frame = _split_frame(return_frame, "test")

    returns_oos = _numeric_series(eval_frame, "forward_return").dropna()
    pnl_series = returns_oos.tolist()
    returns_raw = (
        _numeric_series(eval_frame, "forward_return_raw")
        if "forward_return_raw" in eval_frame.columns
        else _numeric_series(eval_frame, "forward_return")
    ).dropna()
    costs_bps = (_numeric_series(eval_frame, "cost_return", default=0.0).fillna(0.0) * 1e4).tolist()
    if "event_ts" in eval_frame.columns:
        event_ts = pd.to_datetime(eval_frame["event_ts"], utc=True, errors="coerce").dropna()
        timestamps = [ts.isoformat() for ts in event_ts.tolist()]
    else:
        timestamps = []

    split_means = {
        "train": _float_mean(train_frame, "forward_return"),
        "validation": _float_mean(validation_frame, "forward_return"),
        "test": _float_mean(test_frame, "forward_return"),
    }
    fold_scores = [
        float(value)
        for value in (split_means["train"], split_means["validation"], split_means["test"])
        if np.isfinite(value)
    ]
    validation_fold_scores = [
        float(value)
        for value in (split_means["validation"], split_means["test"])
        if np.isfinite(value)
    ]
    eval_mean = float(returns_oos.mean()) if not returns_oos.empty else 0.0
    base_sign = np.sign(eval_mean) if abs(eval_mean) > 1e-12 else 0.0
    non_zero_folds = [np.sign(value) for value in fold_scores if abs(float(value)) > 1e-12]
    sign_consistency = (
        float(np.mean([sign == base_sign for sign in non_zero_folds]))
        if non_zero_folds and base_sign != 0.0
        else 0.0
    )
    eval_std = float(returns_oos.std(ddof=1)) if len(returns_oos) > 1 else 0.0
    stability_score = (
        float(sign_consistency * (abs(eval_mean) / max(eval_std, 1e-8)))
        if abs(eval_mean) > 1e-12
        else 0.0
    )
    gate_stability = bool(sign_consistency >= 0.5 and abs(eval_mean) > 1e-12)

    delayed_labels = _split_labels(delayed_frame)
    delayed_eval = delayed_frame.loc[_evaluation_mask(delayed_labels)].copy()
    delayed_mean = _float_mean(delayed_eval, "forward_return")
    gate_delay_robustness = bool(
        abs(delayed_mean) > 1e-12
        and base_sign != 0.0
        and np.sign(delayed_mean) == base_sign
        and abs(delayed_mean) >= abs(eval_mean) * 0.25
    )

    regime_series = _regime_labels(eval_frame)
    regime_frame = eval_frame.copy()
    regime_frame["regime"] = regime_series.values if not regime_series.empty else []
    regime_info = evaluate_by_regime(regime_frame, value_col="forward_return", regime_col="regime")
    regime_counts = {
        str(regime): int(details.get("n_obs", 0))
        for regime, details in dict(regime_info.get("by_regime", {})).items()
    }
    worst_regime_estimate = float(regime_info.get("worst_regime_estimate", 0.0) or 0.0)
    gate_regime_stability = bool(
        not bool(regime_info.get("regime_flip_flag", False))
        and (
            base_sign == 0.0
            or abs(worst_regime_estimate) <= 1e-12
            or np.sign(worst_regime_estimate) == base_sign
        )
    )

    shift_pass = _placebo_pass(eval_frame, shift_placebo_frame)
    random_pass = _placebo_pass(eval_frame, random_placebo_frame)
    direction_pass = _placebo_pass(eval_frame, direction_placebo_frame)
    control_pass_rate = float(np.mean([not shift_pass, not random_pass, not direction_pass]))

    return {
        "returns_oos_combined": _json_array([float(value) for value in returns_oos.tolist()]),
        "pnl_series": _json_array([float(value) for value in pnl_series]),
        "returns_raw": _json_array([float(value) for value in returns_raw.tolist()]),
        "costs_bps_series": _json_array([float(value) for value in costs_bps]),
        "timestamps": _json_array(timestamps),
        "fold_scores": _json_array([float(value) for value in fold_scores]),
        "validation_fold_scores": _json_array([float(value) for value in validation_fold_scores]),
        "regime_counts": json.dumps(regime_counts, sort_keys=True),
        "mean_train_return": split_means["train"],
        "mean_validation_return": split_means["validation"],
        "mean_test_return": split_means["test"],
        "train_t_stat": _t_stat(train_frame),
        "val_t_stat": _t_stat(validation_frame),
        "oos1_t_stat": _t_stat(eval_frame),
        "test_t_stat": _t_stat(test_frame),
        "sign_consistency": sign_consistency,
        "stability_score": stability_score,
        "gate_stability": gate_stability,
        "gate_delay_robustness": gate_delay_robustness,
        "gate_delayed_entry_stress": gate_delay_robustness,
        "gate_regime_stability": gate_regime_stability,
        "pass_shift_placebo": shift_pass,
        "pass_random_entry_placebo": random_pass,
        "pass_direction_reversal_placebo": direction_pass,
        "control_pass_rate": control_pass_rate,
    }


def split_and_score_candidates(
    candidates: pd.DataFrame,
    events_df: pd.DataFrame,
    *,
    horizon_bars: int,
    split_scheme_id: str,
    purge_bars: int,
    embargo_bars: int,
    bar_duration_minutes: int,
    features_df: Optional[pd.DataFrame] = None,
    entry_lag_bars: int = 1,
    shift_labels_k: int = 0,
    cost_estimate: Optional[object] = None,
    alpha: float = 0.05,
    build_event_return_frame_fn: Callable[..., pd.DataFrame] = build_event_return_frame,
    estimate_effect_from_frame_fn: Callable[..., object] = estimate_effect_from_frame,
) -> pd.DataFrame:
    if candidates.empty:
        return candidates.copy()

    working = events_df.copy()
    resolved_split_scheme_id, train_frac, validation_frac = resolve_split_scheme(split_scheme_id)
    time_col = (
        "enter_ts"
        if "enter_ts" in working.columns
        else ("timestamp" if "timestamp" in working.columns else None)
    )
    if time_col is None:
        out = candidates.copy()
        out["p_value"] = np.nan
        out["p_value_raw"] = np.nan
        out["p_value_for_fdr"] = np.nan
        out["estimate_bps"] = np.nan
        out["stderr_bps"] = np.nan
        out["ci_low_bps"] = np.nan
        out["ci_high_bps"] = np.nan
        out["n_obs"] = 0
        out["n_clusters"] = 0
        out["split_scheme_id"] = resolved_split_scheme_id
        return out

    split_plan_id = (
        f"TVT_{int(round(train_frac * 100))}_{int(round(validation_frac * 100))}_"
        f"{100 - int(round((train_frac + validation_frac) * 100))}"
    )
    current_split_plan_id = (
        str(working.get("split_plan_id", pd.Series(dtype=object)).astype(str).iloc[0])
        if "split_plan_id" in working.columns and not working.empty
        else ""
    )
    if (
        "split_label" not in working.columns
        or working["split_label"].isna().all()
        or current_split_plan_id != split_plan_id
    ):
        working = assign_split_labels(
            working,
            time_col=time_col,
            train_frac=train_frac,
            validation_frac=validation_frac,
            embargo_bars=int(embargo_bars),
            purge_bars=int(purge_bars),
            bar_duration_minutes=int(bar_duration_minutes),
            split_col="split_label",
        )

    out = candidates.copy()
    out["split_scheme_id"] = str(resolved_split_scheme_id)
    out["split_plan_id"] = (
        str(working["split_plan_id"].iloc[0])
        if "split_plan_id" in working.columns and not working.empty
        else ""
    )
    out["purge_bars_used"] = int(purge_bars)
    out["embargo_bars_used"] = int(embargo_bars)
    out["bar_duration_minutes"] = int(bar_duration_minutes)
    out["resolved_train_frac"] = float(train_frac)
    out["resolved_validation_frac"] = float(validation_frac)
    if cost_estimate is not None:
        out["resolved_cost_bps"] = float(cost_estimate.cost_bps)
        out["fee_bps_per_side"] = float(cost_estimate.fee_bps_per_side)
        out["slippage_bps_per_fill"] = float(cost_estimate.slippage_bps_per_fill)
        out["avg_dynamic_cost_bps"] = float(cost_estimate.avg_dynamic_cost_bps)
        out["cost_input_coverage"] = float(cost_estimate.cost_input_coverage)
        out["cost_model_valid"] = bool(cost_estimate.cost_model_valid)
        out["cost_model_source"] = str(cost_estimate.cost_model_source)
        out["cost_regime_multiplier"] = float(cost_estimate.regime_multiplier)
    else:
        out["resolved_cost_bps"] = 0.0
        out["fee_bps_per_side"] = 0.0
        out["slippage_bps_per_fill"] = 0.0
        out["avg_dynamic_cost_bps"] = 0.0
        out["cost_input_coverage"] = 0.0
        out["cost_model_valid"] = True
        out["cost_model_source"] = "static"
        out["cost_regime_multiplier"] = 1.0

    for idx, row in out.iterrows():
        row_horizon_bars = int(
            pd.to_numeric(row.get("horizon_bars", horizon_bars), errors="coerce") or horizon_bars
        )
        row_horizon = str(row.get("horizon", discovery.bars_to_timeframe(row_horizon_bars)))
        return_frame = build_event_return_frame_fn(
            working,
            features_df if features_df is not None else pd.DataFrame(),
            rule=str(row.get("rule_template", "continuation")),
            horizon=row_horizon,
            canonical_family=str(row.get("event_type", "")).split("_")[0],
            shift_labels_k=int(shift_labels_k),
            entry_lag_bars=int(entry_lag_bars),
            horizon_bars_override=row_horizon_bars,
            stop_loss_bps=pd.to_numeric(row.get("stop_loss_bps"), errors="coerce"),
            take_profit_bps=pd.to_numeric(row.get("take_profit_bps"), errors="coerce"),
            stop_loss_atr_multipliers=pd.to_numeric(
                row.get("stop_loss_atr_multipliers"), errors="coerce"
            ),
            take_profit_atr_multipliers=pd.to_numeric(
                row.get("take_profit_atr_multipliers"), errors="coerce"
            ),
            cost_bps=float(cost_estimate.cost_bps) if cost_estimate is not None else 0.0,
            direction_override=pd.to_numeric(row.get("direction"), errors="coerce"),
        )
        delayed_frame = build_event_return_frame_fn(
            working,
            features_df if features_df is not None else pd.DataFrame(),
            rule=str(row.get("rule_template", "continuation")),
            horizon=row_horizon,
            canonical_family=str(row.get("event_type", "")).split("_")[0],
            shift_labels_k=int(shift_labels_k),
            entry_lag_bars=int(entry_lag_bars) + 1,
            horizon_bars_override=row_horizon_bars,
            stop_loss_bps=pd.to_numeric(row.get("stop_loss_bps"), errors="coerce"),
            take_profit_bps=pd.to_numeric(row.get("take_profit_bps"), errors="coerce"),
            stop_loss_atr_multipliers=pd.to_numeric(
                row.get("stop_loss_atr_multipliers"), errors="coerce"
            ),
            take_profit_atr_multipliers=pd.to_numeric(
                row.get("take_profit_atr_multipliers"), errors="coerce"
            ),
            cost_bps=float(cost_estimate.cost_bps) if cost_estimate is not None else 0.0,
            direction_override=pd.to_numeric(row.get("direction"), errors="coerce"),
        )
        time_col = (
            "enter_ts" if "enter_ts" in working.columns else ("timestamp" if "timestamp" in working.columns else "timestamp")
        )
        shift_placebo_events = (
            generate_placebo_events(working, time_col=time_col, shift_bars=1)
            if not working.empty and time_col in working.columns
            else pd.DataFrame()
        )
        shift_placebo_frame = build_event_return_frame_fn(
            shift_placebo_events,
            features_df if features_df is not None else pd.DataFrame(),
            rule=str(row.get("rule_template", "continuation")),
            horizon=row_horizon,
            canonical_family=str(row.get("event_type", "")).split("_")[0],
            shift_labels_k=int(shift_labels_k),
            entry_lag_bars=int(entry_lag_bars),
            horizon_bars_override=row_horizon_bars,
            stop_loss_bps=pd.to_numeric(row.get("stop_loss_bps"), errors="coerce"),
            take_profit_bps=pd.to_numeric(row.get("take_profit_bps"), errors="coerce"),
            stop_loss_atr_multipliers=pd.to_numeric(
                row.get("stop_loss_atr_multipliers"), errors="coerce"
            ),
            take_profit_atr_multipliers=pd.to_numeric(
                row.get("take_profit_atr_multipliers"), errors="coerce"
            ),
            cost_bps=float(cost_estimate.cost_bps) if cost_estimate is not None else 0.0,
            direction_override=pd.to_numeric(row.get("direction"), errors="coerce"),
        )
        random_placebo_frame = build_event_return_frame_fn(
            _random_entry_events(working, features_df),
            features_df if features_df is not None else pd.DataFrame(),
            rule=str(row.get("rule_template", "continuation")),
            horizon=row_horizon,
            canonical_family=str(row.get("event_type", "")).split("_")[0],
            shift_labels_k=int(shift_labels_k),
            entry_lag_bars=int(entry_lag_bars),
            horizon_bars_override=row_horizon_bars,
            stop_loss_bps=pd.to_numeric(row.get("stop_loss_bps"), errors="coerce"),
            take_profit_bps=pd.to_numeric(row.get("take_profit_bps"), errors="coerce"),
            stop_loss_atr_multipliers=pd.to_numeric(
                row.get("stop_loss_atr_multipliers"), errors="coerce"
            ),
            take_profit_atr_multipliers=pd.to_numeric(
                row.get("take_profit_atr_multipliers"), errors="coerce"
            ),
            cost_bps=float(cost_estimate.cost_bps) if cost_estimate is not None else 0.0,
            direction_override=pd.to_numeric(row.get("direction"), errors="coerce"),
        )
        direction_placebo_frame = build_event_return_frame_fn(
            working,
            features_df if features_df is not None else pd.DataFrame(),
            rule=str(row.get("rule_template", "continuation")),
            horizon=row_horizon,
            canonical_family=str(row.get("event_type", "")).split("_")[0],
            shift_labels_k=int(shift_labels_k),
            entry_lag_bars=int(entry_lag_bars),
            horizon_bars_override=row_horizon_bars,
            stop_loss_bps=pd.to_numeric(row.get("stop_loss_bps"), errors="coerce"),
            take_profit_bps=pd.to_numeric(row.get("take_profit_bps"), errors="coerce"),
            stop_loss_atr_multipliers=pd.to_numeric(
                row.get("stop_loss_atr_multipliers"), errors="coerce"
            ),
            take_profit_atr_multipliers=pd.to_numeric(
                row.get("take_profit_atr_multipliers"), errors="coerce"
            ),
            cost_bps=float(cost_estimate.cost_bps) if cost_estimate is not None else 0.0,
            direction_override=-pd.to_numeric(row.get("direction"), errors="coerce"),
        )
        if return_frame.empty:
            eval_frame = pd.DataFrame(columns=["forward_return", "cluster_day"])
            train_frame = pd.DataFrame(columns=["forward_return", "cluster_day"])
            split_labels = pd.Series(dtype=object)
        else:
            split_labels = _split_labels(return_frame)
            evaluation_mask = _evaluation_mask(split_labels)
            eval_frame = return_frame.loc[
                evaluation_mask, ["forward_return", "cluster_day"]
            ].dropna(subset=["forward_return"])
            train_frame = return_frame.loc[
                split_labels == "train", ["forward_return", "cluster_day"]
            ].dropna(subset=["forward_return"])
        estimate = estimate_effect_from_frame_fn(
            eval_frame,
            value_col="forward_return",
            cluster_col="cluster_day",
            alpha=alpha,
            use_bootstrap_ci=True,
            n_boot=400,
        )
        out.at[idx, "estimate"] = float(estimate.estimate)
        out.at[idx, "estimate_bps"] = float(estimate.estimate * 1e4)
        out.at[idx, "stderr"] = float(estimate.stderr)
        out.at[idx, "stderr_bps"] = float(estimate.stderr * 1e4)
        out.at[idx, "ci_low"] = float(estimate.ci_low)
        out.at[idx, "ci_high"] = float(estimate.ci_high)
        out.at[idx, "ci_low_bps"] = float(estimate.ci_low * 1e4)
        out.at[idx, "ci_high_bps"] = float(estimate.ci_high * 1e4)
        out.at[idx, "p_value"] = float(estimate.p_value_raw)
        out.at[idx, "p_value_raw"] = float(estimate.p_value_raw)
        out.at[idx, "p_value_for_fdr"] = float(estimate.p_value_raw)
        out.at[idx, "n_obs"] = int(estimate.n_obs)
        out.at[idx, "sample_size"] = int(estimate.n_obs)
        out.at[idx, "n_clusters"] = int(estimate.n_clusters)
        out.at[idx, "estimation_method"] = str(estimate.method)
        out.at[idx, "cluster_col"] = str(estimate.cluster_col or "cluster_day")
        out.at[idx, "effect_split_basis"] = (
            "validation_test"
            if not eval_frame.empty and bool(split_labels.isin(["validation", "test"]).any())
            else "all"
        )
        out.at[idx, "validation_n_obs"] = int((split_labels == "validation").sum())
        out.at[idx, "test_n_obs"] = int((split_labels == "test").sum())
        out.at[idx, "train_n_obs"] = int((split_labels == "train").sum())
        out.at[idx, "expectancy"] = (
            float(train_frame["forward_return"].mean()) if not train_frame.empty else 0.0
        )
        out.at[idx, "expectancy_bps"] = float(out.at[idx, "expectancy"] * 1e4)
        out.at[idx, "t_stat"] = (
            float(
                eval_frame["forward_return"].mean()
                / (eval_frame["forward_return"].std(ddof=1) / np.sqrt(len(eval_frame)))
            )
            if len(eval_frame) > 1 and float(eval_frame["forward_return"].std(ddof=1) or 0.0) > 0.0
            else 0.0
        )
        confirmatory = _build_confirmatory_evidence(
            return_frame=return_frame,
            delayed_frame=delayed_frame,
            shift_placebo_frame=shift_placebo_frame,
            random_placebo_frame=random_placebo_frame,
            direction_placebo_frame=direction_placebo_frame,
        )
        for column, value in confirmatory.items():
            out.at[idx, column] = value
    return out


def apply_validation_multiple_testing(candidates_df: pd.DataFrame) -> pd.DataFrame:
    if candidates_df.empty:
        return candidates_df.copy()
    out = candidates_df.copy()
    out["event_family"] = out.get("event_type", "").astype(str).str.split("_").str[0]
    out = assign_test_families(
        out,
        family_cols=["run_id", "event_family", "horizon"],
        out_col="correction_family_id",
    )
    out = apply_multiple_testing(
        out,
        p_col="p_value_raw",
        family_col="correction_family_id",
        method="bh",
        out_col="p_value_adj",
    )
    out = apply_multiple_testing(
        out,
        p_col="p_value_raw",
        family_col="correction_family_id",
        method="by",
        out_col="p_value_adj_by",
    )
    out = apply_multiple_testing(
        out,
        p_col="p_value_raw",
        family_col="correction_family_id",
        method="holm",
        out_col="p_value_adj_holm",
    )
    out["correction_method"] = "bh"
    out["q_value"] = pd.to_numeric(out.get("p_value_adj", np.nan), errors="coerce")
    out["q_value_by"] = pd.to_numeric(out.get("p_value_adj_by", np.nan), errors="coerce")
    out["q_value_family"] = out["q_value"]
    out["family_cluster_id"] = (
        out.get("symbol", pd.Series("", index=out.index)).astype(str).str.strip().str.upper()
        + "_"
        + out.get("event_type", pd.Series("", index=out.index)).astype(str).str.strip()
        + "_"
        + out.get("horizon", pd.Series("", index=out.index)).astype(str).str.strip()
        + "_"
        + out.get("state_id", pd.Series("", index=out.index)).astype(str).str.strip()
    )
    p_vals = pd.to_numeric(out.get("p_value_raw", np.nan), errors="coerce")
    eligible = out.loc[p_vals.notna()].copy()
    if not eligible.empty:
        cluster_simes = (
            eligible.groupby("family_cluster_id")["p_value_raw"]
            .apply(lambda s: simes_p_value(pd.to_numeric(s, errors="coerce")))
            .rename("p_value_cluster")
            .reset_index()
        )
        cluster_simes["q_value_cluster"] = bh_adjust(
            cluster_simes["p_value_cluster"].fillna(1.0).to_numpy()
        )
        p_mapping = dict(zip(cluster_simes["family_cluster_id"], cluster_simes["p_value_cluster"]))
        q_mapping = dict(zip(cluster_simes["family_cluster_id"], cluster_simes["q_value_cluster"]))
        out["p_value_cluster"] = out["family_cluster_id"].map(p_mapping)
        out["q_value_cluster"] = out["family_cluster_id"].map(q_mapping)
    else:
        out["p_value_cluster"] = np.nan
        out["q_value_cluster"] = np.nan
    out["is_discovery"] = out["q_value"].fillna(1.0) <= 0.10
    out["is_discovery_by"] = out["q_value_by"].fillna(1.0) <= 0.10
    out["is_discovery_cluster"] = out["q_value_cluster"].fillna(1.0) <= 0.10
    out["gate_multiplicity"] = out["is_discovery"].astype(bool)
    return out
