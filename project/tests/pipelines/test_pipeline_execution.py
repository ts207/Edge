from __future__ import annotations

import os
from pathlib import Path

from project.pipelines import pipeline_execution


def test_run_stage_does_not_mutate_parent_stage_env(monkeypatch):
    captured: dict[str, object] = {}

    def _fake_engine_run_stage(**kwargs):
        captured.update(kwargs)
        return True

    monkeypatch.setattr(pipeline_execution, "_engine_run_stage", _fake_engine_run_stage)
    monkeypatch.delenv("BACKTEST_RUN_ID", raising=False)
    monkeypatch.delenv("BACKTEST_STAGE_INSTANCE_ID", raising=False)

    ok = pipeline_execution.run_stage(
        "build_features",
        Path("fake_stage.py"),
        ["--symbols", "BTCUSDT"],
        "run_env_isolation",
        stage_instance_id="build_features__worker_a",
    )

    assert ok is True
    assert "BACKTEST_RUN_ID" not in os.environ
    assert "BACKTEST_STAGE_INSTANCE_ID" not in os.environ
    assert captured["current_stage_instance_id"] == "build_features__worker_a"
