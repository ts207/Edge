from __future__ import annotations

from pathlib import Path


ALLOWED = {
    Path('project/io/utils.py'),
    Path('project/scripts/generate_synthetic_milestone_data.py'),
}


def test_project_code_uses_shared_storage_abstraction_for_artifact_writes() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    offenders: list[str] = []
    for path in (repo_root / 'project').rglob('*.py'):
        rel = path.relative_to(repo_root)
        if rel in ALLOWED:
            continue
        text = path.read_text(encoding='utf-8')
        if '.to_parquet(' in text:
            offenders.append(str(rel))
    assert offenders == [], f'direct to_parquet bypasses shared storage abstraction: {offenders}'
