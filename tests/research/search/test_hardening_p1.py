import pytest
from project.domain.hypotheses import HypothesisSpec, TriggerSpec
from project.research.hypothesis_registry import _canonical_family, _template_side

def test_hypothesis_spec_immutability():
    """Verify that HypothesisSpec is frozen and attributes cannot be modified."""
    t = TriggerSpec.event("VOL_SPIKE")
    h = HypothesisSpec(trigger=t, direction="long", horizon="15m", template_id="test")
    
    with pytest.raises(Exception): # dataclasses.FrozenInstanceError
        h.direction = "short"

def test_trigger_spec_immutability():
    """Verify that TriggerSpec is frozen."""
    t = TriggerSpec.event("VOL_SPIKE")
    with pytest.raises(Exception):
        t.event_id = "NEW_EVENT"

def test_trigger_ontology_validation_events():
    """Verify that TriggerSpec.validate() rejects unknown event IDs."""
    t = TriggerSpec.event("NON_EXISTENT_EVENT_999")
    object.__setattr__(t, "_force_validation", True)
    with pytest.raises(ValueError, match="Unknown event_id"):
        t.validate()

def test_trigger_ontology_validation_states():
    """Verify that TriggerSpec.validate() rejects unknown state IDs."""
    t = TriggerSpec.state("NON_EXISTENT_STATE_999")
    object.__setattr__(t, "_force_validation", True)
    with pytest.raises(ValueError, match="Unknown state_id"):
        t.validate()


def test_trigger_ontology_validation_accepts_canonical_state_registry_entries():
    t = TriggerSpec.state("AFTERSHOCK_STATE")
    object.__setattr__(t, "_force_validation", True)
    t.validate()

def test_sequence_gap_validation():
    """Verify that sequence max_gap length is validated."""
    t = TriggerSpec.sequence("SEQ", ["VOL_SPIKE", "VOL_SPIKE"], [1, 2])
    object.__setattr__(t, "_force_validation", True)
    with pytest.raises(ValueError, match="Sequence max_gap length"):
        t.validate()

def test_canonical_family_fallback():
    """Verify that _canonical_family uses a robust fallback or reports error."""
    # Hardened fallback:
    assert _canonical_family("UNKNOWN_X_Y_Z") == "UNKNOWN_FAMILY"

def test_template_side_conditional_mapping():
    """Verify that 'conditional' side is mapped to 'both' or similar valid direction."""
    # In hypothesis_registry.py, _template_side(template)
    # The requirement: "Fix discovery registry side generation (conditional → both or explicit rule)"
    # Let's check a template that might be 'conditional' if any exists
    assert _template_side("unknown_template") == "both" 
