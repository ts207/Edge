# tests/research/search/test_evaluator_robustness.py
import pandas as pd
import numpy as np
import pytest
from project.research.search.evaluator import evaluate_hypothesis_batch
from project.domain.hypotheses import HypothesisSpec, TriggerSpec


def _make_diverse_features(n_bars: int = 1000) -> pd.DataFrame:
    np.random.seed(42)
    dates = pd.date_range("2023-01-01", periods=n_bars, freq="5min")
    close = 100.0 + np.cumsum(np.random.normal(0.0001, 0.01, n_bars))
    df = pd.DataFrame({"timestamp": dates, "close": close})
    df["event_test"] = [i % 10 == 0 for i in range(n_bars)]
    
    # Regime columns
    df["state_high_vol_regime"] = [1] * 333 + [0] * 333 + [0] * 334
    df["state_low_vol_regime"] = [0] * 333 + [1] * 333 + [1] * 334
    df["state_funding_positive"] = 1
    df["state_funding_negative"] = 0
    df["state_trend_active"] = 1
    df["state_chop_active"] = 0
    df["state_spread_tight"] = 1
    df["state_spread_wide"] = 0
    
    # Stress features
    df["rv_pct_17280"] = np.random.uniform(0.1, 0.95, n_bars)
    df["spread_zscore"] = np.random.normal(0, 1, n_bars)
    return df


def test_evaluate_hypothesis_batch_contains_new_metrics():
    df = _make_diverse_features()
    spec = HypothesisSpec(
        trigger=TriggerSpec.event("test"),
        direction="long",
        horizon="15m",
        template_id="base",
    )
    result = evaluate_hypothesis_batch([spec], df)
    assert not result.empty
    # We expect the new implementation to include these keys in the metrics
    # Note: we might decide to keep the same column names but change logic
    assert "robustness_score" in result.columns
    # We might add these if we want to expose them directly
    # assert "stress_score" in result.columns
    # assert "kill_switch_count" in result.columns


def test_evaluate_hypothesis_batch_uses_new_robustness_logic():
    """
    Verify that robustness score is no longer just 0.5 or 1.0 (naive logic).
    The new logic produces a continuous score.
    """
    df = _make_diverse_features()
    # Create a hypothesis that has varying performance across regimes
    spec = HypothesisSpec(
        trigger=TriggerSpec.event("test"),
        direction="long",
        horizon="15m",
        template_id="base",
    )
    result = evaluate_hypothesis_batch([spec], df)
    score = result.iloc[0]["robustness_score"]
    # Naive logic only ever produced [0.5, 0.8, 1.0]
    # New logic should produce something more nuanced
    assert score not in [0.5, 0.8, 1.0] or score == 0.0
