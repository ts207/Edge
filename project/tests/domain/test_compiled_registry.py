from __future__ import annotations

from project.domain.compiled_registry import get_domain_registry


def test_domain_registry_compiles_core_event_state_and_template_views():
    registry = get_domain_registry()

    assert registry.has_event("VOL_SHOCK")
    assert registry.has_state("LOW_LIQUIDITY_STATE")
    assert registry.get_operator("mean_reversion") is not None

    event = registry.get_event("VOL_SHOCK")
    assert event is not None
    assert event.event_type == "VOL_SHOCK"
    assert event.canonical_family
    assert event.signal_column
    assert event.spec_path.endswith("VOL_SHOCK.yaml")


def test_domain_registry_includes_runtime_promoted_event_specs():
    registry = get_domain_registry()

    promoted = registry.get_event("LIQUIDITY_STRESS_DIRECT")
    assert promoted is not None
    assert promoted.signal_column == "liquidity_stress_direct_event"
    assert promoted.spec_path.endswith("LIQUIDITY_STRESS_DIRECT.yaml")


def test_domain_registry_exposes_context_and_searchable_family_views():
    registry = get_domain_registry()

    assert registry.resolve_context_state("vol_regime", "high") == "HIGH_VOL_REGIME"
    assert "low" in registry.context_labels_for_family("vol_regime")
    assert "VOLATILITY_TRANSITION" in registry.searchable_event_families
    assert "TREND_STRUCTURE" in registry.searchable_state_families
    assert "AFTERSHOCK_STATE" in registry.valid_state_ids


def test_domain_registry_exposes_robustness_runtime_config():
    registry = get_domain_registry()

    assert len(registry.stress_scenarios) >= 3
    assert registry.stress_scenarios[0]["name"]
    assert registry.stress_scenarios[0]["feature"]

    assert len(registry.kill_switch_candidate_features) >= 5
    assert "rv_pct_17280" in registry.kill_switch_candidate_features


def test_domain_registry_exposes_sequence_and_interaction_runtime_config():
    registry = get_domain_registry()

    assert len(registry.sequence_definitions) >= 1
    assert registry.sequence_definitions[0]["name"]
    assert registry.sequence_definitions[0]["events"]

    assert len(registry.interaction_definitions) >= 1
    assert registry.interaction_definitions[0]["name"]
    assert registry.interaction_definitions[0]["left"]
    assert registry.interaction_definitions[0]["right"]
