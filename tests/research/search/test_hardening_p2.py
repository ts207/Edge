import pytest
import pandas as pd
from project.domain.hypotheses import HypothesisSpec, TriggerSpec
from project.research.search.validation import validate_hypothesis_spec
from project.research.search.evaluator_utils import context_mask

def test_validation_registry_failure(monkeypatch):
    """Verify that validation fails with error when the compiled registry cannot be loaded."""
    import project.research.search.validation as validation

    def mock_registry():
        raise FileNotFoundError("Mock registry missing")

    monkeypatch.setattr(validation, "get_domain_registry", mock_registry)
    
    t = TriggerSpec.event("VOL_SPIKE")
    h = HypothesisSpec(trigger=t, direction="long", horizon="15m", template_id="test", context={"vol": "high"})
    
    errors = validate_hypothesis_spec(h)
    assert any("Failed to load compiled domain registry" in e or "Mock registry missing" in e for e in errors)

def test_evaluator_utils_context_mask_registry_failure(monkeypatch):
    """Verify that context_mask handles registry loading failures gracefully."""
    import project.research.search.evaluator_utils as utils
    
    def mock_load_map():
        raise FileNotFoundError("Mock map failure")
        
    monkeypatch.setattr(utils, "load_context_state_map", mock_load_map)
    # Clear cache
    monkeypatch.setattr(utils, "_CACHED_CONTEXT_MAP", None)
    
    features = pd.DataFrame({"close": [100, 101]}, index=[0, 1])
    # context_mask should return None (resolving to invalid)
    assert context_mask({"vol": "high"}, features) is None
