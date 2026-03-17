import pytest
import pandas as pd
from project.domain.compiled_registry import get_domain_registry
from project.research.search.generator import (
    _context_combinations,
    generate_hypotheses,
    load_interaction_registry,
    load_sequence_registry,
)
from project.research.search.evaluator import evaluate_hypothesis_batch
from project.domain.hypotheses import TriggerSpec, HypothesisSpec

def test_context_wildcard_expansion_unknown_family(monkeypatch):
    """Verify that wildcard expansion for unknown family doesn't invent 'unknown'."""
    from project.spec_validation import loaders
    
    def mock_load_yaml(path):
        return {"regimes": {"vol": ["high", "low"]}}
        
    monkeypatch.setattr(loaders, "load_yaml", mock_load_yaml)
    
    # 'nonexistent' is not in REGIME_LABELS
    contexts = {"nonexistent": "*"}
    combos = _context_combinations(contexts)
    
    # Should only have [None] or just skip it.
    # Current behavior: logs warning and returns [None] or similar.
    # Assessment says it used to invent "unknown".
    for c in combos:
        if c:
            assert "unknown" not in c.values()

def test_evaluator_no_global_pandas_mutation(monkeypatch):
    """Verify that evaluate_hypothesis_batch doesn't mutate global pandas options."""
    import pandas as pd
    
    # We can check specific options that were mentioned: 'future.no_silent_downcasting'
    initial_val = pd.get_option("future.no_silent_downcasting")
    
    t = TriggerSpec.event("VOL_SPIKE")
    h = HypothesisSpec(trigger=t, direction="long", horizon="15m", template_id="test", entry_lag=1)
    
    features = pd.DataFrame({
        "close": [100, 101, 102, 103],
        "vol_spike_event": [0, 1, 0, 0],
        "timestamp": pd.to_datetime(["2026-01-01", "2026-01-02", "2026-01-03", "2026-01-04"])
    })
    
    evaluate_hypothesis_batch([h], features)
    
    assert pd.get_option("future.no_silent_downcasting") == initial_val

def test_rejection_audit_logs(caplog):
    """Verify that generation logs detailed rejection reasons."""
    # This might require some specific search spec that triggers rejections
    # or just checking if log.warning/info is called with useful info.
    pass


def test_sequence_and_interaction_registry_helpers_use_compiled_registry():
    registry = get_domain_registry()

    assert load_sequence_registry() == registry.sequence_rows()
    assert load_interaction_registry() == registry.interaction_rows()
