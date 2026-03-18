from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_research_calibration_baseline_doc_exists_and_mentions_current_defaults():
    path = REPO_ROOT / "docs" / "RESEARCH_CALIBRATION_BASELINE.md"
    text = path.read_text(encoding="utf-8")

    assert "max_phase2_candidate_count_delta_abs = 10" in text
    assert "max_phase2_survivor_count_delta_abs = 2.0" in text
    assert "max_promotion_promoted_count_delta_abs = 2" in text
    assert "max_edge_candidate_count_delta_abs = 2.0" in text
    assert "max_edge_median_resolved_cost_bps_delta_abs = 0.25" in text
    assert "max_edge_median_expectancy_bps_delta_abs = 0.25" in text
    assert "min_total_n_obs = 30" in text
    assert "min_total_n_obs = 4" in text
    assert "synthetic_2025_full_year_v4_promo_relaxed_dsr0" in text
    assert "failed_gate_promo_dsr" in text
    assert "e2e_synth_medium_candidate" in text
    assert "e2e_synth_medium_continuation_only" in text
    assert "edge candidate_count delta=-3" in text
    assert "e2e_synth_medium_continuation_only_runall_searchfix_live" in text
    assert "e2e_synth_medium_continuation_only_runall_fanout_fix" in text
    assert "--templates continuation" in text
    assert "--run_phase2_conditional 1" in text
    assert "PYTHONPATH=. python3 project/pipelines/run_all.py" in text
    assert "--skip_ingest_ohlcv 1" in text
    assert "--funding_scale decimal" in text
    assert "phase2 candidate_count delta=3400" in text
    assert "phase2 survivor_count delta=3400" in text
    assert "edge candidate_count delta=-6" in text
    assert "edge median_resolved_cost_bps delta=-6.0" in text
    assert "edge median_expectancy_bps delta=6.0" in text
    assert "tradable_count" in text
