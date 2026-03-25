import types
from pathlib import Path
import pytest
import sys
from unittest.mock import patch, MagicMock
import yaml

# Add project root to path
sys.path.insert(0, str(Path(__file__).parents[2]))

from project.pipelines.stages.research import build_research_stages


def _make_args(**overrides):
    defaults = dict(
        run_phase2_conditional=1,
        phase2_event_type="all",
        phase2_gate_profile_resolved="auto",
        timeframes="5m",
        concept="",
        seed=42,
        discovery_mode="search",
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
        # New flags
        experiment_config=None,
        registry_root="project/configs/registries",
        events=None,
        templates=None,
        horizons=None,
        directions=None,
        entry_lags=None,
        program_id=None,
        search_budget=None,
    )
    ns = types.SimpleNamespace(**{**defaults, **overrides})
    return ns


@patch("project.pipelines.stages.research.build_experiment_plan")
def test_build_research_stages_with_experiment_config(mock_build_plan, tmp_path):
    # Mock the plan
    mock_trigger = MagicMock()
    mock_trigger.trigger_type = "event"
    mock_trigger.event_id = "VOL_SPIKE"

    mock_hyp = MagicMock()
    mock_hyp.trigger = mock_trigger
    mock_hyp.template_id = "continuation"
    mock_hyp.horizon = "12b"
    mock_hyp.direction = "long"
    mock_hyp.entry_lag = 0

    mock_plan = MagicMock()
    mock_plan.program_id = "test_prog"
    mock_plan.hypotheses = [mock_hyp]
    mock_plan.estimated_hypothesis_count = 1
    mock_build_plan.return_value = mock_plan

    phase2_event_chain = [
        ("VOL_SPIKE", "analyze_events.py", []),
        ("LIQUIDITY_GAP_PRINT", "analyze_events.py", []),
    ]

    experiment_config_path = tmp_path / "some_path.yaml"
    import yaml

    experiment_config_path.write_text(yaml.dump({"program_id": "test_prog"}))
    args = _make_args(experiment_config=str(experiment_config_path))

    stages = build_research_stages(
        args=args,
        run_id="r0",
        symbols="BTCUSDT",
        start="2024-01-01",
        end="2024-03-01",
        research_gate_profile="discovery",
        project_root=tmp_path,
        data_root=tmp_path,
        phase2_event_chain=phase2_event_chain,
    )

    # Check that only VOL_SPIKE stages are planned
    names = [s[0] for s in stages]
    assert any("VOL_SPIKE" in n for n in names)
    assert not any("LIQUIDITY_GAP_PRINT" in n for n in names)

    # Check that discovery stage has the right args
    discovery_stage = next(s for s in stages if "phase2_conditional_hypotheses" in s[0])
    s_args = discovery_stage[2]
    assert "--experiment_config" in s_args
    assert str(experiment_config_path) in s_args
    assert "--program_id" in s_args
    assert "test_prog" in s_args
