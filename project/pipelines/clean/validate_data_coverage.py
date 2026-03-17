from __future__ import annotations
from project.core.config import get_data_root

import argparse
import logging
import sys

import pandas as pd
from project.io.utils import choose_partition_dir, list_parquet_files, read_parquet, run_scoped_lake_path
from project.specs.manifest import finalize_manifest, start_manifest

def main() -> int:
    parser = argparse.ArgumentParser(description="Certification Gate: Minimum Data Coverage")
    parser.add_argument("--run_id", required=True)
    parser.add_argument("--symbols", required=True)
    parser.add_argument("--max_gap_pct", type=float, default=0.05)
    parser.add_argument("--timeframe", default="5m")
    args = parser.parse_args()
    
    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
    data_root = get_data_root()
    
    manifest = start_manifest(f"validate_data_coverage_{args.timeframe}", args.run_id, vars(args), [], [])
    
    symbol_stats = {}
    total_failures = 0
    
    for symbol in symbols:
        candidates = [
            run_scoped_lake_path(data_root, args.run_id, "cleaned", "perp", symbol, f"bars_{args.timeframe}"),
            data_root / "lake" / "cleaned" / "perp" / symbol / f"bars_{args.timeframe}",
        ]
        path = choose_partition_dir(candidates)
        if not path:
            logging.error(f"Missing cleaned bars for {symbol}")
            total_failures += 1
            continue
            
        df = read_parquet(list_parquet_files(path))
        if df.empty:
            logging.error(f"Empty cleaned bars for {symbol}")
            total_failures += 1
            continue
            
        if "is_gap" not in df.columns:
            logging.error(f"Missing 'is_gap' column for {symbol}")
            total_failures += 1
            continue

        gap_pct = float(df["is_gap"].mean())
        symbol_stats[symbol] = {"gap_pct": gap_pct}
        
        if gap_pct > args.max_gap_pct:
            logging.error(f"Symbol {symbol} exceeds max gap pct: {gap_pct:.2%} > {args.max_gap_pct:.2%}")
            total_failures += 1
            
    status = "success" if total_failures == 0 else "failed"
    finalize_manifest(manifest, status, stats=symbol_stats)
    return 1 if total_failures > 0 else 0

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    sys.exit(main())
