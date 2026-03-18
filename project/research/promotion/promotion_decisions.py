from __future__ import annotations

from typing import Any, Dict

import numpy as np

from project.core.coercion import as_bool
from project.core.exceptions import PromotionDecisionError
from project.research.promotion.promotion_decision_support import (
    _apply_bundle_policy_result,
    _confirmatory_deployable_gates,
    _confirmatory_shadow_gates,
    _evaluate_continuation_quality,
    _evaluate_control_audit_and_dsr,
    _evaluate_deploy_oos_and_low_capital,
    _evaluate_market_execution_and_stability,
    _quiet_int,
    _restore_boolean_compat_gates,
)
from project.research.promotion.promotion_result_support import _assemble_promotion_result
from project.research.promotion.promotion_thresholds import _build_bundle_policy
from project.research.validation.evidence_bundle import (
    build_evidence_bundle,
    evaluate_promotion_bundle,
)


def evaluate_row(
    *,
    row: Dict[str, Any],
    hypothesis_index: Dict[str, Dict[str, Any]],
    negative_control_summary: Dict[str, Any],
    max_q_value: float,
    min_events: int,
    min_stability_score: float,
    min_sign_consistency: float,
    min_cost_survival_ratio: float,
    max_negative_control_pass_rate: float,
    min_tob_coverage: float,
    require_hypothesis_audit: bool,
    allow_missing_negative_controls: bool,
    min_net_expectancy_bps: float = 0.0,
    max_fee_plus_slippage_bps: float | None = None,
    max_daily_turnover_multiple: float | None = None,
    require_retail_viability: bool = False,
    require_low_capital_viability: bool = False,
    require_multiplicity_diagnostics: bool = False,
    min_dsr: float = 0.0,
    promotion_confirmatory_gates: Dict[str, Any] | None = None,
    promotion_profile: str = "deploy",
    enforce_baseline_beats_complexity: bool = True,
    enforce_placebo_controls: bool = True,
    enforce_timeframe_consensus: bool = True,
    enforce_regime_stability: bool = True,
    policy_version: str = "phase4_pr5_v1",
    bundle_version: str = "phase4_bundle_v1",
    is_reduced_evidence: bool = False,
    benchmark_certification: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    try:
        from project.research.promotion.promotion_eligibility import _ReasonRecorder
        from project.research.utils.decision_safety import coerce_numeric_nan, finite_le

        reasons = _ReasonRecorder.create()
        event_type = str(row.get("event_type", row.get("event", ""))).strip() or "UNKNOWN_EVENT"
        
        # Benchmark Certification Gate
        bench_pass = True
        if benchmark_certification:
            bench_pass = bool(benchmark_certification.get("passed", False))
            if not bench_pass:
                reasons.add_pair(
                    reject_reason=f"benchmark_{benchmark_certification.get('status', 'failed')}",
                    promo_fail_reason="gate_promo_benchmark_certification",
                    category="benchmark_integrity",
                )
        
        plan_row_id = str(row.get("plan_row_id", "")).strip()
        n_events = _quiet_int(row.get("n_events", row.get("sample_size", 0)), 0)
        q_value = coerce_numeric_nan(row.get("q_value"))

        is_descriptive = as_bool(row.get("event_is_descriptive", False))
        is_trade_trigger = as_bool(row.get("event_is_trade_trigger", True))
        if is_descriptive or not is_trade_trigger:
            reasons.add_pair(
                reject_reason="descriptive_only_event",
                promo_fail_reason="gate_promo_event_discipline",
                category="event_discipline",
            )

        q_value_available = bool(np.isfinite(q_value))
        statistical_pass = (
            q_value_available and finite_le(q_value, max_q_value) and (n_events >= int(min_events))
        )
        if not statistical_pass:
            if not q_value_available:
                reasons.add_pair(
                    reject_reason="statistical_missing_q_value",
                    promo_fail_reason="gate_promo_statistical_q_value",
                    category="statistical_significance",
                )
            reasons.add_pair(
                reject_reason="statistical_significance",
                promo_fail_reason="gate_promo_statistical",
                category="statistical_significance",
            )

        market_eval = _evaluate_market_execution_and_stability(
            row=row,
            min_tob_coverage=min_tob_coverage,
            min_net_expectancy_bps=min_net_expectancy_bps,
            max_fee_plus_slippage_bps=max_fee_plus_slippage_bps,
            max_daily_turnover_multiple=max_daily_turnover_multiple,
            require_retail_viability=require_retail_viability,
            min_cost_survival_ratio=min_cost_survival_ratio,
            min_stability_score=min_stability_score,
            min_sign_consistency=min_sign_consistency,
            enforce_baseline_beats_complexity=enforce_baseline_beats_complexity,
            enforce_placebo_controls=enforce_placebo_controls,
            enforce_timeframe_consensus=enforce_timeframe_consensus,
            reasons=reasons,
        )
        control_eval = _evaluate_control_audit_and_dsr(
            row=row,
            event_type=event_type,
            plan_row_id=plan_row_id,
            hypothesis_index=hypothesis_index,
            negative_control_summary=negative_control_summary,
            max_negative_control_pass_rate=max_negative_control_pass_rate,
            allow_missing_negative_controls=allow_missing_negative_controls,
            require_multiplicity_diagnostics=require_multiplicity_diagnostics,
            require_hypothesis_audit=require_hypothesis_audit,
            min_dsr=min_dsr,
            reasons=reasons,
        )
        deploy_eval = _evaluate_deploy_oos_and_low_capital(
            row=row,
            max_q_value=max_q_value,
            promotion_confirmatory_gates=promotion_confirmatory_gates,
            require_low_capital_viability=require_low_capital_viability,
            reasons=reasons,
        )
        continuation_eval = _evaluate_continuation_quality(
            row=row,
            stability_pass=market_eval["stability_pass"],
            oos_pass=deploy_eval["oos_pass"],
            microstructure_pass=market_eval["microstructure_pass"],
            dsr_pass=control_eval["dsr_pass"],
            reasons=reasons,
        )

        result = _assemble_promotion_result(
            reasons=reasons,
            q_value=q_value,
            n_events=n_events,
            tob_pass=market_eval["tob_pass"],
            require_retail_viability=require_retail_viability,
            require_low_capital_viability=require_low_capital_viability,
            enforce_baseline_beats_complexity=enforce_baseline_beats_complexity,
            enforce_placebo_controls=enforce_placebo_controls,
            enforce_timeframe_consensus=enforce_timeframe_consensus,
            statistical_pass=statistical_pass,
            cost_pass=market_eval["cost_pass"],
            beats_baseline=market_eval["beats_baseline"],
            placebo_pass=market_eval["placebo_pass"],
            stability_pass=market_eval["stability_pass"],
            timeframe_consensus_pass=market_eval["timeframe_consensus_pass"],
            oos_pass=deploy_eval["oos_pass"],
            microstructure_pass=market_eval["microstructure_pass"],
            stressed_cost_pass=market_eval["stressed_cost_pass"],
            delayed_entry_pass=market_eval["delayed_entry_pass"],
            continuation_quality_pass=continuation_eval["continuation_quality_pass"],
            multiplicity_diag_pass=control_eval["multiplicity_diag_pass"],
            audit_pass=control_eval["audit_pass"],
            dsr_pass=control_eval["dsr_pass"],
            multiplicity_pass=deploy_eval["multiplicity_pass"],
            robustness_pass=deploy_eval["robustness_pass"],
            regime_pass=deploy_eval["regime_pass"],
            retail_viability_pass=market_eval["retail_viability_pass"],
            low_capital_viability_pass=deploy_eval["low_capital_viability_pass"],
            q_value_family=deploy_eval["q_value_family"],
            q_value_cluster=deploy_eval["q_value_cluster"],
            q_value_by=deploy_eval["q_value_by"],
            q_value_program=deploy_eval["q_value_program"],
            ss=market_eval["ss"],
            sc=market_eval["sc"],
            csr=market_eval["csr"],
            control_pass=control_eval["control_pass"],
            control_rate=control_eval["control_rate"],
            control_rate_source=control_eval["control_rate_source"],
            tob_coverage=market_eval["tob_coverage"],
            net_expectancy_bps=market_eval["net_expectancy_bps"],
            effective_cost_bps=market_eval["effective_cost_bps"],
            turnover_proxy_mean=market_eval["turnover_proxy_mean"],
            audit_statuses=control_eval["audit_statuses"],
            net_expectancy_pass=market_eval["net_expectancy_pass"],
            cost_budget_pass=market_eval["cost_budget_pass"],
            turnover_pass=market_eval["turnover_pass"],
            dsr_value=control_eval["dsr_value"],
            shrinkage_loso_stable=deploy_eval["shrinkage_loso_stable"],
            shrinkage_borrowing_dominant=deploy_eval["shrinkage_borrowing_dominant"],
            structural_robustness_score=deploy_eval["structural_robustness_score"],
            repeated_fold_consistency=deploy_eval["repeated_fold_consistency"],
            robustness_panel_complete=deploy_eval["robustness_panel_complete"],
            num_regimes=deploy_eval["num_regimes"],
            regime_stability_pass=deploy_eval["regime_stability_pass"],
            structural_break_pass=deploy_eval["structural_break_pass"],
            low_capital_viability_score=deploy_eval["low_capital_viability_score"],
            low_capital_reject_codes=deploy_eval["low_capital_reject_codes"],
            run_mode_normalized=deploy_eval["run_mode_normalized"],
            is_deploy_mode=deploy_eval["is_deploy_mode"],
            is_descriptive=is_descriptive,
            is_trade_trigger=is_trade_trigger,
            max_q_value=max_q_value,
            promotion_profile=promotion_profile,
            is_reduced_evidence=is_reduced_evidence,
            benchmark_pass=bench_pass,
        )
        result["is_continuation_template_family"] = continuation_eval["is_continuation_template_family"]
        result["gate_bridge_tradable"] = "pass" if continuation_eval["bridge_tradable"] else "fail"

        merged_for_bundle = dict(row)
        merged_for_bundle.update(result)
        policy = _build_bundle_policy(
            max_q_value=max_q_value,
            min_events=min_events,
            min_stability_score=min_stability_score,
            min_sign_consistency=min_sign_consistency,
            min_cost_survival_ratio=min_cost_survival_ratio,
            max_negative_control_pass_rate=max_negative_control_pass_rate,
            min_tob_coverage=min_tob_coverage,
            require_hypothesis_audit=require_hypothesis_audit,
            allow_missing_negative_controls=allow_missing_negative_controls,
            require_multiplicity_diagnostics=require_multiplicity_diagnostics,
            require_retail_viability=require_retail_viability,
            require_low_capital_viability=require_low_capital_viability,
            promotion_profile=promotion_profile,
            enforce_baseline_beats_complexity=enforce_baseline_beats_complexity,
            enforce_placebo_controls=enforce_placebo_controls,
            enforce_timeframe_consensus=enforce_timeframe_consensus,
            enforce_regime_stability=enforce_regime_stability,
            policy_version=policy_version,
            bundle_version=bundle_version,
        )
        bundle = build_evidence_bundle(
            merged_for_bundle,
            control_rate=control_eval["control_rate"],
            max_negative_control_pass_rate=float(max_negative_control_pass_rate),
            allow_missing_negative_controls=bool(allow_missing_negative_controls),
            policy_version=policy.policy_version,
            bundle_version=policy.bundle_version,
        )
        bundle_decision = evaluate_promotion_bundle(bundle, policy)
        bundle["promotion_decision"] = dict(bundle_decision)
        bundle["rejection_reasons"] = list(bundle_decision.get("rejection_reasons", []))
        return _restore_boolean_compat_gates(_apply_bundle_policy_result(result, bundle, bundle_decision))
    except Exception as e:
        if isinstance(e, PromotionDecisionError):
            raise
        raise PromotionDecisionError(
            f"Failed to evaluate promotion for candidate {row.get('candidate_id')}: {e}"
        ) from e
