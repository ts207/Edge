from __future__ import annotations

import csv
import json
from pathlib import Path

from project.live.thesis_store import ThesisStore
from project.research.seed_package import package_seed_promoted_theses


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_package_seed_promoted_theses_creates_store_cards_and_overlap(tmp_path: Path) -> None:
    docs_dir = tmp_path / "docs" / "generated"
    data_root = tmp_path / "data"

    _write_csv(
        docs_dir / "promotion_seed_inventory.csv",
        [
            "candidate_id",
            "source_type",
            "event_contract_ids",
            "episode_contract_ids",
            "source_campaign_id",
            "hypothesis_statement",
            "expected_direction_or_path",
            "horizon_guess",
            "invalidation_rule",
            "regime_assumptions",
        ],
        [
            {
                "candidate_id": "THESIS_VOL_SHOCK",
                "source_type": "event",
                "event_contract_ids": "VOL_SHOCK",
                "episode_contract_ids": "",
                "source_campaign_id": "",
                "hypothesis_statement": "VOL_SHOCK should expand realized movement.",
                "expected_direction_or_path": "Expect elevated absolute move after the shock.",
                "horizon_guess": "8-24 bars",
                "invalidation_rule": "follow-through fails within 24 bars",
                "regime_assumptions": "Primary trigger in volatility transition regimes.",
            },
            {
                "candidate_id": "THESIS_LIQUIDITY_VACUUM",
                "source_type": "event",
                "event_contract_ids": "LIQUIDITY_VACUUM",
                "episode_contract_ids": "",
                "source_campaign_id": "",
                "hypothesis_statement": "LIQUIDITY_VACUUM should create unstable continuation or repair.",
                "expected_direction_or_path": "Expect amplified move or repair response.",
                "horizon_guess": "8-24 bars",
                "invalidation_rule": "depth normalizes immediately",
                "regime_assumptions": "Primary trigger in liquidity stress regimes.",
            },
            {
                "candidate_id": "THESIS_VOL_SHOCK_LIQUIDITY_CONFIRM",
                "source_type": "event_plus_confirm",
                "event_contract_ids": "VOL_SHOCK|LIQUIDITY_VACUUM",
                "episode_contract_ids": "",
                "source_campaign_id": "",
                "hypothesis_statement": "VOL_SHOCK plus LIQUIDITY_VACUUM should strengthen the move.",
                "expected_direction_or_path": "Expect a stronger post-shock absolute move than standalone shock.",
                "horizon_guess": "8-24 bars",
                "invalidation_rule": "confirmation fails to arrive near the shock",
                "regime_assumptions": "Requires both shock and liquidity stress.",
            },
        ],
    )

    _write_csv(
        docs_dir / "thesis_empirical_scorecards.csv",
        [
            "candidate_id",
            "empirical_decision",
            "governance_tier",
            "operational_role",
            "deployment_disposition",
            "sample_size_total",
            "validation_samples_total",
            "test_samples_total",
            "median_estimate_bps",
            "median_net_expectancy_bps",
            "best_q_value",
            "best_stability_score",
            "total_score",
            "realized_oos_supported",
            "evidence_gap_summary",
        ],
        [
            {
                "candidate_id": "THESIS_VOL_SHOCK",
                "empirical_decision": "paper_candidate",
                "governance_tier": "A",
                "operational_role": "trigger",
                "deployment_disposition": "primary_trigger_candidate",
                "sample_size_total": "100",
                "validation_samples_total": "60",
                "test_samples_total": "40",
                "median_estimate_bps": "100.5",
                "median_net_expectancy_bps": "94.5",
                "best_q_value": "0.001",
                "best_stability_score": "0.92",
                "total_score": "37",
                "realized_oos_supported": "1",
                "evidence_gap_summary": "",
            },
            {
                "candidate_id": "THESIS_LIQUIDITY_VACUUM",
                "empirical_decision": "needs_more_evidence",
                "governance_tier": "A",
                "operational_role": "trigger",
                "deployment_disposition": "primary_trigger_candidate",
                "sample_size_total": "0",
                "validation_samples_total": "0",
                "test_samples_total": "0",
                "median_estimate_bps": "",
                "median_net_expectancy_bps": "",
                "best_q_value": "",
                "best_stability_score": "",
                "total_score": "20",
                "realized_oos_supported": "0",
                "evidence_gap_summary": "empirical_evidence_bundle_missing",
            },
            {
                "candidate_id": "THESIS_VOL_SHOCK_LIQUIDITY_CONFIRM",
                "empirical_decision": "seed_promote",
                "governance_tier": "A",
                "operational_role": "confirm",
                "deployment_disposition": "seed_review_required",
                "sample_size_total": "80",
                "validation_samples_total": "40",
                "test_samples_total": "40",
                "median_estimate_bps": "90.0",
                "median_net_expectancy_bps": "84.0",
                "best_q_value": "0.010",
                "best_stability_score": "0.80",
                "total_score": "32",
                "realized_oos_supported": "1",
                "evidence_gap_summary": "direct_pair_event_study_missing",
            },
        ],
    )

    vol_promotion_dir = data_root / "reports" / "promotions" / "THESIS_VOL_SHOCK"
    vol_promotion_dir.mkdir(parents=True, exist_ok=True)
    bundle = {
        "candidate_id": "THESIS_VOL_SHOCK",
        "event_type": "VOL_SHOCK",
        "event_family": "VOL_SHOCK",
        "sample_definition": {"n_events": 100, "validation_samples": 60, "test_samples": 40, "symbol": "BTCUSDT"},
        "effect_estimates": {"estimate_bps": 100.5},
        "cost_robustness": {"net_expectancy_bps": 94.5},
        "uncertainty_estimates": {"q_value": 0.001},
        "stability_tests": {"stability_score": 0.92},
        "falsification_results": {
            "negative_control_pass_rate": 0.0,
            "session_transition": {"passed": True},
            "realized_vol_regime": {"passed": True},
        },
        "metadata": {"has_realized_oos_path": True, "input_symbols": ["BTCUSDT", "ETHUSDT"], "notes": "Absolute move thesis."},
    }
    (vol_promotion_dir / "evidence_bundles.jsonl").write_text(json.dumps(bundle) + "\n", encoding="utf-8")

    confirm_promotion_dir = data_root / "reports" / "promotions" / "THESIS_VOL_SHOCK_LIQUIDITY_CONFIRM"
    confirm_promotion_dir.mkdir(parents=True, exist_ok=True)
    confirm_bundle = {
        "candidate_id": "THESIS_VOL_SHOCK_LIQUIDITY_CONFIRM",
        "event_type": "VOL_SHOCK_LIQUIDITY_CONFIRM",
        "event_family": "VOL_SHOCK",
        "sample_definition": {"n_events": 80, "validation_samples": 40, "test_samples": 40, "symbol": "BTCUSDT"},
        "effect_estimates": {"estimate_bps": 90.0},
        "cost_robustness": {"net_expectancy_bps": 84.0},
        "uncertainty_estimates": {"q_value": 0.010},
        "stability_tests": {"stability_score": 0.80},
        "falsification_results": {
            "negative_control_pass_rate": 0.0,
            "session_transition": {"passed": True},
            "realized_vol_regime": {"passed": True},
        },
        "metadata": {"has_realized_oos_path": True, "input_symbols": ["BTCUSDT", "ETHUSDT"], "notes": "Direct paired confirmation thesis."},
    }
    (confirm_promotion_dir / "evidence_bundles.jsonl").write_text(json.dumps(confirm_bundle) + "\n", encoding="utf-8")

    outputs = package_seed_promoted_theses(docs_dir=docs_dir, data_root=data_root, package_run_id="seed_pack_test")

    assert outputs["thesis_store"].exists()
    assert outputs["thesis_index"].exists()
    assert outputs["catalog_md"].exists()
    assert outputs["card_dir"].joinpath("THESIS_VOL_SHOCK.md").exists()
    assert outputs["overlap_json"].exists()

    store = ThesisStore.from_path(outputs["thesis_store"])
    theses = store.all()
    assert len(theses) == 2
    thesis_by_id = {thesis.thesis_id: thesis for thesis in theses}
    thesis = thesis_by_id["THESIS_VOL_SHOCK"]
    assert thesis.primary_event_id == "VOL_SHOCK"
    assert thesis.promotion_class == "paper_promoted"
    assert thesis.deployment_state == "paper_only"
    assert thesis.governance.overlap_group_id
    assert thesis.symbol_scope["symbols"] == ["BTCUSDT", "ETHUSDT"]
    assert thesis.evidence_freshness_date
    assert thesis.review_due_date
    assert thesis.staleness_class == "fresh"

    confirm = thesis_by_id["THESIS_VOL_SHOCK_LIQUIDITY_CONFIRM"]
    assert confirm.requirements.trigger_events == ["VOL_SHOCK"]
    assert confirm.requirements.confirmation_events == ["LIQUIDITY_VACUUM"]
    assert confirm.governance.overlap_group_id

    index = json.loads(outputs["thesis_index"].read_text(encoding="utf-8"))
    assert index["latest_run_id"] == "seed_pack_test"

    summary = json.loads(outputs["summary_json"].read_text(encoding="utf-8"))
    assert summary["invalid_artifact_refs"] == []
    assert summary["artifact_refs"]["thesis_store"]["path"].startswith("data/")
    assert "/home/irene/" not in outputs["summary_md"].read_text(encoding="utf-8")

    overlap_payload = json.loads(outputs["overlap_json"].read_text(encoding="utf-8"))
    assert overlap_payload["thesis_count"] == 2
    catalog_text = outputs["catalog_md"].read_text(encoding="utf-8")
    assert "Primary event id" in catalog_text
    assert "Compat event family" in catalog_text
    card_text = outputs["card_dir"].joinpath("THESIS_VOL_SHOCK.md").read_text(encoding="utf-8")
    assert "Primary event id" in card_text
