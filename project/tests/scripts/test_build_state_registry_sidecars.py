from __future__ import annotations

from project.spec_registry import load_state_registry
from project.scripts.build_state_registry_sidecars import (
    build_runtime_state_registry_payload,
    build_state_grammar_payload,
    build_state_ontology_specs,
)


def test_state_registry_is_aggregated_from_state_specs() -> None:
    payload = load_state_registry()

    assert payload["metadata"]["status"] == "generated"
    assert payload["defaults"]["min_events"] == 200
    state_ids = {row["state_id"] for row in payload["states"]}
    assert "HIGH_VOL_REGIME" in state_ids
    high_vol = next(row for row in payload["states"] if row["state_id"] == "HIGH_VOL_REGIME")
    assert high_vol["kind"] == "state_definition"
    assert high_vol["runtime"]["state_engine"] == "VolatilityRegimeEngine"


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
