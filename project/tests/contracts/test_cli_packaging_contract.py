from __future__ import annotations

import tomllib
from pathlib import Path


CANONICAL_COMMANDS = [
    "backtest",
    "edge-backtest",
    "edge-live-engine",
    "edge-run-all",
    "edge-phase2-discovery",
    "edge-promote",
]
REMOVED_ALIASES = [
    "run-all",
    "promote-candidates",
    "phase2-discovery",
]


def test_canonical_commands_packaged_and_extended_detectors_removed():
    data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    scripts = data["project"]["scripts"]
    for cmd in CANONICAL_COMMANDS:
        assert cmd in scripts
    for cmd in REMOVED_ALIASES:
        assert cmd not in scripts
