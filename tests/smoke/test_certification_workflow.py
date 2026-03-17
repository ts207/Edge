from __future__ import annotations

import json
from pathlib import Path

from project.scripts.run_certification_workflow import run_certification_workflow


def test_certification_workflow_runs_end_to_end(tmp_path: Path) -> None:
    payload = run_certification_workflow(
        root=tmp_path,
        config_path=Path("project/configs/golden_certification.yaml"),
    )
    certification_summary_path = (
        tmp_path / "reliability" / "golden_certification_summary.json"
    )
    certification_manifest_path = (
        tmp_path / "reliability" / "runtime_certification_manifest.json"
    )
    live_state_snapshot_path = tmp_path / "reliability" / "live_state.json"
    workflow_summary_path = tmp_path / "reliability" / "golden_workflow_summary.json"

    assert payload["workflow_id"] == "golden_certification_v1"
    assert certification_summary_path.exists()
    assert certification_manifest_path.exists()
    assert live_state_snapshot_path.exists()
    assert workflow_summary_path.exists()

    certification_summary = json.loads(
        certification_summary_path.read_text(encoding="utf-8")
    )
    certification_manifest = json.loads(
        certification_manifest_path.read_text(encoding="utf-8")
    )
    assert certification_summary["runtime_run_id"] == "smoke_run"
    assert certification_manifest["manifest_type"] == "runtime_certification_manifest"
    assert certification_manifest["status"] == "pass"
    assert certification_manifest["certification_checks"]["postflight_passed"]
    assert certification_manifest["certification_checks"]["feeds_healthy"]
    assert certification_manifest["certification_checks"]["live_state_snapshot_present"]
    assert certification_manifest["certification_checks"]["replay_digest_present"]
    assert certification_summary["live_state_snapshot_path"] == str(live_state_snapshot_path)
    assert certification_manifest["live_state"]["snapshot_path"] == str(live_state_snapshot_path)
