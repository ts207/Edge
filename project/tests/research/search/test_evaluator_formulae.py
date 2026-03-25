import numpy as np
import pandas as pd
import pytest
from project.core.constants import BARS_PER_YEAR_BY_TIMEFRAME, HORIZON_BARS_BY_TIMEFRAME
from project.research.search.evaluator import evaluate_hypothesis_batch
from project.research.search.evaluator_utils import horizon_bars
from project.domain.hypotheses import HypothesisSpec, TriggerSpec


@pytest.fixture
def sample_data():
    """Produce 1000 bars of data with a predictable signal."""
    times = pd.date_range("2024-01-01", periods=1000, freq="5min")
    close = pd.Series(100.0, index=times)
    # Volatility is 1% per bar normally
    rets = np.random.normal(0, 0.01, 1000)
    close = close * np.exp(np.cumsum(rets))

    # Trigger at indices 10, 20, 30...
    # At trigger points, volatility is much lower (0.1%)
    # This will expose the T-stat bias if we only use trigger-subset std.
    mask = np.zeros(1000, dtype=bool)
    mask[np.arange(10, 500, 10)] = True

    # Force positive returns at trigger points to ensure positive t-stat
    # but make them lower vol than global.
    # Global std ~0.01. Subset std ~0.002.
    for i in np.where(mask)[0]:
        rets[i + 1] = 0.005 + np.random.normal(0, 0.001)  # 50bps edge + tiny noise

    close = 100.0 * np.exp(np.cumsum(rets))

    features = pd.DataFrame({"timestamp": times, "close": close, "spike": mask})
    # Pre-add standard columns that evaluator might expect
    features["volume"] = 1000.0
    return features


def test_sharpe_inflation_regression(sample_data):
    """
    Verify that Sharpe is not massively inflated for short horizons.
    Old buggy formula: (mean / std) * sqrt(ann / hbars)
    Correct formula (strategy): (mean / std) * sqrt(ann * n / len(features))
    """
    spec = HypothesisSpec(
        trigger=TriggerSpec.event("spike"), direction="long", horizon="5m", template_id="test"
    )

    results = evaluate_hypothesis_batch([spec], sample_data)
    sharpe = results.iloc[0]["sharpe"]
    print(f"DEBUG: sharpe={sharpe}")
    print(f"DEBUG: results={results.iloc[0].to_dict()}")

    # Old calculation: mean ~ 0.005, std ~ 0.002 -> sr_per_trade ~ 2.5
    # Multiplier = sqrt(105120 / 1) = 324.2
    # Sharpe ~ 2.5 * 324.2 = 810.5
    # Correct calculation: trades_per_year = 10 * (105120 / 1000) = 1051.2
    # SR = 2.5 * sqrt(1051.2) = 2.5 * 32.4 = 81.0

    # We want to catch the 810 vs 81 difference.
    assert sharpe < 150.0, f"Sharpe {sharpe} is inflated. Use strategy-based scaling (n/N)."


def test_tstat_selection_bias_regression(sample_data):
    """
    Verify that T-stat uses population volatility, not subset volatility.
    In sample_data: subset std ~ 0.001, population std ~ 0.01.
    T-stat using subset std will be ~10x higher than it should be.
    """
    spec = HypothesisSpec(
        trigger=TriggerSpec.event("spike"), direction="long", horizon="5m", template_id="test"
    )

    results = evaluate_hypothesis_batch([spec], sample_data)
    t_stat = results.iloc[0]["t_stat"]
    print(f"DEBUG: t_stat={t_stat}")

    # Population std is ~0.01. Edge is 0.005. n=10.
    # Expected t-stat = 0.005 / (0.01 / sqrt(10)) = 0.005 / 0.00316 = 1.58.
    # If inflated (using std~0.001): 0.005 / (0.001 / sqrt(10)) = 15.8.
    assert t_stat < 5.0, f"T-stat {t_stat} is inflated by subset selection bias."


def test_horizon_mapping_uses_canonical_5m_bar_counts():
    assert horizon_bars("1m") == HORIZON_BARS_BY_TIMEFRAME["1m"]
    assert horizon_bars("5m") == HORIZON_BARS_BY_TIMEFRAME["5m"]
    assert horizon_bars("15m") == HORIZON_BARS_BY_TIMEFRAME["15m"]
    assert horizon_bars("60m") == HORIZON_BARS_BY_TIMEFRAME["60m"]
    assert BARS_PER_YEAR_BY_TIMEFRAME["5m"] == 105120
