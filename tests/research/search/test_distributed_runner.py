from __future__ import annotations

import numpy as np
import pandas as pd

from project.domain.hypotheses import HypothesisSpec, TriggerSpec
from project.research.search.evaluator import METRICS_COLUMNS
from project.research.search.distributed_runner import run_distributed_search


def _make_features(n: int = 200) -> pd.DataFrame:
    rng = np.random.default_rng(0)
    ts = pd.date_range("2024-01-01", periods=n, freq="5min", tz="UTC")
    close = 100.0 * np.exp(np.cumsum(rng.normal(0, 0.001, n)))
    return pd.DataFrame(
        {
            "timestamp": ts,
            "close": close,
            "event_vol_spike": (rng.random(n) > 0.9).astype(int),
        }
    )


def _make_hypotheses(n: int = 20) -> list[HypothesisSpec]:
    specs: list[HypothesisSpec] = []
    for i in range(n):
        direction = "long" if i % 2 == 0 else "short"
        specs.append(
            HypothesisSpec(
                trigger=TriggerSpec.event("vol_spike"),
                direction=direction,
                horizon="5m",
                template_id="continuation",
            )
        )

    # Deduplicate by id in case the spec generator would otherwise collide.
    seen: set[str] = set()
    unique: list[HypothesisSpec] = []
    for s in specs:
        hid = s.hypothesis_id()
        if hid not in seen:
            seen.add(hid)
            unique.append(s)
    return unique


def test_run_distributed_search_returns_dataframe():
    hypotheses = _make_hypotheses(10)
    features = _make_features()
    result = run_distributed_search(hypotheses, features, n_workers=1, chunk_size=5)
    assert isinstance(result, pd.DataFrame)


def test_run_distributed_search_has_correct_columns():
    hypotheses = _make_hypotheses(6)
    features = _make_features()
    result = run_distributed_search(hypotheses, features, n_workers=1, chunk_size=3)
    for col in METRICS_COLUMNS:
        assert col in result.columns, f"Missing column: {col}"


def test_run_distributed_search_no_duplicate_hypothesis_ids():
    hypotheses = _make_hypotheses(8)
    features = _make_features()
    result = run_distributed_search(hypotheses, features, n_workers=1, chunk_size=4)
    assert result["hypothesis_id"].nunique() == len(result)


def test_run_distributed_search_empty_hypotheses():
    features = _make_features()
    result = run_distributed_search([], features, n_workers=1)
    assert isinstance(result, pd.DataFrame)
    assert len(result) == 0
