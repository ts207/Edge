from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from project.events.families.oi import DeleveragingWaveDetector
from project.events.detectors.trend import TrendAccelerationDetector

def create_mock_data(n=2000):
    rng = np.random.default_rng(42)
    # Price with some trends and vol
    returns = rng.normal(0, 0.001, n)
    # Add a strong trend
    returns[1000:1100] += 0.005 
    close = 100 * np.exp(np.cumsum(returns))
    
    # OI and Vol for DeleveragingWave
    oi_delta_1h = rng.normal(0, 1.0, n)
    # Inject several sharp drops of varying magnitude
    oi_delta_1h[100] = -10.0
    oi_delta_1h[500] = -5.0
    oi_delta_1h[1500] = -8.0
    
    rv_96 = rng.uniform(0.001, 0.002, n)
    # Inject vol spikes
    rv_96[100] = 0.01
    rv_96[500] = 0.005
    rv_96[1500] = 0.008
    
    close_ser = pd.Series(close)
    df = pd.DataFrame({
        "timestamp": pd.date_range("2024-01-01", periods=n, freq="5min", tz="UTC"),
        "close": close_ser,
        "oi_delta_1h": oi_delta_1h,
        "rv_96": rv_96,
        "open": close_ser.shift(1).fillna(close_ser[0]),
        "high": close_ser * 1.001,
        "low": close_ser * 0.999,
        "volume": 1000.0
    })
    return df

def test_deleveraging_wave_default_is_tight():
    df = create_mock_data()
    detector = DeleveragingWaveDetector()
    events = detector.detect(df, symbol="BTCUSDT")
    
    # Assert fewer than 3 events on this mock data.
    # The shock at 500 should be filtered out by tighter quantiles.
    assert len(events) <= 2

def test_trend_acceleration_default_is_tight():
    df = create_mock_data()
    detector = TrendAccelerationDetector()
    events = detector.detect(df, symbol="BTCUSDT")
    
    # Assert fewer than 5 events on 2000 bars.
    assert len(events) <= 5

def test_false_breakout_distance_filtering():
    from project.events.detectors.trend import FalseBreakoutDetector
    
    # Create data with an 11bps breakout and a 50bps breakout
    n = 200
    close = np.full(n, 100.0)
    
    close[49] = 100.11 # 11bps breakout
    close[50] = 100.00 # Back in
    
    close[150] = 100.50 # 50bps breakout
    close[151] = 100.00 # Back in
    
    df = pd.DataFrame({
        "timestamp": pd.date_range("2024-01-01", periods=n, freq="5min", tz="UTC"),
        "close": pd.Series(close)
    })
    
    detector = FalseBreakoutDetector()
    # With default min_breakout_distance = 0.0025 (25bps), it should IGNORE the 11bps breakout
    # and ONLY detect the 50bps one.
    events = detector.detect(df, symbol="BTCUSDT", trend_window=40)
    
    assert len(events) == 1
    # Check detected_ts instead of timestamp because timestamp is signal_ts (next bar)
    assert events["detected_ts"].iloc[0] == df["timestamp"].iloc[151]
