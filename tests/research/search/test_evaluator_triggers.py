import numpy as np
import pandas as pd
import pytest
from project.research.search.evaluator import evaluate_hypothesis_batch
from project.domain.hypotheses import HypothesisSpec, TriggerSpec

@pytest.fixture
def trigger_data():
    times = pd.date_range("2024-01-01", periods=100, freq="15min")
    close = pd.Series(100.0, index=times)
    # Add noise to ensure non-zero std
    rets = np.random.normal(0, 0.001, 100)
    close = close * np.exp(np.cumsum(rets))
    # Pattern: sequence_<id>, interaction_<id>
    features = pd.DataFrame({
        "timestamp": times,
        "close": close,
        "sequence_test_seq": [False] * 100,
        "interaction_test_int": [False] * 100,
    })
    features.iloc[10, features.columns.get_loc("sequence_test_seq")] = True
    features.iloc[12, features.columns.get_loc("sequence_test_seq")] = True
    features.iloc[14, features.columns.get_loc("sequence_test_seq")] = True
    features.iloc[20, features.columns.get_loc("interaction_test_int")] = True
    features.iloc[22, features.columns.get_loc("interaction_test_int")] = True
    features.iloc[24, features.columns.get_loc("interaction_test_int")] = True
    features["volume"] = 1000.0
    return features

def test_sequence_trigger_evaluation(trigger_data):
    """Verify that SEQUENCE triggers are correctly evaluated."""
    spec = HypothesisSpec(
        trigger=TriggerSpec(trigger_type="sequence", sequence_id="test_seq", events=["A", "B"]),
        direction="long",
        horizon="15m",
        template_id="test"
    )
    # Lower min_sample_size for easy testing
    results = evaluate_hypothesis_batch([spec], trigger_data, min_sample_size=1)
    
    # Should find 3 hits
    assert results.iloc[0]["n"] == 3
    assert results.iloc[0]["valid"] == True

def test_interaction_trigger_evaluation(trigger_data):
    """Verify that INTERACTION triggers are correctly evaluated."""
    spec = HypothesisSpec(
        trigger=TriggerSpec(trigger_type="interaction", interaction_id="test_int", left="A", right="B", op="and"),
        direction="long",
        horizon="15m",
        template_id="test"
    )
    results = evaluate_hypothesis_batch([spec], trigger_data, min_sample_size=1)
    
    # Should find 3 hits
    assert results.iloc[0]["n"] == 3
    assert results.iloc[0]["valid"] == True
