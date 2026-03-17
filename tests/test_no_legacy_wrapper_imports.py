from __future__ import annotations

from pathlib import Path

LEGACY_PREFIXES = (
    "from engine",
    "import engine",
    "from events",
    "import events",
    "from pipelines",
    "import pipelines",
    "from strategies",
    "import strategies",
)


def test_repo_uses_project_namespace_imports():
    repo_root = Path(__file__).resolve().parents[1]
    offenders: list[str] = []
    for path in repo_root.rglob("*.py"):
        if ".venv" in path.parts:
            continue
        if path.parts[0] in {"engine", "events", "pipelines", "strategies"}:
            continue
        text = path.read_text(encoding="utf-8")
        for line_no, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith(LEGACY_PREFIXES):
                offenders.append(f"{path.relative_to(repo_root)}:{line_no}:{stripped}")
    assert not offenders, "Legacy top-level wrapper imports remain:\n" + "\n".join(offenders)
