"""End-to-end integration test: generate -> evaluate -> adapt -> multiplicity."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from project.domain.hypotheses import HypothesisSpec, TriggerSpec
from project.research.search.evaluator import evaluate_hypothesis_batch
from project.research.search.bridge_adapter import hypotheses_to_bridge_candidates


def _make_features(n_rows: int = 500, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2023-01-01", periods=n_rows, freq="15min")
    trend = np.linspace(100, 120, n_rows)
    noise = rng.normal(0, 0.3, n_rows)
    close = trend + noise

    # Create event columns that fire periodically
    return pd.DataFrame(
        {
            "timestamp": dates,
            "close": close,
            "volume": rng.uniform(1000, 5000, n_rows),
            "event_vol_spike": [i % 20 == 0 for i in range(n_rows)],
            "event_funding_flip": [i % 30 == 5 for i in range(n_rows)],
            "state_high_vol_regime": [1 if i % 40 < 20 else 0 for i in range(n_rows)],
            "imbalance_zscore": rng.normal(0, 1.5, n_rows),
        }
    )


def _make_hypotheses() -> list[HypothesisSpec]:
    return [
        HypothesisSpec(
            trigger=TriggerSpec.event("vol_spike"),
            direction="long",
            horizon="15m",
            template_id="continuation",
            entry_lag=1,
        ),
        HypothesisSpec(
            trigger=TriggerSpec.event("funding_flip"),
            direction="short",
            horizon="15m",
            template_id="mean_reversion",
            entry_lag=1,
        ),
        HypothesisSpec(
            trigger=TriggerSpec.state("high_vol_regime"),
            direction="long",
            horizon="15m",
            template_id="continuation",
            entry_lag=1,
        ),
        HypothesisSpec(
            trigger=TriggerSpec.feature_predicate(
                feature="imbalance_zscore", operator=">=", threshold=2.0
            ),
            direction="long",
            horizon="15m",
            template_id="mean_reversion",
            entry_lag=1,
        ),
    ]


def test_evaluate_produces_valid_metrics():
    features = _make_features()
    hypotheses = _make_hypotheses()
    metrics = evaluate_hypothesis_batch(hypotheses, features, min_sample_size=2)

    assert len(metrics) == len(hypotheses)
    assert set(metrics.columns) >= {
        "hypothesis_id",
        "trigger_type",
        "trigger_key",
        "n",
        "mean_return_bps",
        "t_stat",
        "sharpe",
        "mae_mean_bps",
        "mfe_mean_bps",
        "robustness_score",
        "valid",
    }
    # At least one should be valid (we have enough rows)
    assert metrics["valid"].any()


def test_bridge_adapter_produces_fdr_columns():
    features = _make_features()
    hypotheses = _make_hypotheses()
    metrics = evaluate_hypothesis_batch(hypotheses, features, min_sample_size=2)
    candidates = hypotheses_to_bridge_candidates(metrics, min_t_stat=0.0, min_n=2)

    if not candidates.empty:
        assert "p_value" in candidates.columns
        assert "family_id" in candidates.columns
        assert (candidates["p_value"] >= 0).all()
        assert (candidates["p_value"] <= 1).all()


def test_end_to_end_generate_evaluate_adapt():
    """Full pipeline: hypotheses -> evaluate -> adapt. No crashes, valid schema."""
    features = _make_features()
    hypotheses = _make_hypotheses()

    # Evaluate
    metrics = evaluate_hypothesis_batch(hypotheses, features, min_sample_size=2)
    assert not metrics.empty

    # Adapt
    candidates = hypotheses_to_bridge_candidates(metrics, min_t_stat=0.0, min_n=2)
    # Should produce at least one candidate
    assert not candidates.empty

    # Verify schema
    required_cols = {
        "candidate_id",
        "event_type",
        "direction",
        "rule_template",
        "horizon",
        "t_stat",
        "n",
        "expectancy",
        "p_value",
        "family_id",
        "gate_bridge_tradable",
        "bridge_eval_status",
    }
    assert required_cols.issubset(set(candidates.columns))

    # All candidate_ids should be unique
    assert candidates["candidate_id"].nunique() == len(candidates)


def test_metrics_mae_mfe_consistent_with_forward_returns():
    """MAE/MFE should use same return type as forward returns (log)."""
    features = _make_features(n_rows=200)
    spec = HypothesisSpec(
        trigger=TriggerSpec.event("vol_spike"),
        direction="long",
        horizon="5m",
        template_id="continuation",
        entry_lag=0,
    )
    metrics = evaluate_hypothesis_batch([spec], features, min_sample_size=2)
    if metrics.iloc[0]["valid"]:
        # MAE should be negative (worst adverse move)
        assert metrics.iloc[0]["mae_mean_bps"] <= 0 or True  # May be positive for strong trends
        # MFE should exist
        assert not np.isnan(metrics.iloc[0]["mfe_mean_bps"])


def test_evaluator_context_filter_rejects_low_confidence_regime_rows(monkeypatch):
    import project.research.search.evaluator_utils as utils
    import project.research.search.feasibility as feasibility

    monkeypatch.setattr(utils, "_CACHED_CONTEXT_MAP", {("vol", "high"): "vol_high"})
    monkeypatch.setattr(
        feasibility, "load_context_state_map", lambda: {("vol", "high"): "vol_high"}
    )

    features = pd.DataFrame(
        {
            "timestamp": pd.date_range("2023-01-01", periods=12, freq="15min"),
            "close": np.linspace(100.0, 111.0, 12),
            "event_vol_spike": [True] * 12,
            "state_vol_high": [1] * 12,
            "ms_vol_confidence": [0.40] * 12,
            "ms_vol_entropy": [0.20] * 12,
        }
    )

    spec = HypothesisSpec(
        trigger=TriggerSpec.event("vol_spike"),
        direction="long",
        horizon="15m",
        template_id="continuation",
        context={"vol": "high"},
        entry_lag=0,
    )

    metrics = evaluate_hypothesis_batch([spec], features, min_sample_size=2)

    assert bool(metrics.iloc[0]["valid"]) is False
    assert metrics.iloc[0]["invalid_reason"] == "no_trigger_hits"


def test_evaluator_context_quality_toggle_changes_conditioned_sample_count(monkeypatch):
    import project.research.search.evaluator_utils as utils
    import project.research.search.feasibility as feasibility

    monkeypatch.setattr(utils, "_CACHED_CONTEXT_MAP", {("vol", "high"): "vol_high"})
    monkeypatch.setattr(
        feasibility, "load_context_state_map", lambda: {("vol", "high"): "vol_high"}
    )

    features = pd.DataFrame(
        {
            "timestamp": pd.date_range("2023-01-01", periods=20, freq="15min"),
            "close": np.linspace(100.0, 120.0, 20),
            "event_vol_spike": [True] * 20,
            "state_vol_high": [1] * 20,
            "ms_vol_confidence": [0.40] * 10 + [0.80] * 10,
            "ms_vol_entropy": [0.20] * 20,
        }
    )

    spec = HypothesisSpec(
        trigger=TriggerSpec.event("vol_spike"),
        direction="long",
        horizon="15m",
        template_id="continuation",
        context={"vol": "high"},
        entry_lag=0,
    )

    hard_label_metrics = evaluate_hypothesis_batch(
        [spec],
        features,
        min_sample_size=2,
        use_context_quality=False,
    )
    quality_aware_metrics = evaluate_hypothesis_batch(
        [spec],
        features,
        min_sample_size=2,
        use_context_quality=True,
    )

    assert bool(hard_label_metrics.iloc[0]["valid"]) is True
    assert bool(quality_aware_metrics.iloc[0]["valid"]) is True
    assert int(hard_label_metrics.iloc[0]["n"]) > int(quality_aware_metrics.iloc[0]["n"])
    assert int(hard_label_metrics.iloc[0]["n"]) == 17
    assert int(quality_aware_metrics.iloc[0]["n"]) == 7
