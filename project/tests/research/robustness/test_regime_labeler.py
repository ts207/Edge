# tests/research/robustness/test_regime_labeler.py
import pandas as pd
import numpy as np
import pytest
from project.research.robustness.regime_labeler import label_regimes, REGIME_DIMENSIONS


def _make_features_with_states(n_bars: int = 200) -> pd.DataFrame:
    """Synthetic features with known state column patterns."""
    dates = pd.date_range("2023-01-01", periods=n_bars, freq="5min")
    df = pd.DataFrame(
        {
            "timestamp": dates,
            "close": 100.0 + np.cumsum(np.random.normal(0, 0.05, n_bars)),
        }
    )
    # High vol in first half, low vol in second half
    df["state_high_vol_regime"] = [1] * 100 + [0] * 100
    df["state_low_vol_regime"] = [0] * 100 + [1] * 100
    # Funding positive throughout
    df["state_funding_positive"] = 1
    df["state_funding_negative"] = 0
    # Trend in first quarter, chop elsewhere
    df["state_trend_active"] = [1] * 50 + [0] * 150
    df["state_chop_active"] = [0] * 50 + [1] * 150
    # Spread tight throughout
    df["state_spread_tight"] = 1
    df["state_spread_wide"] = 0
    return df


def test_label_regimes_returns_series():
    df = _make_features_with_states()
    labels = label_regimes(df)
    assert isinstance(labels, pd.Series)
    assert len(labels) == len(df)


def test_label_regimes_known_regime():
    df = _make_features_with_states()
    labels = label_regimes(df)
    # First bar: high_vol + funding_pos + trend + tight
    assert "high_vol" in labels.iloc[0]
    assert "funding_pos" in labels.iloc[0]
    assert "trend" in labels.iloc[0]
    assert "tight" in labels.iloc[0]


def test_label_regimes_second_half():
    df = _make_features_with_states()
    labels = label_regimes(df)
    # Bar 150 (second half): low_vol + funding_pos + chop + tight
    assert "low_vol" in labels.iloc[150]
    assert "chop" in labels.iloc[150]


def test_label_regimes_no_state_columns():
    df = pd.DataFrame(
        {
            "timestamp": pd.date_range("2023-01-01", periods=10, freq="5min"),
            "close": 100.0,
        }
    )
    labels = label_regimes(df)
    # Should return "unknown" for all dimensions when no state cols found
    assert all("unknown" in lbl for lbl in labels)


def test_regime_dimensions_constant():
    # REGIME_DIMENSIONS must be a dict mapping dimension_name → {active: state_id, inactive_label: str}
    assert isinstance(REGIME_DIMENSIONS, dict)
    assert len(REGIME_DIMENSIONS) >= 4
    for dim, cfg in REGIME_DIMENSIONS.items():
        assert "states" in cfg
        assert isinstance(cfg["states"], dict)
