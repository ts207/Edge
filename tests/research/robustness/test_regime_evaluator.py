# tests/research/robustness/test_regime_evaluator.py
import pandas as pd
import numpy as np
import pytest
from project.research.robustness.regime_evaluator import evaluate_by_regime
from project.domain.hypotheses import HypothesisSpec, TriggerSpec


def _make_regime_features(n_bars: int = 600) -> pd.DataFrame:
    """
    Two-regime feature table:
    - bars 0..299: high_vol regime, event fires every 10 bars with positive returns
    - bars 300..599: low_vol regime, event fires every 10 bars with negative returns
    """
    np.random.seed(0)
    dates = pd.date_range("2023-01-01", periods=n_bars, freq="5min")

    # Rising price in first half (positive fwd returns), falling in second
    close = np.concatenate([
        100.0 + np.cumsum(np.abs(np.random.normal(0.05, 0.02, 300))),
        100.0 + np.cumsum(-np.abs(np.random.normal(0.05, 0.02, 300))),
    ])

    df = pd.DataFrame({"timestamp": dates, "close": close})
    df["event_vol_shock"] = [i % 10 == 0 for i in range(n_bars)]
    df["state_high_vol_regime"] = [1] * 300 + [0] * 300
    df["state_low_vol_regime"] = [0] * 300 + [1] * 300
    # Set other dimensions to defaults so labeler has full 4D context
    df["state_funding_positive"] = 1
    df["state_funding_negative"] = 0
    df["state_trend_active"] = 0
    df["state_chop_active"] = 1
    df["state_spread_tight"] = 1
    df["state_spread_wide"] = 0
    return df


def test_evaluate_by_regime_returns_dataframe():
    df = _make_regime_features()
    spec = HypothesisSpec(
        trigger=TriggerSpec.event("VOL_SHOCK"),
        direction="long",
        horizon="15m",
        template_id="base",
    )
    result = evaluate_by_regime(spec, df, horizon_bars=3)
    assert isinstance(result, pd.DataFrame)
    assert "regime" in result.columns
    assert "n" in result.columns
    assert "mean_return_bps" in result.columns
    assert "t_stat" in result.columns
    assert "valid" in result.columns


def test_evaluate_by_regime_splits_correctly():
    df = _make_regime_features()
    spec = HypothesisSpec(
        trigger=TriggerSpec.event("VOL_SHOCK"),
        direction="long",
        horizon="15m",
        template_id="base",
    )
    result = evaluate_by_regime(spec, df, horizon_bars=3, min_n_per_regime=5)
    valid = result[result["valid"]]
    # Both high_vol and low_vol regimes should appear
    regime_labels = set(valid["regime"].tolist())
    assert any("high_vol" in r for r in regime_labels)
    assert any("low_vol" in r for r in regime_labels)


def test_evaluate_by_regime_direction_differs():
    df = _make_regime_features()
    spec = HypothesisSpec(
        trigger=TriggerSpec.event("VOL_SHOCK"),
        direction="long",
        horizon="15m",
        template_id="base",
    )
    result = evaluate_by_regime(spec, df, horizon_bars=3, min_n_per_regime=5)
    valid = result[result["valid"]]
    high_vol = valid[valid["regime"].str.contains("high_vol")]["mean_return_bps"].iloc[0]
    low_vol = valid[valid["regime"].str.contains("low_vol")]["mean_return_bps"].iloc[0]
    # High vol half has positive returns, low vol has negative
    assert high_vol > 0
    assert low_vol < 0


def test_evaluate_by_regime_empty_features():
    df = pd.DataFrame(columns=["timestamp", "close", "event_vol_shock"])
    spec = HypothesisSpec(
        trigger=TriggerSpec.event("VOL_SHOCK"),
        direction="long",
        horizon="15m",
        template_id="base",
    )
    result = evaluate_by_regime(spec, df, horizon_bars=3)
    assert result.empty or (not result["valid"].any())
