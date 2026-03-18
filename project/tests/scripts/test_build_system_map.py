from __future__ import annotations

from pathlib import Path

from project.scripts import build_system_map


def test_build_system_map_writes_and_checks(monkeypatch, tmp_path: Path) -> None:
    markdown_path = tmp_path / "docs" / "generated" / "system_map.md"
    json_path = tmp_path / "docs" / "generated" / "system_map.json"
    monkeypatch.setattr(build_system_map, "_target_paths", lambda: (markdown_path, json_path))

    assert build_system_map.main(["--format", "both"]) == 0
    assert markdown_path.exists()
    assert json_path.exists()
    assert build_system_map.main(["--format", "both", "--check"]) == 0

    markdown_path.write_text("drift\n", encoding="utf-8")
    assert build_system_map.main(["--format", "both", "--check"]) == 1
