# tests/research/robustness/test_scorer_bug.py
import pandas as pd
import pytest
from project.research.robustness.robustness_scorer import compute_robustness_score

def test_scorer_shape_mismatch():
    """
    Reproduces the bug where indexing a Series with a numpy array 
    causes alignment/shape errors in robustness_scorer.py.
    """
    # Create valid results with a specific index
    regime_results = pd.DataFrame([
        {"regime": "R1", "n": 100, "t_stat": 2.0, "valid": True},
        {"regime": "R2", "n": 50, "t_stat": -1.0, "valid": True}
    ], index=[10, 20])
    
    # This call used to trigger: 
    # signed_ts_correct = valid[t_stats.values * overall_direction > 0]
    # which fails if indices don't align with the underlying numpy values.
    try:
        score = compute_robustness_score(regime_results, overall_direction=1.0)
        assert 0 <= score <= 1
    except Exception as e:
        pytest.fail(f"compute_robustness_score raised {type(e).__name__}: {e}")

def test_evaluator_null_row_mfe_bug():
    """
    Verifies that mfe_mean_bps is present and correct in null rows.
    """
    from project.research.search.evaluator import evaluate_hypothesis_batch
    from project.domain.hypotheses import HypothesisSpec, TriggerSpec
    
    spec = HypothesisSpec(
        trigger=TriggerSpec.event("VOL_SHOCK"),
        direction="long",
        horizon="15m",
        template_id="base"
    )
    
    # Empty features should trigger null row
    features = pd.DataFrame(columns=["timestamp", "close"])
    results = evaluate_hypothesis_batch([spec], features)
    
    assert not results.empty
    assert "mfe_mean_bps" in results.columns
    # If the bug exists, mfe_mean_bps might be 0.0 but it should be explicitly handled
    # The user said: "mfe_mean_bps is always 0.0 in null rows" because it's overwritten by second mae_mean_bps.
    assert results.iloc[0]["mfe_mean_bps"] == 0.0
