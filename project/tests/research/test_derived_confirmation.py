from __future__ import annotations

import json
from pathlib import Path

from project.research.derived_confirmation import synthesize_confirmation_bundle


def _write_bundle(path: Path, *, candidate_id: str, symbol: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "candidate_id": candidate_id,
        "sample_definition": {
            "n_events": 80,
            "validation_samples": 40,
            "test_samples": 40,
            "symbol": symbol,
            "horizon_bars": 24,
            "start": "2021-01-01T00:00:00Z",
            "end": "2022-01-01T00:00:00Z",
        },
        "effect_estimates": {"estimate_bps": 50.0, "validation_mean_bps": 40.0, "test_mean_bps": 35.0},
        "cost_robustness": {"fees_bps": 5.0, "net_expectancy_bps": 30.0},
        "uncertainty_estimates": {"q_value": 0.05},
        "stability_tests": {
            "stability_score": 0.7,
            "validation_mean_bps": 40.0,
            "test_mean_bps": 35.0,
            "validation_test_gap_bps": 5.0,
        },
        "falsification_results": {
            "negative_control_pass_rate": 0.1,
            "session_transition": {"available": True, "passed": True},
        },
        "metadata": {
            "has_realized_oos_path": True,
            "input_symbols": [symbol],
        },
    }
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def test_structural_confirmation_summary_uses_workspace_relative_artifact_refs(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    docs_dir = tmp_path / "docs"
    _write_bundle(
        data_root / "reports" / "promotions" / "THESIS_VOL_SHOCK" / "evidence_bundles.jsonl",
        candidate_id="THESIS_VOL_SHOCK",
        symbol="BTCUSDT",
    )
    _write_bundle(
        data_root / "reports" / "promotions" / "THESIS_LIQUIDITY_VACUUM" / "evidence_bundles.jsonl",
        candidate_id="THESIS_LIQUIDITY_VACUUM",
        symbol="BTCUSDT",
    )

    out = synthesize_confirmation_bundle(data_root=data_root, docs_dir=docs_dir)

    payload = json.loads(out["summary_json"].read_text(encoding="utf-8"))
    assert payload["invalid_artifact_refs"] == []
    assert payload["artifact_refs"]["bundle_path"]["path"].startswith("data/")
    assert "/home/irene/" not in out["summary_md"].read_text(encoding="utf-8")
