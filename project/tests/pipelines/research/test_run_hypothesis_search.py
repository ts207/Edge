from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

import project.research.run_hypothesis_search as rhs
from project.domain.hypotheses import HypothesisSpec, TriggerSpec


def _make_features(n: int = 100) -> pd.DataFrame:
    rng = np.random.default_rng(7)
    ts = pd.date_range("2024-01-01", periods=n, freq="5min", tz="UTC")
    close = 100.0 * np.exp(np.cumsum(rng.normal(0, 0.001, n)))
    return pd.DataFrame(
        {
            "timestamp": ts,
            "close": close,
            "event_vol_spike": (rng.random(n) > 0.9).astype(int),
        }
    )


def _mock_generation():
    hypothesis = HypothesisSpec(
        trigger=TriggerSpec.event("VOL_SPIKE"),
        direction="long",
        horizon="5m",
        template_id="continuation",
        entry_lag=1,
    )
    return [hypothesis], {
        "generated_rows": [{"hypothesis_id": hypothesis.hypothesis_id()}],
        "rejected_rows": [],
        "feasible_rows": [{"hypothesis_id": hypothesis.hypothesis_id()}],
        "counts": {"generated": 1, "feasible": 1, "rejected": 0},
        "rejection_reason_counts": {},
    }


def test_main_exits_zero(monkeypatch, tmp_path):
    monkeypatch.setattr(rhs, "generate_hypotheses_with_audit", lambda **kwargs: _mock_generation())
    monkeypatch.setattr(
        rhs,
        "_load_all_features",
        lambda symbols, run_id, timeframe, data_root: _make_features(),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_hypothesis_search.py",
            "--run_id",
            "test_run",
            "--symbols",
            "BTCUSDT",
            "--timeframe",
            "5m",
            "--n_workers",
            "1",
            "--out_dir",
            str(tmp_path),
        ],
    )
    rc = rhs.main()
    assert rc == 0


def test_main_writes_parquet_output(monkeypatch, tmp_path):
    monkeypatch.setattr(rhs, "generate_hypotheses_with_audit", lambda **kwargs: _mock_generation())
    monkeypatch.setattr(
        rhs,
        "_load_all_features",
        lambda symbols, run_id, timeframe, data_root: _make_features(),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_hypothesis_search.py",
            "--run_id",
            "test_run",
            "--symbols",
            "BTCUSDT",
            "--timeframe",
            "5m",
            "--n_workers",
            "1",
            "--out_dir",
            str(tmp_path),
        ],
    )
    rhs.main()
    output_file = tmp_path / "hypothesis_metrics.parquet"
    assert output_file.exists()


def test_main_writes_json_summary(monkeypatch, tmp_path):
    monkeypatch.setattr(rhs, "generate_hypotheses_with_audit", lambda **kwargs: _mock_generation())
    monkeypatch.setattr(
        rhs,
        "_load_all_features",
        lambda symbols, run_id, timeframe, data_root: _make_features(),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_hypothesis_search.py",
            "--run_id",
            "test_run",
            "--symbols",
            "BTCUSDT",
            "--timeframe",
            "5m",
            "--n_workers",
            "1",
            "--out_dir",
            str(tmp_path),
        ],
    )
    rhs.main()
    summary_file = tmp_path / "hypothesis_search_summary.json"
    assert summary_file.exists()
    summary = json.loads(summary_file.read_text())
    assert "total_hypotheses" in summary
    assert "feasible_hypotheses" in summary
    assert "rejected_hypotheses" in summary
    assert "passing_filter" in summary
    assert "run_id" in summary
    assert (tmp_path / "generated_hypotheses.parquet").exists()
    assert (tmp_path / "feasible_hypotheses.parquet").exists()
    assert (tmp_path / "evaluated_hypotheses.parquet").exists()
    assert (tmp_path / "gate_failures.parquet").exists()


def test_main_normalizes_nested_audit_columns(monkeypatch, tmp_path):
    hypothesis = HypothesisSpec(
        trigger=TriggerSpec.event("VOL_SPIKE"),
        direction="long",
        horizon="5m",
        template_id="continuation",
        entry_lag=1,
    )
    monkeypatch.setattr(
        rhs,
        "generate_hypotheses_with_audit",
        lambda **kwargs: (
            [hypothesis],
            {
                "generated_rows": [
                    {
                        "hypothesis_id": hypothesis.hypothesis_id(),
                        "context": {},
                        "rejection_details": {},
                    }
                ],
                "rejected_rows": [],
                "feasible_rows": [
                    {
                        "hypothesis_id": hypothesis.hypothesis_id(),
                        "context": {"state_filter": "HIGH_VOL"},
                    }
                ],
                "counts": {"generated": 1, "feasible": 1, "rejected": 0},
                "rejection_reason_counts": {},
            },
        ),
    )
    monkeypatch.setattr(
        rhs,
        "_load_all_features",
        lambda symbols, run_id, timeframe, data_root: _make_features(),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_hypothesis_search.py",
            "--run_id",
            "test_run",
            "--symbols",
            "BTCUSDT",
            "--timeframe",
            "5m",
            "--n_workers",
            "1",
            "--out_dir",
            str(tmp_path),
        ],
    )
    rc = rhs.main()
    assert rc == 0
    generated = pd.read_parquet(tmp_path / "generated_hypotheses.parquet")
    assert generated.loc[0, "context"] == "{}"
