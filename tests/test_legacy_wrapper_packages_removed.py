from __future__ import annotations

from pathlib import Path


def test_legacy_wrapper_packages_removed():
    repo_root = Path(__file__).resolve().parents[1]
    for name in ["engine", "events", "pipelines", "strategies"]:
        assert not (repo_root / name).exists(), f"legacy wrapper package still exists: {name}"
