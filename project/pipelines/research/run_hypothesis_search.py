"""
Pipeline stage: run the hypothesis search engine.

Sequence:
  1. generate_hypotheses() from the configured search space.
  2. Load feature table for each symbol.
  3. run_distributed_search(hypotheses, features).
  4. Write hypothesis_metrics.parquet and hypothesis_search_summary.json.
  5. Optionally write bridge_candidates.parquet (--run_bridge_adapter flag).
"""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import List

import pandas as pd

from project.core.config import get_data_root
from project.research.search.generator import generate_hypotheses_with_audit
from project.research.search.distributed_runner import run_distributed_search
from project.research.search.bridge_adapter import hypotheses_to_bridge_candidates, split_bridge_candidates
from project.research.search.evaluator import evaluated_records_from_metrics
from project.research.phase2 import load_features
from project.io.utils import write_parquet


LOG = logging.getLogger(__name__)


def _normalize_audit_frame(rows: list[dict]) -> pd.DataFrame:
    frame = pd.DataFrame(rows or [])
    if frame.empty:
        return frame
    for column in frame.columns:
        if frame[column].dtype != "object":
            continue
        sample = next(
            (
                value
                for value in frame[column]
                if value is not None and not (isinstance(value, float) and pd.isna(value))
            ),
            None,
        )
        if isinstance(sample, (dict, list, tuple)):
            frame[column] = frame[column].map(
                lambda value: json.dumps(value, sort_keys=True)
                if isinstance(value, (dict, list, tuple))
                else value
            )
    return frame


def _write_hypothesis_audit_artifacts(out_dir: Path, audit: dict) -> None:
    write_parquet(_normalize_audit_frame(audit.get("generated_rows", [])), out_dir / "generated_hypotheses.parquet")
    write_parquet(_normalize_audit_frame(audit.get("rejected_rows", [])), out_dir / "rejected_hypotheses.parquet")
    write_parquet(_normalize_audit_frame(audit.get("feasible_rows", [])), out_dir / "feasible_hypotheses.parquet")


def _write_evaluation_artifacts(out_dir: Path, metrics: pd.DataFrame, gate_failures: pd.DataFrame) -> None:
    write_parquet(evaluated_records_from_metrics(metrics), out_dir / "evaluated_hypotheses.parquet")
    write_parquet(gate_failures, out_dir / "gate_failures.parquet")


def _load_all_features(
    symbols: List[str],
    run_id: str,
    timeframe: str,
    data_root: Path,
) -> pd.DataFrame:
    """Load and concatenate features across all symbols."""
    parts: list[pd.DataFrame] = []
    for sym in symbols:
        df = load_features(data_root, run_id, sym, timeframe=timeframe)
        if not df.empty:
            df = df.copy()
            df["symbol"] = sym
            parts.append(df)
    if not parts:
        return pd.DataFrame()
    return pd.concat(parts, ignore_index=True)


def _make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run hypothesis search engine")
    parser.add_argument("--run_id", required=True)
    parser.add_argument("--symbols", required=True)
    parser.add_argument("--timeframe", default="5m")
    parser.add_argument(
        "--n_workers",
        type=int,
        default=0,
        help="0 = auto (cpu_count)",
    )
    parser.add_argument("--chunk_size", type=int, default=256)
    parser.add_argument("--min_t_stat", type=float, default=1.5)
    parser.add_argument("--min_n", type=int, default=30)
    parser.add_argument("--use_context_quality", type=int, default=1)
    parser.add_argument(
        "--run_bridge_adapter",
        type=int,
        default=0,
        help="1 to emit bridge_candidates.parquet alongside metrics",
    )
    parser.add_argument(
        "--search_space_path",
        default=None,
        help="Optional override for search-space YAML path",
    )
    parser.add_argument(
        "--out_dir",
        default=None,
        help="Optional explicit output directory (for tests/local runs)",
    )
    parser.add_argument(
        "--data_root",
        default=None,
        help="Optional override for data root (defaults to configured data root)",
    )
    return parser


def main() -> int:
    parser = _make_parser()
    args = parser.parse_args()

    data_root = Path(args.data_root) if args.data_root else get_data_root()
    out_dir = Path(args.out_dir) if args.out_dir else (
        data_root / "reports" / "hypothesis_search" / args.run_id
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    symbols = [s.strip().upper() for s in str(args.symbols).split(",") if s.strip()]
    n_workers = args.n_workers if args.n_workers > 0 else None
    search_space_path = Path(args.search_space_path) if args.search_space_path else None

    features = _load_all_features(symbols, args.run_id, args.timeframe, data_root)
    try:
        hypotheses, generation_audit = generate_hypotheses_with_audit(
            search_space_path=search_space_path,
            features=None if features.empty else features,
        )
    except Exception as exc:  # pragma: no cover - defensive
        LOG.error("Failed to generate hypotheses: %s", exc)
        return 1

    _write_hypothesis_audit_artifacts(out_dir, generation_audit)
    LOG.info("Generated %d hypotheses", len(hypotheses))

    if features.empty:
        LOG.warning(
            "No features loaded for symbols=%s run_id=%s; writing empty output.",
            symbols,
            args.run_id,
        )
        metrics = pd.DataFrame()
    else:
        try:
            metrics = run_distributed_search(
                hypotheses,
                features,
                n_workers=n_workers,
                chunk_size=args.chunk_size,
                use_context_quality=bool(int(args.use_context_quality)),
            )
        except Exception as exc:  # pragma: no cover - defensive
            LOG.error("Distributed search failed: %s", exc)
            return 1

    metrics_path = out_dir / "hypothesis_metrics.parquet"
    if not metrics.empty:
        write_parquet(metrics, metrics_path)
    else:
        # Preserve schema by writing an empty frame with no rows.
        write_parquet(pd.DataFrame(), metrics_path)
    _, gate_failures = split_bridge_candidates(
        metrics,
        min_t_stat=args.min_t_stat,
        min_n=args.min_n,
    )
    _write_evaluation_artifacts(out_dir, metrics, gate_failures)

    passing = int(
        (metrics["t_stat"].abs() >= args.min_t_stat).sum()
    ) if (not metrics.empty and "t_stat" in metrics.columns) else 0
    summary = {
        "run_id": args.run_id,
        "symbols": symbols,
        "timeframe": args.timeframe,
        "total_hypotheses": int(generation_audit.get("counts", {}).get("generated", len(hypotheses))),
        "feasible_hypotheses": int(generation_audit.get("counts", {}).get("feasible", len(hypotheses))),
        "rejected_hypotheses": int(generation_audit.get("counts", {}).get("rejected", 0)),
        "rejection_reason_counts": dict(generation_audit.get("rejection_reason_counts", {})),
        "evaluated": int(len(metrics)) if not metrics.empty else 0,
        "passing_filter": passing,
        "use_context_quality": bool(int(args.use_context_quality)),
    }
    (out_dir / "hypothesis_search_summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    if int(args.run_bridge_adapter) and not metrics.empty:
        candidates = hypotheses_to_bridge_candidates(
            metrics,
            min_t_stat=args.min_t_stat,
            min_n=args.min_n,
        )
        write_parquet(candidates, out_dir / "bridge_candidates.parquet")

    LOG.info(
        "Wrote %d evaluated hypotheses (%d passing) to %s",
        len(metrics),
        passing,
        out_dir,
    )
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    raise SystemExit(main())
