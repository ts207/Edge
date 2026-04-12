from __future__ import annotations

from pathlib import Path

from project.reliability.smoke_data import build_smoke_dataset, run_research_smoke


def test_research_smoke_produces_out_of_sample_evidence(tmp_path: Path):
    dataset = build_smoke_dataset(tmp_path, seed=20260101, storage_mode="auto")
    research_result = run_research_smoke(dataset)

    combined = research_result["combined_candidates"]
    assert len(combined) > 0, "Smoke research produced no candidates"

    oos_obs = combined[["validation_n_obs", "test_n_obs"]].fillna(0).sum(axis=1)
    assert (oos_obs > 0).any(), (
        "Smoke research produced no validation/test observations; "
        "the synthetic dataset no longer exercises out-of-sample scoring"
    )
