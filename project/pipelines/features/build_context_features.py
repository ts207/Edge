from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd
from project.core.config import get_data_root
from project.core.feature_schema import feature_dataset_dir_name
from project.features.alignment import (
    align_funding_to_bars as _align_impl,
    assert_complete_funding_series as _assert_impl
)
from project.io.utils import (
    ensure_dir,
    read_parquet,
    write_parquet,
    choose_partition_dir,
    list_parquet_files,
    run_scoped_lake_path,
)
from project.specs.manifest import finalize_manifest, start_manifest

def _align_funding_to_bars(bars: pd.DataFrame, funding: pd.DataFrame, symbol: str) -> pd.DataFrame:
    """Compatibility wrapper for core alignment logic."""
    return _align_impl(bars, funding)

def _assert_complete_funding_series(df: pd.DataFrame, symbol: str) -> pd.Series:
    """Compatibility wrapper for core assertion logic."""
    return _assert_impl(df, symbol=symbol)

def build_context_features(bars: pd.DataFrame, funding: pd.DataFrame, symbol: str) -> pd.DataFrame:
    """Legacy entry point for context feature building."""
    return _align_impl(bars, funding)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build context features.")
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

    manifest = start_manifest("build_context_features", run_id, vars(args), [], [])

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
            
            # Context features for now is just a copy of features with potentially more alignment
            # In some versions it adds more features.
            result = features.copy()
            
            if not result.empty:
                result["timestamp"] = pd.to_datetime(result["timestamp"], utc=True)
                result["symbol"] = symbol
                
                # Write to lake
                out_root = run_scoped_lake_path(data_root, run_id, "features", market, symbol, tf, "context_features")
                for (year, month), group in result.groupby([result["timestamp"].dt.year, result["timestamp"].dt.month]):
                    out_dir = out_root / f"year={year}" / f"month={month:02d}"
                    out_path = out_dir / f"context_features_{symbol}_{year}-{month:02d}.parquet"
                    write_parquet(group, out_path)
                    logging.info(f"Wrote context features for {symbol} {year}-{month:02d} to {out_path}")

        finalize_manifest(manifest, "success")
        return 0
    except Exception as e:
        logging.exception("Context feature building failed")
        finalize_manifest(manifest, "failed", error=str(e))
        return 1


if __name__ == "__main__":
    sys.exit(main())
