"""
Verification tests for event detection logic.
"""

from __future__ import annotations

import pandas as pd
import numpy as np
import pytest
from project.events.families.volatility import VolSpikeDetector
from project.events.families.liquidity import (
    LiquidityStressDetector,
    DirectLiquidityStressDetector,
    ProxyLiquidityStressDetector,
)


def test_direct_vs_proxy_liquidity_detection():
    """Verify that Direct and Proxy detectors enforce their data requirements."""
    n = 100
    # 1. Direct Data
    df_direct = pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=n, freq="5min", tz="UTC"),
            "close": 100.0,
            "high": 100.1,
            "low": 99.9,
            "spread_bps": 2.0,
            "depth_usd": 1000000.0,
        }
    )
    df_direct.loc[50, "spread_bps"] = 20.0
    df_direct.loc[50, "depth_usd"] = 100000.0

    # 2. Proxy Data (no depth_usd)
    df_proxy = pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=n, freq="5min", tz="UTC"),
            "close": 100.0,
            "high": 100.1,
            "low": 99.9,
            "quote_volume": 1000000.0,
        }
    )
    df_proxy.loc[50, "high"] = 105.0  # Spread proxy spike via range
    df_proxy.loc[50, "quote_volume"] = 100000.0

    # Test Direct Detector
    det_direct = DirectLiquidityStressDetector()
    events_direct = det_direct.detect(df_direct, symbol="TEST")
    assert not events_direct.empty
    assert events_direct.iloc[0]["event_type"] == "LIQUIDITY_STRESS_DIRECT"

    with pytest.raises(ValueError, match="missing required columns"):
        det_direct.detect(df_proxy, symbol="TEST")

    # Test Proxy Detector
    det_proxy = ProxyLiquidityStressDetector()
    events_proxy = det_proxy.detect(df_proxy, symbol="TEST")
    assert not events_proxy.empty
    assert events_proxy.iloc[0]["event_type"] == "LIQUIDITY_STRESS_PROXY"

    # Test Legacy Polymorphic Detector
    det_legacy = LiquidityStressDetector()
    # Should detect as direct
    ev_leg_dir = det_legacy.detect(df_direct, symbol="TEST")
    assert ev_leg_dir.iloc[0]["event_type"] == "LIQUIDITY_STRESS_DIRECT"
    # Should detect as proxy
    ev_leg_prox = det_legacy.detect(df_proxy, symbol="TEST")
    assert ev_leg_prox.iloc[0]["event_type"] == "LIQUIDITY_STRESS_PROXY"


from project.eval.detection_verification_suite import (
    DetectionVerificationSuite,
    run_detection_verification,
)


def test_detection_verification_suite_run():
    report = run_detection_verification()
    assert len(report) == 3
    assert all(report["pass"])


def test_vol_spike_detection_on_synthetic_shock():
    """Verify that VolSpikeDetector triggers on a clear volatility shock."""
    # 1. Create synthetic data with a sudden volatility spike
    n = 1000
    np.random.seed(42)
    # Background vol
    prices = np.exp(np.random.randn(n).cumsum() * 0.001) * 100.0
    df = pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=n, freq="5min", tz="UTC"),
            "close": prices,
            "high": prices * 1.001,
            "low": prices * 0.999,
            "rv_96": pd.Series(np.full(n, 0.001)).rolling(96).std(),  # rolling std of returns
            "range_96": pd.Series(np.full(n, 0.002)),
            "range_med_2880": pd.Series(np.full(n, 0.002)),
        }
    )

    # Insert a shock at index 500
    df.loc[500, "close"] = df.loc[499, "close"] * 1.10  # 10% move
    # Recalculate rv_96 around the shock
    logret = np.log(df["close"] / df["close"].shift(1))
    df["rv_96"] = logret.rolling(window=96, min_periods=8).std()

    # 2. Run detector
    detector = VolSpikeDetector()
    events = detector.detect(df, symbol="BTCUSDT")

    # 3. Verify
    assert not events.empty
    # Match using eval_bar_ts
    shock_ts = df.loc[500, "timestamp"]
    end_ts = df.loc[510, "timestamp"]

    shock_events = events[(events["eval_bar_ts"] >= shock_ts) & (events["eval_bar_ts"] <= end_ts)]
    assert len(shock_events) > 0


def test_liquidity_shock_detection_on_synthetic_shock():
    """Verify that LiquidityStressDetector triggers on spread spike + depth collapse."""
    n = 1000
    df = pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=n, freq="5min", tz="UTC"),
            "close": 100.0,
            "high": 100.1,
            "low": 99.9,
            "spread_bps": 2.0,
            "depth_usd": 1000000.0,
        }
    )

    # Insert shock: spread 2 -> 20, depth 1M -> 100k
    df.loc[500, "spread_bps"] = 20.0
    df.loc[500, "depth_usd"] = 100000.0

    detector = LiquidityStressDetector()
    events = detector.detect(df, symbol="BTCUSDT")

    assert not events.empty

    shock_ts = df.loc[500, "timestamp"]
    # Check if any event was EVALUATED at the shock timestamp
    shock_events = events[events["eval_bar_ts"] == shock_ts]

    assert len(shock_events) > 0


def test_detection_edge_case_zero_volume():
    """Verify detectors handle zero volume gracefully."""
    n = 500
    df = pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=n, freq="5min", tz="UTC"),
            "close": 100.0,
            "high": 100.0,
            "low": 100.0,
            "volume": 0.0,
            "rv_96": 0.0,
            "range_96": 0.0,
            "range_med_2880": 0.0,
            "spread_bps": 0.0,
            "depth_usd": 1000000.0,
        }
    )

    # Should not crash
    detector = VolSpikeDetector()
    events = detector.detect(df, symbol="TEST")
    assert isinstance(events, pd.DataFrame)


def test_detection_edge_case_constant_price():
    """Verify detectors don't trigger on constant price."""
    n = 500
    df = pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=n, freq="5min", tz="UTC"),
            "close": 100.0,
            "high": 100.0,
            "low": 100.0,
            "rv_96": 0.0,
            "range_96": 0.0,
            "range_med_2880": 0.0,
            "spread_bps": 0.0,
            "depth_usd": 1000000.0,
        }
    )

    detector = VolSpikeDetector()
    events = detector.detect(df, symbol="TEST")
    assert events.empty
