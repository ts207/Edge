from __future__ import annotations

from pathlib import Path

from project.reliability.cli_smoke import run_smoke_cli


def test_research_smoke(tmp_path: Path):
    summary = run_smoke_cli('research', root=tmp_path, storage_mode='auto')
    assert summary['research']['candidate_rows'] >= 2
