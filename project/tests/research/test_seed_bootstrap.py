from __future__ import annotations

import csv
import json
from pathlib import Path

from project.research.seed_bootstrap import (
    build_promotion_seed_inventory,
    build_thesis_bootstrap_baseline,
    load_seed_promotion_policy,
    write_seed_promotion_policy_artifacts,
)


def test_build_thesis_bootstrap_baseline_handles_empty_store(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("BACKTEST_DATA_ROOT", str(tmp_path / "data"))
    docs = tmp_path / "docs"
    out = build_thesis_bootstrap_baseline(docs_dir=docs)

    payload = json.loads(Path(out["thesis_store_json_path"]).read_text(encoding="utf-8"))
    overlap = json.loads(Path(out["overlap_graph_json_path"]).read_text(encoding="utf-8"))
    md = Path(out["baseline_md_path"]).read_text(encoding="utf-8")

    assert payload["thesis_count"] == 0
    assert payload["status"] == "missing"
    assert payload["thesis_source_mode"] == "none"
    assert overlap["thesis_count"] == 0
    assert "No explicit canonical promoted thesis source was provided." in md


def test_build_thesis_bootstrap_baseline_uses_explicit_run_id(
    tmp_path: Path, monkeypatch
) -> None:
    class _DummyStore:
        def __init__(self) -> None:
            self.source_path = tmp_path / "data" / "live" / "theses" / "run_123" / "promoted_theses.json"

        def all(self):
            return [object(), object()]

        def active_theses(self):
            return [object()]

    monkeypatch.setattr(
        "project.research.seed_bootstrap.ThesisStore.from_run_id",
        lambda run_id, *, data_root=None: _DummyStore(),
    )

    out = build_thesis_bootstrap_baseline(
        docs_dir=tmp_path / "docs",
        data_root=tmp_path / "data",
        thesis_run_id="run_123",
    )

    payload = json.loads(Path(out["thesis_store_json_path"]).read_text(encoding="utf-8"))
    md = Path(out["baseline_md_path"]).read_text(encoding="utf-8")

    assert payload["thesis_source_mode"] == "run_id"
    assert payload["thesis_run_id"] == "run_123"
    assert payload["thesis_count"] == 2
    assert payload["active_thesis_count"] == 1
    assert payload["status"] == "available"
    assert "thesis_run_id: `run_123`" in md


def test_build_promotion_seed_inventory_contains_fallback_candidates(tmp_path: Path) -> None:
    out = build_promotion_seed_inventory(docs_dir=tmp_path)
    with Path(out["csv_path"]).open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    ids = {row["candidate_id"] for row in rows}
    statuses = {row["promotion_status"] for row in rows}
    assert "THESIS_VOL_SHOCK" in ids
    assert "THESIS_BASIS_FND_CONFIRM" in ids
    assert "THESIS_EP_LIQUIDITY_SHOCK" in ids
    status_by_id = {row['candidate_id']: row['promotion_status'] for row in rows}
    assert status_by_id['THESIS_VOL_SHOCK'] == 'test_now'
    assert status_by_id['THESIS_VOL_SHOCK_LIQUIDITY_CONFIRM'] == 'test_now'
    assert "needs_repair" in statuses
    assert "test_now" in statuses


def test_build_promotion_seed_inventory_honors_explicit_max_candidates(tmp_path: Path) -> None:
    out = build_promotion_seed_inventory(docs_dir=tmp_path, max_candidates=12)
    with Path(out["csv_path"]).open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) == 12


def test_seed_promotion_policy_artifacts_render(tmp_path: Path) -> None:
    payload = load_seed_promotion_policy()
    out = write_seed_promotion_policy_artifacts(docs_dir=tmp_path)
    text = Path(out["md_path"]).read_text(encoding="utf-8")

    assert payload["schema_version"] == "seed_promotion_policy_v1"
    assert "seed_promoted" in text
    assert "blocked_dispositions" in text
