from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List

import yaml

import numpy as np
import pandas as pd

from project.core.config import get_data_root
from project.io.utils import ensure_dir, run_scoped_lake_path, write_parquet


FIVE_MINUTES = pd.Timedelta(minutes=5)
FUNDING_INTERVAL = pd.Timedelta(hours=8)
REGIME_SEQUENCE = (
    "basis_desync",
    "funding_dislocation",
    "trend_acceleration_exhaustion",
    "breakout_failure",
    "liquidity_stress",
    "deleveraging_burst",
    "post_deleveraging_rebound",
)

REGIME_EXPECTATIONS: Dict[str, Dict[str, Any]] = {
    "basis_desync": {
        "intended_effect_direction": "desync_signaled",
        "expected_event_types": [
            "CROSS_VENUE_DESYNC",
            "BASIS_DISLOC",
            "SPOT_PERP_BASIS_SHOCK",
        ],
        "expected_detector_families": [
            "cross_venue_desync",
            "basis_dislocation",
            "information_desync",
        ],
    },
    "funding_dislocation": {
        "intended_effect_direction": "funding_extreme_signaled",
        "expected_event_types": [
            "FND_DISLOC",
            "FUNDING_FLIP",
        ],
        "expected_detector_families": [
            "funding_dislocation",
            "positioning_extremes",
        ],
    },
    "trend_acceleration_exhaustion": {
        "intended_effect_direction": "trend_then_reversal",
        "expected_event_types": [
            "TREND_ACCELERATION",
            "TREND_EXHAUSTION_TRIGGER",
            "MOMENTUM_DIVERGENCE_TRIGGER",
        ],
        "expected_detector_families": [
            "trend_structure",
            "forced_flow_and_exhaustion",
        ],
    },
    "breakout_failure": {
        "intended_effect_direction": "failed_breakout_reversal",
        "expected_event_types": [
            "FALSE_BREAKOUT",
            "BREAKOUT_TRIGGER",
            "FAILED_CONTINUATION",
        ],
        "expected_detector_families": [
            "trend_structure",
            "volatility_transition",
            "forced_flow_and_exhaustion",
        ],
    },
    "liquidity_stress": {
        "intended_effect_direction": "liquidity_deterioration",
        "expected_event_types": [
            "LIQUIDITY_STRESS_DIRECT",
            "LIQUIDITY_STRESS_PROXY",
            "PRICE_VOL_IMBALANCE_PROXY",
            "SPREAD_REGIME_WIDENING_EVENT",
        ],
        "expected_detector_families": [
            "liquidity_shock",
            "liquidity_dislocation",
            "temporal",
        ],
    },
    "deleveraging_burst": {
        "intended_effect_direction": "forced_deleveraging",
        "expected_event_types": [
            "DELEVERAGING_WAVE",
            "CLIMAX_VOLUME_BAR",
        ],
        "expected_detector_families": [
            "positioning_extremes",
            "forced_flow_and_exhaustion",
        ],
    },
    "post_deleveraging_rebound": {
        "intended_effect_direction": "rebound_after_deleveraging",
        "expected_event_types": [
            "LIQUIDATION_EXHAUSTION_REVERSAL",
        ],
        "expected_detector_families": [
            "forced_flow_and_exhaustion",
        ],
    },
}


PROFILE_SETTINGS: Dict[str, Dict[str, Any]] = {
    "default": {
        "noise_mult": 1.0,
        "drift_mult": 1.0,
        "basis_wave_mult": 1.0,
        "spread_mult": 1.0,
        "volume_mult": 1.0,
        "oi_mult": 1.0,
        "regime_amplitude_mult": 1.0,
        "schedule_cycle_days": 60,
        "price_anchor": {"BTCUSDT": 95_000.0, "ETHUSDT": 3_200.0, "SOLUSDT": 145.0},
    },
    "2021_bull": {
        "noise_mult": 1.85,
        "drift_mult": 1.45,
        "basis_wave_mult": 1.2,
        "spread_mult": 0.92,
        "volume_mult": 1.35,
        "oi_mult": 1.20,
        "regime_amplitude_mult": 1.15,
        "schedule_cycle_days": 54,
        "price_anchor": {"BTCUSDT": 35_000.0, "ETHUSDT": 2_200.0, "SOLUSDT": 45.0},
    },
    "range_chop": {
        "noise_mult": 1.15,
        "drift_mult": 0.35,
        "basis_wave_mult": 0.75,
        "spread_mult": 1.1,
        "volume_mult": 0.85,
        "oi_mult": 0.92,
        "regime_amplitude_mult": 0.80,
        "schedule_cycle_days": 42,
        "price_anchor": {"BTCUSDT": 68_000.0, "ETHUSDT": 2_950.0, "SOLUSDT": 135.0},
    },
    "stress_crash": {
        "noise_mult": 2.35,
        "drift_mult": 0.55,
        "basis_wave_mult": 1.45,
        "spread_mult": 1.65,
        "volume_mult": 1.40,
        "oi_mult": 0.82,
        "regime_amplitude_mult": 1.45,
        "schedule_cycle_days": 36,
        "price_anchor": {"BTCUSDT": 58_000.0, "ETHUSDT": 2_850.0, "SOLUSDT": 118.0},
    },
    "alt_rotation": {
        "noise_mult": 1.45,
        "drift_mult": 1.05,
        "basis_wave_mult": 1.25,
        "spread_mult": 1.18,
        "volume_mult": 1.55,
        "oi_mult": 1.10,
        "regime_amplitude_mult": 1.20,
        "schedule_cycle_days": 48,
        "price_anchor": {"BTCUSDT": 82_000.0, "ETHUSDT": 4_100.0, "SOLUSDT": 185.0},
    },
}


def _resolve_profile_settings(volatility_profile: str) -> Dict[str, Any]:
    try:
        return PROFILE_SETTINGS[str(volatility_profile)]
    except KeyError as exc:
        choices = ", ".join(sorted(PROFILE_SETTINGS))
        raise ValueError(f"unknown volatility_profile={volatility_profile!r}; expected one of: {choices}") from exc


@dataclass


@dataclass(frozen=True)
class RegimeSegment:
    regime_type: str
    symbol: str
    start_ts: pd.Timestamp
    end_ts: pd.Timestamp
    sign: int
    amplitude: float

    def to_record(self) -> Dict[str, Any]:
        expectations = REGIME_EXPECTATIONS.get(self.regime_type, {})
        return {
            "regime_type": self.regime_type,
            "symbol": self.symbol,
            "start_ts": self.start_ts.isoformat(),
            "end_ts": self.end_ts.isoformat(),
            "sign": int(self.sign),
            "amplitude": float(self.amplitude),
            "intended_effect_direction": expectations.get("intended_effect_direction"),
            "expected_event_types": list(expectations.get("expected_event_types", [])),
            "expected_detector_families": list(expectations.get("expected_detector_families", [])),
        }


def _normalize_bounds(start_date: str, end_date: str) -> tuple[pd.Timestamp, pd.Timestamp]:
    start_ts = pd.Timestamp(start_date, tz="UTC")
    end_ts = pd.Timestamp(end_date, tz="UTC")
    if end_ts <= start_ts:
        raise ValueError("end_date must be after start_date")
    if end_ts.hour == 0 and end_ts.minute == 0 and end_ts.second == 0:
        end_exclusive = end_ts + pd.Timedelta(days=1)
    else:
        end_exclusive = end_ts
    return start_ts, end_exclusive


def _build_index(start_ts: pd.Timestamp, end_exclusive: pd.Timestamp) -> pd.DatetimeIndex:
    return pd.date_range(start=start_ts, end=end_exclusive - FIVE_MINUTES, freq="5min", tz="UTC")


def _regime_offsets(symbol: str) -> Dict[str, List[tuple[int, int, int, float]]]:
    if symbol.upper() == "BTCUSDT":
        return {
            "basis_desync": [(4, 12, 1, 42.0), (18, 10, -1, 38.0), (34, 14, 1, 48.0), (49, 10, -1, 44.0)],
            "funding_dislocation": [(8, 16, 1, 1.8), (24, 16, -1, 2.0), (40, 16, 1, 1.9), (54, 12, -1, 1.7)],
            "trend_acceleration_exhaustion": [(12, 18, 1, 1.0), (28, 18, -1, 1.1), (44, 18, 1, 0.9)],
            "breakout_failure": [(15, 10, 1, 1.3), (31, 10, -1, 1.2), (47, 10, 1, 1.4)],
            "liquidity_stress": [(20, 8, 1, 1.0), (36, 8, -1, 1.0), (52, 8, 1, 1.1)],
            "deleveraging_burst": [(10, 8, -1, 1.3), (26, 8, -1, 1.4), (42, 8, -1, 1.2), (56, 6, -1, 1.1)],
        }
    return {
        "basis_desync": [(6, 12, -1, 35.0), (21, 10, 1, 40.0), (37, 14, -1, 45.0), (51, 10, 1, 39.0)],
        "funding_dislocation": [(9, 16, -1, 1.7), (25, 16, 1, 1.8), (41, 16, -1, 1.9), (55, 12, 1, 1.6)],
        "trend_acceleration_exhaustion": [(13, 18, -1, 1.0), (29, 18, 1, 1.1), (45, 18, -1, 0.95)],
        "breakout_failure": [(17, 10, -1, 1.2), (33, 10, 1, 1.25), (48, 10, -1, 1.35)],
        "liquidity_stress": [(22, 8, 1, 1.0), (38, 8, -1, 1.0), (53, 8, 1, 1.0)],
        "deleveraging_burst": [(11, 8, -1, 1.0), (27, 8, -1, 1.1), (43, 8, -1, 1.0), (57, 6, -1, 0.9)],
    }


def build_regime_schedule(symbol: str, index: pd.DatetimeIndex, volatility_profile: str = "default") -> List[RegimeSegment]:
    start_ts = index[0]
    last_ts = index[-1]
    total_days = (last_ts - start_ts).days
    end_exclusive = last_ts + FIVE_MINUTES
    schedule: List[RegimeSegment] = []
    
    settings = _resolve_profile_settings(volatility_profile)
    cycle_days = int(settings.get("schedule_cycle_days", 60))
    num_cycles = (total_days // cycle_days) + 1
    
    # Base segments from offsets
    for cycle in range(num_cycles):
        cycle_offset_days = cycle * cycle_days
        for regime_type, specs in _regime_offsets(symbol).items():
            for day_offset, duration_hours, sign, amplitude in specs:
                actual_day_offset = cycle_offset_days + day_offset
                seg_start = start_ts + pd.Timedelta(days=actual_day_offset)
                seg_end = seg_start + pd.Timedelta(hours=duration_hours)
                
                if seg_start > last_ts:
                    continue
                seg_end = min(seg_end, end_exclusive)
                schedule.append(
                    RegimeSegment(
                        regime_type=regime_type,
                        symbol=symbol,
                        start_ts=seg_start,
                        end_ts=seg_end,
                        sign=sign,
                        amplitude=amplitude * float(settings.get("regime_amplitude_mult", 1.0)),
                    )
                )
            
    # Add post-deleveraging rebounds
    rebound_hours = 4
    bursts = [s for s in schedule if s.regime_type == "deleveraging_burst"]
    for burst in bursts:
        relief_start = burst.start_ts + (burst.end_ts - burst.start_ts) * 0.70
        start_ts_reb = relief_start
        end_ts_reb = min(start_ts_reb + pd.Timedelta(hours=rebound_hours), end_exclusive)
        
        schedule.append(
            RegimeSegment(
                regime_type="post_deleveraging_rebound",
                symbol=symbol,
                start_ts=start_ts_reb,
                end_ts=end_ts_reb,
                sign=-burst.sign, # Rebound is opposite direction of burst
                amplitude=burst.amplitude,
            )
        )
        
    return sorted(schedule, key=lambda seg: (seg.start_ts, seg.regime_type))


def _segment_mask(index: pd.DatetimeIndex, segment: RegimeSegment) -> np.ndarray:
    return np.asarray((index >= segment.start_ts) & (index < segment.end_ts), dtype=bool)


def _funding_mask(index: pd.DatetimeIndex, segment: RegimeSegment, funding_index: pd.DatetimeIndex) -> np.ndarray:
    return np.asarray((funding_index >= segment.start_ts) & (funding_index < segment.end_ts), dtype=bool)


def generate_symbol_frames(
    *,
    symbol: str,
    start_ts: pd.Timestamp,
    end_exclusive: pd.Timestamp,
    seed: int,
    noise_scale: float = 1.0,
    volatility_profile: str = "default",
) -> Dict[str, Any]:
    index = _build_index(start_ts, end_exclusive)
    funding_index = pd.date_range(start=start_ts, end=end_exclusive - FUNDING_INTERVAL, freq="8h", tz="UTC")
    rng = np.random.default_rng(seed)
    n = len(index)

    settings = _resolve_profile_settings(volatility_profile)
    eff_noise = noise_scale * float(settings.get("noise_mult", 1.0))
    prices = dict(settings.get("price_anchor", {}))
    base_price = float(prices.get(symbol.upper(), 100.0))

    if symbol.upper() == "BTCUSDT":
        base_volume = 220.0
        base_trade_count = 1_200.0
        base_oi = 2.4e9
    elif symbol.upper() == "ETHUSDT":
        base_volume = 1_600.0
        base_trade_count = 2_600.0
        base_oi = 1.2e9
    elif symbol.upper() == "SOLUSDT":
        base_volume = 12_000.0
        base_trade_count = 8_000.0
        base_oi = 4.0e8
    else:
        base_volume = 5_000.0
        base_trade_count = 3_000.0
        base_oi = 1.0e8

    base_drift = 0.00015 * float(settings.get("drift_mult", 1.0))
    returns = rng.normal(0.0, 0.00075 * eff_noise, n)
    returns += base_drift * np.sin(np.linspace(0.0, 10.0 * np.pi, n))
    basis_bps = rng.normal(0.0, 5.0 * eff_noise, n) + (6.0 * float(settings.get("basis_wave_mult", 1.0))) * np.sin(np.linspace(0.0, 4.0 * np.pi, n))
    spread_bps = np.full(n, (2.8 if symbol.upper() == "BTCUSDT" else 3.6) * float(settings.get("spread_mult", 1.0)), dtype=float)
    if symbol.upper() == "SOLUSDT":
        spread_bps = np.full(n, 5.5 * float(settings.get("spread_mult", 1.0)), dtype=float)
    
    volume_mult = np.ones(n, dtype=float) * float(settings.get("volume_mult", 1.0))
    wick_mult = np.ones(n, dtype=float)
    base_oi = base_oi * float(settings.get("oi_mult", 1.0))
    oi = base_oi + np.cumsum(rng.normal(0.0, base_oi * 0.000015 * eff_noise, n))
    liquidation_notional = np.zeros(n, dtype=float)
    funding_rate = rng.normal(0.0, 0.00004 * eff_noise, len(funding_index))

    # ... rest of the logic uses these variables ...
    segments = build_regime_schedule(symbol, index, volatility_profile=volatility_profile)
    for segment in segments:
        mask = _segment_mask(index, segment)
        if not mask.any():
            continue
        window_len = int(mask.sum())
        phase = np.linspace(0.0, 1.0, window_len)
        if segment.regime_type == "basis_desync":
            basis_bps[mask] += segment.sign * segment.amplitude * (0.6 + 0.4 * np.sin(np.pi * phase))
            spread_bps[mask] += 1.5
        elif segment.regime_type == "funding_dislocation":
            fmask = _funding_mask(index, segment, funding_index)
            funding_rate[fmask] += segment.sign * 0.00035 * segment.amplitude
            basis_bps[mask] += segment.sign * 18.0
            volume_mult[mask] *= 1.15
        elif segment.regime_type == "trend_acceleration_exhaustion":
            accel = int(max(2, window_len * 0.65))
            local = np.zeros(window_len)
            local[:accel] += segment.sign * 0.00115 * segment.amplitude
            local[accel:] -= segment.sign * 0.00155 * segment.amplitude
            returns[mask] += local
            volume_mult[mask] *= 1.25
            wick_mult[mask] *= 1.15
        elif segment.regime_type == "breakout_failure":
            compression_len = int(max(24, np.floor(window_len * 0.60)))
            breakout_len = int(max(2, np.ceil(window_len * 0.15)))
            reversal_start = min(window_len, compression_len + breakout_len)
            local = np.zeros(window_len)
            local[:compression_len] += segment.sign * 0.00003 * segment.amplitude
            local[compression_len:reversal_start] += segment.sign * 0.00235 * segment.amplitude
            local[reversal_start:] -= segment.sign * 0.00285 * segment.amplitude
            returns[mask] += local
            seg_wick = np.ones(window_len, dtype=float)
            seg_wick[:compression_len] = 0.32
            seg_wick[compression_len:reversal_start] = 1.45
            seg_wick[reversal_start:] = 1.85
            wick_mult[mask] *= seg_wick
            seg_volume = np.ones(window_len, dtype=float)
            seg_volume[:compression_len] = 0.58
            seg_volume[compression_len:reversal_start] = 1.55
            seg_volume[reversal_start:] = 1.35
            volume_mult[mask] *= seg_volume
            spread_bps[mask] += np.concatenate(
                [
                    np.full(compression_len, 0.45),
                    np.full(max(0, reversal_start - compression_len), 3.2),
                    np.full(max(0, window_len - reversal_start), 4.2),
                ]
            )[:window_len]
        elif segment.regime_type == "liquidity_stress":
            spread_bps[mask] += 12.0 * segment.amplitude
            wick_mult[mask] *= 2.2
            volume_mult[mask] *= 0.22
            basis_bps[mask] += segment.sign * 10.0
        elif segment.regime_type == "deleveraging_burst":
            shock_len = int(max(2, np.ceil(window_len * 0.70)))
            relief_len = max(1, window_len - shock_len)
            local = np.zeros(window_len)
            local[:shock_len] -= 0.0023 * segment.amplitude
            local[shock_len:] += 0.0022 * segment.amplitude
            returns[mask] += local

            oi_profile = np.concatenate(
                [
                    np.linspace(0.0, base_oi * 0.08 * segment.amplitude, shock_len, endpoint=False),
                    np.linspace(base_oi * 0.08 * segment.amplitude, base_oi * 0.05 * segment.amplitude, relief_len),
                ]
            )
            liq_profile = np.concatenate(
                [
                    np.linspace(2.5e5, 2.2e6 * segment.amplitude, shock_len, endpoint=False),
                    np.linspace(2.0e5 * segment.amplitude, 0.0, relief_len),
                ]
            )
            vol_profile = np.concatenate(
                [
                    np.full(shock_len, 1.35),
                    np.linspace(1.08, 0.82, relief_len),
                ]
            )
            wick_profile = np.concatenate(
                [
                    np.full(shock_len, 1.35),
                    np.linspace(1.30, 1.65, relief_len),
                ]
            )

            oi[mask] -= oi_profile[:window_len]
            liquidation_notional[mask] += liq_profile[:window_len]
            volume_mult[mask] *= vol_profile[:window_len]
            wick_mult[mask] *= wick_profile[:window_len]
        elif segment.regime_type == "post_deleveraging_rebound":
            # Rebound after deleveraging: positive returns, declining volume, elevated wicks
            rebound_len = int(max(2, np.ceil(window_len * 0.60)))
            drift_len = max(1, window_len - rebound_len)
            local = np.zeros(window_len)
            local[:rebound_len] += segment.sign * 0.0018 * segment.amplitude
            local[rebound_len:] += segment.sign * 0.0004 * segment.amplitude
            returns[mask] += local

            vol_profile = np.concatenate(
                [
                    np.linspace(1.25, 0.95, rebound_len, endpoint=False),
                    np.full(drift_len, 0.90),
                ]
            )
            wick_profile = np.concatenate(
                [
                    np.linspace(1.45, 1.15, rebound_len, endpoint=False),
                    np.full(drift_len, 1.05),
                ]
            )
            volume_mult[mask] *= vol_profile[:window_len]
            wick_mult[mask] *= wick_profile[:window_len]

    close = base_price * np.exp(np.cumsum(returns))
    open_ = np.concatenate(([close[0]], close[:-1]))
    intrabar_noise = np.abs(rng.normal(0.0012 * eff_noise, 0.00045 * eff_noise, n)) * wick_mult
    high = np.maximum(open_, close) * (1.0 + intrabar_noise)
    low = np.minimum(open_, close) * (1.0 - intrabar_noise * 0.96)
    volume = np.clip(base_volume * volume_mult * (1.0 + rng.normal(0.0, 0.22 * eff_noise, n)), 1.0, None)
    trade_count = np.clip(base_trade_count * volume_mult * (1.0 + rng.normal(0.0, 0.18 * eff_noise, n)), 10.0, None).astype(int)
    quote_volume = volume * close
    taker_ratio = np.clip(0.52 + 0.08 * np.sign(np.nan_to_num(returns)) + rng.normal(0.0, 0.03 * eff_noise, n), 0.15, 0.9)
    taker_buy_volume = volume * taker_ratio
    taker_buy_quote_volume = quote_volume * taker_ratio
    spot_close = close / (1.0 + basis_bps / 10_000.0)
    spot_open = np.concatenate(([spot_close[0]], spot_close[:-1]))
    spot_high = np.maximum(spot_open, spot_close) * (1.0 + intrabar_noise * 0.85)
    spot_low = np.minimum(spot_open, spot_close) * (1.0 - intrabar_noise * 0.82)

    depth_base = quote_volume * 5.0
    depth_usd = depth_base / np.maximum(1.0, 10000.0 * intrabar_noise)
    
    depth_ser = pd.Series(depth_usd)
    spread_ser = pd.Series(spread_bps)
    
    perp = pd.DataFrame(
        {
            "timestamp": index,
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
            "quote_volume": quote_volume,
            "trade_count": trade_count,
            "taker_buy_volume": taker_buy_volume,
            "taker_buy_quote_volume": taker_buy_quote_volume,
            "spread_bps": spread_bps,
            "depth_usd": depth_usd,
            "micro_depth_depletion": 1.0 - (depth_ser / (depth_ser.rolling(24).mean().shift(1).fillna(depth_ser))),
            "micro_spread_stress": spread_ser / (spread_ser.rolling(288).median().shift(1).fillna(spread_ser)),
            "is_synthetic": True,
            "symbol": symbol,
        }
    )
    raw_perp = perp.rename(columns={"taker_buy_volume": "taker_base_volume"}).copy()
    spot = pd.DataFrame(
        {
            "timestamp": index,
            "open": spot_open,
            "high": spot_high,
            "low": spot_low,
            "close": spot_close,
            "volume": volume * 0.92,
            "quote_volume": volume * 0.92 * spot_close,
            "trade_count": np.clip(trade_count * 0.88, 1, None).astype(int),
            "taker_buy_volume": taker_buy_volume * 0.9,
            "taker_buy_quote_volume": taker_buy_quote_volume * 0.9,
            "spread_bps": np.maximum(0.8, spread_bps * 0.65),
            "depth_usd": depth_usd * 0.8,
            "is_synthetic": True,
            "symbol": symbol,
        }
    )
    raw_spot = spot.rename(columns={"taker_buy_volume": "taker_base_volume"}).copy()
    funding = pd.DataFrame(
        {
            "timestamp": funding_index,
            "funding_rate": funding_rate,
            "funding_rate_scaled": funding_rate,
            "source": "synthetic_regimes",
            "symbol": symbol,
            "is_synthetic": True,
        }
    )
    open_interest = pd.DataFrame(
        {
            "timestamp": index,
            "open_interest": np.maximum(1.0, oi),
            "symbol": symbol,
            "is_synthetic": True,
        }
    )
    liquidations = pd.DataFrame(
        {
            "timestamp": index,
            "notional_usd": liquidation_notional,
            "symbol": symbol,
            "is_synthetic": True,
        }
    )
    liquidations = liquidations[liquidations["notional_usd"] > 0.0].reset_index(drop=True)

    return {
        "perp": perp,
        "raw_perp": raw_perp,
        "spot": spot,
        "raw_spot": raw_spot,
        "funding": funding,
        "open_interest": open_interest,
        "liquidations": liquidations,
        "regimes": [segment.to_record() for segment in segments],
    }


def _write_monthly_partitions(df: pd.DataFrame, output_dir: Path, filename_prefix: str) -> List[str]:
    written: List[str] = []
    if df.empty:
        return written
    ts = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    keyed = df.assign(_year=ts.dt.year, _month=ts.dt.month)
    for (year, month), chunk in keyed.groupby(["_year", "_month"], dropna=True):
        target_dir = output_dir / f"year={int(year):04d}" / f"month={int(month):02d}"
        filename = f"{filename_prefix}_{int(year):04d}-{int(month):02d}.parquet"
        actual_path, _ = write_parquet(chunk.drop(columns=["_year", "_month"]), target_dir / filename)
        written.append(str(actual_path))
    return written


def generate_synthetic_crypto_run(
    *,
    run_id: str,
    start_date: str,
    end_date: str,
    data_root: Path | None = None,
    symbols: Iterable[str] = ("BTCUSDT", "ETHUSDT"),
    noise_scale: float = 1.0,
    volatility_profile: str = "default",
) -> Dict[str, Any]:
    root = Path(data_root) if data_root is not None else get_data_root()
    start_ts, end_exclusive = _normalize_bounds(start_date, end_date)

    manifest: Dict[str, Any] = {
        "schema_version": "synthetic_crypto_regimes_v1",
        "run_id": run_id,
        "start_ts": start_ts.isoformat(),
        "end_exclusive_ts": end_exclusive.isoformat(),
        "symbols": [],
        "regime_types": list(REGIME_SEQUENCE),
        "noise_scale": noise_scale,
        "volatility_profile": volatility_profile,
        "available_profiles": sorted(PROFILE_SETTINGS),
    }
    regime_records: List[Dict[str, Any]] = []

    for offset, symbol in enumerate([str(s).strip().upper() for s in symbols if s.strip()]):
        payload = generate_symbol_frames(
            symbol=symbol,
            start_ts=start_ts,
            end_exclusive=end_exclusive,
            seed=20260308 + offset * 101,
            noise_scale=noise_scale,
            volatility_profile=volatility_profile,
        )
        perp_dir = run_scoped_lake_path(root, run_id, "cleaned", "perp", symbol, "bars_5m")
        spot_dir = run_scoped_lake_path(root, run_id, "cleaned", "spot", symbol, "bars_5m")
        raw_perp_dir = run_scoped_lake_path(root, run_id, "raw", "binance", "perp", symbol, "ohlcv_5m")
        raw_spot_dir = run_scoped_lake_path(root, run_id, "raw", "binance", "spot", symbol, "ohlcv_5m")
        funding_dir = run_scoped_lake_path(root, run_id, "raw", "binance", "perp", symbol, "funding")
        oi_dir = run_scoped_lake_path(root, run_id, "raw", "binance", "perp", symbol, "open_interest", "5m")
        liq_dir = run_scoped_lake_path(root, run_id, "raw", "binance", "perp", symbol, "liquidations")

        perp_files = _write_monthly_partitions(payload["perp"], perp_dir, f"bars_{symbol}_5m")
        spot_files = _write_monthly_partitions(payload["spot"], spot_dir, f"bars_{symbol}_spot_5m")
        raw_perp_files = _write_monthly_partitions(payload["raw_perp"], raw_perp_dir, f"ohlcv_{symbol}_5m")
        raw_spot_files = _write_monthly_partitions(payload["raw_spot"], raw_spot_dir, f"ohlcv_{symbol}_spot_5m")
        funding_path, _ = write_parquet(payload["funding"], funding_dir / "funding.parquet")
        oi_path, _ = write_parquet(payload["open_interest"], oi_dir / "open_interest.parquet")
        liq_path, _ = write_parquet(payload["liquidations"], liq_dir / "liquidations.parquet")

        manifest["symbols"].append(
            {
                "symbol": symbol,
                "rows_5m": int(len(payload["perp"])),
                "funding_rows": int(len(payload["funding"])),
                "regime_count": int(len(payload["regimes"])),
                "paths": {
                    "cleaned_perp": perp_files,
                    "cleaned_spot": spot_files,
                    "raw_perp": raw_perp_files,
                    "raw_spot": raw_spot_files,
                    "funding": str(funding_path),
                    "open_interest": str(oi_path),
                    "liquidations": str(liq_path),
                },
            }
        )
        regime_records.extend(payload["regimes"])

    synth_dir = root / "synthetic" / run_id
    ensure_dir(synth_dir)
    regimes_path = synth_dir / "synthetic_regime_segments.json"
    manifest_path = synth_dir / "synthetic_generation_manifest.json"
    regimes_path.write_text(json.dumps({"run_id": run_id, "segments": regime_records}, indent=2), encoding="utf-8")
    manifest["regime_segments_path"] = str(regimes_path)
    manifest["truth_map_path"] = str(regimes_path)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest



def generate_synthetic_dataset_suite(
    *,
    suite_config_path: Path,
    data_root: Path | None = None,
) -> Dict[str, Any]:
    payload = yaml.safe_load(Path(suite_config_path).read_text(encoding="utf-8")) or {}
    datasets = list(payload.get("datasets", []))
    if not datasets:
        raise ValueError("suite config must contain a non-empty 'datasets' list")
    root = Path(data_root) if data_root is not None else get_data_root()
    results: List[Dict[str, Any]] = []
    for item in datasets:
        manifest = generate_synthetic_crypto_run(
            run_id=str(item["run_id"]),
            start_date=str(item["start_date"]),
            end_date=str(item["end_date"]),
            data_root=root,
            symbols=item.get("symbols", ("BTCUSDT", "ETHUSDT")),
            noise_scale=float(item.get("noise_scale", 1.0)),
            volatility_profile=str(item.get("volatility_profile", "default")),
        )
        results.append(manifest)
    suite_name = str(payload.get("suite_name", Path(suite_config_path).stem))
    out_dir = root / "synthetic" / suite_name
    ensure_dir(out_dir)
    out_path = out_dir / "synthetic_dataset_suite_manifest.json"
    suite_manifest = {
        "schema_version": "synthetic_dataset_suite_v1",
        "suite_name": suite_name,
        "config_path": str(Path(suite_config_path)),
        "dataset_count": len(results),
        "datasets": results,
    }
    out_path.write_text(json.dumps(suite_manifest, indent=2), encoding="utf-8")
    return suite_manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate deterministic event-aware synthetic BTC/ETH lake data.")
    parser.add_argument("--run_id", required=True)
    parser.add_argument("--start_date", default="2026-01-01")
    parser.add_argument("--end_date", default="2026-02-28")
    parser.add_argument("--symbols", default="BTCUSDT,ETHUSDT")
    parser.add_argument("--noise_scale", type=float, default=1.0)
    parser.add_argument("--volatility_profile", default="default", choices=sorted(PROFILE_SETTINGS))
    parser.add_argument("--data_root", default=None)
    parser.add_argument("--suite_config", default=None, help="Optional YAML file describing multiple synthetic datasets to generate.")
    args = parser.parse_args(argv)

    data_root = Path(args.data_root) if args.data_root else get_data_root()
    if args.suite_config:
        manifest = generate_synthetic_dataset_suite(
            suite_config_path=Path(str(args.suite_config)),
            data_root=data_root,
        )
    else:
        manifest = generate_synthetic_crypto_run(
            run_id=str(args.run_id),
            start_date=str(args.start_date),
            end_date=str(args.end_date),
            data_root=data_root,
            symbols=[s.strip().upper() for s in str(args.symbols).split(",") if s.strip()],
            noise_scale=args.noise_scale,
            volatility_profile=str(args.volatility_profile),
        )
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
