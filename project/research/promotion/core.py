from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from project.research.promotion.promotion_eligibility import (
    _ReasonRecorder,
    _is_deploy_mode,
    _has_explicit_oos_samples,
    _normalized_run_mode,
    sign_consistency,
    cost_survival_ratio,
    control_rate_details_for_event,
)
from project.research.promotion.promotion_scoring import (
    stability_score,
)
from project.research.promotion.promotion_thresholds import (
    _build_bundle_policy,
)
from project.research.promotion.promotion_gate_evaluators import (
    _confirmatory_shadow_gates,
    _confirmatory_deployable_gates,
    _evaluate_market_execution_and_stability,
    _evaluate_control_audit_and_dsr,
    _evaluate_deploy_oos_and_low_capital,
)
from project.research.promotion.promotion_decision_support import (
    _apply_bundle_policy_result,
)
from project.research.promotion.promotion_result_support import (
    _assemble_promotion_result,
)
from project.research.promotion.promotion_decisions import evaluate_row
from project.research.promotion.promotion_reporting import (
    apply_portfolio_overlap_gate,
    assign_and_validate_promotion_tiers,
    portfolio_diversification_violations,
    build_promotion_capital_footprint,
    build_negative_control_diagnostics,
    build_promotion_statistical_audit,
)
from project.research.promotion.promotion_reporting_support import (
    behavior_key,
    behavior_overlap_score,
    behavior_token_set,
    delay_profile_correlation,
    delay_profile_map,
    resolve_promotion_tier,
    stabilize_promoted_output_schema,
)
from project.research.services.benchmark_governance_service import (
    get_benchmark_certification_for_family,
)

from project.core.config import get_data_root
from project.research.utils.decision_safety import coerce_numeric_nan


def _current_data_root():
    return get_data_root()


def promote_candidates(
    candidates_df: pd.DataFrame,
    promotion_spec: dict[str, Any],
    hypothesis_index: dict[str, dict[str, Any]],
    negative_control_summary: dict[str, Any],
    contract: Any,
    dynamic_min_events: dict[str, int],
    base_min_events: int,
    *,
    max_q_value: float,
    min_stability_score: float,
    min_sign_consistency: float,
    min_cost_survival_ratio: float,
    max_negative_control_pass_rate: float,
    min_tob_coverage: float,
    require_hypothesis_audit: bool,
    allow_missing_negative_controls: bool,
    require_multiplicity_diagnostics: bool,
    min_dsr: float,
    max_overlap_ratio: float,
    max_profile_correlation: float,
    promotion_profile: str,
    min_net_expectancy_bps: float,
    max_fee_plus_slippage_bps: float | None,
    max_daily_turnover_multiple: float | None,
    require_retail_viability: bool,
    require_low_capital_viability: bool,
    enforce_baseline_beats_complexity: bool,
    enforce_placebo_controls: bool,
    enforce_timeframe_consensus: bool,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    from project.eval.multiplicity import (
        apply_program_multiplicity_control,
        formalize_ids,
        update_program_hypothesis_log,
    )

    df = formalize_ids(candidates_df)
    program_id = str(promotion_spec.get("program_id", "default_program")).strip()
    data_root = _current_data_root()
    update_program_hypothesis_log(program_id, data_root, df)
    df = apply_program_multiplicity_control(df, program_id, data_root, alpha=max_q_value)

    audit_rows, promoted_rows = [], []
    ontology_hash = str(promotion_spec.get("ontology_spec_hash", ""))
    is_reduced_evidence = bool(promotion_spec.get("is_reduced_evidence", False))
    promotion_confirmatory_gates = promotion_spec.get("promotion_confirmatory_gates")

    # Pre-cache benchmark certifications for involved families
    unique_families = (
        set(df["family"].dropna().unique()) if "family" in df.columns else set()
    )
    benchmark_certs = {}
    for fam in unique_families:
        benchmark_certs[fam] = get_benchmark_certification_for_family(family=fam)

    for row in df.to_dict(orient="records"):
        event_type = str(row.get("event_type", row.get("event", ""))).strip()
        family = str(row.get("family", "")).strip()

        row_min_events = max(
            int(base_min_events),
            int(dynamic_min_events.get(event_type.upper(), base_min_events)),
        )

        bench_cert = benchmark_certs.get(family)

        eval_row = evaluate_row(
            row=row,
            hypothesis_index=hypothesis_index,
            negative_control_summary=negative_control_summary,
            max_q_value=max_q_value,
            min_events=row_min_events,
            min_stability_score=min_stability_score,
            min_sign_consistency=min_sign_consistency,
            min_cost_survival_ratio=min_cost_survival_ratio,
            max_negative_control_pass_rate=max_negative_control_pass_rate,
            min_tob_coverage=min_tob_coverage,
            require_hypothesis_audit=require_hypothesis_audit,
            allow_missing_negative_controls=allow_missing_negative_controls,
            min_net_expectancy_bps=min_net_expectancy_bps,
            max_fee_plus_slippage_bps=max_fee_plus_slippage_bps,
            max_daily_turnover_multiple=max_daily_turnover_multiple,
            require_retail_viability=require_retail_viability,
            require_low_capital_viability=require_low_capital_viability,
            require_multiplicity_diagnostics=require_multiplicity_diagnostics,
            min_dsr=min_dsr,
            promotion_confirmatory_gates=promotion_confirmatory_gates,
            promotion_profile=promotion_profile,
            enforce_baseline_beats_complexity=enforce_baseline_beats_complexity,
            enforce_placebo_controls=enforce_placebo_controls,
            enforce_timeframe_consensus=enforce_timeframe_consensus,
            benchmark_certification=bench_cert,
        )
        merged = dict(row)
        merged.update(eval_row)
        merged["event"] = str(merged.get("event", merged.get("event_type", ""))).strip()
        merged["event_type"] = str(
            merged.get("event_type", merged.get("event", ""))
        ).strip()
        merged["candidate_id"] = str(merged.get("candidate_id", "")).strip()
        merged["promotion_min_events_threshold"] = int(row_min_events)
        merged["promotion_profile"] = str(promotion_profile)
        merged["is_reduced_evidence"] = is_reduced_evidence
        merged["ontology_hash"] = str(
            merged.get("ontology_spec_hash", ontology_hash)
        ).strip()

        audit_rows.append(merged)
        if merged["promotion_decision"] == "promoted":
            promoted = dict(merged)
            promoted["status"] = "PROMOTED"
            promoted_rows.append(promoted)

    audit_df = pd.DataFrame(audit_rows)
    promoted_df = pd.DataFrame(promoted_rows)

    if "gate_promo_redundancy" not in audit_df.columns:
        audit_df["gate_promo_redundancy"] = True

    for df_item in [audit_df, promoted_df]:
        if not df_item.empty:
            val = df_item.get("bridge_validation_stressed_after_cost_bps")
            df_item["selection_score"] = (
                pd.to_numeric(val, errors="coerce") if val is not None else np.nan
            )

    sort_cols = [
        c
        for c in [
            "selection_score",
            "promotion_score",
            "robustness_score",
            "n_events",
            "candidate_id",
        ]
        if c in audit_df.columns
    ]
    if not audit_df.empty:
        audit_df = audit_df.sort_values(
            sort_cols, ascending=[False] * len(sort_cols)
        ).reset_index(drop=True)

    overlap_dropped_df = pd.DataFrame(
        columns=[
            "candidate_id",
            "event_type",
            "overlap_with_candidate_id",
            "overlap_score",
            "overlap_reason",
        ]
    )
    if not promoted_df.empty:
        promoted_df = promoted_df.sort_values(
            sort_cols, ascending=[False] * len(sort_cols)
        ).reset_index(drop=True)
        promoted_df, overlap_dropped_df = apply_portfolio_overlap_gate(
            promoted_df=promoted_df, max_overlap_ratio=max_overlap_ratio
        )
        if not overlap_dropped_df.empty:
            dropped_ids = set(overlap_dropped_df["candidate_id"].tolist())
            audit_df.loc[
                audit_df["candidate_id"].isin(dropped_ids), "gate_promo_redundancy"
            ] = False
            audit_df.loc[
                audit_df["candidate_id"].isin(dropped_ids), "reject_reason"
            ] = audit_df.loc[
                audit_df["candidate_id"].isin(dropped_ids), "reject_reason"
            ].map(
                lambda x: "|".join(sorted(set(str(x).split("|") + ["portfolio_overlap"])))
                if x
                else "portfolio_overlap"
            )

    audit_df, promoted_df, tier_counts = assign_and_validate_promotion_tiers(
        audit_df=audit_df,
        promoted_df=promoted_df,
        require_retail_viability=bool(require_retail_viability),
        promotion_confirmatory_gates=promotion_confirmatory_gates,
    )

    div_violations = portfolio_diversification_violations(
        promoted_df=promoted_df,
        max_profile_correlation=max_profile_correlation,
        max_overlap_ratio=max_overlap_ratio,
    )
    capital_df, capital_summary = build_promotion_capital_footprint(
        promoted_df=promoted_df, contract=contract
    )

    diagnostics = {
        "tier_counts": tier_counts,
        "portfolio_diversification": div_violations,
        "capital_footprint": capital_summary,
        "overlap_dropped_count": len(overlap_dropped_df),
        "multiplicity_scope": program_id,
        "promotion_profile": str(promotion_profile),
    }

    return audit_df, promoted_df, diagnostics


def ensure_candidate_schema(df: pd.DataFrame) -> pd.DataFrame:
    from project.research.research_core import ensure_candidate_schema as _ensure

    return _ensure(df)

__all__ = [
    "_ReasonRecorder",
    "_is_deploy_mode",
    "_has_explicit_oos_samples",
    "_normalized_run_mode",
    "sign_consistency",
    "stability_score",
    "cost_survival_ratio",
    "control_rate_details_for_event",
    "_build_bundle_policy",
    "_confirmatory_shadow_gates",
    "_confirmatory_deployable_gates",
    "_apply_bundle_policy_result",
    "_evaluate_market_execution_and_stability",
    "_evaluate_control_audit_and_dsr",
    "_evaluate_deploy_oos_and_low_capital",
    "_assemble_promotion_result",
    "evaluate_row",
    "build_negative_control_diagnostics",
    "build_promotion_statistical_audit",
    "build_promotion_capital_footprint",
    "behavior_key",
    "behavior_token_set",
    "behavior_overlap_score",
    "delay_profile_map",
    "delay_profile_correlation",
    "apply_portfolio_overlap_gate",
    "portfolio_diversification_violations",
    "resolve_promotion_tier",
    "assign_and_validate_promotion_tiers",
    "stabilize_promoted_output_schema",
    "_current_data_root",
    "promote_candidates",
    "ensure_candidate_schema",
]
