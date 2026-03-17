from __future__ import annotations

import importlib
import json
from pathlib import Path
from types import SimpleNamespace

import yaml

from project.research.agent_io.execute_proposal import build_run_all_command, execute_proposal

execute_proposal_module = importlib.import_module("project.research.agent_io.execute_proposal")


def _write_registry(reg_dir: Path) -> None:
    reg_dir.mkdir(parents=True, exist_ok=True)
    (reg_dir / "events.yaml").write_text(
        yaml.dump(
            {
                "events": {
                    "BASIS_DISLOC": {
                        "enabled": True,
                        "instrument_classes": ["crypto"],
                        "sequence_eligible": True,
                        "requires_features": [],
                    }
                }
            }
        )
    )
    (reg_dir / "states.yaml").write_text(yaml.dump({"states": {}}))
    (reg_dir / "features.yaml").write_text(yaml.dump({"features": {}}))
    (reg_dir / "templates.yaml").write_text(
        yaml.dump({"templates": {"continuation": {"enabled": True, "supports_trigger_types": ["EVENT"]}}})
    )
    (reg_dir / "contexts.yaml").write_text(
        yaml.dump({"context_dimensions": {"session": {"allowed_values": ["open", "close"]}}})
    )
    (reg_dir / "search_limits.yaml").write_text(
        yaml.dump(
            {
                "limits": {
                    "max_events_per_run": 10,
                    "max_templates_per_run": 10,
                    "max_horizons_per_run": 10,
                    "max_directions_per_run": 10,
                    "max_entry_lags_per_run": 4,
                    "max_hypotheses_total": 1000,
                    "max_hypotheses_per_template": 250,
                    "max_hypotheses_per_event_family": 300,
                },
                "defaults": {
                    "horizons_bars": [12, 24],
                    "directions": ["long", "short"],
                    "entry_lags": [0, 1],
                },
            }
        )
    )
    (reg_dir / "detectors.yaml").write_text(
        yaml.dump({"detector_ownership": {"BASIS_DISLOC": "BasisDislocDetector"}})
    )


def _write_proposal(path: Path) -> None:
    path.write_text(
        yaml.dump(
            {
                "program_id": "btc_campaign",
                "description": "basis continuation slice",
                "run_mode": "research",
                "objective": "retail_profitability",
                "promotion_mode": "research",
                "symbols": ["BTCUSDT"],
                "timeframe": "5m",
                "start": "2026-01-01",
                "end": "2026-01-31",
                "instrument_classes": ["crypto"],
                "trigger_space": {
                    "allowed_trigger_types": ["EVENT"],
                    "events": {"include": ["BASIS_DISLOC"]},
                },
                "templates": ["continuation"],
                "contexts": {"session": ["open"]},
                "horizons_bars": [12],
                "directions": ["long", "short"],
                "entry_lags": [0],
                "knobs": {"candidate_promotion_min_events": 60},
            }
        ),
        encoding="utf-8",
    )


def test_build_run_all_command_includes_outer_window_and_experiment_config(tmp_path):
    cmd = build_run_all_command(
        run_id="unit_run",
        registry_root=tmp_path / "registries",
        experiment_config_path=tmp_path / "experiment.yaml",
        run_all_overrides={
            "mode": "research",
            "program_id": "btc_campaign",
            "candidate_promotion_profile": "research",
            "candidate_promotion_min_events": 60,
        },
        symbols=["BTCUSDT"],
        start="2026-01-01",
        end="2026-01-31",
        plan_only=True,
        dry_run=False,
    )

    assert "--experiment_config" in cmd
    assert "--symbols" in cmd
    assert "--start" in cmd
    assert "--end" in cmd
    assert "--plan_only" in cmd
    assert "--candidate_promotion_min_events" in cmd


def test_execute_proposal_translates_and_invokes_run_all(monkeypatch, tmp_path):
    proposal_path = tmp_path / "proposal.yaml"
    registry_root = tmp_path / "registries"
    out_dir = tmp_path / "out"
    data_root = tmp_path / "data"
    _write_registry(registry_root)
    _write_proposal(proposal_path)

    captured = {}

    def _fake_run(cmd, **kwargs):
        captured["cmd"] = list(cmd)
        captured["kwargs"] = kwargs
        return SimpleNamespace(returncode=0, stdout="Plan for run unit_run:\n", stderr="")

    monkeypatch.setattr(execute_proposal_module.subprocess, "run", _fake_run)

    result = execute_proposal(
        proposal_path,
        run_id="unit_run",
        registry_root=registry_root,
        out_dir=out_dir,
        data_root=data_root,
        plan_only=True,
    )

    overrides = json.loads((out_dir / "run_all_overrides.json").read_text(encoding="utf-8"))
    assert result["returncode"] == 0
    assert Path(result["experiment_config_path"]).exists()
    assert overrides["candidate_promotion_min_events"] == 60
    assert "--experiment_config" in captured["cmd"]
    assert "--registry_root" in captured["cmd"]
    assert "--plan_only" in captured["cmd"]
    assert captured["kwargs"]["env"]["BACKTEST_DATA_ROOT"] == str(data_root)
