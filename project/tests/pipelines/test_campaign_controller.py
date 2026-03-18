import pytest
import pandas as pd
import json
import sys
import yaml
from pathlib import Path
from project.pipelines.research.campaign_controller import CampaignController, CampaignConfig, CampaignSummary

@pytest.fixture
def test_env(tmp_path):
    reg_dir = tmp_path / "registries"
    reg_dir.mkdir()
    
    (reg_dir / "events.yaml").write_text(yaml.dump({
        "events": {
            "E1": {"enabled": True, "family": "F1", "instrument_classes": ["crypto"]},
            "E2": {"enabled": True, "family": "F1", "instrument_classes": ["crypto"]},
            "E3": {"enabled": True, "family": "F2", "instrument_classes": ["crypto"]},
            "E4": {"enabled": True, "family": "F2", "instrument_classes": ["crypto"]}
        }
    }))
    (reg_dir / "templates.yaml").write_text(yaml.dump({"templates": {"continuation": {"enabled": True, "supports_trigger_types": ["EVENT"]}}}))
    (reg_dir / "contexts.yaml").write_text(yaml.dump({"context_dimensions": {}}))
    (reg_dir / "search_limits.yaml").write_text(yaml.dump({"limits": {"max_events_per_run": 10, "max_templates_per_run": 10}}))
    (reg_dir / "states.yaml").write_text(yaml.dump({"states": {}}))
    (reg_dir / "features.yaml").write_text(yaml.dump({"features": {}}))
    (reg_dir / "detectors.yaml").write_text(yaml.dump({"detector_ownership": {}}))
    
    data_root = tmp_path / "data"
    data_root.mkdir()
    
    config = CampaignConfig(program_id="test_campaign", max_runs=2)
    return CampaignController(config, data_root, reg_dir)

def test_campaign_request_generation(test_env):
    controller = test_env
    req = controller._propose_next_request()
    assert req is not None
    assert req["program_id"] == "test_campaign"
    assert len(req["trigger_space"]["events"]["include"]) > 0

def test_frontier_tracking(test_env, tmp_path):
    controller = test_env
    # Mock a ledger where E1 is tested but E2 is not (F1 is partial)
    # E3 and E4 are untested (F2 is not yet started)
    ledger_data = [
        {
            "hypothesis_id": "h1",
            "trigger_payload": json.dumps({"event_id": "E1"}),
            "eval_status": "evaluated",
            "expectancy": 0.1,
            "run_id": "run1"
        }
    ]
    pd.DataFrame(ledger_data).to_parquet(controller.ledger_path)
    
    summary = controller._update_campaign_stats()
    assert summary.total_runs == 1
    
    frontier = json.loads(controller.frontier_path.read_text())
    assert "E1" not in frontier["untested_events"]
    assert "E2" in frontier["untested_events"]
    assert "E3" in frontier["untested_events"]
    
    # F1 is partially explored (E1 tested, E2 not)
    assert "F1" in frontier["partially_explored_families"]
    # F2 is NOT partially explored because tested count is 0
    assert "F2" not in frontier["partially_explored_families"]


def test_campaign_request_skips_events_seen_in_json_trigger_payload(test_env):
    controller = test_env
    pd.DataFrame(
        [
            {
                "hypothesis_id": "h1",
                "trigger_payload": json.dumps({"event_id": "E1"}),
                "eval_status": "evaluated",
                "expectancy": 0.1,
                "run_id": "run1",
            }
        ]
    ).to_parquet(controller.ledger_path)

    req = controller._propose_next_request()

    assert req is not None
    assert "E1" not in req["trigger_space"]["events"]["include"]


def test_execute_pipeline_invokes_run_all(monkeypatch, test_env, tmp_path):
    controller = test_env
    captured = {}

    def _fake_run(cmd, check, cwd):
        captured["cmd"] = list(cmd)
        captured["check"] = check
        captured["cwd"] = cwd

    monkeypatch.setattr("project.pipelines.research.campaign_controller.subprocess.run", _fake_run)

    config_path = tmp_path / "experiment.yaml"
    config_path.write_text("program_id: test_campaign\n", encoding="utf-8")
    controller._execute_pipeline(config_path, "campaign_run_1")

    assert captured["cmd"][:3] == [sys.executable, "-m", "project.pipelines.run_all"]
    assert captured["check"] is True
