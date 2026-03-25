from __future__ import annotations

import importlib.util
import sys

import pytest

from project.tests.conftest import PROJECT_ROOT

CLI_PATH = PROJECT_ROOT / "cli.py"


def _load_cli_module():
    spec = importlib.util.spec_from_file_location("project_cli", CLI_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def test_cli_rejects_removed_strategy_subcommand(monkeypatch, capsys):
    cli = _load_cli_module()
    monkeypatch.setattr(sys, "argv", ["backtest", "strategy", "eval"])
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert int(exc.value.code) == 2
    err = capsys.readouterr().err.lower()
    assert "invalid choice: 'strategy'" in err


def test_cli_pipeline_run_all_delegates(monkeypatch):
    cli = _load_cli_module()
    captured = {"argv": None}

    def _fake_main():
        captured["argv"] = list(sys.argv)
        return 0

    monkeypatch.setattr(cli.run_all, "main", _fake_main)
    monkeypatch.setattr(sys, "argv", ["backtest", "pipeline", "run-all", "--run_id", "unit"])
    assert cli.main() == 0
    assert captured["argv"] == ["pipelines/run_all.py", "--run_id", "unit"]
