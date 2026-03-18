from __future__ import annotations

from project.research.search.feasibility import FeasibilityResult
from project.domain.hypotheses import HypothesisSpec, TriggerSpec
from project.research.search.stage_models import (
    CandidateHypothesis,
    EvaluatedHypothesis,
    FeasibilityCheckedHypothesis,
)


def _spec() -> HypothesisSpec:
    return HypothesisSpec(
        trigger=TriggerSpec.event("VOL_SPIKE"),
        direction="long",
        horizon="15m",
        template_id="continuation",
        entry_lag=1,
    )


def test_candidate_hypothesis_record_is_deterministic():
    spec = _spec()
    candidate = CandidateHypothesis(spec=spec, search_spec_name="phase1")

    row = candidate.to_record()

    assert row["hypothesis_id"] == spec.hypothesis_id()
    assert row["trigger_type"] == "event"
    assert row["search_spec_name"] == "phase1"
    assert row["status"] == "candidate"


def test_feasibility_checked_hypothesis_serializes_rejection():
    checked = FeasibilityCheckedHypothesis(
        candidate=CandidateHypothesis(spec=_spec(), search_spec_name="phase1"),
        feasibility=FeasibilityResult(
            valid=False,
            reasons=("missing_event_column", "missing_context_state_column"),
            details={"event_id": "VOL_SPIKE"},
        ),
    )

    row = checked.to_record()

    assert row["status"] == "rejected"
    assert row["rejection_reason"] == "missing_event_column"
    assert row["rejection_reasons"] == ["missing_event_column", "missing_context_state_column"]
    assert row["rejection_details"]["event_id"] == "VOL_SPIKE"


def test_evaluated_hypothesis_serializes_metrics():
    evaluated = EvaluatedHypothesis(
        checked=FeasibilityCheckedHypothesis(
            candidate=CandidateHypothesis(spec=_spec(), search_spec_name="phase1"),
            feasibility=FeasibilityResult(valid=True),
        ),
        valid=True,
        metrics={"n": 12, "t_stat": 2.5, "mean_return_bps": 14.2},
    )

    row = evaluated.to_record()

    assert row["status"] == "evaluated"
    assert row["valid"] is True
    assert row["n"] == 12
    assert row["t_stat"] == 2.5
    assert row["mean_return_bps"] == 14.2
