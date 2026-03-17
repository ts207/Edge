from __future__ import annotations

import json
from typing import Any, Dict, List

import numpy as np
import pandas as pd

from project.core.coercion import as_bool, safe_float, safe_int
from project.research.utils.decision_safety import (
    finite_ge,
    finite_le,
    bool_gate,
    coerce_numeric_nan,
)

from project.eval.selection_bias import deflated_sharpe_ratio as _deflated_sharpe_ratio
from project.research.helpers.viability import evaluate_retail_constraints
from project.research.promotion.multi_timeframe import evaluate_timeframe_consensus
from project.research.validation.evidence_bundle import (
    build_evidence_bundle,
    evaluate_promotion_bundle,
)

from project.research.promotion.promotion_eligibility import (
    _ReasonRecorder,
    _is_deploy_mode,
    _has_explicit_oos_samples,
    sign_consistency,
    cost_survival_ratio,
    control_rate_details_for_event,
)
from project.research.promotion.promotion_scoring import (
    calculate_promotion_score,
    stability_score,
)
from project.research.promotion.promotion_thresholds import _build_bundle_policy


def _quiet_float(value: Any, default: float) -> float:
    if value is None or (isinstance(value, float) and not np.isfinite(value)):
        return float(default)
    coerced = safe_float(value, default)
    return float(default if coerced is None else coerced)


def _quiet_int(value: Any, default: int) -> int:
    if value is None or (isinstance(value, float) and not np.isfinite(value)):
        return int(default)
    coerced = safe_int(value, default)
    return int(default if coerced is None else coerced)


def _confirmatory_shadow_gates(
    promotion_confirmatory_gates: Dict[str, Any] | None,
) -> Dict[str, Any]:
    gates = promotion_confirmatory_gates or {}
    shadow = gates.get("shadow", {})
    return shadow if isinstance(shadow, dict) else {}


def _confirmatory_deployable_gates(
    promotion_confirmatory_gates: Dict[str, Any] | None,
) -> Dict[str, Any]:
    gates = promotion_confirmatory_gates or {}
    deployable = gates.get("deployable", {})
    return deployable if isinstance(deployable, dict) else {}


def _apply_bundle_policy_result(
    base_result: Dict[str, Any], bundle: Dict[str, Any], bundle_decision: Dict[str, Any]
) -> Dict[str, Any]:
    merged = dict(base_result)
    pre_bundle_decision = str(base_result.get("promotion_decision", "rejected"))
    pre_bundle_track = str(base_result.get("promotion_track", "fallback_only"))
    pre_bundle_score = float(base_result.get("promotion_score", 0.0) or 0.0)

    merged["bundle_version"] = str(bundle.get("bundle_version", ""))
    merged["policy_version"] = str(bundle.get("policy_version", ""))
    merged["evidence_bundle_json"] = json.dumps(bundle, sort_keys=True)
    merged["pre_bundle_promotion_decision"] = pre_bundle_decision
    merged["pre_bundle_promotion_track"] = pre_bundle_track
    merged["pre_bundle_promotion_score"] = pre_bundle_score
    merged["bundle_rejection_reasons"] = "|".join(
        sorted(set(map(str, bundle_decision.get("rejection_reasons", []))))
    )
    merged["regime_flip_flag"] = bool(
        bundle.get("stability_tests", {}).get("regime_flip_flag", False)
    )
    merged["cross_symbol_sign_consistency"] = _quiet_float(
        bundle.get("stability_tests", {}).get("cross_symbol_sign_consistency", np.nan),
        np.nan,
    )
    merged["rolling_instability_score"] = _quiet_float(
        bundle.get("stability_tests", {}).get("rolling_instability_score", np.nan),
        np.nan,
    )

    gate_map = {
        "statistical": "gate_promo_statistical",
        "multiplicity_diagnostics": "gate_promo_multiplicity_diagnostics",
        "multiplicity_confirmatory": "gate_promo_multiplicity_confirmatory",
        "stability": "gate_promo_stability",
        "negative_control": "gate_promo_negative_control",
        "falsification": "gate_promo_falsification",
        "cost_survival": "gate_promo_cost_survival",
        "microstructure": "gate_promo_microstructure",
        "stressed_cost_survival": "gate_promo_stressed_cost_survival",
        "delayed_entry_stress": "gate_promo_delayed_entry_stress",
        "baseline_beats_complexity": "gate_promo_baseline_beats_complexity",
        "placebo_controls": "gate_promo_placebo_controls",
        "timeframe_consensus": "gate_promo_timeframe_consensus",
        "oos_validation": "gate_promo_oos_validation",
        "hypothesis_audit": "gate_promo_hypothesis_audit",
        "retail_viability": "gate_promo_retail_viability",
        "low_capital_viability": "gate_promo_low_capital_viability",
        "event_discipline": "gate_promo_event_discipline",
        "tob_coverage": "gate_promo_tob_coverage",
        "dsr": "gate_promo_dsr",
        "robustness": "gate_promo_robustness",
        "regime": "gate_promo_regime",
    }
    gate_results = dict(bundle_decision.get("gate_results", {}))
    for src_key, dst_key in gate_map.items():
        if src_key in gate_results:
            merged[dst_key] = str(gate_results[src_key])

    merged["promotion_decision"] = str(
        bundle_decision.get("promotion_status", merged.get("promotion_decision", "rejected"))
    )
    merged["promotion_track"] = str(
        bundle_decision.get("promotion_track", merged.get("promotion_track", "fallback_only"))
    )
    merged["promotion_score"] = float(
        bundle_decision.get("rank_score", merged.get("promotion_score", 0.0))
    )
    merged["bundle_policy_overrode_decision"] = bool(
        merged["promotion_decision"] != pre_bundle_decision
    )
    merged["bundle_policy_overrode_track"] = bool(
        merged["promotion_track"] != pre_bundle_track
    )
    merged["bundle_policy_overrode_score"] = bool(
        float(merged["promotion_score"]) != pre_bundle_score
    )

    combined_reasons = sorted(
        set(
            [r for r in str(merged.get("reject_reason", "")).split("|") if r]
            + list(bundle_decision.get("rejection_reasons", []))
        )
    )
    merged["reject_reason"] = "|".join(combined_reasons)
    primary_gate = str(merged.get("promotion_fail_gate_primary", "")).strip()
    if not primary_gate and merged["promotion_decision"] != "promoted":
        reasons = list(bundle_decision.get("rejection_reasons", []))
        if reasons:
            first_reason = str(reasons[0])
            mapped = gate_map.get(first_reason)
            if mapped:
                merged["promotion_fail_gate_primary"] = mapped
                merged["promotion_fail_reason_primary"] = f"failed_{mapped}"
    merged["fallback_used"] = bool(merged.get("promotion_track", "fallback_only") != "standard")
    merged["fallback_reason"] = (
        ""
        if not merged["fallback_used"]
        else str(
            merged.get("fallback_reason")
            or merged.get("promotion_fail_gate_primary")
            or "non_standard_track"
        )
    )
    merged["promotion_audit"] = {
        key: value for key, value in merged.items() if key.startswith("gate_")
    }
    return merged


_BOOLEAN_COMPAT_GATES = {
    "gate_promo_dsr",
    "gate_promo_low_capital_viability",
    "gate_promo_baseline_beats_complexity",
    "gate_promo_placebo_controls",
}


_CONTINUATION_TEMPLATE_VERBS = {
    "continuation",
    "trend_continuation",
    "momentum_fade",
    "pullback_entry",
    "only_if_funding",
}


def _restore_boolean_compat_gates(result: Dict[str, Any]) -> Dict[str, Any]:
    restored = dict(result)
    for key in _BOOLEAN_COMPAT_GATES:
        if key in restored:
            restored[key] = bool_gate(restored[key])
    audit = restored.get("promotion_audit")
    if isinstance(audit, dict):
        restored["promotion_audit"] = {
            key: (bool_gate(value) if key in _BOOLEAN_COMPAT_GATES else value)
            for key, value in audit.items()
        }
    return restored


def _is_continuation_template_family(row: Dict[str, Any]) -> bool:
    template_verb = str(row.get("template_verb", "")).strip().lower()
    return template_verb in _CONTINUATION_TEMPLATE_VERBS


def _evaluate_continuation_quality(
    *,
    row: Dict[str, Any],
    stability_pass: bool,
    oos_pass: bool,
    microstructure_pass: bool,
    dsr_pass: bool,
    reasons: _ReasonRecorder,
) -> Dict[str, Any]:
    is_continuation_template_family = _is_continuation_template_family(row)
    bridge_tradable = bool_gate(row.get("gate_bridge_tradable"))
    continuation_quality_pass = True
    if is_continuation_template_family and bridge_tradable:
        continuation_quality_pass = bool(
            stability_pass and oos_pass and microstructure_pass and dsr_pass
        )
        if not continuation_quality_pass:
            if not stability_pass:
                reasons.add_reject(
                    "continuation_quality_stability",
                    category="continuation_quality",
                )
            if not oos_pass:
                reasons.add_reject(
                    "continuation_quality_oos_validation",
                    category="continuation_quality",
                )
            if not microstructure_pass:
                reasons.add_reject(
                    "continuation_quality_microstructure",
                    category="continuation_quality",
                )
            if not dsr_pass:
                reasons.add_reject(
                    "continuation_quality_dsr",
                    category="continuation_quality",
                )
            reasons.add_promo_fail(
                "gate_promo_continuation_quality",
                category="continuation_quality",
            )
    return {
        "is_continuation_template_family": bool(is_continuation_template_family),
        "bridge_tradable": bool(bridge_tradable),
        "continuation_quality_pass": bool(continuation_quality_pass),
    }


def _evaluate_market_execution_and_stability(
    *,
    row: Dict[str, Any],
    min_tob_coverage: float,
    min_net_expectancy_bps: float,
    max_fee_plus_slippage_bps: float | None,
    max_daily_turnover_multiple: float | None,
    require_retail_viability: bool,
    min_cost_survival_ratio: float,
    min_stability_score: float,
    min_sign_consistency: float,
    enforce_baseline_beats_complexity: bool,
    enforce_placebo_controls: bool,
    enforce_timeframe_consensus: bool,
    reasons: _ReasonRecorder,
) -> Dict[str, Any]:
    retail_eval = evaluate_retail_constraints(
        row,
        min_tob_coverage=float(min_tob_coverage),
        min_net_expectancy_bps=float(min_net_expectancy_bps),
        max_fee_plus_slippage_bps=max_fee_plus_slippage_bps,
        max_daily_turnover_multiple=max_daily_turnover_multiple,
    )
    tob_coverage = coerce_numeric_nan(retail_eval.get("tob_coverage"))
    net_expectancy_bps = coerce_numeric_nan(retail_eval.get("net_expectancy_bps"))
    effective_cost_bps = _quiet_float(retail_eval.get("effective_cost_bps"), np.nan)
    turnover_proxy_mean = _quiet_float(retail_eval.get("turnover_proxy_mean"), np.nan)

    tob_pass = bool_gate(retail_eval.get("gate_tob_coverage"))
    net_expectancy_pass = bool_gate(retail_eval.get("gate_net_expectancy"))
    cost_budget_pass = bool_gate(retail_eval.get("gate_cost_budget"))
    turnover_pass = bool_gate(retail_eval.get("gate_turnover"))
    retail_viability_pass = bool(net_expectancy_pass and cost_budget_pass and turnover_pass)

    if bool(require_retail_viability) and not retail_viability_pass:
        if not net_expectancy_pass:
            reasons.add_pair(
                reject_reason="retail_net_expectancy",
                promo_fail_reason="gate_promo_retail_net_expectancy",
                category="retail_viability",
            )
        if not cost_budget_pass:
            reasons.add_pair(
                reject_reason="retail_cost_budget",
                promo_fail_reason="gate_promo_retail_cost_budget",
                category="retail_viability",
            )
        if not turnover_pass:
            reasons.add_pair(
                reject_reason="retail_turnover",
                promo_fail_reason="gate_promo_retail_turnover",
                category="retail_viability",
            )

    csr = cost_survival_ratio(row)
    cost_pass = finite_ge(csr, min_cost_survival_ratio)
    if not cost_pass:
        reasons.add_pair(
            reject_reason="cost_survival",
            promo_fail_reason="gate_promo_cost_survival",
            category="cost_realism",
        )

    baseline_expectancy = coerce_numeric_nan(row.get("baseline_expectancy_bps"))
    beats_baseline = bool(
        np.isfinite(net_expectancy_bps)
        and np.isfinite(baseline_expectancy)
        and (net_expectancy_bps > baseline_expectancy * 1.1)
    )
    if bool(enforce_baseline_beats_complexity) and not beats_baseline:
        reasons.add_pair(
            reject_reason="failed_baseline_comparison",
            promo_fail_reason="gate_promo_baseline_beats_complexity",
            category="baseline_comparison",
        )

    shift_placebo_pass = bool_gate(row.get("pass_shift_placebo"))
    random_placebo_pass = bool_gate(row.get("pass_random_entry_placebo"))
    direction_placebo_pass = bool_gate(row.get("pass_direction_reversal_placebo"))
    placebo_pass = shift_placebo_pass and random_placebo_pass and direction_placebo_pass
    if bool(enforce_placebo_controls) and not placebo_pass:
        reasons.add_pair(
            reject_reason="failed_placebo_controls",
            promo_fail_reason="gate_promo_placebo_controls",
            category="falsification",
        )

    sc = sign_consistency(row)
    ss = stability_score(row, sc)
    gate_stability = bool_gate(row.get("gate_stability"))
    gate_delay_robustness = bool_gate(row.get("gate_delay_robustness"))
    stability_pass = (
        gate_stability
        and finite_ge(ss, min_stability_score)
        and finite_ge(sc, min_sign_consistency)
        and gate_delay_robustness
    )
    if not stability_pass:
        if not gate_stability:
            reasons.add_pair(
                reject_reason="stability_gate",
                promo_fail_reason="gate_promo_stability_gate",
                category="stability",
            )
        if ss < float(min_stability_score):
            reasons.add_pair(
                reject_reason="stability_score",
                promo_fail_reason="gate_promo_stability_score",
                category="stability",
            )
        if sc < float(min_sign_consistency):
            reasons.add_pair(
                reject_reason="stability_sign_consistency",
                promo_fail_reason="gate_promo_stability_sign_consistency",
                category="stability",
            )
        if not gate_delay_robustness:
            reasons.add_pair(
                reject_reason="delay_robustness_fail",
                promo_fail_reason="gate_promo_delay_robustness_fail",
                category="stability",
            )

    consensus_eval = evaluate_timeframe_consensus(
        base_timeframe="5m",
        alternate_timeframes=["1m", "15m"],
        row=row,
        min_consensus_ratio=0.3,
    )
    timeframe_consensus_pass = bool(consensus_eval["pass_consensus"])
    if bool(enforce_timeframe_consensus) and not timeframe_consensus_pass:
        reasons.add_pair(
            reject_reason="timeframe_consensus_fail",
            promo_fail_reason="gate_promo_timeframe_consensus",
            category="timeframe_consensus",
        )

    microstructure_pass = bool_gate(row.get("gate_bridge_microstructure"))
    if not microstructure_pass:
        reasons.add_pair(
            reject_reason="microstructure_risk",
            promo_fail_reason="gate_promo_microstructure",
            category="microstructure",
        )

    stressed_cost_pass = bool_gate(row.get("gate_after_cost_stressed_positive"))
    if not stressed_cost_pass:
        reasons.add_pair(
            reject_reason="stressed_cost_survival_fail",
            promo_fail_reason="gate_promo_stressed_cost_survival",
            category="stress_tests",
        )

    delayed_entry_pass = bool_gate(row.get("gate_delayed_entry_stress"))
    if not delayed_entry_pass:
        reasons.add_pair(
            reject_reason="delayed_entry_fragility",
            promo_fail_reason="gate_promo_delayed_entry_stress",
            category="stress_tests",
        )

    return {
        "tob_coverage": tob_coverage,
        "net_expectancy_bps": net_expectancy_bps,
        "effective_cost_bps": effective_cost_bps,
        "turnover_proxy_mean": turnover_proxy_mean,
        "tob_pass": tob_pass,
        "net_expectancy_pass": net_expectancy_pass,
        "cost_budget_pass": cost_budget_pass,
        "turnover_pass": turnover_pass,
        "retail_viability_pass": retail_viability_pass,
        "csr": csr,
        "cost_pass": cost_pass,
        "beats_baseline": beats_baseline,
        "placebo_pass": placebo_pass,
        "sc": sc,
        "ss": ss,
        "stability_pass": stability_pass,
        "timeframe_consensus_pass": timeframe_consensus_pass,
        "microstructure_pass": microstructure_pass,
        "stressed_cost_pass": stressed_cost_pass,
        "delayed_entry_pass": delayed_entry_pass,
    }


def _evaluate_control_audit_and_dsr(
    *,
    row: Dict[str, Any],
    event_type: str,
    plan_row_id: str,
    hypothesis_index: Dict[str, Dict[str, Any]],
    negative_control_summary: Dict[str, Any],
    max_negative_control_pass_rate: float,
    allow_missing_negative_controls: bool,
    require_multiplicity_diagnostics: bool,
    require_hypothesis_audit: bool,
    min_dsr: float,
    reasons: _ReasonRecorder,
) -> Dict[str, Any]:
    control_details = control_rate_details_for_event(
        row=row,
        event_type=event_type,
        summary=negative_control_summary,
    )
    control_rate = control_details["rate"]
    control_rate_source = str(control_details["source"])
    if control_rate is None:
        control_pass = bool(allow_missing_negative_controls)
        if not control_pass:
            reasons.add_pair(
                reject_reason="negative_control_missing",
                promo_fail_reason="gate_promo_negative_control_missing",
                category="negative_controls",
            )
    else:
        control_pass = control_rate <= float(max_negative_control_pass_rate)
        if not control_pass:
            reasons.add_pair(
                reject_reason="negative_control_fail",
                promo_fail_reason="gate_promo_negative_control_fail",
                category="negative_controls",
            )

    q_value_by = _quiet_float(row.get("q_value_by"), np.nan)
    q_value_cluster = _quiet_float(row.get("q_value_cluster"), np.nan)
    multiplicity_diag_available = bool(
        np.isfinite(q_value_by) and np.isfinite(q_value_cluster)
    )
    multiplicity_diag_pass = bool(
        (not require_multiplicity_diagnostics) or multiplicity_diag_available
    )
    if not multiplicity_diag_pass:
        reasons.add_pair(
            reject_reason="multiplicity_diagnostics_missing",
            promo_fail_reason="gate_promo_multiplicity_diagnostics",
            category="multiplicity_diagnostics",
        )

    audit_pass = True
    audit_statuses: List[str] = []
    if plan_row_id:
        audit_info = hypothesis_index.get(plan_row_id)
        if audit_info:
            audit_statuses = list(audit_info.get("statuses", []))
            audit_pass = bool(audit_info.get("executed", False))
            if not audit_pass:
                reasons.add_pair(
                    reject_reason="hypothesis_not_executed",
                    promo_fail_reason="gate_promo_hypothesis_not_executed",
                    category="hypothesis_audit",
                )
        else:
            if require_hypothesis_audit:
                audit_pass = False
                reasons.add_pair(
                    reject_reason="hypothesis_missing_audit",
                    promo_fail_reason="gate_promo_hypothesis_missing_audit",
                    category="hypothesis_audit",
                )
    elif require_hypothesis_audit:
        audit_pass = False
        reasons.add_pair(
            reject_reason="hypothesis_missing_plan_row_id",
            promo_fail_reason="gate_promo_hypothesis_missing_plan_row_id",
            category="hypothesis_audit",
        )

    dsr_value = 0.0
    dsr_pass = True
    if float(min_dsr) > 0.0:
        returns_oos = row.get("returns_oos_combined")
        n_trials = max(1, _quiet_int(row.get("num_tests_event_family", 1), 1))
        if isinstance(returns_oos, (list, np.ndarray, pd.Series)) and len(returns_oos) >= 10:
            oos_series = pd.Series(returns_oos)
            dsr_value = float(_deflated_sharpe_ratio(oos_series, n_trials=n_trials))
        else:
            dsr_pass = False
            reasons.add_reject("missing_realized_oos_path", category="dsr")
            dsr_value = 0.0

        dsr_pass = dsr_pass and (dsr_value >= float(min_dsr))
        if not dsr_pass:
            if "missing_realized_oos_path" not in reasons.reject_reasons:
                reasons.add_reject("dsr_below_threshold", category="dsr")
            reasons.add_promo_fail("gate_promo_dsr", category="dsr")

    return {
        "control_rate": control_rate,
        "control_rate_source": control_rate_source,
        "control_pass": control_pass,
        "q_value_by": q_value_by,
        "q_value_cluster": q_value_cluster,
        "multiplicity_diag_pass": multiplicity_diag_pass,
        "audit_pass": audit_pass,
        "audit_statuses": audit_statuses,
        "dsr_value": dsr_value,
        "dsr_pass": dsr_pass,
    }


def _evaluate_deploy_oos_and_low_capital(
    *,
    row: Dict[str, Any],
    max_q_value: float,
    promotion_confirmatory_gates: Dict[str, Any] | None,
    require_low_capital_viability: bool,
    reasons: _ReasonRecorder,
) -> Dict[str, Any]:
    q_value_family = _quiet_float(row.get("q_value_family"), np.nan)
    q_value_cluster = _quiet_float(row.get("q_value_cluster"), np.nan)
    q_value_by = _quiet_float(row.get("q_value_by"), np.nan)
    q_value_program = _quiet_float(row.get("q_value_program"), np.nan)
    shrinkage_loso_stable = as_bool(row.get("shrinkage_loso_stable", False))
    shrinkage_borrowing_dominant = as_bool(row.get("shrinkage_borrowing_dominant", False))
    structural_robustness_score = _quiet_float(row.get("structural_robustness_score"), np.nan)
    repeated_fold_consistency = _quiet_float(row.get("repeated_fold_consistency"), np.nan)
    robustness_panel_complete = as_bool(row.get("robustness_panel_complete", False))
    regime_counts = row.get("regime_counts", {})
    if isinstance(regime_counts, str):
        try:
            regime_counts = json.loads(regime_counts)
        except Exception:
            regime_counts = {}
    if not isinstance(regime_counts, dict):
        regime_counts = {}
    num_regimes = len([r for r, c in regime_counts.items() if _quiet_int(c, 0) >= 10])
    regime_stability_pass = as_bool(row.get("gate_regime_stability", False))
    structural_break_pass = as_bool(row.get("gate_structural_break", False))

    is_deploy = _is_deploy_mode(row)
    multiplicity_pass, robustness_pass, regime_pass = True, True, True

    if is_deploy:
        deployable_gates = _confirmatory_deployable_gates(promotion_confirmatory_gates)
        cluster_pass = (
            np.isfinite(q_value_cluster) and (q_value_cluster <= float(max_q_value))
        ) or as_bool(row.get("waiver_bounded_correlation", False))
        by_pass = np.isfinite(q_value_by) and (q_value_by <= float(max_q_value) * 2.0)
        if not cluster_pass:
            reasons.add_reject(
                "multiplicity_cluster_q", category="deploy_confirmatory", deploy_only=True
            )
            multiplicity_pass = False
        if not by_pass:
            reasons.add_reject(
                "multiplicity_by_diagnostic",
                category="deploy_confirmatory",
                deploy_only=True,
            )
            multiplicity_pass = False
        if not shrinkage_loso_stable:
            reasons.add_reject(
                "shrinkage_loso_unstable", category="deploy_confirmatory", deploy_only=True
            )
            multiplicity_pass = False
        if shrinkage_borrowing_dominant:
            reasons.add_reject(
                "shrinkage_borrowing_dominant",
                category="deploy_confirmatory",
                deploy_only=True,
            )
            multiplicity_pass = False
        if not robustness_panel_complete:
            reasons.add_reject(
                "robustness_panel_incomplete",
                category="deploy_confirmatory",
                deploy_only=True,
            )
            robustness_pass = False
        elif (
            not np.isfinite(structural_robustness_score)
        ) or structural_robustness_score < 0.6:
            reasons.add_reject(
                "robustness_structural_low",
                category="deploy_confirmatory",
                deploy_only=True,
            )
            robustness_pass = False
        if (not np.isfinite(repeated_fold_consistency)) or repeated_fold_consistency < 0.5:
            reasons.add_reject(
                "temporal_consistency_low",
                category="deploy_confirmatory",
                deploy_only=True,
            )
            robustness_pass = False

        min_regimes_req = int(deployable_gates.get("min_regimes_supported", 2))
        if num_regimes < min_regimes_req and not as_bool(
            row.get("is_regime_specific", False)
        ):
            reasons.add_reject(
                f"regime_thin_support (regimes={num_regimes} < {min_regimes_req})",
                category="deploy_confirmatory",
                deploy_only=True,
            )
            regime_pass = False
        if not regime_stability_pass:
            reasons.add_reject(
                "regime_instability", category="deploy_confirmatory", deploy_only=True
            )
            regime_pass = False
        if not structural_break_pass:
            reasons.add_reject(
                "structural_break_detected", category="deploy_confirmatory", deploy_only=True
            )
            regime_pass = False
        bridge_certified = as_bool(row.get("bridge_certified", False))
        if not bridge_certified:
            reasons.add_reject(
                "bridge_uncertified", category="deploy_confirmatory", deploy_only=True
            )
            robustness_pass = False

    validation_samples = safe_int(row.get("validation_samples", 0), 0)
    test_samples = safe_int(row.get("test_samples", 0), 0)
    oos_pass = True
    if _has_explicit_oos_samples(row):
        shadow_gates = _confirmatory_shadow_gates(promotion_confirmatory_gates)
        min_val_events = int(shadow_gates.get("min_oos_event_count", 20))
        min_test_events = int(shadow_gates.get("min_oos_event_count", 20))
        train_effect = coerce_numeric_nan(
            row.get("mean_train_return", row.get("effect_raw"))
        )
        val_effect = coerce_numeric_nan(row.get("mean_validation_return"))
        test_effect = coerce_numeric_nan(row.get("mean_test_return"))
        direction_match = True
        if abs(train_effect) > 1e-9:
            if abs(val_effect) > 1e-9 and np.sign(val_effect) != np.sign(train_effect):
                direction_match = False
            if abs(test_effect) > 1e-9 and np.sign(test_effect) != np.sign(train_effect):
                direction_match = False
        oos_pass = validation_samples >= min_val_events
        if "test_samples" in row:
            oos_pass = oos_pass and (test_samples >= min_test_events)
        oos_pass = oos_pass and direction_match
        if not oos_pass:
            if validation_samples < min_val_events or test_samples < min_test_events:
                reasons.add_reject(
                    f"oos_insufficient_samples (val={validation_samples}, test={test_samples})",
                    category="oos_validation",
                )
            if not direction_match:
                reasons.add_reject("oos_direction_flip", category="oos_validation")
            reasons.add_promo_fail("gate_promo_oos_validation", category="oos_validation")

    low_capital_viability_pass = bool_gate(row.get("gate_bridge_low_capital_viability"))
    low_capital_viability_score = _quiet_float(
        row.get("low_capital_viability_score", np.nan), np.nan
    )
    low_capital_reject_codes = [
        token.strip()
        for token in str(row.get("low_capital_reject_reason_codes", "")).split(",")
        if token.strip()
    ]
    if bool(require_low_capital_viability) and not low_capital_viability_pass:
        reasons.add_reject("low_capital_viability", category="low_capital_viability")
        for code in low_capital_reject_codes:
            reasons.add_reject(code.lower(), category="low_capital_viability")
        reasons.add_promo_fail(
            "gate_promo_low_capital_viability", category="low_capital_viability"
        )

    return {
        "run_mode_normalized": str(row.get("run_mode", "")).strip().lower(),
        "is_deploy_mode": is_deploy,
        "deploy_only_reject_reasons": list(reasons.deploy_only_reject_reasons),
        "q_value_family": q_value_family,
        "q_value_cluster": q_value_cluster,
        "q_value_by": q_value_by,
        "q_value_program": q_value_program,
        "shrinkage_loso_stable": shrinkage_loso_stable,
        "shrinkage_borrowing_dominant": shrinkage_borrowing_dominant,
        "structural_robustness_score": structural_robustness_score,
        "repeated_fold_consistency": repeated_fold_consistency,
        "robustness_panel_complete": robustness_panel_complete,
        "num_regimes": num_regimes,
        "regime_stability_pass": regime_stability_pass,
        "structural_break_pass": structural_break_pass,
        "multiplicity_pass": multiplicity_pass,
        "robustness_pass": robustness_pass,
        "regime_pass": regime_pass,
        "oos_pass": oos_pass,
        "low_capital_viability_pass": low_capital_viability_pass,
        "low_capital_viability_score": low_capital_viability_score,
        "low_capital_reject_codes": low_capital_reject_codes,
    }


def _assemble_promotion_result(
    *,
    reasons: _ReasonRecorder,
    q_value: float,
    n_events: int,
    tob_pass: bool,
    require_retail_viability: bool,
    require_low_capital_viability: bool,
    enforce_baseline_beats_complexity: bool,
    enforce_placebo_controls: bool,
    enforce_timeframe_consensus: bool,
    statistical_pass: bool,
    cost_pass: bool,
    beats_baseline: bool,
    placebo_pass: bool,
    stability_pass: bool,
    timeframe_consensus_pass: bool,
    oos_pass: bool,
    microstructure_pass: bool,
    stressed_cost_pass: bool,
    delayed_entry_pass: bool,
    continuation_quality_pass: bool,
    multiplicity_diag_pass: bool,
    audit_pass: bool,
    dsr_pass: bool,
    multiplicity_pass: bool,
    robustness_pass: bool,
    regime_pass: bool,
    retail_viability_pass: bool,
    low_capital_viability_pass: bool,
    q_value_family: float,
    q_value_cluster: float,
    q_value_by: float,
    q_value_program: float,
    ss: float,
    sc: float,
    csr: float,
    control_pass: bool,
    control_rate: float | None,
    control_rate_source: str,
    tob_coverage: float,
    net_expectancy_bps: float,
    effective_cost_bps: float,
    turnover_proxy_mean: float,
    audit_statuses: List[str],
    net_expectancy_pass: bool,
    cost_budget_pass: bool,
    turnover_pass: bool,
    dsr_value: float,
    shrinkage_loso_stable: bool,
    shrinkage_borrowing_dominant: bool,
    structural_robustness_score: float,
    repeated_fold_consistency: float,
    robustness_panel_complete: bool,
    num_regimes: int,
    regime_stability_pass: bool,
    structural_break_pass: bool,
    low_capital_viability_score: float,
    low_capital_reject_codes: List[str],
    run_mode_normalized: str,
    is_deploy_mode: bool,
    is_descriptive: bool,
    is_trade_trigger: bool,
    max_q_value: float,
    promotion_profile: str,
) -> Dict[str, Any]:
    promoted = bool(
        statistical_pass
        and cost_pass
        and (beats_baseline or not bool(enforce_baseline_beats_complexity))
        and (placebo_pass or not bool(enforce_placebo_controls))
        and stability_pass
        and (timeframe_consensus_pass or not bool(enforce_timeframe_consensus))
        and oos_pass
        and microstructure_pass
        and stressed_cost_pass
        and delayed_entry_pass
        and continuation_quality_pass
        and multiplicity_diag_pass
        and audit_pass
        and dsr_pass
        and multiplicity_pass
        and robustness_pass
        and regime_pass
        and (retail_viability_pass or not bool(require_retail_viability))
        and (low_capital_viability_pass or not bool(require_low_capital_viability))
    )

    promotion_track = "standard" if (promoted and tob_pass) else "fallback_only"
    promotion_decision = "promoted" if promoted else "rejected"
    promotion_score = calculate_promotion_score(
        statistical_pass=statistical_pass,
        stability_pass=stability_pass,
        cost_pass=cost_pass,
        tob_pass=tob_pass,
        oos_pass=oos_pass,
        multiplicity_pass=multiplicity_pass,
        placebo_pass=placebo_pass,
        timeframe_consensus_pass=timeframe_consensus_pass,
    )
    primary_promo_fail = reasons.primary_promo_fail()
    fallback_used = promotion_track != "standard"
    fallback_reason = (
        "" if not fallback_used else (primary_promo_fail or "non_standard_track")
    )

    return {
        "promotion_decision": promotion_decision,
        "promotion_profile": str(promotion_profile),
        "promotion_track": promotion_track,
        "fallback_used": bool(fallback_used),
        "fallback_reason": str(fallback_reason),
        "promotion_score": float(promotion_score),
        "reject_reason": reasons.unique_reject_reason_str(),
        "promotion_fail_gate_primary": primary_promo_fail,
        "promotion_fail_reason_primary": f"failed_{primary_promo_fail}"
        if primary_promo_fail
        else "",
        "run_mode_normalized": run_mode_normalized,
        "is_deploy_mode": bool(is_deploy_mode),
        "deploy_only_reject_reason": reasons.unique_deploy_only_reject_reason_str(),
        "reject_reason_categories_json": reasons.categorized_reject_json(),
        "promotion_fail_reason_categories_json": reasons.categorized_promo_fail_json(),
        "q_value": float(q_value),
        "q_value_family": float(q_value_family),
        "q_value_cluster": float(q_value_cluster),
        "q_value_by": float(q_value_by),
        "q_value_program": float(q_value_program),
        "n_events": int(n_events),
        "stability_score": float(ss),
        "sign_consistency": float(sc),
        "cost_survival_ratio": float(csr),
        "control_pass_rate": None if control_rate is None else float(control_rate),
        "control_rate_source": control_rate_source,
        "tob_coverage": float(tob_coverage),
        "net_expectancy_bps": float(net_expectancy_bps),
        "effective_cost_bps": None
        if not np.isfinite(effective_cost_bps)
        else float(effective_cost_bps),
        "turnover_proxy_mean": None
        if not np.isfinite(turnover_proxy_mean)
        else float(turnover_proxy_mean),
        "audit_statuses": audit_statuses,
        "gate_promo_statistical": "pass" if statistical_pass else "fail",
        "gate_promo_multiplicity_diagnostics": "pass" if multiplicity_diag_pass else "fail",
        "gate_promo_multiplicity_cluster": "pass" if (np.isfinite(q_value_cluster) and (q_value_cluster <= float(max_q_value))) else "fail",
        "gate_promo_multiplicity_confirmatory": "pass" if multiplicity_pass else "fail",
        "gate_promo_stability": "pass" if stability_pass else "fail",
        "gate_promo_cost_survival": "pass" if cost_pass else "fail",
        "gate_promo_negative_control": "pass" if control_pass else "fail",
        "gate_promo_falsification": "pass" if (control_pass and placebo_pass) else "fail",
        "gate_promo_hypothesis_audit": "pass" if audit_pass else "fail",
        "gate_promo_tob_coverage": "pass" if tob_pass else "fail",
        "gate_promo_oos_validation": "pass" if oos_pass else "fail",
        "gate_promo_microstructure": "pass" if microstructure_pass else "fail",
        "gate_promo_retail_net_expectancy": bool(net_expectancy_pass),
        "gate_promo_retail_cost_budget": bool(cost_budget_pass),
        "gate_promo_retail_turnover": bool(turnover_pass),
        "gate_promo_retail_viability": "pass" if retail_viability_pass else "fail",
        "gate_promo_low_capital_viability": bool(low_capital_viability_pass),
        "low_capital_viability_score": None
        if not np.isfinite(low_capital_viability_score)
        else float(low_capital_viability_score),
        "low_capital_reject_reason_codes": ",".join(low_capital_reject_codes),
        "dsr_value": float(dsr_value),
        "gate_promo_dsr": bool(dsr_pass),
        "shrinkage_loso_stable": bool(shrinkage_loso_stable),
        "shrinkage_borrowing_dominant": bool(shrinkage_borrowing_dominant),
        "structural_robustness_score": float(structural_robustness_score),
        "repeated_fold_consistency": float(repeated_fold_consistency),
        "robustness_panel_complete": bool(robustness_panel_complete),
        "gate_promo_robustness": "pass" if robustness_pass else "fail",
        "gate_promo_regime": "pass" if regime_pass else "fail",
        "gate_regime_stability": "pass" if regime_stability_pass else "fail",
        "num_regimes_supported": int(num_regimes),
        "gate_structural_break": "pass" if structural_break_pass else "fail",
        "gate_promo_baseline_beats_complexity": bool(beats_baseline),
        "gate_promo_placebo_controls": bool(placebo_pass),
        "gate_promo_event_discipline": "pass" if (not is_descriptive and is_trade_trigger) else "fail",
        "gate_promo_stressed_cost_survival": "pass" if stressed_cost_pass else "fail",
        "gate_promo_delayed_entry_stress": "pass" if delayed_entry_pass else "fail",
        "gate_promo_timeframe_consensus": "pass" if timeframe_consensus_pass else "fail",
        "gate_promo_continuation_quality": "pass" if continuation_quality_pass else "fail",
    }


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
) -> Dict[str, Any]:
    from project.core.exceptions import PromotionDecisionError
    try:
        reasons = _ReasonRecorder.create()
        event_type = (
            str(row.get("event_type", row.get("event", ""))).strip() or "UNKNOWN_EVENT"
        )
        plan_row_id = str(row.get("plan_row_id", "")).strip()
        n_events = _quiet_int(row.get("n_events", row.get("sample_size", 0)), 0)
        q_value = coerce_numeric_nan(row.get("q_value"))

        # Layer 1: Global event discipline
        is_descriptive = as_bool(row.get("event_is_descriptive", False))
        is_trade_trigger = as_bool(row.get("event_is_trade_trigger", True))
        if is_descriptive or not is_trade_trigger:
            reasons.add_pair(
                reject_reason="descriptive_only_event",
                promo_fail_reason="gate_promo_event_discipline",
                category="event_discipline",
            )

        # Layer 2: Event Validity
        q_value_available = bool(np.isfinite(q_value))
        statistical_pass = (
            q_value_available
            and finite_le(q_value, max_q_value)
            and (n_events >= int(min_events))
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

        # Layer 3 & 4: Market, Execution, Baseline and Stability
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

        # Layer 5: Controls, Audit and DSR
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

        # Layer 6: Deploy, OOS and Low Capital
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

        # Layer 7: Assemble Result
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
        return _restore_boolean_compat_gates(
            _apply_bundle_policy_result(result, bundle, bundle_decision)
        )
    except Exception as e:
        if isinstance(e, PromotionDecisionError):
            raise
        raise PromotionDecisionError(f"Failed to evaluate promotion for candidate {row.get('candidate_id')}: {e}") from e
