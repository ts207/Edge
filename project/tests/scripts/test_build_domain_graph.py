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
    assert payload["template_operator_definitions"]["mean_reversion"]["raw"]["side_policy"] == "contrarian"
    assert payload["template_operator_definitions"]["continuation"]["raw"]["supports_trigger_types"] == [
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
