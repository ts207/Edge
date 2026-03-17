from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from project import PROJECT_ROOT
from project.core.config import get_data_root
from project.core.execution_costs import resolve_execution_costs
from project.core.timeframes import normalize_timeframe, timeframe_to_minutes
from project.events.event_specs import EVENT_REGISTRY_SPECS
from project.io.utils import ensure_dir
from project.research.cost_calibration import CandidateCostEstimate, ToBRegimeCostCalibrator
from project.research import discovery
from project.research.gating import build_event_return_frame
from project.research.hypothesis_registry import Hypothesis, HypothesisRegistry
from project.research.phase2 import load_features, prepare_events_dataframe
from project.research.services.pathing import phase2_event_out_dir
from project.research.services.phase2_diagnostics import (
    build_prepare_events_diagnostics,
    get_prepare_events_diagnostics,
    split_counts as phase2_split_counts,
)
from project.research.services.reporting_service import write_candidate_reports
from project.research.validation import (
    apply_multiple_testing,
    assign_split_labels,
    assign_test_families,
    estimate_effect_from_frame,
    resolve_split_scheme,
)
from project.specs.manifest import finalize_manifest, start_manifest

ResolvedCandidateCostEstimate = CandidateCostEstimate
DEFAULT_SAMPLE_QUALITY_POLICY: Dict[str, Dict[str, int]] = {
    "standard": {
        "min_validation_n_obs": 2,
        "min_test_n_obs": 2,
        "min_total_n_obs": 10,
    },
    "synthetic": {
        "min_validation_n_obs": 1,
        "min_test_n_obs": 1,
        "min_total_n_obs": 4,
    },
}

@dataclass(frozen=True)
class CandidateDiscoveryConfig:
    run_id: str
    symbols: tuple[str, ...]
    config_paths: tuple[str, ...]
    data_root: Path
    event_type: str
    timeframe: str
    horizon_bars: int
    out_dir: Optional[Path]
    run_mode: str
    split_scheme_id: str
    embargo_bars: int
    purge_bars: int
    train_only_lambda_used: float
    discovery_profile: str
    candidate_generation_method: str
    concept_file: Optional[str]
    entry_lag_bars: int
    shift_labels_k: int
    fees_bps: Optional[float]
    slippage_bps: Optional[float]
    cost_bps: Optional[float]
    cost_calibration_mode: str
    cost_min_tob_coverage: float
    cost_tob_tolerance_minutes: int
    candidate_origin_run_id: Optional[str]
    frozen_spec_hash: Optional[str]
    templates: Optional[tuple[str, ...]] = None
    horizons: Optional[tuple[str, ...]] = None
    directions: Optional[tuple[str, ...]] = None
    entry_lags: Optional[tuple[int, ...]] = None
    program_id: Optional[str] = None
    search_budget: Optional[int] = None
    experiment_config: Optional[str] = None
    registry_root: Optional[Path] = None
    min_validation_n_obs: Optional[int] = None
    min_test_n_obs: Optional[int] = None
    min_total_n_obs: Optional[int] = None

    def resolved_out_dir(self) -> Path:
        if self.out_dir is not None:
            return self.out_dir
        return phase2_event_out_dir(
            data_root=self.data_root,
            run_id=self.run_id,
            event_type=self.event_type,
            timeframe=self.timeframe,
        )

    def manifest_params(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "symbols": ",".join(self.symbols),
            "config": list(self.config_paths),
            "data_root": str(self.data_root),
            "event_type": self.event_type,
            "templates": list(self.templates) if self.templates else None,
            "horizons": list(self.horizons) if self.horizons else None,
            "directions": list(self.directions) if self.directions else None,
            "entry_lags": list(self.entry_lags) if self.entry_lags else None,
            "program_id": self.program_id,
            "search_budget": self.search_budget,
            "timeframe": self.timeframe,
            "horizon_bars": self.horizon_bars,
            "out_dir": str(self.out_dir) if self.out_dir is not None else None,
            "run_mode": self.run_mode,
            "split_scheme_id": self.split_scheme_id,
            "embargo_bars": self.embargo_bars,
            "purge_bars": self.purge_bars,
            "train_only_lambda_used": self.train_only_lambda_used,
            "discovery_profile": self.discovery_profile,
            "candidate_generation_method": self.candidate_generation_method,
            "concept_file": self.concept_file,
            "entry_lag_bars": self.entry_lag_bars,
            "shift_labels_k": self.shift_labels_k,
            "fees_bps": self.fees_bps,
            "slippage_bps": self.slippage_bps,
            "cost_bps": self.cost_bps,
            "cost_calibration_mode": self.cost_calibration_mode,
            "cost_min_tob_coverage": self.cost_min_tob_coverage,
            "cost_tob_tolerance_minutes": self.cost_tob_tolerance_minutes,
            "candidate_origin_run_id": self.candidate_origin_run_id,
            "frozen_spec_hash": self.frozen_spec_hash,
            "experiment_config": self.experiment_config,
            "registry_root": str(self.registry_root) if self.registry_root is not None else None,
            "min_validation_n_obs": None if self.min_validation_n_obs is None else int(self.min_validation_n_obs),
            "min_test_n_obs": None if self.min_test_n_obs is None else int(self.min_test_n_obs),
            "min_total_n_obs": None if self.min_total_n_obs is None else int(self.min_total_n_obs),
        }


@dataclass
class CandidateDiscoveryResult:
    exit_code: int
    output_dir: Path
    combined_candidates: pd.DataFrame = field(default_factory=pd.DataFrame)
    symbol_candidates: Dict[str, pd.DataFrame] = field(default_factory=dict)
    manifest: Dict[str, Any] = field(default_factory=dict)


def _sample_quality_summary(df: pd.DataFrame) -> Dict[str, Any]:
    if df.empty:
        return {
            "candidates_total": 0,
            "zero_validation_rows": 0,
            "zero_test_rows": 0,
            "zero_eval_rows": 0,
            "median_validation_n_obs": 0.0,
            "median_test_n_obs": 0.0,
            "median_n_obs": 0.0,
        }
    validation = pd.to_numeric(df.get("validation_n_obs", 0), errors="coerce").fillna(0)
    test = pd.to_numeric(df.get("test_n_obs", 0), errors="coerce").fillna(0)
    n_obs = pd.to_numeric(df.get("n_obs", 0), errors="coerce").fillna(0)
    return {
        "candidates_total": int(len(df)),
        "zero_validation_rows": int((validation <= 0).sum()),
        "zero_test_rows": int((test <= 0).sum()),
        "zero_eval_rows": int(((validation <= 0) & (test <= 0)).sum()),
        "median_validation_n_obs": float(validation.median()) if not validation.empty else 0.0,
        "median_test_n_obs": float(test.median()) if not test.empty else 0.0,
        "median_n_obs": float(n_obs.median()) if not n_obs.empty else 0.0,
    }


def _survivor_quality_summary(df: pd.DataFrame) -> Dict[str, Any]:
    if df.empty:
        return {
            "survivors_total": 0,
            "median_q_value": 1.0,
            "median_q_value_by": 1.0,
            "median_estimate_bps": 0.0,
            "median_cost_bps": 0.0,
            "families_with_survivors": 0,
        }
    survivors = df[pd.to_numeric(df.get("is_discovery", False), errors="coerce").fillna(0).astype(bool)].copy()
    if survivors.empty:
        return {
            "survivors_total": 0,
            "median_q_value": 1.0,
            "median_q_value_by": 1.0,
            "median_estimate_bps": 0.0,
            "median_cost_bps": 0.0,
            "families_with_survivors": 0,
        }
    return {
        "survivors_total": int(len(survivors)),
        "median_q_value": float(pd.to_numeric(survivors.get("q_value", 1.0), errors="coerce").fillna(1.0).median()),
        "median_q_value_by": float(pd.to_numeric(survivors.get("q_value_by", 1.0), errors="coerce").fillna(1.0).median()),
        "median_estimate_bps": float(pd.to_numeric(survivors.get("estimate_bps", 0.0), errors="coerce").fillna(0.0).median()),
        "median_cost_bps": float(pd.to_numeric(survivors.get("resolved_cost_bps", 0.0), errors="coerce").fillna(0.0).median()),
        "families_with_survivors": int(survivors["family_id"].nunique()) if "family_id" in survivors.columns else 0,
    }


def _build_false_discovery_diagnostics(combined: pd.DataFrame) -> Dict[str, Any]:
    gate_rejections = pd.to_numeric(
        combined.get("rejected_by_sample_quality", pd.Series(False, index=combined.index)),
        errors="coerce",
    ).fillna(0).astype(bool)
    survivors_before_gate = pd.to_numeric(
        combined.get("is_discovery_pre_sample_quality", pd.Series(False, index=combined.index)),
        errors="coerce",
    ).fillna(0).astype(bool)
    fail_reason_counts = (
        combined.loc[gate_rejections, "sample_quality_fail_reason"].astype(str).value_counts().to_dict()
        if "sample_quality_fail_reason" in combined.columns and bool(gate_rejections.any())
        else {}
    )
    if combined.empty:
        return {
            "global": {
                "candidates_total": 0,
                "symbols_total": 0,
                "survivors_total": 0,
                "families_total": 0,
            },
            "sample_quality": _sample_quality_summary(combined),
            "sample_quality_gate": {
                "survivors_before_gate": 0,
                "survivors_after_gate": 0,
                "rejected_by_sample_quality_gate": 0,
                "fail_reason_counts": {},
            },
            "survivor_quality": _survivor_quality_summary(combined),
            "by_symbol": {},
        }

    by_symbol: Dict[str, Any] = {}
    for symbol, sym_df in combined.groupby("symbol", sort=True):
        by_symbol[str(symbol)] = {
            "sample_quality": _sample_quality_summary(sym_df),
            "sample_quality_gate": {
                "survivors_before_gate": int(
                    pd.to_numeric(
                        sym_df.get("is_discovery_pre_sample_quality", pd.Series(False, index=sym_df.index)),
                        errors="coerce",
                    ).fillna(0).astype(bool).sum()
                ),
                "survivors_after_gate": int(pd.to_numeric(sym_df.get("is_discovery", False), errors="coerce").fillna(0).astype(bool).sum()),
                "rejected_by_sample_quality_gate": int(
                    pd.to_numeric(
                        sym_df.get("rejected_by_sample_quality", pd.Series(False, index=sym_df.index)),
                        errors="coerce",
                    ).fillna(0).astype(bool).sum()
                ),
                "fail_reason_counts": (
                    sym_df.loc[
                        pd.to_numeric(
                            sym_df.get("rejected_by_sample_quality", pd.Series(False, index=sym_df.index)),
                            errors="coerce",
                        ).fillna(0).astype(bool),
                        "sample_quality_fail_reason",
                    ].astype(str).value_counts().to_dict()
                    if "sample_quality_fail_reason" in sym_df.columns
                    else {}
                ),
            },
            "survivor_quality": _survivor_quality_summary(sym_df),
        }

    return {
        "global": {
            "candidates_total": int(len(combined)),
            "symbols_total": int(combined["symbol"].nunique()) if "symbol" in combined.columns else 0,
            "survivors_total": int(pd.to_numeric(combined.get("is_discovery", False), errors="coerce").fillna(0).astype(bool).sum()),
            "families_total": int(combined["family_id"].nunique()) if "family_id" in combined.columns else 0,
        },
        "sample_quality": _sample_quality_summary(combined),
        "sample_quality_gate": {
            "survivors_before_gate": int(survivors_before_gate.sum()),
            "survivors_after_gate": int(pd.to_numeric(combined.get("is_discovery", False), errors="coerce").fillna(0).astype(bool).sum()),
            "rejected_by_sample_quality_gate": int(gate_rejections.sum()),
            "fail_reason_counts": {str(key): int(value) for key, value in fail_reason_counts.items()},
        },
        "survivor_quality": _survivor_quality_summary(combined),
        "by_symbol": by_symbol,
    }


def _resolve_sample_quality_policy(config: CandidateDiscoveryConfig) -> Dict[str, Any]:
    profile = str(config.discovery_profile or "standard").strip().lower()
    defaults = DEFAULT_SAMPLE_QUALITY_POLICY.get(profile, DEFAULT_SAMPLE_QUALITY_POLICY["standard"])
    resolved = {
        "profile": profile,
        "min_validation_n_obs": int(config.min_validation_n_obs) if config.min_validation_n_obs is not None else int(defaults["min_validation_n_obs"]),
        "min_test_n_obs": int(config.min_test_n_obs) if config.min_test_n_obs is not None else int(defaults["min_test_n_obs"]),
        "min_total_n_obs": int(config.min_total_n_obs) if config.min_total_n_obs is not None else int(defaults["min_total_n_obs"]),
        "explicit_overrides": {
            "min_validation_n_obs": config.min_validation_n_obs is not None,
            "min_test_n_obs": config.min_test_n_obs is not None,
            "min_total_n_obs": config.min_total_n_obs is not None,
        },
    }
    return resolved


def _apply_sample_quality_gates(
    candidates_df: pd.DataFrame,
    *,
    min_validation_n_obs: int,
    min_test_n_obs: int,
    min_total_n_obs: int,
) -> pd.DataFrame:
    if candidates_df.empty:
        return candidates_df.copy()
    out = candidates_df.copy()
    validation = pd.to_numeric(out.get("validation_n_obs", 0), errors="coerce").fillna(0)
    test = pd.to_numeric(out.get("test_n_obs", 0), errors="coerce").fillna(0)
    total = pd.to_numeric(out.get("n_obs", 0), errors="coerce").fillna(0)
    multiplicity_survivor = pd.to_numeric(out.get("is_discovery", False), errors="coerce").fillna(0).astype(bool)

    gate_validation = validation >= int(min_validation_n_obs)
    gate_test = test >= int(min_test_n_obs)
    gate_total = total >= int(min_total_n_obs)
    gate_sample_quality = gate_validation & gate_test & gate_total

    fail_reason = np.where(
        ~gate_validation,
        "min_validation_n_obs",
        np.where(~gate_test, "min_test_n_obs", np.where(~gate_total, "min_total_n_obs", "")),
    )

    out["gate_min_validation_n_obs"] = gate_validation.astype(bool)
    out["gate_min_test_n_obs"] = gate_test.astype(bool)
    out["gate_min_total_n_obs"] = gate_total.astype(bool)
    out["gate_sample_quality"] = gate_sample_quality.astype(bool)
    out["sample_quality_fail_reason"] = pd.Series(fail_reason, index=out.index).astype(str)
    out["is_discovery_pre_sample_quality"] = multiplicity_survivor.astype(bool)
    out["rejected_by_sample_quality"] = (multiplicity_survivor & ~gate_sample_quality).astype(bool)
    out["is_discovery"] = (multiplicity_survivor & gate_sample_quality).astype(bool)
    return out
def _bar_duration_minutes_from_timeframe(timeframe: str) -> int:
    return int(timeframe_to_minutes(normalize_timeframe(timeframe or "5m")))


def _split_and_score_candidates(
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
    cost_estimate: Optional[ResolvedCandidateCostEstimate] = None,
) -> pd.DataFrame:
    if candidates.empty:
        return candidates.copy()

    working = events_df.copy()
    resolved_split_scheme_id, train_frac, validation_frac = resolve_split_scheme(split_scheme_id)
    time_col = "enter_ts" if "enter_ts" in working.columns else ("timestamp" if "timestamp" in working.columns else None)
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

    if (
        "split_label" not in working.columns
        or working["split_label"].isna().all()
        or str(working.get("split_plan_id", pd.Series(dtype=object)).astype(str).iloc[0] if "split_plan_id" in working.columns and not working.empty else "")
        != f"TVT_{int(round(train_frac*100))}_{int(round(validation_frac*100))}_{100-int(round((train_frac+validation_frac)*100))}"
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
    out["split_plan_id"] = str(working["split_plan_id"].iloc[0]) if "split_plan_id" in working.columns and not working.empty else ""
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
        row_horizon_bars = int(pd.to_numeric(row.get("horizon_bars", horizon_bars), errors="coerce") or horizon_bars)
        row_horizon = str(row.get("horizon", discovery.bars_to_timeframe(row_horizon_bars)))
        return_frame = build_event_return_frame(
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
            stop_loss_atr_multipliers=pd.to_numeric(row.get("stop_loss_atr_multipliers"), errors="coerce"),
            take_profit_atr_multipliers=pd.to_numeric(row.get("take_profit_atr_multipliers"), errors="coerce"),
            cost_bps=float(cost_estimate.cost_bps) if cost_estimate is not None else 0.0,
            direction_override=pd.to_numeric(row.get("direction"), errors="coerce"),
        )
        if return_frame.empty:
            eval_frame = pd.DataFrame(columns=["forward_return", "cluster_day"])
            train_frame = pd.DataFrame(columns=["forward_return", "cluster_day"])
            split_labels = pd.Series(dtype=object)
        else:
            split_labels = return_frame["split_label"].astype(str).str.lower()
            evaluation_mask = split_labels.isin(["validation", "test"])
            if not bool(evaluation_mask.any()):
                evaluation_mask = split_labels != "train"
            if not bool(evaluation_mask.any()):
                evaluation_mask = pd.Series(True, index=return_frame.index)
            eval_frame = return_frame.loc[evaluation_mask, ["forward_return", "cluster_day"]].dropna(subset=["forward_return"])
            train_frame = return_frame.loc[split_labels == "train", ["forward_return", "cluster_day"]].dropna(subset=["forward_return"])
        estimate = estimate_effect_from_frame(
            eval_frame,
            value_col="forward_return",
            cluster_col="cluster_day",
            alpha=0.05,
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
        out.at[idx, "effect_split_basis"] = "validation_test" if not eval_frame.empty and bool(split_labels.isin(["validation", "test"]).any()) else "all"
        out.at[idx, "validation_n_obs"] = int((split_labels == "validation").sum())
        out.at[idx, "test_n_obs"] = int((split_labels == "test").sum())
        out.at[idx, "train_n_obs"] = int((split_labels == "train").sum())
        out.at[idx, "expectancy"] = float(train_frame["forward_return"].mean()) if not train_frame.empty else 0.0
        out.at[idx, "expectancy_bps"] = float(out.at[idx, "expectancy"] * 1e4)
        out.at[idx, "t_stat"] = float(
            eval_frame["forward_return"].mean() / (eval_frame["forward_return"].std(ddof=1) / np.sqrt(len(eval_frame)))
        ) if len(eval_frame) > 1 and float(eval_frame["forward_return"].std(ddof=1) or 0.0) > 0.0 else 0.0
    return out


def _apply_validation_multiple_testing(candidates_df: pd.DataFrame) -> pd.DataFrame:
    if candidates_df.empty:
        return candidates_df.copy()
    out = candidates_df.copy()
    out["event_family"] = out.get("event_type", "").astype(str).str.split("_").str[0]
    out = assign_test_families(
        out,
        family_cols=["run_id", "event_family", "horizon"],
        out_col="correction_family_id",
    )
    out = apply_multiple_testing(out, p_col="p_value_raw", family_col="correction_family_id", method="bh", out_col="p_value_adj")
    out = apply_multiple_testing(out, p_col="p_value_raw", family_col="correction_family_id", method="by", out_col="p_value_adj_by")
    out = apply_multiple_testing(out, p_col="p_value_raw", family_col="correction_family_id", method="holm", out_col="p_value_adj_holm")
    out["correction_method"] = "bh"
    out["q_value"] = pd.to_numeric(out.get("p_value_adj", np.nan), errors="coerce")
    out["q_value_by"] = pd.to_numeric(out.get("p_value_adj_by", np.nan), errors="coerce")
    out["q_value_family"] = out["q_value"]
    out["q_value_cluster"] = out["q_value_by"]
    out["is_discovery"] = out["q_value"].fillna(1.0) <= 0.10
    out["is_discovery_by"] = out["q_value_by"].fillna(1.0) <= 0.10
    out["gate_multiplicity"] = out["is_discovery"].astype(bool)
    return out


def execute_candidate_discovery(config: CandidateDiscoveryConfig) -> CandidateDiscoveryResult:
    if config.entry_lag_bars < 1:
        return CandidateDiscoveryResult(exit_code=1, output_dir=config.resolved_out_dir())

    out_dir = config.resolved_out_dir()
    ensure_dir(out_dir)
    manifest = start_manifest("phase2_candidate_discovery", config.run_id, config.manifest_params(), [], [])
    hyp_registry = HypothesisRegistry()
    symbol_candidates: Dict[str, pd.DataFrame] = {}
    combined = pd.DataFrame()
    symbol_diagnostics: Dict[str, Dict[str, Any]] = {}
    sample_quality_policy = _resolve_sample_quality_policy(config)

    try:
        try:
            resolved_costs = resolve_execution_costs(
                project_root=PROJECT_ROOT.parent,
                config_paths=config.config_paths,
                fees_bps=config.fees_bps,
                slippage_bps=config.slippage_bps,
                cost_bps=config.cost_bps,
            )
        except FileNotFoundError:
            fee_bps = float(config.fees_bps) if config.fees_bps is not None else 4.0
            slippage_bps = float(config.slippage_bps) if config.slippage_bps is not None else 2.0
            total_cost_bps = float(config.cost_bps) if config.cost_bps is not None else fee_bps + slippage_bps
            resolved_costs = type(
                "ResolvedCostsFallback",
                (),
                {
                    "config_digest": "fallback:no_config",
                    "cost_bps": float(total_cost_bps),
                    "fee_bps_per_side": float(fee_bps),
                    "slippage_bps_per_fill": float(slippage_bps),
                },
            )()
        cost_calibrator = ToBRegimeCostCalibrator(
            run_id=config.run_id,
            data_root=config.data_root,
            base_fee_bps=resolved_costs.fee_bps_per_side,
            base_slippage_bps=resolved_costs.slippage_bps_per_fill,
            static_cost_bps=resolved_costs.cost_bps,
            mode=str(config.cost_calibration_mode or "auto"),
            min_tob_coverage=float(config.cost_min_tob_coverage),
            tob_tolerance_minutes=int(config.cost_tob_tolerance_minutes),
        )
        event_frames: List[pd.DataFrame] = []
        for symbol in config.symbols:
            # If experiment is active, we might need multiple event types for sequences/interactions
            load_event_type: str | List[str] = config.event_type
            if config.experiment_config:
                import importlib
                experiment_engine = importlib.import_module("project.pipelines.research.experiment_engine")
                plan = experiment_engine.build_experiment_plan(
                    Path(config.experiment_config),
                    config.registry_root or Path("project/configs/registries"),
                )
                
                # Filter required event IDs for this symbol/run
                # We load all events mentioned in any hypothesis trigger to support cross-event evaluation
                required_events = set()
                for h in plan.hypotheses:
                    t = h.trigger
                    if t.trigger_type == "event" and t.event_id:
                        required_events.add(t.event_id)
                    elif t.trigger_type == "sequence" and t.events:
                        required_events.update(t.events)
                    elif t.trigger_type == "interaction":
                        if t.left: required_events.add(t.left)
                        if t.right: required_events.add(t.right)
                
                if required_events:
                    # Keep current event_type in the list just in case, but usually it's already there
                    required_events.add(config.event_type)
                    load_event_type = sorted(list(required_events))

            events_df = prepare_events_dataframe(
                data_root=config.data_root,
                run_id=config.run_id,
                event_type=load_event_type,
                symbols=[symbol],
                event_registry_specs=EVENT_REGISTRY_SPECS,
                horizons=[discovery.bars_to_timeframe(config.horizon_bars)],
                entry_lag_bars=config.entry_lag_bars,
                fam_config={},
                logger=logging.getLogger(__name__),
                run_mode=config.run_mode,
                timeframe=config.timeframe,
            )
            prepare_diag = get_prepare_events_diagnostics(events_df)
            if not prepare_diag:
                prepare_diag = build_prepare_events_diagnostics(
                    run_id=config.run_id,
                    event_type=config.event_type,
                    symbols_requested=[symbol],
                    raw_event_count=int(len(events_df)),
                    canonical_episode_count=int(len(events_df)),
                    split_counts_payload=phase2_split_counts(events_df),
                    loaded_from_fallback_file=False,
                    holdout_integrity_failed=False,
                    resplit_attempted=False,
                    returned_empty_due_to_holdout=False,
                    min_validation_events=1,
                    min_test_events=1,
                    returned_rows=int(len(events_df)),
                )
            symbol_diag: Dict[str, Any] = {
                "symbol": symbol,
                "event_type": config.event_type,
                "generated_candidate_rows": 0,
                "post_split_candidate_rows": 0,
                "multiplicity_survivors": 0,
                "rejected_by_min_sample": 0,
                "prepare_events": prepare_diag,
            }
            if events_df.empty:
                symbol_diagnostics[symbol] = symbol_diag
                continue

            features_df = load_features(
                data_root=config.data_root,
                run_id=config.run_id,
                symbol=symbol,
                timeframe=config.timeframe,
            )
            cost_estimate = cost_calibrator.estimate(symbol=symbol, events_df=events_df)
            symbol_diag["cost_estimate"] = {
                "cost_bps": float(cost_estimate.cost_bps),
                "fee_bps_per_side": float(cost_estimate.fee_bps_per_side),
                "slippage_bps_per_fill": float(cost_estimate.slippage_bps_per_fill),
                "avg_dynamic_cost_bps": float(cost_estimate.avg_dynamic_cost_bps),
                "cost_input_coverage": float(cost_estimate.cost_input_coverage),
                "cost_model_valid": bool(cost_estimate.cost_model_valid),
                "cost_model_source": str(cost_estimate.cost_model_source),
                "regime_multiplier": float(cost_estimate.regime_multiplier),
            }

            if config.experiment_config:
                candidates = discovery._synthesize_experiment_hypotheses(
                    run_id=config.run_id,
                    symbol=symbol,
                    events_df=events_df,
                    features_df=features_df,
                    experiment_config=config.experiment_config,
                    event_type=config.event_type,
                    registry_root=config.registry_root or Path("project/configs/registries"),
                )
            elif config.concept_file:
                candidates = discovery._synthesize_concept_candidates(
                    run_id=config.run_id,
                    symbol=symbol,
                    events_df=events_df,
                    features_df=features_df,
                    entry_lag_bars=config.entry_lag_bars,
                    concept_file=config.concept_file,
                )
            else:
                direction_policy = discovery.resolve_registry_direction_policy(
                    events_df,
                    event_type=config.event_type,
                    default=0.0,
                )
                symbol_diag["direction_policy"] = {
                    "policy": str(direction_policy["policy"]),
                    "source": str(direction_policy["source"]),
                    "resolved": bool(direction_policy["resolved"]),
                    "direction_sign": float(direction_policy["direction_sign"]),
                }
                candidates = discovery._synthesize_registry_candidates(
                    run_id=config.run_id,
                    symbol=symbol,
                    event_type=config.event_type,
                    events_df=events_df,
                    horizon_bars=config.horizon_bars,
                    entry_lag_bars=config.entry_lag_bars,
                    templates=config.templates,
                    horizons=config.horizons,
                    directions=config.directions,
                    entry_lags=config.entry_lags,
                    search_budget=config.search_budget,
                )
                if candidates.empty and not bool(direction_policy["resolved"]):
                    symbol_diag["direction_policy"]["skipped_non_directional_registry_generation"] = True
            symbol_diag["generated_candidate_rows"] = int(len(candidates))
            if candidates.empty:
                symbol_diagnostics[symbol] = symbol_diag
                continue

            candidates["run_id"] = config.run_id
            candidates["run_mode"] = config.run_mode
            candidates["discovery_batch"] = config.run_id
            candidates["candidate_generation_method"] = config.candidate_generation_method
            candidates["split_scheme_id"] = config.split_scheme_id
            bar_duration_minutes = _bar_duration_minutes_from_timeframe(config.timeframe)
            candidates = _split_and_score_candidates(
                candidates,
                events_df,
                horizon_bars=config.horizon_bars,
                split_scheme_id=config.split_scheme_id,
                purge_bars=config.purge_bars,
                embargo_bars=config.embargo_bars,
                bar_duration_minutes=bar_duration_minutes,
                features_df=features_df,
                entry_lag_bars=config.entry_lag_bars,
                shift_labels_k=config.shift_labels_k,
                cost_estimate=cost_estimate,
            )
            symbol_diag["post_split_candidate_rows"] = int(len(candidates))
            if "validation_n_obs" in candidates.columns or "test_n_obs" in candidates.columns:
                symbol_diag["rejected_by_min_sample"] = int(
                    (
                        pd.to_numeric(candidates.get("validation_n_obs", 0), errors="coerce").fillna(0) <= 0
                    ).sum()
                    + (
                        pd.to_numeric(candidates.get("test_n_obs", 0), errors="coerce").fillna(0) <= 0
                    ).sum()
                )
            for idx, row in candidates.iterrows():
                hyp = Hypothesis(
                    event_family=str(row.get("event_type", "")).split("_")[0],
                    event_type=str(row.get("event_type", "")),
                    symbol_scope=symbol,
                    side=discovery.action_name_from_direction(row.get("direction", 0.0)),
                    horizon=str(config.horizon_bars),
                    condition_template="standard_v1",
                    state_filter="none",
                    parameterization_id="v1",
                    family_id=str(row.get("family_id", "default")),
                    cluster_id=f"{symbol}_cluster_day",
                )
                candidates.at[idx, "hypothesis_id"] = hyp_registry.register(hyp)
            symbol_candidates[symbol] = candidates
            symbol_diagnostics[symbol] = symbol_diag
            event_frames.append(candidates)

        if event_frames:
            combined = pd.concat(event_frames, ignore_index=True)
            combined = _apply_validation_multiple_testing(combined)
            combined = _apply_sample_quality_gates(
                combined,
                min_validation_n_obs=int(sample_quality_policy["min_validation_n_obs"]),
                min_test_n_obs=int(sample_quality_policy["min_test_n_obs"]),
                min_total_n_obs=int(sample_quality_policy["min_total_n_obs"]),
            )
            symbol_candidates = {
                str(symbol): sym_df.copy()
                for symbol, sym_df in combined.groupby("symbol")
            }
            for symbol, sym_df in symbol_candidates.items():
                symbol_diagnostics.setdefault(symbol, {"symbol": symbol})
                pre_gate_survivors = int(
                    pd.to_numeric(sym_df.get("is_discovery_pre_sample_quality", False), errors="coerce")
                    .fillna(0)
                    .astype(bool)
                    .sum()
                )
                symbol_diagnostics[symbol]["multiplicity_survivors"] = int(
                    pd.to_numeric(sym_df.get("is_discovery", False), errors="coerce")
                    .fillna(0)
                    .astype(bool)
                    .sum()
                )
                symbol_diagnostics[symbol]["rejected_by_sample_quality_gate"] = int(
                    pd.to_numeric(sym_df.get("rejected_by_sample_quality", False), errors="coerce")
                    .fillna(0)
                    .astype(bool)
                    .sum()
                )
                symbol_diagnostics[symbol]["survivors_before_sample_quality_gate"] = pre_gate_survivors

        write_candidate_reports(
            out_dir=out_dir,
            combined_candidates=combined,
            symbol_candidates=symbol_candidates,
            diagnostics={
                "run_id": config.run_id,
                "event_type": config.event_type,
                "timeframe": config.timeframe,
                "cost_coordinate": {
                    "config_digest": resolved_costs.config_digest,
                    "cost_bps": float(resolved_costs.cost_bps),
                    "fee_bps_per_side": float(resolved_costs.fee_bps_per_side),
                    "slippage_bps_per_fill": float(resolved_costs.slippage_bps_per_fill),
                },
                "symbols_requested": list(config.symbols),
                "symbols_with_candidates": sorted(symbol_candidates),
                "combined_candidate_rows": int(len(combined)),
                "sample_quality_gate_thresholds": {
                    "min_validation_n_obs": int(sample_quality_policy["min_validation_n_obs"]),
                    "min_test_n_obs": int(sample_quality_policy["min_test_n_obs"]),
                    "min_total_n_obs": int(sample_quality_policy["min_total_n_obs"]),
                },
                "sample_quality_gate_policy": sample_quality_policy,
                "false_discovery_diagnostics": _build_false_discovery_diagnostics(combined),
                "symbol_diagnostics": [symbol_diagnostics[s] for s in sorted(symbol_diagnostics)],
            },
        )

        reg_hash = hyp_registry.write_artifacts(out_dir)
        manifest["hypothesis_registry_hash"] = reg_hash
        finalize_manifest(manifest, "success")
        return CandidateDiscoveryResult(0, out_dir, combined, symbol_candidates, manifest)
    except Exception as exc:
        logging.exception("Discovery failed")
        finalize_manifest(manifest, "failed", error=str(exc))
        return CandidateDiscoveryResult(1, out_dir, combined, symbol_candidates, manifest)
