import types
from pathlib import Path
import pytest
import sys
from unittest.mock import patch

# Add project root to path
sys.path.insert(0, str(Path(__file__).parents[2]))

from project.pipelines.stages.research import build_research_stages

def _make_args(**overrides):
    defaults = dict(
        run_phase2_conditional=1,
        phase2_event_type="all",
        phase2_gate_profile_resolved="auto",
        timeframes="15m",
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

DUMMY_REGISTRY = {
    "defaults": {
        "templates": ["continuation", "mean_reversion"],
        "horizons": ["5m", "15m", "60m"],
    },
    "events": {
        "VOL_SPIKE": {
            "templates": ["continuation", "mean_reversion", "vol_expansion"],
            "horizons": ["60m"],
        },
        "LIQUIDITY_GAP_PRINT": {
            "templates": ["continuation", "mean_reversion"],
            "horizons": ["15m"],
        }
    }
}

@patch("project.pipelines.research.registry_validation.load_template_registry")
def test_filter_events_by_agent_selection(mock_load_registry, tmp_path):
    mock_load_registry.return_value = DUMMY_REGISTRY
    
    phase2_event_chain = [
        ("VOL_SPIKE", "analyze_events.py", []),
        ("LIQUIDITY_GAP_PRINT", "analyze_events.py", []),
        ("TREND_ACCELERATION", "analyze_events.py", []),
    ]
    
    # Select only VOL_SPIKE
    args = _make_args(events=["VOL_SPIKE"])
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
    
    names = [s[0] for s in stages]
    assert any("VOL_SPIKE" in n for n in names)
    assert not any("LIQUIDITY_GAP_PRINT" in n for n in names)
    assert not any("TREND_ACCELERATION" in n for n in names)

@patch("project.pipelines.research.registry_validation.load_template_registry")
def test_invalid_event_raises_error(mock_load_registry, tmp_path):
    mock_load_registry.return_value = DUMMY_REGISTRY
    
    args = _make_args(events=["INVALID_EVENT"])
    with pytest.raises(ValueError, match="Event ID 'INVALID_EVENT' is not in the authoritative registry"):
        build_research_stages(
            args=args,
            run_id="r0",
            symbols="BTCUSDT",
            start="2024-01-01",
            end="2024-03-01",
            research_gate_profile="discovery",
            project_root=tmp_path,
            data_root=tmp_path,
            phase2_event_chain=[],
        )

@patch("project.pipelines.research.registry_validation.load_template_registry")
def test_invalid_template_raises_error(mock_load_registry, tmp_path):
    mock_load_registry.return_value = DUMMY_REGISTRY
    
    args = _make_args(templates=["INVALID_TEMPLATE"])
    with pytest.raises(ValueError, match="Template 'INVALID_TEMPLATE' is not in the authoritative registry"):
        build_research_stages(
            args=args,
            run_id="r0",
            symbols="BTCUSDT",
            start="2024-01-01",
            end="2024-03-01",
            research_gate_profile="discovery",
            project_root=tmp_path,
            data_root=tmp_path,
            phase2_event_chain=[],
        )

@patch("project.pipelines.research.registry_validation.load_template_registry")
def test_pass_templates_and_horizons_to_stages(mock_load_registry, tmp_path):
    mock_load_registry.return_value = DUMMY_REGISTRY
    
    phase2_event_chain = [("VOL_SPIKE", "analyze_events.py", [])]
    
    args = _make_args(
        events=["VOL_SPIKE"], 
        templates=["continuation"], 
        horizons=["15m", "60m"],
        directions=["long"],
        entry_lags=[1, 2],
        program_id="test_program",
        search_budget=100
    )
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
    
    discovery_stage = next(s for s in stages if "phase2_conditional_hypotheses" in s[0])
    s_args = discovery_stage[2]
    
    assert "--templates" in s_args
    assert "continuation" in s_args
    assert "--horizons" in s_args
    assert "15m" in s_args
    assert "60m" in s_args
    assert "--directions" in s_args
    assert "long" in s_args
    assert "--entry_lags" in s_args
    assert "1" in s_args
    assert "2" in s_args
    assert "--program_id" in s_args
    assert "test_program" in s_args
    assert "--search_budget" in s_args
    assert "100" in s_args
