from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from project.scripts import run_researcher_verification as verification


def test_verify_experiment_artifacts_accepts_nested_search_engine_layout(tmp_path, monkeypatch):
    data_root = tmp_path / "data"
    run_id = "run_123"
    phase2_dir = data_root / "reports" / "phase2" / run_id / "search_engine"
    promotion_dir = data_root / "reports" / "promotions" / run_id
    run_dir = data_root / "runs" / run_id
    phase2_dir.mkdir(parents=True, exist_ok=True)
    promotion_dir.mkdir(parents=True, exist_ok=True)
    run_dir.mkdir(parents=True, exist_ok=True)

    (run_dir / "run_manifest.json").write_text(json.dumps({"run_id": run_id}), encoding="utf-8")
    (phase2_dir / "phase2_diagnostics.json").write_text(
        json.dumps({"schema_version": "phase2_diagnostics_v1"}), encoding="utf-8"
    )
    (phase2_dir / "phase2_candidates.parquet").write_text("", encoding="utf-8")

    seen_paths: list[Path] = []

    def fake_read_parquet(path):
        seen_paths.append(Path(path))
        return pd.DataFrame({"candidate_id": ["cand_1"]})

    monkeypatch.setattr(verification.pd, "read_parquet", fake_read_parquet)
    monkeypatch.setattr(verification, "validate_dataframe_for_schema", lambda df, schema: None)
    monkeypatch.setattr(verification, "validate_promotion_artifacts", lambda path: None)

    verification._verify_experiment_artifacts(
        repo_root=Path("."),
        data_root=data_root,
        run_id=run_id,
    )

    assert seen_paths == [phase2_dir / "phase2_candidates.parquet"]
