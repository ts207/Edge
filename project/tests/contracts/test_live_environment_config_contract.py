from __future__ import annotations

from pathlib import Path

from project.scripts.run_live_engine import load_live_engine_config


def test_live_environment_configs_use_distinct_order_sources_and_snapshot_paths() -> None:
    paper = load_live_engine_config(Path("project/configs/live_paper.yaml"))
    production = load_live_engine_config(Path("project/configs/live_production.yaml"))

    assert paper["oms_lineage"]["order_source"] == "paper_oms"
    assert production["oms_lineage"]["order_source"] == "production_oms"
    assert paper["live_state_snapshot_path"] == "artifacts/live_state_paper.json"
    assert production["live_state_snapshot_path"] == "artifacts/live_state_production.json"
    assert paper["live_state_snapshot_path"] != production["live_state_snapshot_path"]
    assert int(paper["microstructure_recovery_streak"]) >= 1
    assert int(production["microstructure_recovery_streak"]) >= 1
    assert float(paper["account_sync_interval_seconds"]) > float(
        production["account_sync_interval_seconds"]
    )
    assert int(paper["account_sync_failure_threshold"]) > int(
        production["account_sync_failure_threshold"]
    )
    assert int(paper["execution_degradation_min_samples"]) > int(
        production["execution_degradation_min_samples"]
    )
    assert float(paper["execution_degradation_block_edge_bps"]) < float(
        production["execution_degradation_block_edge_bps"]
    )
    assert float(paper["execution_degradation_throttle_scale"]) > float(
        production["execution_degradation_throttle_scale"]
    )
