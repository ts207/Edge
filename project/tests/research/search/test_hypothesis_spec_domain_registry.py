from __future__ import annotations

from project.domain.hypotheses import TriggerSpec


def test_trigger_spec_event_validates_against_domain_registry():
    trigger = TriggerSpec.event("VOL_SHOCK")
    assert trigger.event_id == "VOL_SHOCK"
