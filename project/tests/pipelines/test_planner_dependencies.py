from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).parents[2]))


def test_phase2_search_engine_waits_for_registry_stages():
    from project.pipelines.planner import _resolve_dependencies

    stage_names = [
        "build_market_context_1m",
        "build_market_context_5m",
        "build_market_context_15m",
        "build_event_registry__BASIS_DISLOC_5m",
        "build_event_registry__BREAKOUT_TRIGGER_5m",
        "phase2_search_engine",
    ]

    deps = _resolve_dependencies("phase2_search_engine", stage_names)

    assert "build_market_context_1m" in deps
    assert "build_market_context_5m" in deps
    assert "build_market_context_15m" in deps
    assert "build_event_registry__BASIS_DISLOC_5m" in deps
    assert "build_event_registry__BREAKOUT_TRIGGER_5m" in deps


def test_build_universe_snapshots_waits_for_cleaned_stages():
    from project.pipelines.planner import _resolve_dependencies

    stage_names = [
        "build_cleaned_1m",
        "build_cleaned_5m",
        "build_cleaned_5m_spot",
        "build_universe_snapshots",
    ]

    deps = _resolve_dependencies("build_universe_snapshots", stage_names)

    assert "build_cleaned_1m" in deps
    assert "build_cleaned_5m" in deps
    assert "build_cleaned_5m_spot" not in deps


def test_phase2_event_conditioned_stages_are_timeframe_scoped():
    from project.pipelines.planner import _resolve_dependencies

    stage_names = [
        "canonicalize_event_episodes__VOL_SHOCK_5m",
        "canonicalize_event_episodes__VOL_SHOCK_15m",
        "phase2_conditional_hypotheses__VOL_SHOCK_5m",
        "phase2_conditional_hypotheses__VOL_SHOCK_15m",
        "bridge_evaluate_phase2__VOL_SHOCK_5m",
        "bridge_evaluate_phase2__VOL_SHOCK_15m",
    ]

    phase2_15m_deps = _resolve_dependencies(
        "phase2_conditional_hypotheses__VOL_SHOCK_15m", stage_names
    )
    bridge_15m_deps = _resolve_dependencies("bridge_evaluate_phase2__VOL_SHOCK_15m", stage_names)

    assert phase2_15m_deps == ["canonicalize_event_episodes__VOL_SHOCK_15m"]
    assert bridge_15m_deps == ["phase2_conditional_hypotheses__VOL_SHOCK_15m"]


def test_summarize_discovery_quality_waits_for_all_phase2_outputs():
    from project.pipelines.planner import _resolve_dependencies

    stage_names = [
        "phase2_conditional_hypotheses__VOL_SHOCK_5m",
        "bridge_evaluate_phase2__VOL_SHOCK_5m",
        "phase2_search_engine",
        "summarize_discovery_quality",
    ]

    deps = _resolve_dependencies("summarize_discovery_quality", stage_names)

    assert "phase2_conditional_hypotheses__VOL_SHOCK_5m" in deps
    assert "bridge_evaluate_phase2__VOL_SHOCK_5m" in deps
    assert "phase2_search_engine" in deps


def test_compile_strategy_blueprints_waits_for_promotions_without_checklist():
    from project.pipelines.planner import _resolve_dependencies

    stage_names = [
        "promote_candidates",
        "compile_strategy_blueprints",
    ]

    deps = _resolve_dependencies("compile_strategy_blueprints", stage_names)

    assert deps == ["promote_candidates"]


def test_select_profitable_strategies_waits_for_strategy_candidates():
    from project.pipelines.planner import _resolve_dependencies

    stage_names = [
        "promote_candidates",
        "update_edge_registry",
        "build_strategy_candidates",
        "select_profitable_strategies",
    ]

    deps = _resolve_dependencies("select_profitable_strategies", stage_names)

    assert deps == ["build_strategy_candidates"]
