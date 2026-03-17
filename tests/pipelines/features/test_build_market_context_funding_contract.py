from __future__ import annotations

import pandas as pd
import pytest

from project.pipelines.features import build_market_context

def _feature_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "timestamp": pd.to_datetime(
                [
                    "2026-01-01T00:00:00Z",
                    "2026-01-01T00:05:00Z",
                    "2026-01-01T00:10:00Z",
                    "2026-01-01T00:15:00Z",
                ],
                utc=True,
            ),
            "close": [100.0, 101.0, 100.5, 101.5],
            "rv_96": [0.1, 0.2, 0.15, 0.22],
            "rv_pct_17280": [0.2, 0.4, 0.6, 0.8],
            "range_96": [2.0, 2.0, 2.0, 2.0],
            "range_med_2880": [4.0, 4.0, 4.0, 4.0],
        }
    )

def test_build_market_context_uses_canonical_funding_rate_scaled():
    features = _feature_frame()
    features["funding_rate_scaled"] = [0.0002, -0.0002, 0.0003, -0.0003]
    features["funding_rate"] = [999.0, 999.0, 999.0, 999.0]

    out = build_market_context._build_market_context(symbol="BTCUSDT", features=features)

    assert out["funding_rate_bps"].tolist() == pytest.approx([2.0, -2.0, 3.0, -3.0])
    assert set(out["carry_state_code"].tolist()) == {1.0, -1.0}

def test_build_market_context_requires_funding_rate_scaled_column():
    features = _feature_frame()
    features["funding_rate"] = [0.0002, -0.0002, 0.0003, -0.0003]

    with pytest.raises(ValueError, match="missing funding_rate_scaled"):
        build_market_context._build_market_context(symbol="BTCUSDT", features=features)

def test_build_market_context_handles_funding_gaps(caplog):
    features = _feature_frame()
    features["funding_rate_scaled"] = [0.0002, None, 0.0003, -0.0003]

    with caplog.at_level("WARNING"):
        out = build_market_context._build_market_context(symbol="BTCUSDT", features=features)
    
    assert "funding_rate_scaled contains 1/4 missing rows (25.00%) for BTCUSDT" in caplog.text
    # Should be filled with 0.0
    assert out.iloc[1]["funding_rate_scaled"] == 0.0
    assert out.iloc[1]["funding_rate_bps"] == 0.0

def test_build_market_context_handles_fully_missing_funding(caplog):
    features = _feature_frame()
    features["funding_rate_scaled"] = [None, None, None, None]

    with caplog.at_level("WARNING"):
        out = build_market_context._build_market_context(symbol="BTCUSDT", features=features)

    assert "funding_rate_scaled unavailable for BTCUSDT; defaulting all 4/4 rows to 0.0" in caplog.text
    assert out["funding_rate_scaled"].tolist() == [0.0, 0.0, 0.0, 0.0]

def test_build_market_context_materializes_canonical_state_columns():
    features = _feature_frame()
    features["funding_rate_scaled"] = [0.0002, -0.0002, 0.0003, -0.0003]
    features["spread_zscore"] = [0.5, 2.0, 2.5, 1.0]
    features["oi_notional"] = [100.0, 150.0, 200.0, 250.0]
    features["oi_delta_1h"] = [-10.0, -20.0, -5.0, -40.0]

    out = build_market_context._build_market_context(symbol="BTCUSDT", features=features)

    expected_state_cols = {
        "low_liquidity_state",
        "spread_elevated_state",
        "refill_lag_state",
        "aftershock_state",
        "compression_state_flag",
        "high_vol_regime",
        "low_vol_regime",
        "crowding_state",
        "funding_persistence_state",
        "deleveraging_state",
    }
    assert expected_state_cols.issubset(set(out.columns))
