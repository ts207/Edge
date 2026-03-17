from __future__ import annotations
from project.core.config import get_data_root

import argparse
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from project.io.utils import ensure_dir, write_parquet
from project.specs.manifest import finalize_manifest, start_manifest

_BAR_FREQ = "5min"
_SPREAD_STRESS_THRESHOLD = 2.0  # multiples of median spread


def _load_tob_1s(run_id: str, symbol: str) -> pd.DataFrame:
    data_root = get_data_root()
    candidates = [
        data_root / "runs" / run_id / "lake" / "perp" / symbol / "tob_1s.parquet",
        data_root / "lake" / "perp" / symbol / "tob_1s.parquet",
    ]
    for path in candidates:
        if path.exists():
            try:
                return pd.read_parquet(path)
            except Exception:
                pass
    return pd.DataFrame()


def _build_rollup(symbol: str, tob: pd.DataFrame) -> pd.DataFrame:
    """Aggregate 1s top-of-book data into 5m microstructure metrics."""
    if tob.empty:
        return pd.DataFrame(
            columns=["timestamp", "symbol", "micro_spread_stress", "micro_depth_depletion",
                     "micro_sweep_pressure", "micro_imbalance", "micro_feature_coverage"]
        )

    tob = tob.copy()
    tob["timestamp"] = pd.to_datetime(tob["timestamp"], utc=True)
    tob = tob.sort_values("timestamp").reset_index(drop=True)

    tob["spread_bps"] = (tob["ask_price"] - tob["bid_price"]) / tob["bid_price"] * 10_000.0
    has_depth = "bid_qty" in tob.columns and "ask_qty" in tob.columns
    if has_depth:
        total_qty = tob["bid_qty"] + tob["ask_qty"]
        tob["imbalance"] = np.where(
            total_qty > 0, (tob["bid_qty"] - tob["ask_qty"]) / total_qty, 0.0
        )
        tob["depth"] = tob["bid_qty"] + tob["ask_qty"]

    # Floor to 5m bars
    tob["bar_ts"] = tob["timestamp"].dt.floor(_BAR_FREQ)

    # Global median spread for stress ratio
    global_median_spread = tob["spread_bps"].median()
    if global_median_spread <= 0:
        global_median_spread = 1.0

    rows = []
    for bar_ts, group in tob.groupby("bar_ts", sort=True):
        n = len(group)
        spread_mean = float(group["spread_bps"].mean())
        micro_spread_stress = spread_mean / global_median_spread

        if has_depth:
            depth_mean = float(group["depth"].mean())
            depth_min = float(group["depth"].min())
            micro_depth_depletion = 1.0 - (depth_min / depth_mean) if depth_mean > 0 else 0.0
            micro_imbalance = float(group["imbalance"].abs().mean())
            # Sweep pressure: fraction of bars where imbalance > 0.5
            micro_sweep_pressure = float((group["imbalance"].abs() > 0.5).mean())
        else:
            micro_depth_depletion = 0.0
            micro_imbalance = 0.0
            micro_sweep_pressure = 0.0

        micro_feature_coverage = float(n) / 300.0  # 300 = 5*60 1s bars

        rows.append({
            "timestamp": bar_ts,
            "symbol": symbol,
            "micro_spread_stress": micro_spread_stress,
            "micro_depth_depletion": micro_depth_depletion,
            "micro_sweep_pressure": micro_sweep_pressure,
            "micro_imbalance": micro_imbalance,
            "micro_feature_coverage": micro_feature_coverage,
        })

    if not rows:
        return pd.DataFrame(
            columns=["timestamp", "symbol", "micro_spread_stress", "micro_depth_depletion",
                     "micro_sweep_pressure", "micro_imbalance", "micro_feature_coverage"]
        )

    out = pd.DataFrame(rows)
    out["timestamp"] = pd.to_datetime(out["timestamp"], utc=True)
    return out.sort_values("timestamp").reset_index(drop=True)


def main(argv=None) -> int:
    data_root = get_data_root()
    parser = argparse.ArgumentParser(description="Build microstructure rollup.")
    parser.add_argument("--run_id", required=True)
    parser.add_argument("--symbols", required=True)
    parser.add_argument("--start", default=None)
    parser.add_argument("--end", default=None)
    parser.add_argument("--out_dir", default=None)
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    out_dir = Path(args.out_dir) if args.out_dir else data_root / "reports" / "microstructure" / args.run_id
    ensure_dir(out_dir)

    manifest = start_manifest("build_microstructure_rollup", args.run_id, vars(args), [], [])

    try:
        symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
        all_frames = []
        for symbol in symbols:
            tob = _load_tob_1s(args.run_id, symbol)
            if tob.empty:
                continue
            if "timestamp" in tob.columns:
                tob["timestamp"] = pd.to_datetime(tob["timestamp"], utc=True)
                if args.start:
                    start_ts = pd.Timestamp(args.start, tz="UTC")
                    tob = tob[tob["timestamp"] >= start_ts]
                if args.end:
                    end_ts = pd.Timestamp(args.end, tz="UTC") + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
                    tob = tob[tob["timestamp"] <= end_ts]
            rolled = _build_rollup(symbol, tob)
            all_frames.append(rolled)

        if all_frames:
            result = pd.concat(all_frames, ignore_index=True)
        else:
            result = pd.DataFrame(
                columns=["timestamp", "symbol", "micro_spread_stress", "micro_depth_depletion",
                         "micro_sweep_pressure", "micro_imbalance", "micro_feature_coverage"]
            )

        write_parquet(result, out_dir / "microstructure_rollup.parquet")
        finalize_manifest(manifest, "success", stats={"bars": len(result)})
        return 0
    except Exception:
        logging.exception("Microstructure rollup failed")
        finalize_manifest(manifest, "failed")
        return 1


def build_microstructure_rollup(bars: pd.DataFrame, symbol: str) -> pd.DataFrame:
    """Public API wrapper."""
    return _build_rollup(symbol, bars)
