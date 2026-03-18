from project.domain.hypotheses import HypothesisSpec, TriggerSpec

def test_hypothesis_id_determinism():
    """Verify that logically equivalent specs produce the same ID."""
    t = TriggerSpec.event("VOL_SPIKE")
    
    # None vs empty dict
    h1 = HypothesisSpec(trigger=t, direction="long", horizon="15m", template_id="test", context=None)
    h2 = HypothesisSpec(trigger=t, direction="long", horizon="15m", template_id="test", context={})
    
    assert h1.hypothesis_id() == h2.hypothesis_id()
    assert h1.context is None
    assert h2.context is None

def test_hypothesis_context_order_determinism():
    """Verify that context key order doesn't affect ID."""
    t = TriggerSpec.event("VOL_SPIKE")
    
    h1 = HypothesisSpec(trigger=t, direction="long", horizon="15m", template_id="test", 
                        context={"b": "2", "a": "1"})
    h2 = HypothesisSpec(trigger=t, direction="long", horizon="15m", template_id="test", 
                        context={"a": "1", "b": "2"})
    
    assert h1.hypothesis_id() == h2.hypothesis_id()
    assert h1.context == {"a": "1", "b": "2"}

def test_trigger_normalization():
    """Verify that trigger fields are normalized (casing/whitespace)."""
    t1 = TriggerSpec.event("vol_spike ")
    t2 = TriggerSpec.event(" VOL_SPIKE")
    
    assert t1.event_id == "VOL_SPIKE"
    assert t2.event_id == "VOL_SPIKE"
    
    h1 = HypothesisSpec(trigger=t1, direction="LONG", horizon="15m", template_id="test")
    h2 = HypothesisSpec(trigger=t2, direction="long ", horizon="15m", template_id="test")
    
    assert h1.hypothesis_id() == h2.hypothesis_id()
    assert h1.direction == "long"
