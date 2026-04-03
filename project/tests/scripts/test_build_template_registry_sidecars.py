from __future__ import annotations

from project.scripts.build_template_registry_sidecars import (
    build_ontology_template_registry_payload,
    build_runtime_template_registry_payload,
)


def test_runtime_template_registry_payload_uses_canonical_operator_runtime_fields() -> None:
    payload = build_runtime_template_registry_payload()

    continuation = payload["templates"]["continuation"]
    assert continuation["enabled"] is True
    assert continuation["supports_contexts"] is True
    assert continuation["supports_trigger_types"] == ["EVENT", "STATE", "SEQUENCE", "INTERACTION"]


def test_ontology_template_registry_payload_uses_canonical_family_and_filter_fields() -> None:
    payload = build_ontology_template_registry_payload()

    families = payload["families"]
    assert "LIQUIDITY_DISLOCATION" in families
    assert "mean_reversion" in families["LIQUIDITY_DISLOCATION"]["allowed_templates"]

    filters = payload["filter_templates"]
    assert filters["only_if_regime"]["feature"] == "rv_pct_17280"
    assert filters["only_if_regime"]["operator"] == ">"
