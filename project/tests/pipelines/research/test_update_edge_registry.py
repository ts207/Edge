from __future__ import annotations

import json

from pathlib import Path

import pandas as pd

import project.pipelines.research.update_edge_registry as update_edge_registry

def _write_run_manifest(data_root: Path, run_id: str) -> None:
    run_dir = data_root / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    payload = {"run_id": run_id, "ontology_spec_hash": "sha256:test"}
    (run_dir / "run_manifest.json").write_text(json.dumps(payload), encoding="utf-8")

def _write_promotions(data_root: Path, run_id: str, effect: float) -> None:
    promo_dir = data_root / "reports" / "promotions" / run_id
    promo_dir.mkdir(parents=True, exist_ok=True)
    promoted = pd.DataFrame(
        [
            {
                "candidate_id": f"cand_{run_id}",
                "status": "PROMOTED",
                "event_type": "VOL_SHOCK",
                "template_id": "mean_reversion",
                "direction_rule": "contrarian",
                "signal_polarity_logic": "shock_up_short_shock_down_long",
                "promotion_score": 0.9,
                "promotion_decision": "promoted",
                "effect_shrunk_state": effect,
                "stability_score": 0.4,
            }
        ]
    )
    audit = pd.DataFrame(
        [
            {
                "candidate_id": f"cand_{run_id}",
                "event_type": "VOL_SHOCK",
                "template_id": "mean_reversion",
                "direction_rule": "contrarian",
                "signal_polarity_logic": "shock_up_short_shock_down_long",
                "promotion_score": 0.9,
                "promotion_decision": "promoted",
                "effect_shrunk_state": effect,
                "stability_score": 0.4,
            }
        ]
    )
    promoted.to_parquet(promo_dir / "promoted_candidates.parquet", index=False)
    audit.to_parquet(promo_dir / "promotion_audit.parquet", index=False)
    footprint = pd.DataFrame(
        [
            {
                "candidate_id": f"cand_{run_id}",
                "event_type": "VOL_SHOCK",
                "estimated_position_notional_usd": 2500.0,
                "slot_pressure_fraction": 1.2 if run_id == "r2" else 0.8,
                "leverage_usage_fraction": 0.25,
                "gate_capital_slot_within_limit": run_id != "r2",
                "gate_capital_leverage_within_budget": True,
            }
        ]
    )
    footprint.to_parquet(promo_dir / "promotion_capital_footprint.parquet", index=False)


def _write_promotions_statistical_audit_only(data_root: Path, run_id: str, effect: float) -> None:
    promo_dir = data_root / "reports" / "promotions" / run_id
    promo_dir.mkdir(parents=True, exist_ok=True)
    promoted = pd.DataFrame(
        [
            {
                "candidate_id": f"cand_{run_id}",
                "status": "PROMOTED",
                "event_type": "VOL_SHOCK",
                "template_id": "mean_reversion",
                "direction_rule": "contrarian",
                "signal_polarity_logic": "shock_up_short_shock_down_long",
                "promotion_score": 0.9,
                "promotion_decision": "promoted",
                "effect_shrunk_state": effect,
                "stability_score": 0.4,
            }
        ]
    )
    audit = pd.DataFrame(
        [
            {
                "candidate_id": f"cand_{run_id}",
                "event_type": "VOL_SHOCK",
                "template_id": "mean_reversion",
                "direction_rule": "contrarian",
                "signal_polarity_logic": "shock_up_short_shock_down_long",
                "promotion_score": 0.9,
                "promotion_decision": "promoted",
                "effect_shrunk_state": effect,
                "stability_score": 0.4,
            }
        ]
    )
    promoted.to_parquet(promo_dir / "promoted_candidates.parquet", index=False)
    audit.to_parquet(promo_dir / "promotion_statistical_audit.parquet", index=False)
    footprint = pd.DataFrame(
        [
            {
                "candidate_id": f"cand_{run_id}",
                "event_type": "VOL_SHOCK",
                "estimated_position_notional_usd": 2500.0,
                "slot_pressure_fraction": 0.8,
                "leverage_usage_fraction": 0.25,
                "gate_capital_slot_within_limit": True,
                "gate_capital_leverage_within_budget": True,
            }
        ]
    )
    footprint.to_parquet(promo_dir / "promotion_capital_footprint.parquet", index=False)

def test_update_edge_registry_appends_and_aggregates(monkeypatch, tmp_path):
    data_root = tmp_path / "data"
    monkeypatch.setattr(update_edge_registry, "get_data_root", lambda: data_root)

    _write_run_manifest(data_root, "r1")
    _write_promotions(data_root, "r1", 0.02)
    rc = update_edge_registry.main(
        [
            "--run_id",
            "r1",
            "--promote_baseline",
            "1",
            "--promote_baseline_id",
            "baseline_r1",
        ]
    )
    assert rc == 0

    _write_run_manifest(data_root, "r2")
    _write_promotions(data_root, "r2", 0.01)
    rc = update_edge_registry.main(
        [
            "--run_id",
            "r2",
            "--baseline_id",
            "baseline_r1",
        ]
    )
    assert rc == 0

    latest_snapshot = data_root / "runs" / "r2" / "research" / "edge_registry.parquet"
    assert latest_snapshot.exists()
    snapshot_df = pd.read_parquet(latest_snapshot)
    assert len(snapshot_df) == 1
    row = snapshot_df.iloc[0]
    assert int(row["times_tested"]) == 2
    assert int(row["times_promoted"]) == 2
    assert row["first_seen_run"] == "r1"
    assert row["last_seen_run"] == "r2"
    assert abs(float(row["median_effect"]) - 0.015) < 1e-9
    assert abs(float(row["capital_slot_pressure_median"]) - 1.0) < 1e-9
    assert int(row["capital_slot_limit_breaches"]) == 1

def test_update_edge_registry_replay_with_same_baseline_is_isolated(monkeypatch, tmp_path):
    data_root = tmp_path / "data"
    monkeypatch.setattr(update_edge_registry, "get_data_root", lambda: data_root)

    _write_run_manifest(data_root, "r1")
    _write_promotions(data_root, "r1", 0.02)
    rc = update_edge_registry.main(
        [
            "--run_id",
            "r1",
            "--promote_baseline",
            "1",
            "--promote_baseline_id",
            "baseline_r1",
        ]
    )
    assert rc == 0

    _write_run_manifest(data_root, "r2")
    _write_promotions(data_root, "r2", 0.01)
    rc = update_edge_registry.main(
        [
            "--run_id",
            "r2",
            "--baseline_id",
            "baseline_r1",
        ]
    )
    assert rc == 0

    _write_run_manifest(data_root, "r3")
    _write_promotions(data_root, "r3", 0.03)
    rc = update_edge_registry.main(
        [
            "--run_id",
            "r3",
            "--baseline_id",
            "baseline_r1",
        ]
    )
    assert rc == 0

    snapshot_r3 = data_root / "runs" / "r3" / "research" / "edge_registry.parquet"
    df_r3 = pd.read_parquet(snapshot_r3)
    row = df_r3.iloc[0]
    # baseline_r1 + r3 only; r2 must not leak into this replay.
    assert int(row["times_tested"]) == 2
    assert row["first_seen_run"] == "r1"
    assert row["last_seen_run"] == "r3"


def test_update_edge_registry_falls_back_to_promotion_statistical_audit(monkeypatch, tmp_path):
    data_root = tmp_path / "data"
    monkeypatch.setattr(update_edge_registry, "get_data_root", lambda: data_root)

    _write_run_manifest(data_root, "r_stat")
    _write_promotions_statistical_audit_only(data_root, "r_stat", 0.02)

    rc = update_edge_registry.main(["--run_id", "r_stat"])

    assert rc == 0
    latest_snapshot = data_root / "runs" / "r_stat" / "research" / "edge_registry.parquet"
    assert latest_snapshot.exists()
