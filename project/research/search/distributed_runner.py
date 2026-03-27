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


def _evaluate_chunk(args: Tuple[Sequence[HypothesisSpec], pd.DataFrame, int, bool]) -> pd.DataFrame:
    """Worker function: unpack and evaluate a chunk of hypotheses."""
    chunk, features, min_sample_size, use_context_quality = args
    if features.empty:
        return pd.DataFrame(columns=METRICS_COLUMNS)
    return evaluate_hypothesis_batch(
        list(chunk),
        features,
        min_sample_size=min_sample_size,
        use_context_quality=use_context_quality,
    )


def run_distributed_search(
    hypotheses: List[HypothesisSpec],
    features: pd.DataFrame,
    *,
    n_workers: Optional[int] = None,
    chunk_size: int = 256,
    min_sample_size: int = 20,
    use_context_quality: bool = True,
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
        hypotheses[i : i + int(chunk_size)] for i in range(0, len(hypotheses), int(chunk_size))
    ]
    if not chunks:
        return pd.DataFrame(columns=METRICS_COLUMNS)

    if effective_workers == 1 or len(chunks) == 1:
        parts = [
            evaluate_hypothesis_batch(
                chunk,
                features,
                min_sample_size=min_sample_size,
                use_context_quality=use_context_quality,
            )
            for chunk in chunks
        ]
    else:
        try:
            # Note: Passing DataFrame directly works efficiently on Unix via fork (copy-on-write).
            # On Windows/MacOS (spawn), this will pickle the DataFrame which is still
            # more efficient than to_dict("records").
            with multiprocessing.Pool(effective_workers) as pool:
                # OOM Fix (SL-001): Only pass the subset of columns that these specific hypotheses need
                # rather than the full feature dataframe. This prevents massive memory duplication.
                args_list = []
                for chunk in chunks:
                    # Determine required columns for this chunk
                    req_cols = set(["symbol", "time_open", "time_close"])
                    for h in chunk:
                        if hasattr(h, "features"):
                            req_cols.update(h.features)
                        if hasattr(h, "feature_weights"):
                            req_cols.update(h.feature_weights.keys())

                    # Filter to available columns to avoid KeyError
                    valid_cols = [c for c in req_cols if c in features.columns]
                    chunk_features = features[valid_cols] if valid_cols else features

                    args_list.append((chunk, chunk_features, min_sample_size, use_context_quality))

                parts = pool.map(_evaluate_chunk, args_list)
        except Exception as exc:
            log.warning(
                "Multiprocessing in run_distributed_search (workers=%d, chunks=%d) failed: %s. "
                "Falling back to sequential execution.",
                effective_workers,
                len(chunks),
                exc,
                exc_info=True,
            )
            parts = [
                evaluate_hypothesis_batch(
                    chunk,
                    features,
                    min_sample_size=min_sample_size,
                    use_context_quality=use_context_quality,
                )
                for chunk in chunks
            ]

    non_empty_parts = [p for p in parts if p is not None and not p.empty]
    if not non_empty_parts:
        return pd.DataFrame(columns=METRICS_COLUMNS)

    normalized_parts = []
    for p in non_empty_parts:
        expected_cols = set(METRICS_COLUMNS)
        if p.columns.tolist() != list(METRICS_COLUMNS):
            for col in expected_cols - set(p.columns):
                p = p.copy()
                p[col] = None
            p = p[list(METRICS_COLUMNS)]
        p.attrs = {}
        normalized_parts.append(p)

    combined = pd.concat(normalized_parts, ignore_index=True)
    if "hypothesis_id" in combined.columns:
        combined = combined.drop_duplicates(subset=["hypothesis_id"]).reset_index(drop=True)
    return combined
