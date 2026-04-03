from __future__ import annotations

from project.scripts.build_state_registry_sidecars import (
    build_runtime_state_registry_payload,
    build_state_grammar_payload,
    build_state_ontology_specs,
)


def test_runtime_state_registry_payload_uses_canonical_state_metadata() -> None:
    payload = build_runtime_state_registry_payload()

    high_vol = payload["states"]["HIGH_VOL_REGIME"]
    assert high_vol["state_engine"] == "VolatilityRegimeEngine"
    assert high_vol["instrument_classes"] == ["crypto", "equities", "futures"]
    assert high_vol["tags"] == ["volatility"]

    crowding = payload["states"]["CROWDING_STATE"]
    assert crowding["state_engine"] == "MarketStateEngine"
    assert crowding["tags"] == ["positioning"]


def test_state_grammar_payload_uses_canonical_context_dimensions() -> None:
    payload = build_state_grammar_payload()

    assert payload["regimes"]["vol_regime"] == ["low", "high"]
    assert payload["context_state_map"]["vol_regime"]["high"] == "high_vol_regime"
    assert payload["context_state_map"]["funding_regime"]["crowded"] == "crowding_state"


def test_state_ontology_specs_cover_materialized_state_rows() -> None:
    payload = build_state_ontology_specs()

    assert "LOW_LIQUIDITY_STATE" in payload
    assert payload["LOW_LIQUIDITY_STATE"]["family"] == "LIQUIDITY_DISLOCATION"
    assert "mean_reversion" in payload["LOW_LIQUIDITY_STATE"]["allowed_templates"]
