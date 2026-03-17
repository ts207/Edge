from __future__ import annotations

import json
from pathlib import Path

from project.research.services import run_comparison_service as svc


def test_compare_phase2_run_diagnostics_reports_candidate_and_survivor_shifts():
    baseline = {
        "combined_candidate_rows": 10,
        "false_discovery_diagnostics": {
            "global": {"candidates_total": 10, "survivors_total": 3, "symbols_total": 2, "families_total": 4},
            "sample_quality": {"zero_eval_rows": 1, "median_validation_n_obs": 12.0, "median_test_n_obs": 11.0},
            "sample_quality_gate": {"rejected_by_sample_quality_gate": 1},
            "survivor_quality": {"median_q_value": 0.03, "median_estimate_bps": 8.0},
        },
    }
    candidate = {
        "combined_candidate_rows": 14,
        "false_discovery_diagnostics": {
            "global": {"candidates_total": 14, "survivors_total": 5, "symbols_total": 2, "families_total": 6},
            "sample_quality": {"zero_eval_rows": 3, "median_validation_n_obs": 9.0, "median_test_n_obs": 8.0},
            "sample_quality_gate": {"rejected_by_sample_quality_gate": 4},
            "survivor_quality": {"median_q_value": 0.05, "median_estimate_bps": 6.5},
        },
    }

    out = svc.compare_phase2_run_diagnostics(baseline, candidate)
    assert out["delta"]["candidate_count"] == 4
    assert out["delta"]["survivor_count"] == 2
    assert out["delta"]["zero_eval_rows"] == 2
    assert out["delta"]["sample_quality_gate_rejections"] == 3
    assert out["delta"]["median_survivor_estimate_bps"] == -1.5


def test_summarize_phase2_distribution_falls_back_to_legacy_search_engine_fields():
    diagnostics = {
        "bridge_candidates_rows": 20,
        "multiplicity_discoveries": 6,
        "discovery_profile": "standard",
        "search_spec": "spec/search_space.yaml",
        "symbol_diagnostics": [{"symbol": "BTCUSDT"}, {"symbol": "ETHUSDT"}, {"symbol": "SOLUSDT"}],
    }

    out = svc.summarize_phase2_distribution(diagnostics)

    assert out["candidate_count"] == 20
    assert out["survivor_count"] == 6
    assert out["symbol_count"] == 3
    assert out["discovery_profile"] == "standard"
    assert out["search_spec"] == "spec/search_space.yaml"


def test_compare_promotion_run_diagnostics_reports_fail_gate_and_reason_shifts():
    baseline = {
        "decision_summary": {
            "candidates_total": 8,
            "promoted_count": 2,
            "rejected_count": 6,
            "mean_failed_gate_count_rejected": 1.5,
            "primary_fail_gate_counts": {"gate_promo_stability": 3},
            "primary_reject_reason_counts": {"stability_score": 2},
        }
    }
    candidate = {
        "decision_summary": {
            "candidates_total": 8,
            "promoted_count": 1,
            "rejected_count": 7,
            "mean_failed_gate_count_rejected": 2.0,
            "primary_fail_gate_counts": {"gate_promo_stability": 2, "gate_promo_negative_control": 3},
            "primary_reject_reason_counts": {"stability_score": 1, "negative_control_fail": 3},
        }
    }

    out = svc.compare_promotion_run_diagnostics(baseline, candidate)
    assert out["delta"]["promoted_count"] == -1
    assert out["fail_gate_shift"]["gate_promo_negative_control"] == 3
    assert out["fail_gate_shift"]["gate_promo_stability"] == -1
    assert out["reject_reason_shift"]["negative_control_fail"] == 3


def test_compare_edge_candidate_reports_captures_cost_and_expectancy_shifts(tmp_path: Path):
    baseline = tmp_path / "baseline.parquet"
    candidate = tmp_path / "candidate.parquet"

    import pandas as pd

    pd.DataFrame(
        [
            {"gate_bridge_tradable": "fail", "resolved_cost_bps": 0.5, "expectancy_bps": -0.5, "avg_dynamic_cost_bps": 0.5},
            {"gate_bridge_tradable": "pass", "resolved_cost_bps": 0.5, "expectancy_bps": 1.0, "avg_dynamic_cost_bps": 0.5},
        ]
    ).to_parquet(baseline)
    pd.DataFrame(
        [
            {"gate_bridge_tradable": "pass", "resolved_cost_bps": 0.1, "expectancy_bps": -0.1, "avg_dynamic_cost_bps": 0.1},
            {"gate_bridge_tradable": "pass", "resolved_cost_bps": 0.1, "expectancy_bps": 1.4, "avg_dynamic_cost_bps": 0.1},
        ]
    ).to_parquet(candidate)

    out = svc.compare_edge_candidate_reports(
        pd.read_parquet(baseline),
        pd.read_parquet(candidate),
    )

    assert out["delta"]["tradable_count"] == 1
    assert out["delta"]["median_resolved_cost_bps"] == -0.4
    assert round(out["delta"]["median_expectancy_bps"], 6) == 0.4


def test_compare_run_reports_reads_json_files(tmp_path):
    baseline_phase2 = tmp_path / "baseline_phase2.json"
    candidate_phase2 = tmp_path / "candidate_phase2.json"
    baseline_promo = tmp_path / "baseline_promo.json"
    candidate_promo = tmp_path / "candidate_promo.json"
    baseline_edge = tmp_path / "baseline_edge.parquet"
    candidate_edge = tmp_path / "candidate_edge.parquet"

    baseline_phase2.write_text(json.dumps({"false_discovery_diagnostics": {"global": {"candidates_total": 2, "survivors_total": 1}}}), encoding="utf-8")
    candidate_phase2.write_text(json.dumps({"false_discovery_diagnostics": {"global": {"candidates_total": 5, "survivors_total": 2}}}), encoding="utf-8")
    baseline_promo.write_text(json.dumps({"decision_summary": {"candidates_total": 1, "promoted_count": 1, "rejected_count": 0}}), encoding="utf-8")
    candidate_promo.write_text(json.dumps({"decision_summary": {"candidates_total": 1, "promoted_count": 0, "rejected_count": 1}}), encoding="utf-8")
    import pandas as pd
    pd.DataFrame([{"gate_bridge_tradable": "fail", "resolved_cost_bps": 0.5, "expectancy_bps": -0.5}]).to_parquet(baseline_edge)
    pd.DataFrame([{"gate_bridge_tradable": "pass", "resolved_cost_bps": 0.1, "expectancy_bps": -0.1}]).to_parquet(candidate_edge)

    out = svc.compare_run_reports(
        baseline_phase2_path=baseline_phase2,
        candidate_phase2_path=candidate_phase2,
        baseline_promotion_path=baseline_promo,
        candidate_promotion_path=candidate_promo,
        baseline_edge_candidates_path=baseline_edge,
        candidate_edge_candidates_path=candidate_edge,
    )

    assert out["phase2"]["delta"]["candidate_count"] == 3
    assert out["promotion"]["delta"]["promoted_count"] == -1
    assert out["edge_candidates"]["delta"]["tradable_count"] == 1
    assert out["artifacts"]["promotion"] == {"baseline_exists": True, "candidate_exists": True}
    assert out["artifacts"]["edge_candidates"] == {"baseline_exists": True, "candidate_exists": True}


def test_assess_run_comparison_reports_warn_or_fail_status():
    comparison = {
        "phase2": {
            "delta": {
                "candidate_count": 2,
                "zero_eval_rows": 1,
                "median_survivor_q_value": 0.25,
                "median_survivor_estimate_bps": -7.0,
            }
        },
        "promotion": {
            "delta": {
                "promoted_count": -4,
            },
            "reject_reason_shift": {
                "negative_control_fail": 6,
            },
        },
        "artifacts": {
            "promotion": {"baseline_exists": True, "candidate_exists": True},
            "edge_candidates": {"baseline_exists": False, "candidate_exists": False},
        },
    }

    warn = svc.assess_run_comparison(comparison, mode="warn")
    fail = svc.assess_run_comparison(comparison, mode="enforce")

    assert warn["status"] == "warn"
    assert fail["status"] == "fail"
    assert fail["violation_count"] >= 4
    assert any("negative_control_fail" in message for message in fail["violations"])


def test_resolve_drift_thresholds_pins_current_calibration_defaults():
    resolved = svc.resolve_drift_thresholds()

    assert resolved == {
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
    }


def test_assess_run_comparison_skips_candidate_count_enforcement_on_profile_mismatch():
    comparison = {
        "phase2": {
            "baseline": {"discovery_profile": "standard", "search_spec": "spec/search_space.yaml"},
            "candidate": {"discovery_profile": "synthetic", "search_spec": "synthetic_truth"},
            "delta": {
                "candidate_count": 30,
                "zero_eval_rows": 0,
                "median_survivor_q_value": 0.0,
                "median_survivor_estimate_bps": 0.0,
            },
        },
        "promotion": {
            "delta": {"promoted_count": 0},
            "reject_reason_shift": {},
        },
    }

    assessed = svc.assess_run_comparison(comparison, mode="enforce")

    assert assessed["status"] == "pass"
    assert assessed["profile_mismatch"] is True
    assert assessed["violation_count"] == 0
    assert any("candidate-count drift threshold was not enforced" in note for note in assessed["notes"])


def test_assess_run_comparison_warns_on_mass_promotion_shift_from_dsr_relaxation():
    comparison = {
        "phase2": {
            "baseline": {"discovery_profile": "standard", "search_spec": "spec/search_space.yaml"},
            "candidate": {"discovery_profile": "standard", "search_spec": "spec/search_space.yaml"},
            "delta": {
                "candidate_count": 0,
                "zero_eval_rows": 0,
                "median_survivor_q_value": 0.0,
                "median_survivor_estimate_bps": 0.0,
            },
        },
        "promotion": {
            "delta": {"promoted_count": 12},
            "reject_reason_shift": {"failed_gate_promo_dsr": -12},
        },
        "artifacts": {
            "promotion": {"baseline_exists": True, "candidate_exists": True},
            "edge_candidates": {"baseline_exists": False, "candidate_exists": False},
        },
    }

    assessed = svc.assess_run_comparison(comparison, mode="warn")

    assert assessed["status"] == "warn"
    assert assessed["profile_mismatch"] is False
    assert assessed["violation_count"] == 2
    assert any("promoted_count delta=12" in message for message in assessed["violations"])
    assert any("failed_gate_promo_dsr" in message for message in assessed["violations"])


def test_assess_run_comparison_warns_on_edge_cost_and_expectancy_shift():
    comparison = {
        "phase2": {
            "baseline": {"discovery_profile": "standard", "search_spec": "spec/search_space.yaml"},
            "candidate": {"discovery_profile": "standard", "search_spec": "spec/search_space.yaml"},
            "delta": {
                "candidate_count": 0,
                "zero_eval_rows": 0,
                "median_survivor_q_value": 0.0,
                "median_survivor_estimate_bps": 0.0,
            },
        },
        "promotion": {
            "delta": {"promoted_count": 0},
            "reject_reason_shift": {},
        },
        "edge_candidates": {
            "delta": {
                "tradable_count": 0,
                "candidate_count": 0,
                "after_cost_positive_validation_count": 0,
                "median_resolved_cost_bps": -0.4,
                "median_expectancy_bps": 0.4,
            },
        },
        "artifacts": {
            "promotion": {"baseline_exists": False, "candidate_exists": False},
            "edge_candidates": {"baseline_exists": True, "candidate_exists": True},
        },
    }

    assessed = svc.assess_run_comparison(comparison, mode="warn")

    assert assessed["status"] == "warn"
    assert any("median_resolved_cost_bps" in message for message in assessed["violations"])
    assert any("median_expectancy_bps" in message for message in assessed["violations"])


def test_assess_run_comparison_warns_on_edge_candidate_count_shift():
    comparison = {
        "phase2": {
            "baseline": {"discovery_profile": "standard", "search_spec": "spec/search_space.yaml"},
            "candidate": {"discovery_profile": "standard", "search_spec": "spec/search_space.yaml"},
            "delta": {
                "candidate_count": 0,
                "survivor_count": 0,
                "zero_eval_rows": 0,
                "median_survivor_q_value": 0.0,
                "median_survivor_estimate_bps": 0.0,
            },
        },
        "promotion": {
            "delta": {"promoted_count": 0},
            "reject_reason_shift": {},
        },
        "edge_candidates": {
            "delta": {
                "candidate_count": -3,
                "tradable_count": 0,
                "after_cost_positive_validation_count": 0,
                "median_resolved_cost_bps": 0.0,
                "median_expectancy_bps": 0.0,
            },
        },
        "artifacts": {
            "promotion": {"baseline_exists": False, "candidate_exists": False},
            "edge_candidates": {"baseline_exists": True, "candidate_exists": True},
        },
    }

    assessed = svc.assess_run_comparison(comparison, mode="warn")

    assert assessed["status"] == "warn"
    assert any("edge candidate_count" in message for message in assessed["violations"])


def test_assess_run_comparison_warns_on_phase2_survivor_count_shift():
    comparison = {
        "phase2": {
            "baseline": {"discovery_profile": "standard", "search_spec": "spec/search_space.yaml"},
            "candidate": {"discovery_profile": "standard", "search_spec": "spec/search_space.yaml"},
            "delta": {
                "candidate_count": 0,
                "survivor_count": -3,
                "zero_eval_rows": 0,
                "median_survivor_q_value": 0.0,
                "median_survivor_estimate_bps": 0.0,
            },
        },
        "promotion": {
            "delta": {"promoted_count": 0},
            "reject_reason_shift": {},
        },
        "edge_candidates": {
            "delta": {
                "tradable_count": 0,
                "after_cost_positive_validation_count": 0,
                "median_resolved_cost_bps": 0.0,
                "median_expectancy_bps": 0.0,
            },
        },
    }

    assessed = svc.assess_run_comparison(comparison, mode="warn")

    assert assessed["status"] == "warn"
    assert any("survivor_count" in message for message in assessed["violations"])


def test_assess_run_comparison_passes_for_identical_corrected_artifacts():
    comparison = {
        "phase2": {
            "baseline": {"discovery_profile": "standard", "search_spec": "spec/search_space.yaml"},
            "candidate": {"discovery_profile": "standard", "search_spec": "spec/search_space.yaml"},
            "delta": {
                "candidate_count": 0,
                "survivor_count": 0,
                "zero_eval_rows": 0,
                "median_survivor_q_value": 0.0,
                "median_survivor_estimate_bps": 0.0,
            },
        },
        "promotion": {
            "delta": {"promoted_count": 0},
            "reject_reason_shift": {},
        },
        "edge_candidates": {
            "delta": {
                "candidate_count": 0,
                "tradable_count": 0,
                "after_cost_positive_validation_count": 0,
                "median_resolved_cost_bps": 0.0,
                "median_expectancy_bps": 0.0,
                "median_avg_dynamic_cost_bps": 0.0,
                "median_bridge_validation_after_cost_bps": 0.0,
            },
        },
    }

    assessed = svc.assess_run_comparison(comparison, mode="warn")

    assert assessed["status"] == "pass"
    assert assessed["violation_count"] == 0


def test_assess_run_comparison_skips_edge_and_promotion_enforcement_when_artifacts_missing():
    comparison = {
        "phase2": {
            "baseline": {"discovery_profile": "standard", "search_spec": "spec/search_space.yaml"},
            "candidate": {"discovery_profile": "standard", "search_spec": "spec/search_space.yaml"},
            "delta": {
                "candidate_count": 0,
                "survivor_count": 0,
                "zero_eval_rows": 0,
                "median_survivor_q_value": 0.0,
                "median_survivor_estimate_bps": 0.0,
            },
        },
        "promotion": {
            "delta": {"promoted_count": 12},
            "reject_reason_shift": {"failed_gate_promo_dsr": -12},
        },
        "edge_candidates": {
            "delta": {
                "candidate_count": -6,
                "tradable_count": 4,
                "after_cost_positive_validation_count": 3,
                "median_resolved_cost_bps": -6.0,
                "median_expectancy_bps": 6.0,
            },
        },
        "artifacts": {
            "promotion": {"baseline_exists": False, "candidate_exists": False},
            "edge_candidates": {"baseline_exists": True, "candidate_exists": False},
        },
    }

    assessed = svc.assess_run_comparison(comparison, mode="warn")

    assert assessed["status"] == "pass"
    assert assessed["violation_count"] == 0
    assert any("promotion artifact missing" in note for note in assessed["notes"])
    assert any("edge candidate artifact missing" in note for note in assessed["notes"])
