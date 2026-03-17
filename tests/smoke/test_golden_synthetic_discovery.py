from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from project.io.utils import ensure_dir, write_parquet
from project.scripts.run_golden_synthetic_discovery import run_golden_synthetic_discovery


class _Completed:
    def __init__(self, returncode: int = 0):
        self.returncode = returncode
        self.stdout = ""
        self.stderr = ""


def test_golden_synthetic_discovery_workflow_writes_summary(tmp_path: Path, monkeypatch) -> None:
    def _fake_runner(*, data_root: Path, argv: list[str]):
        run_id = argv[argv.index("--run_id") + 1]
        out_dir = data_root / "reports" / "phase2" / run_id / "search_engine"
        ensure_dir(out_dir)
        write_parquet(
            pd.DataFrame([{"event_type": "CROSS_VENUE_DESYNC", "candidate_id": "cand-1"}]),
            out_dir / "phase2_candidates.parquet",
        )
        (out_dir / "phase2_diagnostics.json").write_text(
            json.dumps({"discovery_profile": "synthetic", "hypotheses_generated": 12, "bridge_candidates_rows": 1}, indent=2),
            encoding="utf-8",
        )
        return _Completed(0)

    monkeypatch.setattr(
        "project.scripts.run_golden_synthetic_discovery.validate_detector_truth",
        lambda **kwargs: {"passed": True, "event_reports": [{"event_type": "CROSS_VENUE_DESYNC"}]},
    )

    payload = run_golden_synthetic_discovery(
        root=tmp_path,
        config_path=Path("project/configs/golden_synthetic_discovery.yaml"),
        pipeline_runner=_fake_runner,
    )
    summary_path = tmp_path / "reliability" / "golden_synthetic_discovery_summary.json"

    assert payload["workflow_id"] == "golden_synthetic_discovery_v1"
    assert summary_path.exists()

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["truth_validation"]["passed"] is True
    assert summary["candidate_summary"]["candidate_rows"] == 1
    assert summary["search_engine_diagnostics"]["discovery_profile"] == "synthetic"

