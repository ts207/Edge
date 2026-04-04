import json
from datetime import datetime
from pathlib import Path

import pytest

from project.research.validation.contracts import (
    ValidationBundle,
    ValidatedCandidateRecord,
    ValidationDecision,
    ValidationMetrics,
    ValidationReasonCodes,
)
from project.research.validation.result_writer import (
    write_validation_bundle,
    load_validation_bundle,
)


def test_validation_bundle_serialization(tmp_path):
    run_id = "test_run_123"
    created_at = datetime.now().isoformat()
    
    decision = ValidationDecision(
        status="validated",
        candidate_id="cand_1",
        run_id=run_id,
        reason_codes=[],
        summary="Looks good"
    )
    
    metrics = ValidationMetrics(
        sample_count=100,
        expectancy=0.05,
        p_value=0.01
    )
    
    candidate = ValidatedCandidateRecord(
        candidate_id="cand_1",
        decision=decision,
        metrics=metrics,
        anchor_summary="Summary",
        template_id="tpl_1",
        direction="long",
        horizon_bars=12
    )
    
    bundle = ValidationBundle(
        run_id=run_id,
        created_at=created_at,
        validated_candidates=[candidate],
        summary_stats={"total": 1}
    )
    
    # Write to tmp_path
    bundle_path = write_validation_bundle(bundle, base_dir=tmp_path)
    assert bundle_path.exists()
    
    # Load back
    loaded = load_validation_bundle(run_id, base_dir=tmp_path)
    assert loaded is not None
    assert loaded.run_id == run_id
    assert len(loaded.validated_candidates) == 1
    assert loaded.validated_candidates[0].candidate_id == "cand_1"
    assert loaded.validated_candidates[0].decision.status == "validated"
    assert loaded.validated_candidates[0].metrics.expectancy == 0.05


def test_validation_reason_codes():
    assert ValidationReasonCodes.FAILED_STABILITY == "failed_stability"
    
    decision = ValidationDecision(
        status="rejected",
        candidate_id="cand_2",
        run_id="run_2",
        reason_codes=[ValidationReasonCodes.FAILED_STABILITY]
    )
    
    assert ValidationReasonCodes.FAILED_STABILITY in decision.reason_codes


def test_invalid_status():
    with pytest.raises(ValueError):
        ValidationDecision(
            status="invalid_status",
            candidate_id="cand_3",
            run_id="run_3"
        )
