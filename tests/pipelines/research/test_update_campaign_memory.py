from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

import project.pipelines.research.update_campaign_memory as update_campaign_memory


def _write_run_manifest(data_root: Path, run_id: str, *, program_id: str) -> None:
    run_dir = data_root / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "run_manifest.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "program_id": program_id,
                "objective_name": "retail_profitability",
                "symbols": "BTCUSDT",
                "start": "2026-01-01",
                "end": "2026-01-31",
                "run_mode": "research",
                "status": "success",
            }
        ),
        encoding="utf-8",
    )
    (run_dir / "validate_feature_integrity_5m.json").write_text(
        json.dumps({"status": "warning", "symbols_with_issues": 1}),
        encoding="utf-8",
    )


def test_update_campaign_memory_materializes_memory_and_compat_outputs(monkeypatch, tmp_path):
    data_root = tmp_path / "data"
    monkeypatch.setattr(update_campaign_memory, "get_data_root", lambda: data_root)

    run_id = "r1"
    program_id = "btc_campaign"
    _write_run_manifest(data_root, run_id, program_id=program_id)

    edge_dir = data_root / "reports" / "edge_candidates" / run_id
    edge_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {
                "candidate_id": "c1",
                "hypothesis_id": "h1",
                "event_type": "BASIS_DISLOC",
                "trigger_type": "EVENT",
                "template_id": "continuation",
                "direction": "long",
                "horizon": "15m",
                "entry_lag": 0,
                "symbol": "BTCUSDT",
                "q_value": 0.04,
                "validation_samples": 7,
                "test_samples": 5,
                "train_n_obs": 12,
                "net_expectancy_bps": 2.5,
                "bridge_validation_stressed_after_cost_bps": 1.0,
                "stability_score": 0.7,
                "gate_bridge_tradable": True,
                "gate_promo_statistical": True,
                "gate_promo_retail_net_expectancy": False,
                "promotion_decision": "rejected",
                "promotion_fail_gate_primary": "gate_promo_retail_net_expectancy",
            }
        ]
    ).to_parquet(edge_dir / "edge_candidates_normalized.parquet", index=False)

    promo_dir = data_root / "reports" / "promotions" / run_id
    promo_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {
                "candidate_id": "c1",
                "event_type": "BASIS_DISLOC",
                "template_id": "continuation",
                "direction": "long",
                "horizon": "15m",
                "promotion_decision": "rejected",
                "promotion_fail_gate_primary": "gate_promo_retail_net_expectancy",
                "q_value": 0.04,
                "gate_promo_statistical": True,
                "net_expectancy_bps": 2.5,
                "stability_score": 0.7,
            }
        ]
    ).to_parquet(promo_dir / "promotion_statistical_audit.parquet", index=False)

    phase2_dir = data_root / "reports" / "phase2" / run_id
    phase2_dir.mkdir(parents=True, exist_ok=True)
    (phase2_dir / "discovery_quality_summary.json").write_text(
        json.dumps({"total_candidates": 1}),
        encoding="utf-8",
    )

    rc = update_campaign_memory.main(
        [
            "--run_id", run_id,
            "--program_id", program_id,
            "--data_root", str(data_root),
            "--promising_top_k", "1",
            "--avoid_top_k", "1",
            "--repair_top_k", "1",
            "--exploit_top_k", "1",
            "--frontier_untested_top_k", "1",
            "--frontier_repair_top_k", "1",
            "--exhausted_failure_threshold", "1",
        ]
    )
    assert rc == 0

    memory_root = data_root / "artifacts" / "experiments" / program_id / "memory"
    assert (memory_root / "tested_regions.parquet").exists()
    assert (memory_root / "reflections.parquet").exists()
    assert (memory_root / "belief_state.json").exists()
    assert (memory_root / "next_actions.json").exists()

    tested_regions = pd.read_parquet(memory_root / "tested_regions.parquet")
    reflections = pd.read_parquet(memory_root / "reflections.parquet")
    assert len(tested_regions) == 1
    assert tested_regions.iloc[0]["event_type"] == "BASIS_DISLOC"
    assert reflections.iloc[0]["program_id"] == program_id

    campaign_dir = data_root / "artifacts" / "experiments" / program_id
    summary = json.loads((campaign_dir / "campaign_summary.json").read_text(encoding="utf-8"))
    frontier = json.loads((campaign_dir / "search_frontier.json").read_text(encoding="utf-8"))
    assert summary["program_id"] == program_id
    assert "candidate_next_moves" in frontier
    assert len(summary["top_performing_regions"]) == 1
    assert len(frontier["untested_registry_events"]) == 1

    belief_state = json.loads((memory_root / "belief_state.json").read_text(encoding="utf-8"))
    next_actions = json.loads((memory_root / "next_actions.json").read_text(encoding="utf-8"))
    assert len(belief_state["promising_regions"]) == 1
    assert len(belief_state["avoid_regions"]) == 1
    assert len(next_actions["exploit"]) == 1


def test_update_campaign_memory_uses_explicit_data_root_for_manifest(monkeypatch, tmp_path):
    data_root = tmp_path / "data"
    monkeypatch.setattr(update_campaign_memory, "get_data_root", lambda: tmp_path / "wrong_data")

    run_id = "r_explicit_root"
    program_id = "btc_campaign"
    _write_run_manifest(data_root, run_id, program_id=program_id)

    edge_dir = data_root / "reports" / "edge_candidates" / run_id
    edge_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([]).to_parquet(edge_dir / "edge_candidates_normalized.parquet", index=False)

    promo_dir = data_root / "reports" / "promotions" / run_id
    promo_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([]).to_parquet(promo_dir / "promotion_statistical_audit.parquet", index=False)

    phase2_dir = data_root / "reports" / "phase2" / run_id
    phase2_dir.mkdir(parents=True, exist_ok=True)
    (phase2_dir / "discovery_quality_summary.json").write_text(json.dumps({}), encoding="utf-8")

    rc = update_campaign_memory.main(
        [
            "--run_id", run_id,
            "--data_root", str(data_root),
        ]
    )

    assert rc == 0
