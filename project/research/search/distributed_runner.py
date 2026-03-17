"""
Distributed hypothesis search runner.

Partitions a list of HypothesisSpec instances into chunks and evaluates each
chunk via multiprocessing.Pool. Optimized to avoid redundant to_dict calls.
"""
from __future__ import annotations

import logging
import multiprocessing
from typing import List, Optional, Sequence, Tuple

import pandas as pd

from project.domain.hypotheses import HypothesisSpec
from project.research.search.evaluator import evaluate_hypothesis_batch, METRICS_COLUMNS


log = logging.getLogger(__name__)


def _evaluate_chunk(args: Tuple[Sequence[HypothesisSpec], pd.DataFrame, int]) -> pd.DataFrame:
    """Worker function: unpack and evaluate a chunk of hypotheses."""
    chunk, features, min_sample_size = args
    if features.empty:
        return pd.DataFrame(columns=METRICS_COLUMNS)
    return evaluate_hypothesis_batch(list(chunk), features, min_sample_size=min_sample_size)


def run_distributed_search(
    hypotheses: List[HypothesisSpec],
    features: pd.DataFrame,
    *,
    n_workers: Optional[int] = None,
    chunk_size: int = 256,
    min_sample_size: int = 20,
) -> pd.DataFrame:
    """
    Evaluate hypotheses against features, optionally in parallel.
    """
    if not hypotheses:
        return pd.DataFrame(columns=METRICS_COLUMNS)

    if features is None or features.empty:
        return pd.DataFrame(columns=METRICS_COLUMNS)

    effective_workers = n_workers if n_workers is not None else multiprocessing.cpu_count()
    try:
        effective_workers = max(1, int(effective_workers))
    except Exception:
        effective_workers = 1

    chunks: list[list[HypothesisSpec]] = [
        hypotheses[i : i + int(chunk_size)]
        for i in range(0, len(hypotheses), int(chunk_size))
    ]
    if not chunks:
        return pd.DataFrame(columns=METRICS_COLUMNS)

    if effective_workers == 1 or len(chunks) == 1:
        parts = [
            evaluate_hypothesis_batch(chunk, features, min_sample_size=min_sample_size)
            for chunk in chunks
        ]
    else:
        try:
            # Note: Passing DataFrame directly works efficiently on Unix via fork (copy-on-write).
            # On Windows/MacOS (spawn), this will pickle the DataFrame which is still 
            # more efficient than to_dict("records").
            with multiprocessing.Pool(effective_workers) as pool:
                parts = pool.map(
                    _evaluate_chunk,
                    [(chunk, features, min_sample_size) for chunk in chunks],
                )
        except Exception as exc:
            log.warning(
                "Multiprocessing in run_distributed_search (workers=%d, chunks=%d) failed: %s. "
                "Falling back to sequential execution.",
                effective_workers, 
                len(chunks),
                exc,
                exc_info=True
            )
            parts = [
                evaluate_hypothesis_batch(
                    chunk, features, min_sample_size=min_sample_size
                )
                for chunk in chunks
            ]

    non_empty_parts = [p for p in parts if p is not None and not p.empty]
    if not non_empty_parts:
        return pd.DataFrame(columns=METRICS_COLUMNS)

    combined = pd.concat(non_empty_parts, ignore_index=True)
    if "hypothesis_id" in combined.columns:
        combined = combined.drop_duplicates(subset=["hypothesis_id"]).reset_index(drop=True)
    return combined
