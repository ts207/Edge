from __future__ import annotations

import argparse
import sys

from project.pipelines import run_all


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="backtest",
        description="Canonical CLI for the research-to-production strategy pipeline.",
    )
    subparsers = parser.add_subparsers(dest="command")

    # Pipeline subcommands
    pipeline_parser = subparsers.add_parser("pipeline", help="Pipeline commands")
    pipeline_sub = pipeline_parser.add_subparsers(dest="pipeline_command")
    pipeline_sub.add_parser("run-all", help="Run full pipeline")
    pipeline_sub.required = True

    # Ingest subcommand
    ingest_parser = subparsers.add_parser("ingest", help="Ingest raw data from external exchanges")
    ingest_parser.add_argument("--run_id", required=True, help="Unique identifier for this run")
    ingest_parser.add_argument(
        "--symbols", required=True, help="Comma‑separated list of symbols to ingest"
    )
    ingest_parser.add_argument("--start", required=True, help="Inclusive start date (YYYY-MM-DD)")
    ingest_parser.add_argument("--end", required=True, help="Inclusive end date (YYYY-MM-DD)")
    ingest_parser.add_argument(
        "--timeframe",
        default="1m",
        help="Timeframe to ingest, e.g. 1m, 5m. Only minute‑based intervals are valid.",
    )
    ingest_parser.add_argument(
        "--out_root",
        default=None,
        help="Output root directory for ingested Parquet files. Defaults to data root",
    )
    ingest_parser.add_argument(
        "--concurrency", type=int, default=5, help="Number of concurrent downloads"
    )
    ingest_parser.add_argument("--max_retries", type=int, default=5)
    ingest_parser.add_argument("--retry_backoff_sec", type=float, default=2.0)
    ingest_parser.add_argument("--force", type=int, default=0)
    ingest_parser.add_argument("--log_path", default=None)

    subparsers.required = True
    return parser


def main() -> int:
    parser = _build_parser()
    args, unknown = parser.parse_known_args()

    if args.command == "pipeline" and args.pipeline_command == "run-all":
        sys.argv = ["pipelines/run_all.py"] + unknown
        return int(run_all.main())

    if args.command == "ingest":
        from project.pipelines.ingest import ingest_binance_um_ohlcv as _ingest_ohlcv

        # Construct argv for the ingestion script.  We preserve unknown arguments
        # so that any extra flags supported by the ingestion implementation
        # remain functional.
        ingest_argv = [
            "ingest_binance_um_ohlcv.py",
            f"--run_id={args.run_id}",
            f"--symbols={args.symbols}",
            f"--start={args.start}",
            f"--end={args.end}",
            f"--timeframe={args.timeframe}",
            f"--concurrency={args.concurrency}",
            f"--max_retries={args.max_retries}",
            f"--retry_backoff_sec={args.retry_backoff_sec}",
            f"--force={args.force}",
        ]
        if args.out_root:
            ingest_argv.append(f"--out_root={args.out_root}")
        if args.log_path:
            ingest_argv.append(f"--log_path={args.log_path}")
        ingest_argv.extend(unknown)
        # Temporarily replace sys.argv for ingestion
        orig_argv = list(sys.argv)
        sys.argv = ingest_argv
        try:
            return _ingest_ohlcv.main()
        finally:
            sys.argv = orig_argv

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
