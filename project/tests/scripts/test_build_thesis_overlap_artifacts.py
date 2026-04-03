from __future__ import annotations

from pathlib import Path

import pytest

from project.scripts import build_thesis_overlap_artifacts as script


class _DummyStore:
    def __init__(self, *, run_id: str, theses: list[object]) -> None:
        self.run_id = run_id
        self._theses = list(theses)

    def all(self) -> list[object]:
        return list(self._theses)


def test_main_loads_overlap_input_from_explicit_run_id(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def _from_run_id(run_id: str, *, data_root: Path | None = None):
        captured["run_id"] = run_id
        captured["data_root"] = data_root
        return _DummyStore(run_id=run_id, theses=[{"thesis_id": "t1"}])

    def _write(theses, docs_dir: Path, *, source_run_id: str) -> None:
        captured["theses"] = list(theses)
        captured["docs_dir"] = docs_dir
        captured["source_run_id"] = source_run_id

    monkeypatch.setattr(script.ThesisStore, "from_run_id", _from_run_id)
    monkeypatch.setattr(script, "write_thesis_overlap_artifacts", _write)

    exit_code = script.main(
        [
            "--run_id",
            "run_123",
            "--data_root",
            str(tmp_path / "data"),
            "--docs_dir",
            str(tmp_path / "docs"),
        ]
    )

    assert exit_code == 0
    assert captured["run_id"] == "run_123"
    assert captured["data_root"] == tmp_path / "data"
    assert captured["theses"] == [{"thesis_id": "t1"}]
    assert captured["docs_dir"] == tmp_path / "docs"
    assert captured["source_run_id"] == "run_123"


def test_main_loads_overlap_input_from_explicit_thesis_path(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}
    thesis_path = tmp_path / "live" / "theses" / "run_456" / "promoted_theses.json"

    def _from_path(path: str):
        captured["thesis_path"] = path
        return _DummyStore(run_id="run_456", theses=[{"thesis_id": "t2"}])

    def _write(theses, docs_dir: Path, *, source_run_id: str) -> None:
        captured["theses"] = list(theses)
        captured["docs_dir"] = docs_dir
        captured["source_run_id"] = source_run_id

    monkeypatch.setattr(script.ThesisStore, "from_path", _from_path)
    monkeypatch.setattr(script, "write_thesis_overlap_artifacts", _write)

    exit_code = script.main(
        [
            "--thesis_path",
            str(thesis_path),
            "--docs_dir",
            str(tmp_path / "docs"),
        ]
    )

    assert exit_code == 0
    assert captured["thesis_path"] == str(thesis_path)
    assert captured["theses"] == [{"thesis_id": "t2"}]
    assert captured["docs_dir"] == tmp_path / "docs"
    assert captured["source_run_id"] == "run_456"


def test_parser_requires_explicit_source() -> None:
    with pytest.raises(SystemExit):
        script.main([])
