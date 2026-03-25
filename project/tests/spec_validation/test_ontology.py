import pytest
from project.spec_validation.ontology import (
    load_ontology_events,
    load_ontology_states,
    get_event_ids_for_family,
    get_state_ids_for_family,
    validate_ontology,
)


def test_load_ontology_events():
    events = load_ontology_events()
    assert len(events) > 0
    assert "VOL_SPIKE" in events


def test_get_event_ids_for_family():
    ids = get_event_ids_for_family("VOLATILITY_TRANSITION")
    assert "VOL_SPIKE" in ids
    assert "VOL_CLUSTER_SHIFT" in ids


def test_validate_ontology():
    errors = validate_ontology()
    assert len(errors) == 0, f"Ontology errors: {errors}"
