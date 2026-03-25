from __future__ import annotations

from pathlib import Path

from project.artifacts.catalog import (
    blueprint_summary_path,
    checklist_path,
    kpi_scorecard_path,
    load_json_dict,
    phase2_candidates_path,
    promotion_summary_path,
    run_manifest_path,
)


def test_catalog_paths_and_json_loading(tmp_path: Path) -> None:
    root = tmp_path / "data"
    run_id = "r1"
    assert run_manifest_path(run_id, root) == root / "runs" / run_id / "run_manifest.json"
    assert (
        checklist_path(run_id, root)
        == root / "runs" / run_id / "research_checklist" / "checklist.json"
    )
    assert kpi_scorecard_path(run_id, root) == root / "runs" / run_id / "kpi_scorecard.json"
    assert (
        promotion_summary_path(run_id, root)
        == root / "reports" / "promotions" / run_id / "promotion_summary.json"
    )
    assert (
        blueprint_summary_path(run_id, root)
        == root / "reports" / "strategy_blueprints" / run_id / "blueprint_summary.json"
    )

    p = run_manifest_path(run_id, root)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text('{"status": "success"}', encoding="utf-8")
    assert load_json_dict(p)["status"] == "success"


def test_phase2_candidates_prefers_existing_parquet(tmp_path: Path) -> None:
    root = tmp_path / "data"
    base = root / "reports" / "phase2" / "r2" / "VOL"
    base.mkdir(parents=True, exist_ok=True)
    csv_path = base / "phase2_candidates.csv"
    csv_path.write_text("candidate_id\n1\n", encoding="utf-8")
    assert phase2_candidates_path("r2", "VOL", root) == csv_path
    pq_path = base / "phase2_candidates.parquet"
    pq_path.write_bytes(b"PAR1")
    assert phase2_candidates_path("r2", "VOL", root) == pq_path
