from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Mapping, Sequence

import pandas as pd


DEFAULT_DRIFT_THRESHOLDS: Dict[str, float] = {
    "max_phase2_candidate_count_delta_abs": 10.0,
    "max_phase2_survivor_count_delta_abs": 2.0,
    "max_phase2_zero_eval_rows_increase": 0.0,
    "max_phase2_survivor_q_value_increase": 0.05,
    "max_phase2_survivor_estimate_bps_drop": 3.0,
    "max_promotion_promoted_count_delta_abs": 2.0,
    "max_reject_reason_shift_abs": 3.0,
    "max_edge_tradable_count_delta_abs": 2.0,
    "max_edge_candidate_count_delta_abs": 2.0,
    "max_edge_after_cost_positive_validation_count_delta_abs": 2.0,
    "max_edge_median_resolved_cost_bps_delta_abs": 0.25,
    "max_edge_median_expectancy_bps_delta_abs": 0.25,
    "max_regime_incidence_drift_abs": 0.15,
    "max_regime_actionability_drift_abs": 2.0,
    "max_regime_direct_proxy_gap_drift_abs": 5.0,
}


def research_diagnostics_paths(*, data_root: Path, run_id: str) -> Dict[str, Path]:
    return {
        "phase2": data_root
        / "reports"
        / "phase2"
        / run_id
        / "search_engine"
        / "phase2_diagnostics.json",
        "promotion": data_root / "reports" / "promotions" / run_id / "promotion_diagnostics.json",
        "edge_candidates": data_root
        / "reports"
        / "edge_candidates"
        / run_id
        / "edge_candidates_normalized.parquet",
        "regime_effectiveness": data_root
        / "reports"
        / "regime_effectiveness"
        / run_id
        / "regime_effectiveness_summary.json",
    }


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _as_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _read_parquet(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_parquet(path)
    except Exception:
        return pd.DataFrame()


def _series_median(df: pd.DataFrame, column: str, default: float = 0.0) -> float:
    if column not in df.columns or df.empty:
        return float(default)
    series = pd.to_numeric(df[column], errors="coerce").dropna()
    if series.empty:
        return float(default)
    return float(series.median())


def _count_pass_like(df: pd.DataFrame, column: str) -> int:
    if column not in df.columns or df.empty:
        return 0
    values = df[column]
    normalized = values.astype(str).str.strip().str.lower()
    return int(normalized.isin({"1", "true", "pass", "passed", "ok"}).sum())


def _run_manifest_path(*, data_root: Path, run_id: str) -> Path:
    return data_root / "runs" / run_id / "run_manifest.json"


def _checklist_path(*, data_root: Path, run_id: str) -> Path:
    return data_root / "runs" / run_id / "research_checklist" / "checklist.json"


def _as_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def summarize_phase2_distribution(diagnostics: Mapping[str, Any]) -> Dict[str, Any]:
    false_diag = diagnostics.get("false_discovery_diagnostics", {})
    global_diag = false_diag.get("global", {})
    sample_quality = false_diag.get("sample_quality", {})
    sample_quality_gate = false_diag.get("sample_quality_gate", {})
    survivor_quality = false_diag.get("survivor_quality", {})
    symbol_diagnostics = diagnostics.get("symbol_diagnostics", []) or []
    return {
        "candidate_count": _as_int(
            global_diag.get(
                "candidates_total",
                diagnostics.get(
                    "combined_candidate_rows", diagnostics.get("bridge_candidates_rows", 0)
                ),
            )
        ),
        "survivor_count": _as_int(
            global_diag.get("survivors_total", diagnostics.get("multiplicity_discoveries", 0))
        ),
        "symbol_count": _as_int(
            global_diag.get(
                "symbols_total",
                len(diagnostics.get("symbols_with_candidates", []) or symbol_diagnostics),
            )
        ),
        "family_count": _as_int(global_diag.get("families_total", 0)),
        "discovery_profile": str(diagnostics.get("discovery_profile", "") or ""),
        "search_spec": str(diagnostics.get("search_spec", "") or ""),
        "zero_eval_rows": _as_int(sample_quality.get("zero_eval_rows", 0)),
        "sample_quality_gate_rejections": _as_int(
            sample_quality_gate.get("rejected_by_sample_quality_gate", 0)
        ),
        "median_validation_n_obs": _as_float(sample_quality.get("median_validation_n_obs", 0.0)),
        "median_test_n_obs": _as_float(sample_quality.get("median_test_n_obs", 0.0)),
        "median_survivor_q_value": _as_float(survivor_quality.get("median_q_value", 1.0), 1.0),
        "median_survivor_estimate_bps": _as_float(survivor_quality.get("median_estimate_bps", 0.0)),
    }


def summarize_promotion_distribution(diagnostics: Mapping[str, Any]) -> Dict[str, Any]:
    decision_summary = diagnostics.get("decision_summary", {})
    return {
        "candidate_count": _as_int(decision_summary.get("candidates_total", 0)),
        "promoted_count": _as_int(decision_summary.get("promoted_count", 0)),
        "rejected_count": _as_int(decision_summary.get("rejected_count", 0)),
        "mean_failed_gate_count_rejected": _as_float(
            decision_summary.get("mean_failed_gate_count_rejected", 0.0)
        ),
        "primary_fail_gate_counts": dict(decision_summary.get("primary_fail_gate_counts", {})),
        "primary_reject_reason_counts": dict(
            decision_summary.get("primary_reject_reason_counts", {})
        ),
    }


def summarize_edge_candidate_distribution(frame: pd.DataFrame) -> Dict[str, Any]:
    return {
        "candidate_count": int(len(frame)),
        "tradable_count": _count_pass_like(frame, "gate_bridge_tradable"),
        "after_cost_positive_validation_count": _count_pass_like(
            frame, "gate_bridge_after_cost_positive_validation"
        ),
        "median_resolved_cost_bps": _series_median(frame, "resolved_cost_bps", 0.0),
        "median_expectancy_bps": _series_median(frame, "expectancy_bps", 0.0),
        "median_avg_dynamic_cost_bps": _series_median(frame, "avg_dynamic_cost_bps", 0.0),
        "median_bridge_validation_after_cost_bps": _series_median(
            frame, "bridge_validation_after_cost_bps", 0.0
        ),
    }


def summarize_regime_effectiveness_distribution(summary: Mapping[str, Any]) -> Dict[str, Any]:
    top_regimes = summary.get("top_regimes_by_incidence", [])
    bucket_counts = summary.get("recommended_bucket_counts", {})
    if not isinstance(top_regimes, list):
        top_regimes = []
    if not isinstance(bucket_counts, Mapping):
        bucket_counts = {}
    top_regime = top_regimes[0] if top_regimes else {}
    return {
        "status": str(summary.get("status", "") or ""),
        "regimes_total": _as_int(summary.get("regimes_total", 0)),
        "episodes_total": _as_int(summary.get("episodes_total", 0)),
        "scorecard_rows": _as_int(summary.get("scorecard_rows", 0)),
        "top_regime": str(top_regime.get("canonical_regime", "") or ""),
        "top_regime_episode_count": _as_int(top_regime.get("episode_count", 0)),
        "trade_generating_count": _as_int(bucket_counts.get("trade_generating", 0)),
        "trade_filtering_count": _as_int(bucket_counts.get("trade_filtering", 0)),
        "context_only_count": _as_int(bucket_counts.get("context_only", 0)),
    }


def summarize_run_research_status(
    *,
    data_root: Path,
    run_id: str,
) -> Dict[str, Any]:
    manifest = _read_json(_run_manifest_path(data_root=data_root, run_id=run_id))
    checklist = _read_json(_checklist_path(data_root=data_root, run_id=run_id))
    diag_paths = research_diagnostics_paths(data_root=data_root, run_id=run_id)
    phase2 = summarize_phase2_distribution(_read_json(diag_paths["phase2"]))
    promotion = summarize_promotion_distribution(_read_json(diag_paths["promotion"]))
    edge_candidates = summarize_edge_candidate_distribution(_read_parquet(diag_paths["edge_candidates"]))
    regime_effectiveness = summarize_regime_effectiveness_distribution(
        _read_json(diag_paths["regime_effectiveness"])
    )
    manifest_status = str(manifest.get("status", "") or "").strip().lower()
    checklist_decision = str(
        checklist.get("decision", manifest.get("checklist_decision", "")) or ""
    ).strip()
    failed_stage = str(manifest.get("failed_stage", "") or "").strip()
    if manifest_status != "success":
        trust_classification = "infrastructure_suspect"
    elif checklist_decision == "KEEP_RESEARCH":
        trust_classification = "research_reject"
    elif checklist_decision:
        trust_classification = "research_pass"
    else:
        trust_classification = "needs_review"
    return {
        "run_id": run_id,
        "manifest_status": manifest_status or "missing",
        "failed_stage": failed_stage,
        "finished_at": str(manifest.get("finished_at", "") or ""),
        "checklist_decision": checklist_decision,
        "checklist_failure_reasons": _as_string_list(checklist.get("failure_reasons", [])),
        "trust_classification": trust_classification,
        "phase2": phase2,
        "promotion": promotion,
        "edge_candidates": edge_candidates,
        "regime_effectiveness": regime_effectiveness,
        "artifact_paths": {key: str(value) for key, value in diag_paths.items()},
    }


def compare_phase2_run_diagnostics(
    baseline: Mapping[str, Any],
    candidate: Mapping[str, Any],
) -> Dict[str, Any]:
    base = summarize_phase2_distribution(baseline)
    cand = summarize_phase2_distribution(candidate)
    return {
        "baseline": base,
        "candidate": cand,
        "delta": {
            "candidate_count": cand["candidate_count"] - base["candidate_count"],
            "survivor_count": cand["survivor_count"] - base["survivor_count"],
            "zero_eval_rows": cand["zero_eval_rows"] - base["zero_eval_rows"],
            "sample_quality_gate_rejections": cand["sample_quality_gate_rejections"]
            - base["sample_quality_gate_rejections"],
            "median_validation_n_obs": cand["median_validation_n_obs"]
            - base["median_validation_n_obs"],
            "median_test_n_obs": cand["median_test_n_obs"] - base["median_test_n_obs"],
            "median_survivor_q_value": cand["median_survivor_q_value"]
            - base["median_survivor_q_value"],
            "median_survivor_estimate_bps": cand["median_survivor_estimate_bps"]
            - base["median_survivor_estimate_bps"],
        },
    }


def compare_promotion_run_diagnostics(
    baseline: Mapping[str, Any],
    candidate: Mapping[str, Any],
) -> Dict[str, Any]:
    base = summarize_promotion_distribution(baseline)
    cand = summarize_promotion_distribution(candidate)
    return {
        "baseline": base,
        "candidate": cand,
        "delta": {
            "candidate_count": cand["candidate_count"] - base["candidate_count"],
            "promoted_count": cand["promoted_count"] - base["promoted_count"],
            "rejected_count": cand["rejected_count"] - base["rejected_count"],
            "mean_failed_gate_count_rejected": cand["mean_failed_gate_count_rejected"]
            - base["mean_failed_gate_count_rejected"],
        },
        "fail_gate_shift": {
            key: _as_int(cand["primary_fail_gate_counts"].get(key, 0))
            - _as_int(base["primary_fail_gate_counts"].get(key, 0))
            for key in sorted(
                set(base["primary_fail_gate_counts"]) | set(cand["primary_fail_gate_counts"])
            )
        },
        "reject_reason_shift": {
            key: _as_int(cand["primary_reject_reason_counts"].get(key, 0))
            - _as_int(base["primary_reject_reason_counts"].get(key, 0))
            for key in sorted(
                set(base["primary_reject_reason_counts"])
                | set(cand["primary_reject_reason_counts"])
            )
        },
    }


def compare_edge_candidate_reports(
    baseline: pd.DataFrame,
    candidate: pd.DataFrame,
) -> Dict[str, Any]:
    base = summarize_edge_candidate_distribution(baseline)
    cand = summarize_edge_candidate_distribution(candidate)
    return {
        "baseline": base,
        "candidate": cand,
        "delta": {
            "candidate_count": cand["candidate_count"] - base["candidate_count"],
            "tradable_count": cand["tradable_count"] - base["tradable_count"],
            "after_cost_positive_validation_count": cand["after_cost_positive_validation_count"]
            - base["after_cost_positive_validation_count"],
            "median_resolved_cost_bps": cand["median_resolved_cost_bps"]
            - base["median_resolved_cost_bps"],
            "median_expectancy_bps": cand["median_expectancy_bps"] - base["median_expectancy_bps"],
            "median_avg_dynamic_cost_bps": cand["median_avg_dynamic_cost_bps"]
            - base["median_avg_dynamic_cost_bps"],
            "median_bridge_validation_after_cost_bps": cand[
                "median_bridge_validation_after_cost_bps"
            ]
            - base["median_bridge_validation_after_cost_bps"],
        },
    }


def compare_regime_effectiveness_reports(
    baseline: Mapping[str, Any],
    candidate: Mapping[str, Any],
) -> Dict[str, Any]:
    base = summarize_regime_effectiveness_distribution(baseline)
    cand = summarize_regime_effectiveness_distribution(candidate)
    return {
        "baseline": base,
        "candidate": cand,
        "delta": {
            "regimes_total": cand["regimes_total"] - base["regimes_total"],
            "episodes_total": cand["episodes_total"] - base["episodes_total"],
            "scorecard_rows": cand["scorecard_rows"] - base["scorecard_rows"],
            "top_regime_episode_count": cand["top_regime_episode_count"] - base["top_regime_episode_count"],
            "trade_generating_count": cand["trade_generating_count"] - base["trade_generating_count"],
            "trade_filtering_count": cand["trade_filtering_count"] - base["trade_filtering_count"],
            "context_only_count": cand["context_only_count"] - base["context_only_count"],
        },
        "top_regime_changed": bool(base["top_regime"] != cand["top_regime"]),
    }


def compare_run_reports(
    *,
    baseline_phase2_path: Path,
    candidate_phase2_path: Path,
    baseline_promotion_path: Path,
    candidate_promotion_path: Path,
    baseline_edge_candidates_path: Path,
    candidate_edge_candidates_path: Path,
    baseline_regime_effectiveness_path: Path,
    candidate_regime_effectiveness_path: Path,
) -> Dict[str, Any]:
    baseline_phase2_exists = baseline_phase2_path.exists()
    candidate_phase2_exists = candidate_phase2_path.exists()
    baseline_promotion_exists = baseline_promotion_path.exists()
    candidate_promotion_exists = candidate_promotion_path.exists()
    baseline_edge_exists = baseline_edge_candidates_path.exists()
    candidate_edge_exists = candidate_edge_candidates_path.exists()
    baseline_regime_exists = baseline_regime_effectiveness_path.exists()
    candidate_regime_exists = candidate_regime_effectiveness_path.exists()
    return {
        "phase2": compare_phase2_run_diagnostics(
            _read_json(baseline_phase2_path),
            _read_json(candidate_phase2_path),
        ),
        "promotion": compare_promotion_run_diagnostics(
            _read_json(baseline_promotion_path),
            _read_json(candidate_promotion_path),
        ),
        "edge_candidates": compare_edge_candidate_reports(
            _read_parquet(baseline_edge_candidates_path),
            _read_parquet(candidate_edge_candidates_path),
        ),
        "regime_effectiveness": compare_regime_effectiveness_reports(
            _read_json(baseline_regime_effectiveness_path),
            _read_json(candidate_regime_effectiveness_path),
        ),
        "artifacts": {
            "phase2": {
                "baseline_exists": bool(baseline_phase2_exists),
                "candidate_exists": bool(candidate_phase2_exists),
            },
            "promotion": {
                "baseline_exists": bool(baseline_promotion_exists),
                "candidate_exists": bool(candidate_promotion_exists),
            },
            "edge_candidates": {
                "baseline_exists": bool(baseline_edge_exists),
                "candidate_exists": bool(candidate_edge_exists),
            },
            "regime_effectiveness": {
                "baseline_exists": bool(baseline_regime_exists),
                "candidate_exists": bool(candidate_regime_exists),
            },
        },
    }


def compare_run_ids(
    *,
    data_root: Path,
    baseline_run_id: str,
    candidate_run_id: str,
) -> Dict[str, Any]:
    baseline_paths = research_diagnostics_paths(data_root=data_root, run_id=baseline_run_id)
    candidate_paths = research_diagnostics_paths(data_root=data_root, run_id=candidate_run_id)
    return compare_run_reports(
        baseline_phase2_path=baseline_paths["phase2"],
        candidate_phase2_path=candidate_paths["phase2"],
        baseline_promotion_path=baseline_paths["promotion"],
        candidate_promotion_path=candidate_paths["promotion"],
        baseline_edge_candidates_path=baseline_paths["edge_candidates"],
        candidate_edge_candidates_path=candidate_paths["edge_candidates"],
        baseline_regime_effectiveness_path=baseline_paths["regime_effectiveness"],
        candidate_regime_effectiveness_path=candidate_paths["regime_effectiveness"],
    )


def resolve_drift_thresholds(
    thresholds: Mapping[str, Any] | None = None,
) -> Dict[str, float]:
    resolved = dict(DEFAULT_DRIFT_THRESHOLDS)
    for key, default in DEFAULT_DRIFT_THRESHOLDS.items():
        if thresholds is None or key not in thresholds:
            resolved[key] = float(default)
        else:
            resolved[key] = _as_float(thresholds.get(key), float(default))
    return resolved


def assess_run_comparison(
    comparison: Mapping[str, Any],
    *,
    thresholds: Mapping[str, Any] | None = None,
    mode: str = "warn",
) -> Dict[str, Any]:
    resolved_mode = str(mode or "warn").strip().lower()
    resolved_thresholds = resolve_drift_thresholds(thresholds)
    baseline_phase2 = dict(comparison.get("phase2", {}).get("baseline", {}))
    candidate_phase2 = dict(comparison.get("phase2", {}).get("candidate", {}))
    phase2_delta = dict(comparison.get("phase2", {}).get("delta", {}))
    promotion_delta = dict(comparison.get("promotion", {}).get("delta", {}))
    reject_reason_shift = dict(comparison.get("promotion", {}).get("reject_reason_shift", {}))
    edge_delta = dict(comparison.get("edge_candidates", {}).get("delta", {}))
    regime_delta = dict(comparison.get("regime_effectiveness", {}).get("delta", {}))
    artifacts = dict(comparison.get("artifacts", {}))
    promotion_artifacts = dict(artifacts.get("promotion", {}))
    edge_artifacts = dict(artifacts.get("edge_candidates", {}))
    regime_artifacts = dict(artifacts.get("regime_effectiveness", {}))
    promotion_artifacts_present = bool(
        promotion_artifacts.get("baseline_exists", False)
        and promotion_artifacts.get("candidate_exists", False)
    )
    edge_artifacts_present = bool(
        edge_artifacts.get("baseline_exists", False)
        and edge_artifacts.get("candidate_exists", False)
    )
    regime_artifacts_present = bool(
        regime_artifacts.get("baseline_exists", False)
        and regime_artifacts.get("candidate_exists", False)
    )
    profile_mismatch = str(baseline_phase2.get("discovery_profile", "") or "") != str(
        candidate_phase2.get("discovery_profile", "") or ""
    ) or str(baseline_phase2.get("search_spec", "") or "") != str(
        candidate_phase2.get("search_spec", "") or ""
    )

    checks: list[tuple[bool, str]] = []
    if not profile_mismatch:
        checks.append(
            (
                abs(_as_int(phase2_delta.get("candidate_count", 0)))
                > resolved_thresholds["max_phase2_candidate_count_delta_abs"],
                f"phase2 candidate_count delta={_as_int(phase2_delta.get('candidate_count', 0))} exceeds {resolved_thresholds['max_phase2_candidate_count_delta_abs']}",
            )
        )
    checks.extend(
        [
            (
                abs(_as_int(phase2_delta.get("survivor_count", 0)))
                > resolved_thresholds["max_phase2_survivor_count_delta_abs"],
                f"phase2 survivor_count delta={_as_int(phase2_delta.get('survivor_count', 0))} exceeds {resolved_thresholds['max_phase2_survivor_count_delta_abs']}",
            ),
            (
                _as_int(phase2_delta.get("zero_eval_rows", 0))
                > resolved_thresholds["max_phase2_zero_eval_rows_increase"],
                f"phase2 zero_eval_rows increase={_as_int(phase2_delta.get('zero_eval_rows', 0))} exceeds {resolved_thresholds['max_phase2_zero_eval_rows_increase']}",
            ),
            (
                _as_float(phase2_delta.get("median_survivor_q_value", 0.0))
                > resolved_thresholds["max_phase2_survivor_q_value_increase"],
                f"phase2 survivor q-value increase={_as_float(phase2_delta.get('median_survivor_q_value', 0.0)):.4f} exceeds {resolved_thresholds['max_phase2_survivor_q_value_increase']:.4f}",
            ),
            (
                (-_as_float(phase2_delta.get("median_survivor_estimate_bps", 0.0)))
                > resolved_thresholds["max_phase2_survivor_estimate_bps_drop"],
                f"phase2 survivor estimate drop={-_as_float(phase2_delta.get('median_survivor_estimate_bps', 0.0)):.4f} exceeds {resolved_thresholds['max_phase2_survivor_estimate_bps_drop']:.4f}",
            ),
            (
                promotion_artifacts_present
                and abs(_as_int(promotion_delta.get("promoted_count", 0)))
                > resolved_thresholds["max_promotion_promoted_count_delta_abs"],
                f"promotion promoted_count delta={_as_int(promotion_delta.get('promoted_count', 0))} exceeds {resolved_thresholds['max_promotion_promoted_count_delta_abs']}",
            ),
            (
                edge_artifacts_present
                and abs(_as_int(edge_delta.get("candidate_count", 0)))
                > resolved_thresholds["max_edge_candidate_count_delta_abs"],
                f"edge candidate_count delta={_as_int(edge_delta.get('candidate_count', 0))} exceeds {resolved_thresholds['max_edge_candidate_count_delta_abs']}",
            ),
            (
                edge_artifacts_present
                and abs(_as_int(edge_delta.get("tradable_count", 0)))
                > resolved_thresholds["max_edge_tradable_count_delta_abs"],
                f"edge tradable_count delta={_as_int(edge_delta.get('tradable_count', 0))} exceeds {resolved_thresholds['max_edge_tradable_count_delta_abs']}",
            ),
            (
                edge_artifacts_present
                and abs(_as_int(edge_delta.get("after_cost_positive_validation_count", 0)))
                > resolved_thresholds["max_edge_after_cost_positive_validation_count_delta_abs"],
                f"edge after_cost_positive_validation_count delta={_as_int(edge_delta.get('after_cost_positive_validation_count', 0))} exceeds {resolved_thresholds['max_edge_after_cost_positive_validation_count_delta_abs']}",
            ),
            (
                edge_artifacts_present
                and abs(_as_float(edge_delta.get("median_resolved_cost_bps", 0.0)))
                > resolved_thresholds["max_edge_median_resolved_cost_bps_delta_abs"],
                f"edge median_resolved_cost_bps delta={_as_float(edge_delta.get('median_resolved_cost_bps', 0.0)):.4f} exceeds {resolved_thresholds['max_edge_median_resolved_cost_bps_delta_abs']:.4f}",
            ),
            (
                edge_artifacts_present
                and abs(_as_float(edge_delta.get("median_expectancy_bps", 0.0)))
                > resolved_thresholds["max_edge_median_expectancy_bps_delta_abs"],
                f"edge median_expectancy_bps delta={_as_float(edge_delta.get('median_expectancy_bps', 0.0)):.4f} exceeds {resolved_thresholds['max_edge_median_expectancy_bps_delta_abs']:.4f}",
            ),
            (
                regime_artifacts_present
                and abs(_as_float(regime_delta.get("trade_generating_count", 0.0)))
                > resolved_thresholds["max_regime_actionability_drift_abs"],
                f"regime trade_generating_count delta={_as_float(regime_delta.get('trade_generating_count', 0.0)):.4f} exceeds {resolved_thresholds['max_regime_actionability_drift_abs']:.4f}",
            ),
            (
                regime_artifacts_present
                and abs(_as_float(regime_delta.get("trade_filtering_count", 0.0)))
                > resolved_thresholds["max_regime_actionability_drift_abs"],
                f"regime trade_filtering_count delta={_as_float(regime_delta.get('trade_filtering_count', 0.0)):.4f} exceeds {resolved_thresholds['max_regime_actionability_drift_abs']:.4f}",
            ),
        ]
    )
    if promotion_artifacts_present:
        for reason, shift in sorted(reject_reason_shift.items()):
            checks.append(
                (
                    abs(_as_int(shift)) > resolved_thresholds["max_reject_reason_shift_abs"],
                    f"promotion reject_reason shift for {reason}={_as_int(shift)} exceeds {resolved_thresholds['max_reject_reason_shift_abs']}",
                )
            )

    violations = [message for failed, message in checks if failed]
    notes: list[str] = []
    if profile_mismatch:
        notes.append(
            "phase2 profile/search-spec mismatch detected; candidate-count drift threshold was not enforced"
        )
    if not promotion_artifacts_present:
        notes.append(
            "promotion artifact missing for baseline or candidate run; promotion drift thresholds were not enforced"
        )
    if not edge_artifacts_present:
        notes.append(
            "edge candidate artifact missing for baseline or candidate run; edge drift thresholds were not enforced"
        )
    if not regime_artifacts_present:
        notes.append(
            "regime effectiveness artifact missing for baseline or candidate run; regime drift thresholds were not enforced"
        )
    if resolved_mode == "off":
        status = "off"
    elif not violations:
        status = "pass"
    elif resolved_mode == "enforce":
        status = "fail"
    else:
        status = "warn"
    return {
        "mode": resolved_mode,
        "status": status,
        "violation_count": int(len(violations)),
        "violations": violations,
        "notes": notes,
        "profile_mismatch": bool(profile_mismatch),
        "thresholds": resolved_thresholds,
    }


def render_run_comparison_summary(payload: Mapping[str, Any]) -> str:
    comparison = dict(payload.get("comparison", {}))
    assessment = dict(payload.get("assessment", {}))
    phase2 = dict(comparison.get("phase2", {}))
    promotion = dict(comparison.get("promotion", {}))
    edge_candidates = dict(comparison.get("edge_candidates", {}))
    regime_effectiveness = dict(comparison.get("regime_effectiveness", {}))
    lines = [
        "# Research Run Comparison",
        "",
        f"Baseline run: {payload.get('baseline_run_id', '')}",
        f"Candidate run: {payload.get('candidate_run_id', '')}",
        f"Assessment: {assessment.get('status', 'unknown')} ({assessment.get('mode', 'warn')})",
        "",
        "## Phase 2",
        f"- candidate delta: {phase2.get('delta', {}).get('candidate_count', 0)}",
        f"- survivor delta: {phase2.get('delta', {}).get('survivor_count', 0)}",
        f"- zero-eval row delta: {phase2.get('delta', {}).get('zero_eval_rows', 0)}",
        f"- sample-quality gate rejection delta: {phase2.get('delta', {}).get('sample_quality_gate_rejections', 0)}",
        f"- survivor q-value delta: {phase2.get('delta', {}).get('median_survivor_q_value', 0.0)}",
        f"- survivor estimate bps delta: {phase2.get('delta', {}).get('median_survivor_estimate_bps', 0.0)}",
        "",
        "## Promotion",
        f"- promoted delta: {promotion.get('delta', {}).get('promoted_count', 0)}",
        f"- rejected delta: {promotion.get('delta', {}).get('rejected_count', 0)}",
        f"- mean failed-gate-count delta: {promotion.get('delta', {}).get('mean_failed_gate_count_rejected', 0.0)}",
        "",
        "## Edge Candidates",
        f"- candidate delta: {edge_candidates.get('delta', {}).get('candidate_count', 0)}",
        f"- tradable delta: {edge_candidates.get('delta', {}).get('tradable_count', 0)}",
        f"- after-cost-positive delta: {edge_candidates.get('delta', {}).get('after_cost_positive_validation_count', 0)}",
        f"- resolved cost bps delta: {edge_candidates.get('delta', {}).get('median_resolved_cost_bps', 0.0)}",
        f"- expectancy bps delta: {edge_candidates.get('delta', {}).get('median_expectancy_bps', 0.0)}",
        "",
        "## Regime Effectiveness",
        f"- regimes total delta: {regime_effectiveness.get('delta', {}).get('regimes_total', 0)}",
        f"- episodes total delta: {regime_effectiveness.get('delta', {}).get('episodes_total', 0)}",
        f"- trade-generating delta: {regime_effectiveness.get('delta', {}).get('trade_generating_count', 0)}",
        f"- trade-filtering delta: {regime_effectiveness.get('delta', {}).get('trade_filtering_count', 0)}",
        f"- top regime changed: {regime_effectiveness.get('top_regime_changed', False)}",
        "",
        "## Alerts",
    ]
    violations = list(assessment.get("violations", []))
    if violations:
        lines.extend([f"- {message}" for message in violations])
    else:
        lines.append("- none")
    notes = list(assessment.get("notes", []))
    if notes:
        lines.extend(["", "## Notes"])
        lines.extend([f"- {message}" for message in notes])
    return "\n".join(lines) + "\n"


def build_run_matrix_summary(
    *,
    data_root: Path,
    baseline_run_id: str,
    candidate_run_ids: Sequence[str],
    thresholds: Mapping[str, Any] | None = None,
    drift_mode: str = "warn",
) -> Dict[str, Any]:
    ordered_run_ids: list[str] = []
    for run_id in [baseline_run_id, *candidate_run_ids]:
        token = str(run_id or "").strip()
        if token and token not in ordered_run_ids:
            ordered_run_ids.append(token)
    baseline_summary = summarize_run_research_status(data_root=data_root, run_id=baseline_run_id)
    run_summaries = {
        run_id: summarize_run_research_status(data_root=data_root, run_id=run_id)
        for run_id in ordered_run_ids
    }
    comparisons = []
    for run_id in ordered_run_ids:
        if run_id == baseline_run_id:
            continue
        comparison = compare_run_ids(
            data_root=data_root,
            baseline_run_id=baseline_run_id,
            candidate_run_id=run_id,
        )
        assessment = assess_run_comparison(
            comparison,
            thresholds=thresholds,
            mode=drift_mode,
        )
        comparisons.append(
            {
                "baseline_run_id": baseline_run_id,
                "candidate_run_id": run_id,
                "comparison": comparison,
                "assessment": assessment,
            }
        )
    return {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "baseline_run_id": baseline_run_id,
        "drift_mode": str(drift_mode or "warn"),
        "thresholds": resolve_drift_thresholds(thresholds),
        "baseline_summary": baseline_summary,
        "run_summaries": run_summaries,
        "comparisons": comparisons,
    }


def render_run_matrix_summary(payload: Mapping[str, Any]) -> str:
    baseline_summary = dict(payload.get("baseline_summary", {}))
    run_summaries = dict(payload.get("run_summaries", {}))
    comparisons = list(payload.get("comparisons", []))
    lines = [
        "# Research Run Matrix Summary",
        "",
        f"Baseline run: {payload.get('baseline_run_id', '')}",
        f"Drift mode: {payload.get('drift_mode', 'warn')}",
        "",
        "## Runs",
    ]
    for run_id, summary in run_summaries.items():
        phase2 = dict(summary.get("phase2", {}))
        promotion = dict(summary.get("promotion", {}))
        edge = dict(summary.get("edge_candidates", {}))
        regimes = dict(summary.get("regime_effectiveness", {}))
        failures = list(summary.get("checklist_failure_reasons", []))
        lines.append(
            f"- `{run_id}`: {summary.get('trust_classification', 'unknown')} | "
            f"manifest={summary.get('manifest_status', 'missing')} | "
            f"checklist={summary.get('checklist_decision', '') or 'none'} | "
            f"phase2_candidates={phase2.get('candidate_count', 0)} | "
            f"promoted={promotion.get('promoted_count', 0)} | "
            f"tradable={edge.get('tradable_count', 0)} | "
            f"regimes={regimes.get('regimes_total', 0)}"
        )
        if failures:
            lines.append(f"  failures: {', '.join(failures)}")
    lines.extend(["", "## Baseline Drift"])
    if not comparisons:
        lines.append("- none")
    else:
        for item in comparisons:
            assessment = dict(item.get("assessment", {}))
            candidate = str(item.get("candidate_run_id", "") or "")
            lines.append(
                f"- `{candidate}`: {assessment.get('status', 'unknown')} "
                f"(violations={assessment.get('violation_count', 0)})"
            )
            for violation in list(assessment.get("violations", []))[:5]:
                lines.append(f"  violation: {violation}")
            for note in list(assessment.get("notes", []))[:3]:
                lines.append(f"  note: {note}")
    lines.extend(
        [
            "",
            "## Baseline Snapshot",
            f"- manifest={baseline_summary.get('manifest_status', 'missing')}",
            f"- checklist={baseline_summary.get('checklist_decision', '') or 'none'}",
            f"- phase2_candidates={baseline_summary.get('phase2', {}).get('candidate_count', 0)}",
            f"- promoted={baseline_summary.get('promotion', {}).get('promoted_count', 0)}",
            f"- tradable={baseline_summary.get('edge_candidates', {}).get('tradable_count', 0)}",
            f"- regimes={baseline_summary.get('regime_effectiveness', {}).get('regimes_total', 0)}",
        ]
    )
    return "\n".join(lines) + "\n"


def write_run_matrix_summary_report(
    *,
    data_root: Path,
    baseline_run_id: str,
    candidate_run_ids: Sequence[str],
    out_dir: Path,
    thresholds: Mapping[str, Any] | None = None,
    drift_mode: str = "warn",
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = build_run_matrix_summary(
        data_root=data_root,
        baseline_run_id=baseline_run_id,
        candidate_run_ids=candidate_run_ids,
        thresholds=thresholds,
        drift_mode=drift_mode,
    )
    out_path = out_dir / "research_run_matrix_summary.json"
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    (out_dir / "research_run_matrix_summary.md").write_text(
        render_run_matrix_summary(payload),
        encoding="utf-8",
    )
    return out_path


def write_run_comparison_report(
    *,
    data_root: Path,
    baseline_run_id: str,
    candidate_run_id: str,
    out_dir: Path | None = None,
    report_out: Path | None = None,
    summary_out: Path | None = None,
    thresholds: Mapping[str, Any] | None = None,
    drift_mode: str = "warn",
) -> Path:
    report_dir = (
        out_dir
        if out_dir is not None
        else data_root
        / "reports"
        / "research_comparison"
        / candidate_run_id
        / f"vs_{baseline_run_id}"
    )
    report_dir.mkdir(parents=True, exist_ok=True)
    output_path = (
        report_out if report_out is not None else report_dir / "research_run_comparison.json"
    )
    baseline_paths = research_diagnostics_paths(data_root=data_root, run_id=baseline_run_id)
    candidate_paths = research_diagnostics_paths(data_root=data_root, run_id=candidate_run_id)
    comparison = compare_run_ids(
        data_root=data_root,
        baseline_run_id=baseline_run_id,
        candidate_run_id=candidate_run_id,
    )
    assessment = assess_run_comparison(
        comparison,
        thresholds=thresholds,
        mode=drift_mode,
    )
    payload = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "baseline_run_id": baseline_run_id,
        "candidate_run_id": candidate_run_id,
        "baseline_paths": {key: str(value) for key, value in baseline_paths.items()},
        "candidate_paths": {key: str(value) for key, value in candidate_paths.items()},
        "comparison": comparison,
        "assessment": assessment,
    }
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    summary_path = (
        summary_out
        if summary_out is not None
        else report_dir / "research_run_comparison_summary.md"
    )
    summary_path.write_text(render_run_comparison_summary(payload), encoding="utf-8")
    return output_path
