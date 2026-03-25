from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

from project import PROJECT_ROOT

import project.pipelines.run_all as run_all
import project.pipelines.pipeline_planning as pipeline_planning
from project.pipelines.stages.evaluation import build_evaluation_stages


def _load_manifest(tmp_path, run_id: str) -> dict:
    import json
    path = tmp_path / "data" / "runs" / run_id / "run_manifest.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_run_all_runtime_postflight_enforce_blocks_on_violations(monkeypatch, tmp_path):
    executed: list[str] = []

    def fake_run_stage(stage, script, base_args, run_id, **kwargs) -> bool:
        executed.append(stage)
        return True

    monkeypatch.setattr(run_all, "DATA_ROOT", tmp_path / "data")
    monkeypatch.setattr(run_all, "_git_commit", lambda _project_root: "test-sha")
    monkeypatch.setattr(run_all, "_run_stage", fake_run_stage)
    monkeypatch.setattr(
        run_all,
        "_run_runtime_postflight_audit",
        lambda _run_id, determinism_replay_checks: {
            "status": "failed",
            "event_source_path": "data/events/runtime_postflight_block/events.parquet",
            "event_count": 12,
            "normalized_event_count": 12,
            "normalization_issue_count": 0,
            "normalization_issue_examples": [],
            "watermark_status": "failed",
            "watermark_violation_count": 2,
            "watermark_violations_by_type": {
                "future_event_time": 1,
                "decision_before_watermark": 1,
            },
            "watermark_violation_examples": ["event_id=e1 event_time_us=10 > recv_time_us=1"],
            "max_observed_lag_us": 2_000_000,
            "determinism_replay_checks_status": (
                "pending_runtime_integration" if determinism_replay_checks else "disabled"
            ),
        },
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_all.py",
            "--run_id",
            "runtime_postflight_block",
            "--symbols",
            "BTCUSDT",
            "--start",
            "2024-01-01",
            "--end",
            "2024-01-02",
            "--runtime_invariants_mode",
            "enforce",
            "--skip_ingest_ohlcv",
            "1",
            "--skip_ingest_funding",
            "1",
            "--skip_ingest_spot_ohlcv",
            "1",
            "--run_phase2_conditional",
            "0",
            "--run_strategy_blueprint_compiler",
            "0",
            "--run_strategy_builder",
            "0",
            "--run_candidate_promotion",
            "0",
            "--run_edge_registry_update",
            "0",
            "--run_edge_candidate_universe",
            "0",
            "--run_naive_entry_eval",
            "0",
            "--run_expectancy_analysis",
            "0",
            "--run_expectancy_robustness",
            "0",
            "--run_recommendations_checklist",
            "0",
            "--run_interaction_lift",
            "0",
        ],
    )

    rc = run_all.main()
    assert rc == 1
    assert executed
    manifest = _load_manifest(tmp_path, "runtime_postflight_block")
    assert manifest["status"] == "failed"
    assert manifest["failed_stage"] == "runtime_invariants_postflight"
    assert manifest["runtime_postflight_status"] == "failed"
    assert int(manifest["runtime_watermark_violation_count"]) == 2
    assert manifest["runtime_invariants_status"] == "violations"


def test_run_all_runtime_postflight_audit_mode_records_violations_and_succeeds(
    monkeypatch, tmp_path
):
    def fake_run_stage(stage, script, base_args, run_id, **kwargs) -> bool:
        return True

    monkeypatch.setattr(run_all, "DATA_ROOT", tmp_path / "data")
    monkeypatch.setattr(run_all, "_git_commit", lambda _project_root: "test-sha")
    monkeypatch.setattr(run_all, "_run_stage", fake_run_stage)
    monkeypatch.setattr(
        run_all,
        "_run_runtime_postflight_audit",
        lambda _run_id, determinism_replay_checks: {
            "status": "failed",
            "event_source_path": "data/events/runtime_postflight_audit/events.parquet",
            "event_count": 9,
            "normalized_event_count": 9,
            "normalization_issue_count": 0,
            "normalization_issue_examples": [],
            "watermark_status": "failed",
            "watermark_violation_count": 1,
            "watermark_violations_by_type": {"future_event_time": 1},
            "watermark_violation_examples": ["event_id=e9 event_time_us=20 > recv_time_us=1"],
            "max_observed_lag_us": 1_000_000,
            "determinism_replay_checks_status": (
                "pending_runtime_integration" if determinism_replay_checks else "disabled"
            ),
        },
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_all.py",
            "--run_id",
            "runtime_postflight_audit",
            "--symbols",
            "BTCUSDT",
            "--start",
            "2024-01-01",
            "--end",
            "2024-01-02",
            "--runtime_invariants_mode",
            "audit",
            "--skip_ingest_ohlcv",
            "1",
            "--skip_ingest_funding",
            "1",
            "--skip_ingest_spot_ohlcv",
            "1",
            "--run_phase2_conditional",
            "0",
            "--run_strategy_blueprint_compiler",
            "0",
            "--run_strategy_builder",
            "0",
            "--run_candidate_promotion",
            "0",
            "--run_edge_registry_update",
            "0",
            "--run_edge_candidate_universe",
            "0",
            "--run_naive_entry_eval",
            "0",
            "--run_expectancy_analysis",
            "0",
            "--run_expectancy_robustness",
            "0",
            "--run_recommendations_checklist",
            "0",
            "--run_interaction_lift",
            "0",
        ],
    )

    rc = run_all.main()
    assert rc == 0
    manifest = _load_manifest(tmp_path, "runtime_postflight_audit")
    assert manifest["status"] == "success"
    assert manifest["runtime_postflight_status"] == "failed"
    assert manifest["runtime_invariants_status"] == "violations"
    assert int(manifest["runtime_watermark_violation_count"]) == 1


def test_run_all_runtime_mode_plans_runtime_stages(monkeypatch, tmp_path):
    executed: list[str] = []

    def fake_run_stage(stage, script, base_args, run_id, **kwargs) -> bool:
        executed.append(stage)
        return False

    monkeypatch.setattr(run_all, "DATA_ROOT", tmp_path / "data")
    monkeypatch.setattr(run_all, "_git_commit", lambda _project_root: "test-sha")
    monkeypatch.setattr(run_all, "_run_stage", fake_run_stage)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_all.py",
            "--run_id",
            "runtime_stage_plan",
            "--symbols",
            "BTCUSDT",
            "--start",
            "2024-01-01",
            "--end",
            "2024-01-02",
            "--runtime_invariants_mode",
            "audit",
            "--determinism_replay_checks",
            "1",
            "--oms_replay_checks",
            "1",
            "--skip_ingest_ohlcv",
            "1",
            "--skip_ingest_funding",
            "1",
            "--skip_ingest_spot_ohlcv",
            "1",
            "--run_phase2_conditional",
            "0",
            "--run_strategy_blueprint_compiler",
            "0",
            "--run_strategy_builder",
            "0",
            "--run_profitable_selector",
            "0",
            "--run_recommendations_checklist",
            "0",
            "--run_interaction_lift",
            "0",
        ],
    )

    rc = run_all.main()
    assert rc == 1
    assert executed
    manifest = _load_manifest(tmp_path, "runtime_stage_plan")
    planned = list(manifest.get("planned_stages", []))
    assert "build_normalized_replay_stream" in planned
    assert "run_causal_lane_ticks" in planned
    assert "run_determinism_replay_checks" in planned
    assert "run_oms_replay_validation" in planned


def test_run_all_emit_run_hash_computed_when_requested(monkeypatch, tmp_path):
    def fake_run_stage(stage, script, base_args, run_id, **kwargs) -> bool:
        return True

    monkeypatch.setattr(run_all, "DATA_ROOT", tmp_path / "data")
    monkeypatch.setattr(run_all, "_git_commit", lambda _project_root: "test-sha")
    monkeypatch.setattr(run_all, "_run_stage", fake_run_stage)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_all.py",
            "--run_id",
            "runtime_hash_emit",
            "--symbols",
            "BTCUSDT",
            "--start",
            "2024-01-01",
            "--end",
            "2024-01-02",
            "--runtime_invariants_mode",
            "audit",
            "--emit_run_hash",
            "1",
            "--skip_ingest_ohlcv",
            "1",
            "--skip_ingest_funding",
            "1",
            "--skip_ingest_spot_ohlcv",
            "1",
            "--run_phase2_conditional",
            "0",
            "--run_strategy_blueprint_compiler",
            "0",
            "--run_strategy_builder",
            "0",
            "--run_profitable_selector",
            "0",
            "--run_recommendations_checklist",
            "0",
            "--run_interaction_lift",
            "0",
        ],
    )

    rc = run_all.main()
    assert rc == 0
    manifest = _load_manifest(tmp_path, "runtime_hash_emit")
    assert manifest["emit_run_hash"] is True
    assert manifest["run_hash_status"] == "computed"
    assert str(manifest["run_hash"]).startswith("blake2b_256:")
    assert manifest["hash_schema_version"] == "runtime_hash_v1"


def test_run_all_enforce_fails_on_firewall_or_determinism_or_oms_violations(monkeypatch, tmp_path):
    def fake_run_stage(stage, script, base_args, run_id, **kwargs) -> bool:
        return True

    monkeypatch.setattr(run_all, "DATA_ROOT", tmp_path / "data")
    monkeypatch.setattr(run_all, "_git_commit", lambda _project_root: "test-sha")
    monkeypatch.setattr(run_all, "_run_stage", fake_run_stage)
    monkeypatch.setattr(
        run_all,
        "_refresh_runtime_lineage_fields",
        lambda manifest, run_id, determinism_replay_checks_requested, oms_replay_checks_requested: (
            manifest.update(
                {
                    "runtime_firewall_violation_count": 1,
                    "runtime_firewall_violation_examples": [
                        "role=alpha provenance=execution forbidden"
                    ],
                    "determinism_status": "failed",
                    "determinism_replay_checks_status": "failed",
                    "oms_replay_status": "failed",
                    "oms_replay_violation_count": 1,
                    "oms_replay_violation_examples": [
                        "order_id=o1 fill without submit event_id=e2"
                    ],
                }
            )
        ),
    )
    monkeypatch.setattr(
        run_all,
        "_run_runtime_postflight_audit",
        lambda _run_id, determinism_replay_checks: {
            "status": "pass",
            "event_source_path": "data/events/runtime_postflight_pass/events.parquet",
            "event_count": 5,
            "normalized_event_count": 5,
            "normalization_issue_count": 0,
            "normalization_issue_examples": [],
            "watermark_status": "pass",
            "watermark_violation_count": 0,
            "watermark_violations_by_type": {},
            "watermark_violation_examples": [],
            "max_observed_lag_us": 0,
            "determinism_replay_checks_status": (
                "not_run" if determinism_replay_checks else "disabled"
            ),
        },
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_all.py",
            "--run_id",
            "runtime_enforce_firewall_determinism",
            "--symbols",
            "BTCUSDT",
            "--start",
            "2024-01-01",
            "--end",
            "2024-01-02",
            "--runtime_invariants_mode",
            "enforce",
            "--determinism_replay_checks",
            "1",
            "--oms_replay_checks",
            "1",
            "--skip_ingest_ohlcv",
            "1",
            "--skip_ingest_funding",
            "1",
            "--skip_ingest_spot_ohlcv",
            "1",
            "--run_phase2_conditional",
            "0",
            "--run_strategy_blueprint_compiler",
            "0",
            "--run_strategy_builder",
            "0",
            "--run_profitable_selector",
            "0",
            "--run_recommendations_checklist",
            "0",
            "--run_interaction_lift",
            "0",
        ],
    )

    rc = run_all.main()
    assert rc == 1
    manifest = _load_manifest(tmp_path, "runtime_enforce_firewall_determinism")
    assert manifest["status"] == "failed"
    assert manifest["failed_stage"] == "runtime_invariants_postflight"
    assert int(manifest["runtime_firewall_violation_count"]) == 1
    assert manifest["determinism_status"] == "failed"
    assert manifest["oms_replay_status"] == "failed"


def test_run_all_resume_from_failed_stage_instance(monkeypatch, tmp_path):
    executed: list[str] = []

    def fake_run_stage(stage, script, base_args, run_id, **kwargs) -> bool:
        executed.append(stage)
        return False

    data_root = tmp_path / "data"
    run_dir = data_root / "runs" / "resume_run"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "run_manifest.json").write_text(
        json.dumps(
            {
                "status": "failed",
                "failed_stage_instance": "build_features_5m",
                "ontology_spec_hash": run_all.ontology_spec_hash(run_all.PROJECT_ROOT.parent),
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(run_all, "DATA_ROOT", data_root)
    monkeypatch.setattr(run_all, "_git_commit", lambda _project_root: "test-sha")
    monkeypatch.setattr(run_all, "_run_stage", fake_run_stage)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_all.py",
            "--run_id",
            "resume_run",
            "--symbols",
            "BTCUSDT",
            "--start",
            "2024-01-01",
            "--end",
            "2024-01-02",
            "--skip_ingest_ohlcv",
            "1",
            "--skip_ingest_funding",
            "1",
            "--skip_ingest_spot_ohlcv",
            "1",
            "--run_phase2_conditional",
            "0",
            "--run_strategy_blueprint_compiler",
            "0",
            "--run_strategy_builder",
            "0",
            "--run_recommendations_checklist",
            "0",
            "--resume_from_failed_stage",
            "1",
        ],
    )
    rc = run_all.main()
    assert rc == 1
    assert executed
    assert executed[0] == "build_cleaned_5m"


def test_run_all_success_clears_failed_stage_instance(monkeypatch, tmp_path):
    def fake_run_stage(stage, script, base_args, run_id, **kwargs) -> bool:
        return True

    data_root = tmp_path / "data"
    run_dir = data_root / "runs" / "resume_ok"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "run_manifest.json").write_text(
        json.dumps(
            {
                "status": "failed",
                "failed_stage": "build_features",
                "failed_stage_instance": "build_features",
                "ontology_spec_hash": run_all.ontology_spec_hash(run_all.PROJECT_ROOT.parent),
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(run_all, "DATA_ROOT", data_root)
    monkeypatch.setattr(run_all, "_git_commit", lambda _project_root: "test-sha")
    monkeypatch.setattr(run_all, "_run_stage", fake_run_stage)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_all.py",
            "--run_id",
            "resume_ok",
            "--symbols",
            "BTCUSDT",
            "--start",
            "2024-01-01",
            "--end",
            "2024-01-02",
            "--skip_ingest_ohlcv",
            "1",
            "--skip_ingest_funding",
            "1",
            "--skip_ingest_spot_ohlcv",
            "1",
            "--run_phase2_conditional",
            "0",
            "--run_strategy_blueprint_compiler",
            "0",
            "--run_strategy_builder",
            "0",
            "--run_recommendations_checklist",
            "0",
            "--run_candidate_promotion",
            "0",
            "--run_edge_registry_update",
            "0",
            "--run_edge_candidate_universe",
            "0",
            "--run_naive_entry_eval",
            "0",
            "--run_expectancy_analysis",
            "0",
            "--run_expectancy_robustness",
            "0",
            "--run_interaction_lift",
            "0",
        ],
    )
    rc = run_all.main()
    assert rc == 0
    manifest = _load_manifest(tmp_path, "resume_ok")
    assert manifest["status"] == "success"
    assert manifest["failed_stage"] is None
    assert manifest["failed_stage_instance"] is None


def test_benchmark_pipeline_script_writes_outputs(tmp_path, monkeypatch):
    data_root = tmp_path / "data"
    run_dir = data_root / "runs" / "bench_run"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "run_manifest.json").write_text(
        json.dumps(
            {
                "run_id": "bench_run",
                "status": "success",
                "failed_stage": None,
                "symbols": ["BTCUSDT"],
                "start": "2024-01-01",
                "end": "2024-01-02",
                "stage_timings_sec": {"build_market_context": 12.3, "build_features": 4.2},
            }
        ),
        encoding="utf-8",
    )

    script_path = PROJECT_ROOT / "scripts" / "benchmark_pipeline.py"
    spec = importlib.util.spec_from_file_location("benchmark_pipeline", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)

    monkeypatch.setattr(module, "DATA_ROOT", data_root)
    monkeypatch.setenv("BACKTEST_DATA_ROOT", str(data_root))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "benchmark_pipeline.py",
            "--run_id",
            "bench_run",
            "--out_dir",
            str(data_root / "reports" / "perf"),
        ],
    )
    rc = module.main()
    assert rc == 0
    assert (data_root / "reports" / "perf" / "summary.json").exists()
    assert (data_root / "reports" / "perf" / "stages.csv").exists()


def test_run_all_writes_kpi_scorecard_from_promotion_audit(monkeypatch, tmp_path):
    def fake_run_stage(stage, script, base_args, run_id, **kwargs) -> bool:
        return True

    data_root = tmp_path / "data"
    run_id = "kpi_scorecard_run"
    promo_dir = data_root / "reports" / "promotions" / run_id
    promo_dir.mkdir(parents=True, exist_ok=True)
    (promo_dir / "promotion_audit.csv").write_text(
        "\n".join(
            [
                "candidate_id,n_events,bridge_validation_stressed_after_cost_bps,sign_consistency,turnover_proxy_mean,naive_max_drawdown",
                "c1,100,10.0,0.50,0.80,-0.10",
                "c2,50,20.0,1.00,1.20,-0.20",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(run_all, "DATA_ROOT", data_root)
    monkeypatch.setattr(run_all, "_git_commit", lambda _project_root: "test-sha")
    monkeypatch.setattr(run_all, "_run_stage", fake_run_stage)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_all.py",
            "--run_id",
            run_id,
            "--symbols",
            "BTCUSDT",
            "--start",
            "2024-01-01",
            "--end",
            "2024-01-02",
            "--run_phase2_conditional",
            "0",
            "--run_strategy_blueprint_compiler",
            "0",
            "--run_strategy_builder",
            "0",
            "--run_candidate_promotion",
            "0",
            "--run_edge_registry_update",
            "0",
            "--run_edge_candidate_universe",
            "0",
            "--run_naive_entry_eval",
            "0",
            "--run_expectancy_analysis",
            "0",
            "--run_expectancy_robustness",
            "0",
            "--run_recommendations_checklist",
            "0",
            "--run_interaction_lift",
            "0",
            "--skip_ingest_ohlcv",
            "1",
            "--skip_ingest_funding",
            "1",
            "--skip_ingest_spot_ohlcv",
            "1",
        ],
    )
    rc = run_all.main()
    assert rc == 0

    scorecard_path = data_root / "runs" / run_id / "kpi_scorecard.json"
    assert scorecard_path.exists()
    payload = json.loads(scorecard_path.read_text(encoding="utf-8"))
    assert payload["completeness"] == "complete"
    assert payload["source"]["name"] == "promotion_audit"
    assert abs(float(payload["metrics"]["net_expectancy_bps"]["value"]) - 15.0) < 1e-9
    assert abs(float(payload["metrics"]["oos_sign_consistency"]["value"]) - 0.75) < 1e-9
    assert abs(float(payload["metrics"]["turnover_proxy_mean"]["value"]) - 1.0) < 1e-9
    assert abs(float(payload["metrics"]["trade_count"]["value"]) - 150.0) < 1e-9
    assert abs(float(payload["metrics"]["max_drawdown_pct"]["value"]) - (-0.2)) < 1e-9


def test_run_all_certification_auto_enables_strict_modes(monkeypatch, tmp_path):
    data_root = tmp_path / "data"

    def fake_run_stage(stage, script, base_args, run_id, **kwargs) -> bool:
        return False

    monkeypatch.setattr(run_all, "DATA_ROOT", data_root)
    monkeypatch.setattr(run_all, "_git_commit", lambda _project_root: "test-sha")
    monkeypatch.setattr(run_all, "_run_stage", fake_run_stage)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_all.py",
            "--run_id",
            "cert_auto_strict",
            "--symbols",
            "BTCUSDT",
            "--start",
            "2024-01-01",
            "--end",
            "2024-01-02",
            "--mode",
            "certification",
        ],
    )
    rc = run_all.main()
    assert rc == 1
    manifest = _load_manifest(tmp_path, "cert_auto_strict")
    assert manifest["strict_run_scoped_reads"] is True
    assert manifest["require_stage_manifests"] is True


def test_run_all_research_defaults_disable_strict_modes(monkeypatch, tmp_path):
    data_root = tmp_path / "data"

    def fake_run_stage(stage, script, base_args, run_id, **kwargs) -> bool:
        return False

    monkeypatch.setattr(run_all, "DATA_ROOT", data_root)
    monkeypatch.setattr(run_all, "_git_commit", lambda _project_root: "test-sha")
    monkeypatch.setattr(run_all, "_run_stage", fake_run_stage)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_all.py",
            "--run_id",
            "research_default_modes",
            "--symbols",
            "BTCUSDT",
            "--start",
            "2024-01-01",
            "--end",
            "2024-01-02",
            "--mode",
            "research",
        ],
    )
    rc = run_all.main()
    assert rc == 1
    manifest = _load_manifest(tmp_path, "research_default_modes")
    assert manifest["strict_run_scoped_reads"] is False
    assert manifest["require_stage_manifests"] is False


def test_data_fingerprint_ignores_timestamp_and_path_relocation(monkeypatch, tmp_path):
    data_root = tmp_path / "data"
    monkeypatch.setattr(run_all, "DATA_ROOT", data_root)
    src_dir = data_root / "lake" / "raw" / "binance" / "perp" / "BTCUSDT" / "part_a"
    src_dir.mkdir(parents=True, exist_ok=True)
    file_a = src_dir / "slice.csv"
    file_a.write_text("a,b\n1,2\n", encoding="utf-8")

    hash_1, lineage_1 = run_all._data_fingerprint(["BTCUSDT"], "fp_run_1")
    assert lineage_1["file_count"] == 1

    os.utime(file_a, None)
    hash_2, lineage_2 = run_all._data_fingerprint(["BTCUSDT"], "fp_run_2")
    assert lineage_2["file_count"] == 1
    assert hash_2 == hash_1

    relocated_dir = data_root / "lake" / "raw" / "binance" / "perp" / "BTCUSDT" / "part_b"
    relocated_dir.mkdir(parents=True, exist_ok=True)
    file_b = relocated_dir / "slice.csv"
    file_b.write_text(file_a.read_text(encoding="utf-8"), encoding="utf-8")
    file_a.unlink()

    hash_3, lineage_3 = run_all._data_fingerprint(["BTCUSDT"], "fp_run_3")
    assert lineage_3["file_count"] == 1
    assert hash_3 == hash_1
