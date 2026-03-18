from __future__ import annotations

from typing import Callable, Optional

import numpy as np
import pandas as pd

from project.research import discovery
from project.research.gating import build_event_return_frame
from project.research.validation import (
    apply_multiple_testing,
    assign_split_labels,
    assign_test_families,
    estimate_effect_from_frame,
    resolve_split_scheme,
)


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

    split_plan_id = (
        f"TVT_{int(round(train_frac*100))}_{int(round(validation_frac*100))}_"
        f"{100-int(round((train_frac+validation_frac)*100))}"
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
        str(working["split_plan_id"].iloc[0]) if "split_plan_id" in working.columns and not working.empty else ""
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
        row_horizon_bars = int(pd.to_numeric(row.get("horizon_bars", horizon_bars), errors="coerce") or horizon_bars)
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
            eval_frame = return_frame.loc[evaluation_mask, ["forward_return", "cluster_day"]].dropna(
                subset=["forward_return"]
            )
            train_frame = return_frame.loc[split_labels == "train", ["forward_return", "cluster_day"]].dropna(
                subset=["forward_return"]
            )
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
            "validation_test" if not eval_frame.empty and bool(split_labels.isin(["validation", "test"]).any()) else "all"
        )
        out.at[idx, "validation_n_obs"] = int((split_labels == "validation").sum())
        out.at[idx, "test_n_obs"] = int((split_labels == "test").sum())
        out.at[idx, "train_n_obs"] = int((split_labels == "train").sum())
        out.at[idx, "expectancy"] = (
            float(train_frame["forward_return"].mean()) if not train_frame.empty else 0.0
        )
        out.at[idx, "expectancy_bps"] = float(out.at[idx, "expectancy"] * 1e4)
        out.at[idx, "t_stat"] = float(
            eval_frame["forward_return"].mean()
            / (eval_frame["forward_return"].std(ddof=1) / np.sqrt(len(eval_frame)))
        ) if len(eval_frame) > 1 and float(eval_frame["forward_return"].std(ddof=1) or 0.0) > 0.0 else 0.0
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
        out, p_col="p_value_raw", family_col="correction_family_id", method="bh", out_col="p_value_adj"
    )
    out = apply_multiple_testing(
        out, p_col="p_value_raw", family_col="correction_family_id", method="by", out_col="p_value_adj_by"
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
    out["q_value_cluster"] = out["q_value_by"]
    out["is_discovery"] = out["q_value"].fillna(1.0) <= 0.10
    out["is_discovery_by"] = out["q_value_by"].fillna(1.0) <= 0.10
    out["gate_multiplicity"] = out["is_discovery"].astype(bool)
    return out
