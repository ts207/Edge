from __future__ import annotations

from project.domain.registry_loader import build_domain_graph_payload


def test_domain_graph_payload_contains_core_domain_sections() -> None:
    payload = build_domain_graph_payload()

    assert payload["kind"] == "domain_graph"
    assert "event_definitions" in payload
    assert "state_definitions" in payload
    assert "template_operator_definitions" in payload
    assert "regime_definitions" in payload
    assert "thesis_definitions" in payload
    assert "context_state_map" in payload
    assert "sequence_definitions" in payload
    assert "interaction_definitions" in payload


def test_domain_graph_payload_carries_runtime_and_state_metadata() -> None:
    payload = build_domain_graph_payload()

    depth_collapse = payload["event_definitions"]["DEPTH_COLLAPSE"]
    assert depth_collapse["detector_name"] == "DepthCollapseDetector"
    assert depth_collapse["canonical_regime"] == "LIQUIDITY_STRESS"

    assert "LOW_LIQUIDITY_STATE" in payload["state_definitions"]
    assert (
        payload["state_definitions"]["HIGH_VOL_REGIME"]["state_engine"]
        == "VolatilityRegimeEngine"
    )
    assert payload["state_definitions"]["HIGH_VOL_REGIME"]["instrument_classes"] == [
        "crypto",
        "equities",
        "futures",
    ]
    assert "mean_reversion" in payload["template_operator_definitions"]
    assert payload["template_operator_definitions"]["mean_reversion"]["template_kind"] == "execution_template"
    assert payload["template_operator_definitions"]["mean_reversion"]["side_policy"] == "contrarian"
    assert payload["template_operator_definitions"]["continuation"]["supports_trigger_types"] == [
        "EVENT",
        "STATE",
        "SEQUENCE",
        "INTERACTION",
    ]
    assert payload["regime_definitions"]["LIQUIDITY_STRESS"]["execution_style"] == "spread_aware"
    assert payload["thesis_definitions"]["THESIS_VOL_SHOCK"]["trigger_events"] == [
        "VOL_SHOCK"
    ]
    assert payload["thesis_definitions"]["THESIS_VOL_SHOCK_LIQUIDITY_CONFIRM"]["confirmation_events"] == [
        "LIQUIDITY_VACUUM"
    ]


def test_domain_graph_payload_is_a_slim_runtime_read_model() -> None:
    payload = build_domain_graph_payload()

    depth_collapse = payload["event_definitions"]["DEPTH_COLLAPSE"]
    assert "source_kind" not in depth_collapse
    assert set(depth_collapse["raw"].keys()) <= {
        "templates",
        "horizons",
        "conditioning_cols",
        "max_candidates_per_run",
        "state_overrides",
        "precedence_reason",
    }

    assert "raw" not in payload["state_definitions"]["HIGH_VOL_REGIME"]
    assert "source_kind" not in payload["state_definitions"]["HIGH_VOL_REGIME"]
    assert "raw" not in payload["regime_definitions"]["LIQUIDITY_STRESS"]
    assert "source_kind" not in payload["regime_definitions"]["LIQUIDITY_STRESS"]
    assert "raw" not in payload["thesis_definitions"]["THESIS_VOL_SHOCK"]
    assert "source_kind" not in payload["thesis_definitions"]["THESIS_VOL_SHOCK"]
    assert "raw" not in payload["template_operator_definitions"]["continuation"]

    unified = payload["unified_payload"]
    assert unified["kind"] == "event_unified_registry"
    assert "canonical_regimes" not in unified

    template_registry = payload["template_registry_payload"]
    assert template_registry["kind"] == "template_registry"
    assert "operators" not in template_registry

    family_registry = payload["family_registry_payload"]
    assert family_registry["kind"] == "family_registry"
