"""
Rich Bridge adapter: translate hypothesis metrics into full production schema.

Takes the rich metrics DataFrame produced by the hypothesis evaluator and 
maps them into the 40+ column schema expected by bridge evaluation and
blueprint compilation.
"""
from __future__ import annotations

import re
import logging
import pandas as pd
import numpy as np

from project.research.gating import two_sided_p_from_t
from project.spec_validation import get_event_family, resolve_execution_templates

log = logging.getLogger(__name__)

def _sanitize_event_type(row: pd.Series) -> str:
    trigger_type = str(row.get("trigger_type", "event")).lower()
    key = str(row.get("trigger_key", "UNKNOWN")).upper()
    # Strip "type:" prefix from trigger_key (e.g. "event:VOL_SPIKE" -> "VOL_SPIKE")
    if ":" in key:
        key = key.split(":", 1)[1]
    clean_key = re.sub(r"[^A-Z0-9_]+", "_", key)
    if trigger_type == "event":
        return clean_key
    if trigger_type == "state":
        return f"STATE_{clean_key}"
    if trigger_type == "transition":
        return f"TRANSITION_{clean_key}"
    return f"FEATURE_{clean_key}"


def hypotheses_to_bridge_candidates(
    metrics_df: pd.DataFrame,
    *,
    min_t_stat: float = 1.5,
    min_n: int = 30,
) -> pd.DataFrame:
    """
    Map evaluator metrics to the production schema.
    """
    filtered, _ = split_bridge_candidates(metrics_df, min_t_stat=min_t_stat, min_n=min_n)
    if filtered.empty:
        return pd.DataFrame()

    # Core Mappings
    out = pd.DataFrame()
    out["candidate_id"] = filtered["hypothesis_id"].astype(str)
    out["event_type"] = [
        _sanitize_event_type(row) for _, row in filtered.iterrows()
    ]
    out["direction"] = filtered["direction"].astype(str)
    out["rule_template"] = filtered["template_id"].astype(str)
    out["template_verb"] = out["rule_template"]
    out["horizon"] = filtered["horizon"].astype(str)
    out["t_stat"] = filtered["t_stat"].astype(float)
    out["n"] = filtered["n"].astype(int)
    out["sample_size"] = out["n"]
    out["n_events"] = out["n"]
    for source_col in (
        "train_n_obs",
        "validation_n_obs",
        "test_n_obs",
        "validation_samples",
        "test_samples",
    ):
        if source_col in filtered.columns:
            out[source_col] = pd.to_numeric(filtered[source_col], errors="coerce").fillna(0).astype(int)
        else:
            out[source_col] = 0
    
    # Financial Mappings (bps -> decimal)
    out["expectancy"] = filtered["mean_return_bps"] / 10000.0
    out["mean_return_bps"] = filtered["mean_return_bps"]
    out["after_cost_expectancy_per_trade"] = filtered["cost_adjusted_return_bps"] / 10000.0
    
    # Stress testing: subtract an additional 2bps
    out["stressed_after_cost_expectancy_per_trade"] = (filtered["cost_adjusted_return_bps"] - 2.0) / 10000.0
    
    # Rich Metrics
    out["robustness_score"] = filtered["robustness_score"]
    out["stress_test_survival"] = filtered["stress_score"] if "stress_score" in filtered.columns else 0.0
    out["kill_switch_count"] = (filtered["kill_switch_count"] if "kill_switch_count" in filtered.columns else 0)
    out["kill_switch_count"] = out["kill_switch_count"].astype(int)
    
    out["delta_adverse_mean"] = filtered["mae_mean_bps"] / 10000.0
    out["delta_opportunity_mean"] = filtered["mfe_mean_bps"] / 10000.0
    out["capacity_proxy"] = filtered["capacity_proxy"]
    out["turnover_proxy_mean"] = 0.5 # Default turnover proxy
    
    # Gating Flags
    out["gate_oos_validation"] = filtered["robustness_score"] >= 0.7
    out["gate_multiplicity"] = False # Will be set by apply_multiplicity_controls()
    out["gate_c_regime_stable"] = filtered["robustness_score"] >= 0.6
    out["gate_after_cost_positive"] = filtered["cost_adjusted_return_bps"] > 0
    out["gate_after_cost_stressed_positive"] = (filtered["cost_adjusted_return_bps"] - 2.0) > 0
    
    # Overall Tradability
    # A candidate is "tradable" if it passes t-stat, n, OOS score, 
    # and survives at least 50% of stress scenarios.
    out["gate_bridge_tradable"] = (
        (out["t_stat"].abs() >= 2.0) & 
        (out["gate_after_cost_stressed_positive"]) &
        (out["gate_oos_validation"]) &
        (out["stress_test_survival"] >= 0.5)
    )
    
    out["bridge_eval_status"] = np.where(out["gate_bridge_tradable"], "tradable", "rejected")
    out["promotion_track"] = np.where(out["gate_bridge_tradable"], "standard", "fallback_only")
    
    # Structural stats (needed for blueprint compilation)
    out["pnl_series"] = "[]"

    # Derive p-values from t-statistics
    out["p_value"] = [
        two_sided_p_from_t(float(row["t_stat"]), max(1, int(row["n"]) - 1))
        for _, row in filtered.iterrows()
    ]
    out["p_value_for_fdr"] = out["p_value"]

    # Derive family_id from trigger metadata
    out["family_id"] = (
        filtered["trigger_type"].astype(str) + "_"
        + filtered["template_id"].astype(str) + "_"
        + filtered["horizon"].astype(str)
    ).values

    # Derive canonical_family from trigger_key (the part after "type:", e.g. "event:VOL_SPIKE" -> "VOL_SPIKE")
    out["canonical_family"] = filtered["trigger_key"].apply(
        lambda k: str(k).split(":", 1)[1].upper() if ":" in str(k) else str(k).upper()
    ).values

    # Symbol placeholder
    if "symbol" not in out.columns:
        out["symbol"] = "ALL"

    # Expand base candidates (template_id="base") into one row per execution template.
    # Filter template candidates pass through unchanged.
    base_mask = out["rule_template"] == "base"
    if base_mask.any():
        base_rows = out[base_mask]
        filter_rows = out[~base_mask]
        expanded_parts = [filter_rows]
        for _, row in base_rows.iterrows():
            event_id = str(row.get("canonical_family", ""))
            family = get_event_family(event_id) if event_id else None
            exec_templates = resolve_execution_templates(family) if family else []
            if not exec_templates:
                if family:
                    log.warning("No execution templates resolved for family %r (event_id=%r); keeping as 'base'", family, event_id)
                # No execution templates found — keep as "base" rather than drop
                expanded_parts.append(pd.DataFrame([row]))
                continue
            for tmpl in exec_templates:
                new_row = row.copy()
                new_row["rule_template"] = tmpl
                new_row["template_verb"] = tmpl
                expanded_parts.append(pd.DataFrame([new_row]))
        out = pd.concat(expanded_parts, ignore_index=True)

    return out.reset_index(drop=True)


def split_bridge_candidates(
    metrics_df: pd.DataFrame,
    *,
    min_t_stat: float = 1.5,
    min_n: int = 30,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if metrics_df.empty:
        return pd.DataFrame(), pd.DataFrame()

    valid_mask = metrics_df["valid"].fillna(False)
    min_n_mask = pd.to_numeric(metrics_df["n"], errors="coerce").fillna(0) >= int(min_n)
    min_t_mask = pd.to_numeric(metrics_df["t_stat"], errors="coerce").abs().fillna(0.0) >= float(min_t_stat)
    pass_mask = valid_mask & min_n_mask & min_t_mask

    filtered = metrics_df[pass_mask].copy()
    failed = metrics_df[~pass_mask].copy()
    if not failed.empty:
        reasons: list[list[str]] = []
        primary: list[str] = []
        for _, row in failed.iterrows():
            row_reasons: list[str] = []
            if not bool(row.get("valid", False)):
                row_reasons.append(str(row.get("invalid_reason") or "invalid"))
            else:
                if int(pd.to_numeric(row.get("n", 0), errors="coerce") or 0) < int(min_n):
                    row_reasons.append("min_sample_size")
                if abs(float(pd.to_numeric(row.get("t_stat", 0.0), errors="coerce") or 0.0)) < float(min_t_stat):
                    row_reasons.append("min_t_stat")
            if not row_reasons:
                row_reasons = ["filtered_out"]
            reasons.append(row_reasons)
            primary.append(row_reasons[0])
        failed["gate_failure_reasons"] = reasons
        failed["gate_failure_reason"] = primary
        failed["status"] = "gate_failed"
    return filtered, failed
