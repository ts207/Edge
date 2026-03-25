from __future__ import annotations

import os
import subprocess
import sys
import json
import uuid
from pathlib import Path

from project.tests.conftest import REPO_ROOT

_REPO_ROOT = str(REPO_ROOT)


def _env_with_pythonpath() -> dict:
    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{_REPO_ROOT}:{existing}" if existing else _REPO_ROOT
    env["BACKTEST_DATA_ROOT"] = str(Path(_REPO_ROOT) / "data")
    return env


def test_run_all_plan_only():
    """Verify that run_all.py --plan_only 1 works without execution."""
    cmd = [
        sys.executable,
        "-m",
        "project.pipelines.run_all",
        "--run_id",
        "smoke_test_plan",
        "--symbols",
        "BTCUSDT",
        "--start",
        "2024-01-01",
        "--end",
        "2024-01-02",
        "--plan_only",
        "1",
    ]
    result = subprocess.run(
        cmd, capture_output=True, text=True, cwd=_REPO_ROOT, env=_env_with_pythonpath()
    )
    assert result.returncode == 0, result.stderr
    assert "Plan for run smoke_test_plan" in result.stdout


def test_run_all_dry_run():
    """Verify that run_all.py --dry_run 1 initializes manifest but does not execute."""
    run_id = f"smoke_test_dry_{uuid.uuid4().hex[:8]}"
    cmd = [
        sys.executable,
        "-m",
        "project.pipelines.run_all",
        "--run_id",
        run_id,
        "--symbols",
        "BTCUSDT",
        "--start",
        "2024-01-01",
        "--end",
        "2024-01-02",
        "--dry_run",
        "1",
    ]
    result = subprocess.run(
        cmd, capture_output=True, text=True, cwd=_REPO_ROOT, env=_env_with_pythonpath()
    )
    assert result.returncode == 0, result.stderr
    assert f"Dry run for {run_id} completed" in result.stdout
    manifest_path = Path(_REPO_ROOT) / "data" / "runs" / run_id / "run_manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert payload["status"] == "success"
    assert payload["dry_run"] is True
    assert payload["normalized_symbols"] == ["BTCUSDT"]
    assert payload["normalized_timeframes"] == ["5m"]
