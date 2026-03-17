from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd

from project.core.config import get_data_root
from project.core.feature_schema import feature_dataset_dir_name
from project.io.utils import (
    ensure_dir,
    read_parquet,
    write_parquet,
    choose_partition_dir,
    list_parquet_files,
    run_scoped_lake_path,
)
from project.specs.manifest import finalize_manifest, start_manifest

_FUNDING_PERSIST_WINDOW = 12  # bars
_HIGH_VOL_PCT = 80
_LOW_VOL_PCT = 20
_SPREAD_ELEVATED_Z = 1.5
_CROWDING_OI_DELTA_PCT = 0.05


def _build_market_context(symbol: str, features: pd.DataFrame) -> pd.DataFrame:
    if "funding_rate_scaled" not in features.columns:
        raise ValueError(f"missing funding_rate_scaled for {symbol}")
    if features["funding_rate_scaled"].isna().any():
        missing_count = int(features["funding_rate_scaled"].isna().sum())
        total_rows = int(len(features))
        gap_pct = (missing_count / total_rows) if total_rows else 0.0
        if missing_count == total_rows:
            logging.warning(
                "funding_rate_scaled unavailable for %s; defaulting all %s/%s rows to 0.0",
                symbol,
                missing_count,
                total_rows,
            )
        else:
            logging.warning(
                "funding_rate_scaled contains %s/%s missing rows (%.2f%%) for %s; defaulting gaps to 0.0",
                missing_count,
                total_rows,
                gap_pct * 100.0,
                symbol,
            )
        features["funding_rate_scaled"] = features["funding_rate_scaled"].fillna(0.0)

    out = features.copy()

    # funding_rate_bps
    out["funding_rate_bps"] = out["funding_rate_scaled"] * 10_000.0

    # carry_state_code: +1 positive funding, -1 negative
    out["carry_state_code"] = np.where(out["funding_rate_scaled"] >= 0, 1.0, -1.0)

    funding_sign = np.sign(out["funding_rate_scaled"].fillna(0.0))
    funding_sign = pd.Series(funding_sign, index=out.index, dtype=float)
    funding_sign = funding_sign.where(funding_sign != 0.0, np.nan)
    funding_run_id = (funding_sign != funding_sign.shift()).cumsum()
    funding_streak = funding_sign.groupby(funding_run_id, dropna=False).cumcount() + 1
    out["funding_persistence_state"] = (
        funding_sign.notna() & (funding_streak >= _FUNDING_PERSIST_WINDOW)
    ).astype(float)

    # vol regime: use rv_96 percentile if available, else rv_pct_17280
    if "rv_pct_17280" in out.columns:
        out["high_vol_regime"] = (out["rv_pct_17280"] >= _HIGH_VOL_PCT / 100.0).astype(float)
        out["low_vol_regime"] = (out["rv_pct_17280"] <= _LOW_VOL_PCT / 100.0).astype(float)
    else:
        out["high_vol_regime"] = 0.0
        out["low_vol_regime"] = 0.0

    # spread_elevated_state
    if "spread_zscore" in out.columns:
        out["spread_elevated_state"] = (out["spread_zscore"] > _SPREAD_ELEVATED_Z).astype(float)
    else:
        out["spread_elevated_state"] = 0.0

    # low_liquidity_state: high_vol OR spread_elevated
    out["low_liquidity_state"] = (
        (out["high_vol_regime"] > 0) | (out["spread_elevated_state"] > 0)
    ).astype(float)

    # refill_lag_state: oi_delta negative (de-risking)
    if "oi_delta_1h" in out.columns:
        out["refill_lag_state"] = (out["oi_delta_1h"] < 0).astype(float)
        out["deleveraging_state"] = (
            out["oi_delta_1h"] < -out["oi_notional"].abs() * _CROWDING_OI_DELTA_PCT
            if "oi_notional" in out.columns
            else out["oi_delta_1h"] < 0
        ).astype(float)
    else:
        out["refill_lag_state"] = 0.0
        out["deleveraging_state"] = 0.0

    # aftershock_state: high vol + spread elevated
    out["aftershock_state"] = (
        (out["high_vol_regime"] > 0) & (out["spread_elevated_state"] > 0)
    ).astype(float)

    # compression_state_flag: low vol + low spread
    out["compression_state_flag"] = (
        (out["low_vol_regime"] > 0) & (out["spread_elevated_state"] == 0)
    ).astype(float)

    # crowding_state: OI high + funding positive
    if "oi_notional" in out.columns:
        oi_high = out["oi_notional"] > out["oi_notional"].rolling(96, min_periods=1).quantile(0.75)
        out["crowding_state"] = (oi_high & (out["funding_rate_scaled"] > 0)).astype(float)
    else:
        out["crowding_state"] = 0.0

    # trend regimes: use rolling log returns
    if "logret_1" in out.columns:
        rolling_ret = out["logret_1"].rolling(96, min_periods=1).sum()
        vol = out["logret_1"].rolling(96, min_periods=1).std() * np.sqrt(96)
        out["bull_trend_regime"] = (rolling_ret > vol).astype(float)
        out["bear_trend_regime"] = (rolling_ret < -vol).astype(float)
        out["chop_regime"] = ((rolling_ret.abs() <= vol)).astype(float)
    else:
        out["bull_trend_regime"] = 0.0
        out["bear_trend_regime"] = 0.0
        out["chop_regime"] = 0.0

    # ms_liquidation_state: rolling liquidation pressure
    if "liquidation_notional" in out.columns:
        liq_q80 = out["liquidation_notional"].rolling(288, min_periods=1).quantile(0.80)
        out["ms_liquidation_state"] = (out["liquidation_notional"] > liq_q80).astype(float)
    else:
        out["ms_liquidation_state"] = 0.0

    return out


def build_market_context(bars: pd.DataFrame, funding: pd.DataFrame, symbol: str) -> pd.DataFrame:
    """Build market context features."""
    features = bars.copy()
    if not funding.empty and "funding_rate_scaled" in funding.columns:
        features = features.merge(
            funding[["timestamp", "funding_rate_scaled"]], on="timestamp", how="left"
        )
    return _build_market_context(symbol, features)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build market context.")
    parser.add_argument("--run_id", required=True)
    parser.add_argument("--symbols", required=True)
    parser.add_argument("--timeframe", default="5m")
    parser.add_argument("--market", default="perp")
    parser.add_argument("--start", default=None)
    parser.add_argument("--end", default=None)
    parser.add_argument("--force", type=int, default=0)
    parser.add_argument("--log_path", default=None)
    args = parser.parse_args()

    run_id = args.run_id
    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    tf = args.timeframe
    market = args.market
    
    from project.core.config import get_data_root
    data_root = get_data_root()

    log_handlers = [logging.StreamHandler(sys.stdout)]
    if args.log_path:
        ensure_dir(Path(args.log_path).parent)
        log_handlers.append(logging.FileHandler(args.log_path))
    logging.basicConfig(level=logging.INFO, handlers=log_handlers, format="%(asctime)s %(levelname)s %(message)s")

    manifest = start_manifest("build_market_context", run_id, vars(args), [], [])

    try:
        for symbol in symbols:
            feature_dataset = feature_dataset_dir_name()
            feat_paths = [
                run_scoped_lake_path(data_root, run_id, "features", market, symbol, tf, feature_dataset),
                data_root / "lake" / "features" / market / symbol / tf / feature_dataset,
            ]
            feat_dir = choose_partition_dir(feat_paths)
            if not feat_dir:
                logging.warning(f"No {feature_dataset} found for {symbol} {tf}")
                continue
            features = read_parquet(list_parquet_files(feat_dir))
            
            # build_market_context expects bars and funding? 
            # Actually, _build_market_context expects the features DataFrame which ALREADY has funding_rate_scaled.
            result = _build_market_context(symbol, features)
            
            if not result.empty:
                result["timestamp"] = pd.to_datetime(result["timestamp"], utc=True)
                result["symbol"] = symbol
                
                # Write to lake
                out_root = run_scoped_lake_path(data_root, run_id, "features", market, symbol, tf, "market_context")
                for (year, month), group in result.groupby([result["timestamp"].dt.year, result["timestamp"].dt.month]):
                    out_dir = out_root / f"year={year}" / f"month={month:02d}"
                    out_path = out_dir / f"market_context_{symbol}_{year}-{month:02d}.parquet"
                    write_parquet(group, out_path)
                    logging.info(f"Wrote market context for {symbol} {year}-{month:02d} to {out_path}")

        finalize_manifest(manifest, "success")
        return 0
    except Exception as e:
        logging.exception("Market context building failed")
        finalize_manifest(manifest, "failed", error=str(e))
        return 1


if __name__ == "__main__":
    sys.exit(main())
