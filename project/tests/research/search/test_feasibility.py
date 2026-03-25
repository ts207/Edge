from __future__ import annotations

import pandas as pd

from project.research.search.evaluator import evaluate_hypothesis_batch
from project.research.search.feasibility import check_hypothesis_feasibility
from project.domain.hypotheses import HypothesisSpec, TriggerSpec


def test_event_hypothesis_is_feasible_without_runtime_features():
    spec = HypothesisSpec(
        trigger=TriggerSpec.event("VOL_SPIKE"),
        direction="long",
        horizon="15m",
        template_id="continuation",
        entry_lag=1,
    )

    result = check_hypothesis_feasibility(spec)

    assert result.valid
    assert result.reasons == ()


def test_incompatible_template_family_is_rejected():
    spec = HypothesisSpec(
        trigger=TriggerSpec.event("VOL_SPIKE"),
        direction="long",
        horizon="15m",
        template_id="false_breakout_reversal",
        entry_lag=1,
    )

    result = check_hypothesis_feasibility(spec)

    assert not result.valid
    assert "incompatible_template_family" in result.reasons


def test_evaluator_marks_missing_event_column_with_explicit_reason():
    spec = HypothesisSpec(
        trigger=TriggerSpec.event("VOL_SPIKE"),
        direction="long",
        horizon="15m",
        template_id="continuation",
        entry_lag=1,
    )
    features = pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-01", periods=4, freq="15min"),
            "close": [100.0, 101.0, 102.0, 103.0],
            "volume": [1000.0, 1000.0, 1000.0, 1000.0],
        }
    )

    result = evaluate_hypothesis_batch([spec], features, min_sample_size=1)

    assert bool(result.iloc[0]["valid"]) is False
    assert result.iloc[0]["invalid_reason"] == "missing_event_column"
