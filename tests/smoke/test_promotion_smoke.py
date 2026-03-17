from __future__ import annotations

from pathlib import Path

from project.reliability.cli_smoke import run_smoke_cli


def test_promotion_smoke(tmp_path: Path):
    summary = run_smoke_cli('promotion', root=tmp_path, storage_mode='auto')
    assert summary['promotion']['bundle_rows'] >= 1
