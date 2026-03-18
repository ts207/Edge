from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from project.events.families.canonical_proxy import AbsorptionProxyDetector, DepthStressProxyDetector
from project.io.utils import read_parquet
from project.scripts.detector_audit_module import _enrich_df
from project.scripts.generate_synthetic_crypto_regimes import (
    build_regime_schedule,
    generate_synthetic_crypto_run,
    generate_symbol_frames,
)


def test_generate_symbol_frames_has_regimes_and_supporting_streams():
    payload = generate_symbol_frames(
        symbol="BTCUSDT",
        start_ts=pd.Timestamp("2026-01-01T00:00:00Z"),
        end_exclusive=pd.Timestamp("2026-01-08T00:00:00Z"),
        seed=7,
    )

    assert not payload["perp"].empty
    assert not payload["spot"].empty
    assert not payload["funding"].empty
    assert not payload["open_interest"].empty
    assert "spread_bps" in payload["perp"].columns
    assert "bid_depth_usd" in payload["perp"].columns
    assert "ask_depth_usd" in payload["perp"].columns
    assert "imbalance" in payload["perp"].columns
    assert len(payload["regimes"]) > 0


def test_deleveraging_regime_includes_relief_phase():
    payload = generate_symbol_frames(
        symbol="BTCUSDT",
        start_ts=pd.Timestamp("2026-01-01T00:00:00Z"),
        end_exclusive=pd.Timestamp("2026-03-01T00:00:00Z"),
        seed=7,
    )

    regimes = [seg for seg in payload["regimes"] if seg["regime_type"] == "deleveraging_burst"]
    assert regimes
    segment = regimes[0]
    perp = payload["perp"].copy()
    perp["timestamp"] = pd.to_datetime(perp["timestamp"], utc=True)
    liq = payload["liquidations"].copy()
    liq["timestamp"] = pd.to_datetime(liq["timestamp"], utc=True)

    seg_start = pd.Timestamp(segment["start_ts"], tz="UTC")
    seg_end = pd.Timestamp(segment["end_ts"], tz="UTC")
    seg_mask = (perp["timestamp"] >= seg_start) & (perp["timestamp"] < seg_end)
    seg_frame = perp.loc[seg_mask, ["timestamp", "close"]].reset_index(drop=True)
    assert not seg_frame.empty

    split_idx = max(1, int(len(seg_frame) * 0.70))
    shock = seg_frame.iloc[:split_idx]
    relief = seg_frame.iloc[split_idx:]
    assert not relief.empty
    assert shock["close"].iloc[-1] < shock["close"].iloc[0]
    assert relief["close"].iloc[-1] >= relief["close"].iloc[0]

    liq_seg = liq[(liq["timestamp"] >= seg_start) & (liq["timestamp"] < seg_end)].reset_index(drop=True)
    assert not liq_seg.empty
    liq_split = max(1, int(len(liq_seg) * 0.70))
    relief_liq = liq_seg["notional_usd"].iloc[liq_split:]
    assert relief_liq.iloc[-1] < relief_liq.iloc[0]
    assert relief_liq.iloc[-1] <= liq_seg["notional_usd"].max() * 0.1


def test_generate_synthetic_crypto_run_writes_run_scoped_lake(tmp_path):
    manifest = generate_synthetic_crypto_run(
        run_id="synthetic_test",
        start_date="2026-01-01",
        end_date="2026-01-20",
        data_root=tmp_path,
        symbols=["BTCUSDT", "ETHUSDT"],
    )

    manifest_path = tmp_path / "synthetic" / "synthetic_test" / "synthetic_generation_manifest.json"
    regimes_path = tmp_path / "synthetic" / "synthetic_test" / "synthetic_regime_segments.json"
    assert manifest_path.exists()
    assert regimes_path.exists()

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "synthetic_crypto_regimes_v1"
    assert len(payload["symbols"]) == 2
    assert payload["truth_map_path"] == str(regimes_path)

    truth = json.loads(regimes_path.read_text(encoding="utf-8"))
    assert truth["segments"]
    first_segment = truth["segments"][0]
    assert "expected_event_types" in first_segment
    assert "supporting_event_types" in first_segment
    assert "expected_detector_families" in first_segment
    assert "intended_effect_direction" in first_segment
    assert any(seg["regime_type"] == "post_deleveraging_rebound" for seg in truth["segments"])

    btc_perp = tmp_path / "lake" / "runs" / "synthetic_test" / "cleaned" / "perp" / "BTCUSDT" / "bars_5m"
    funding_path = Path(payload["symbols"][0]["paths"]["funding"])
    assert btc_perp.exists()
    assert funding_path.exists()

    funding = read_parquet(funding_path)
    assert "funding_rate_scaled" in funding.columns
    assert len(funding) > 0


def test_breakout_failure_regime_seeds_compression_then_expansion():
    payload = generate_symbol_frames(
        symbol="BTCUSDT",
        start_ts=pd.Timestamp("2026-01-01T00:00:00Z"),
        end_exclusive=pd.Timestamp("2026-03-01T00:00:00Z"),
        seed=7,
    )

    breakout_segment = next(seg for seg in payload["regimes"] if seg["regime_type"] == "breakout_failure")
    perp = payload["perp"].copy()
    perp["timestamp"] = pd.to_datetime(perp["timestamp"], utc=True)

    seg_start = pd.Timestamp(breakout_segment["start_ts"], tz="UTC")
    seg_end = pd.Timestamp(breakout_segment["end_ts"], tz="UTC")
    seg = perp[(perp["timestamp"] >= seg_start) & (perp["timestamp"] < seg_end)].reset_index(drop=True)
    assert not seg.empty

    compression_len = max(1, int(len(seg) * 0.60))
    breakout_len = max(1, int(len(seg) * 0.15))
    reversal_start = min(len(seg), compression_len + breakout_len)
    bar_range = ((seg["high"] - seg["low"]) / seg["close"]).astype(float)

    compressed = bar_range.iloc[:compression_len].median()
    breakout = bar_range.iloc[compression_len:reversal_start].median()
    reversal = bar_range.iloc[reversal_start:].median()

    assert compressed < breakout
    assert breakout < reversal


def test_liquidity_stress_regime_collapses_quote_volume_and_widens_spread():
    payload = generate_symbol_frames(
        symbol="BTCUSDT",
        start_ts=pd.Timestamp("2026-01-01T00:00:00Z"),
        end_exclusive=pd.Timestamp("2026-03-01T00:00:00Z"),
        seed=7,
    )

    liquidity_segment = next(seg for seg in payload["regimes"] if seg["regime_type"] == "liquidity_stress")
    perp = payload["perp"].copy()
    perp["timestamp"] = pd.to_datetime(perp["timestamp"], utc=True)

    seg_start = pd.Timestamp(liquidity_segment["start_ts"], tz="UTC")
    seg_end = pd.Timestamp(liquidity_segment["end_ts"], tz="UTC")
    seg = perp[(perp["timestamp"] >= seg_start) & (perp["timestamp"] < seg_end)].reset_index(drop=True)
    baseline = perp[(perp["timestamp"] >= seg_start - pd.Timedelta(hours=8)) & (perp["timestamp"] < seg_start)].reset_index(drop=True)

    assert not seg.empty
    assert not baseline.empty
    assert seg["quote_volume"].median() < baseline["quote_volume"].median() * 0.5
    assert seg["spread_bps"].median() > baseline["spread_bps"].median() * 2.0
    supporting = set(liquidity_segment["supporting_event_types"])
    assert {"ABSORPTION_PROXY", "DEPTH_STRESS_PROXY"}.issubset(supporting)
    windows = liquidity_segment["event_truth_windows"]
    assert "ABSORPTION_PROXY" in windows
    assert "DEPTH_STRESS_PROXY" in windows
    abs_window = windows["ABSORPTION_PROXY"][0]
    depth_window = windows["DEPTH_STRESS_PROXY"][0]
    assert pd.Timestamp(abs_window["start_ts"], tz="UTC") > seg_start
    assert pd.Timestamp(depth_window["end_ts"], tz="UTC") < seg_end


def test_liquidity_stress_regime_supports_proxy_detectors():
    payload = generate_symbol_frames(
        symbol="BTCUSDT",
        start_ts=pd.Timestamp("2026-01-01T00:00:00Z"),
        end_exclusive=pd.Timestamp("2026-03-01T00:00:00Z"),
        seed=7,
    )

    enriched = _enrich_df(payload["perp"])
    absorption_events = AbsorptionProxyDetector().detect(enriched, symbol="BTCUSDT")
    depth_events = DepthStressProxyDetector().detect(enriched, symbol="BTCUSDT")

    assert len(absorption_events) >= 1
    assert len(depth_events) >= 1


def test_post_deleveraging_rebound_properties():
    payload = generate_symbol_frames(
        symbol="BTCUSDT",
        start_ts=pd.Timestamp("2026-01-01T00:00:00Z"),
        end_exclusive=pd.Timestamp("2026-03-01T00:00:00Z"),
        seed=7,
    )

    rebound_segments = [seg for seg in payload["regimes"] if seg["regime_type"] == "post_deleveraging_rebound"]
    assert rebound_segments
    
    perp = payload["perp"].copy()
    perp["timestamp"] = pd.to_datetime(perp["timestamp"], utc=True)

    for segment in rebound_segments:
        seg_start = pd.Timestamp(segment["start_ts"], tz="UTC")
        seg_end = pd.Timestamp(segment["end_ts"], tz="UTC")
        seg = perp[(perp["timestamp"] >= seg_start) & (perp["timestamp"] < seg_end)].reset_index(drop=True)
        
        assert not seg.empty
        
        # Check returns (should match segment sign)
        total_ret = (seg["close"].iloc[-1] / seg["close"].iloc[0]) - 1.0
        if segment["sign"] > 0:
            assert total_ret > 0
        else:
            assert total_ret < 0
            
        # Check volume decay (first half should have higher volume than second half)
        mid_idx = len(seg) // 2
        assert seg["volume"].iloc[:mid_idx].mean() > seg["volume"].iloc[mid_idx:].mean()
        
        # Check wicks (should be elevated compared to baseline quiet periods)
        baseline = perp[(perp["timestamp"] >= seg_start - pd.Timedelta(hours=8)) & (perp["timestamp"] < seg_start)].reset_index(drop=True)
        if not baseline.empty:
            wick_seg = (seg["high"] - np.maximum(seg["open"], seg["close"])) / seg["close"]
            wick_base = (baseline["high"] - np.maximum(baseline["open"], baseline["close"])) / baseline["close"]
            assert wick_seg.mean() > wick_base.mean()
