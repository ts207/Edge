"""Tests for canonical search-only discovery planning."""

import types
from pathlib import Path
import pytest
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parents[2]))


# Build a comprehensive args namespace that satisfies build_research_stages
def _make_args(**overrides):
    defaults = dict(
        run_phase2_conditional=1,
        phase2_event_type="all",
        phase2_gate_profile_resolved="auto",
        timeframes="15m",
        concept="",
        seed=42,
        discovery_mode="search",
        # Added missing defaults
        phase2_shift_labels_k=0,
        mode="research",
        phase2_cost_calibration_mode="static",
        phase2_cost_min_tob_coverage=0.6,
        phase2_cost_tob_tolerance_minutes=10,
        retail_profile="standard",
        run_bridge_eval_phase2=0,
        bridge_train_frac=0.6,
        bridge_validation_frac=0.2,
        bridge_embargo_days=1,
        bridge_edge_cost_k=2.0,
        bridge_stressed_cost_multiplier=1.5,
        bridge_min_validation_trades=20,
        bridge_candidate_mask="auto",
        run_discovery_quality_summary=0,
        run_naive_entry_eval=0,
        naive_min_trades=20,
        naive_min_expectancy_after_cost=0.0,
        naive_max_drawdown=1.0,
        run_candidate_promotion=0,
        candidate_promotion_max_q_value=0.2,
        candidate_promotion_min_events=20,
        candidate_promotion_min_stability_score=0.6,
        candidate_promotion_min_sign_consistency=0.6,
        candidate_promotion_min_cost_survival_ratio=0.5,
        candidate_promotion_min_tob_coverage=0.6,
        candidate_promotion_max_negative_control_pass_rate=0.1,
        candidate_promotion_require_hypothesis_audit=1,
        candidate_promotion_allow_missing_negative_controls=0,
        run_edge_registry_update=0,
        run_expectancy_analysis=0,
        run_expectancy_robustness=0,
        run_recommendations_checklist=0,
        run_interaction_lift=0,
    )
    ns = types.SimpleNamespace(**{**defaults, **overrides})
    return ns


def test_discovery_mode_search_includes_search_stage(tmp_path):
    from project.pipelines.stages.research import build_research_stages

    stages = build_research_stages(
        args=_make_args(discovery_mode="search"),
        run_id="r0",
        symbols="BTCUSDT",
        start="2024-01-01",
        end="2024-03-01",
        research_gate_profile="discovery",
        project_root=tmp_path,
        data_root=tmp_path,
        phase2_event_chain=[],
    )
    names = [s[0] for s in stages]
    assert any("phase2_search_engine" in n for n in names)
    assert not any("compare_discovery_paths" in n for n in names)
    assert "phase1_correlation_clustering" in names


def test_discovery_mode_argument_is_ignored_in_favor_of_canonical_search(tmp_path):
    from project.pipelines.stages.research import build_research_stages

    stages = build_research_stages(
        args=_make_args(discovery_mode="legacy"),
        run_id="r0",
        symbols="BTCUSDT",
        start="2024-01-01",
        end="2024-03-01",
        research_gate_profile="discovery",
        project_root=tmp_path,
        data_root=tmp_path,
        phase2_event_chain=[],
    )
    names = [s[0] for s in stages]
    assert any("phase2_search_engine" in n for n in names)
    assert not any("compare_discovery_paths" in n for n in names)
