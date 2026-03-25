from __future__ import annotations
import json
import sys
from pathlib import Path

import pytest

import project.pipelines.run_all as run_all


def _arg_value(args: list[str], flag: str) -> str:
    idx = args.index(flag)
    return str(args[idx + 1])


def test_run_all_ohlcv_ingest_respects_force_flag(monkeypatch, tmp_path):
    captured: list[tuple[str, list[str]]] = []

    def fake_run_stage(stage, script, base_args, run_id, **kwargs) -> bool:
        captured.append((stage, list(base_args)))
        return False

    monkeypatch.setattr(run_all, "DATA_ROOT", tmp_path / "data")
    monkeypatch.setattr(run_all, "_git_commit", lambda _project_root: "test-sha")
    monkeypatch.setattr(run_all, "_run_stage", fake_run_stage)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_all.py",
            "--symbols",
            "BTCUSDT",
            "--start",
            "2024-01-01",
            "--end",
            "2024-01-02",
            "--force",
            "0",
        ],
    )

    rc = run_all.main()
    assert rc == 1
    assert captured
    stage, args = captured[0]
    assert stage == "ingest_binance_um_ohlcv_5m"
    assert _arg_value(args, "--force") == "0"


def test_run_all_bridge_stage_default_embargo_is_nonzero(monkeypatch, tmp_path):
    captured: list[tuple[str, list[str]]] = []

    def fake_run_stage(stage, script, base_args, run_id, **kwargs) -> bool:
        captured.append((stage, list(base_args)))
        return True

    monkeypatch.setattr(run_all, "DATA_ROOT", tmp_path / "data")
    monkeypatch.setattr(run_all, "_git_commit", lambda _project_root: "test-sha")
    monkeypatch.setattr(run_all, "_run_stage", fake_run_stage)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_all.py",
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
            "1",
            "--phase2_event_type",
            "all",
            "--run_bridge_eval_phase2",
            "1",
            "--run_strategy_blueprint_compiler",
            "0",
            "--run_strategy_builder",
            "0",
            "--run_recommendations_checklist",
            "0",
        ],
    )

    rc = run_all.main()
    assert rc == 0
    bridge = [row for row in captured if row[0].startswith("bridge_evaluate_phase2")]
    assert bridge
    _, bridge_args = bridge[0]
    assert _arg_value(bridge_args, "--embargo_days") == "1"
    assert _arg_value(bridge_args, "--candidate_mask") == "auto"


def test_run_all_target_families_are_not_routed_to_canonical_analyzer():
    target_reports_dirs = {
        "liquidity_dislocation",
        "volatility_transition",
        "positioning_extremes",
        "forced_flow_and_exhaustion",
        "trend_structure",
        "statistical_dislocation",
        "regime_transition",
        "information_desync",
        "temporal_structure",
        "execution_friction",
    }
    for event_type, script_name, _ in run_all.PHASE2_EVENT_CHAIN:
        spec = run_all.EVENT_REGISTRY_SPECS[event_type]
        if str(spec.reports_dir).strip().lower() in target_reports_dirs:
            assert script_name != "analyze_canonical_events.py", (
                f"event_type={event_type} still routes to canonical"
            )


def test_run_all_phase2_chain_has_registry_and_scripts():
    assert run_all._validate_phase2_event_chain() == []


def test_run_all_phase2_chain_validation_reports_missing_entries(monkeypatch):
    monkeypatch.setattr(
        run_all,
        "PHASE2_EVENT_CHAIN",
        [("unknown_event_type", "missing_script.py", [])],
    )
    issues = run_all._validate_phase2_event_chain()
    assert any("Missing event spec/registry entry" in issue for issue in issues)
    assert any("Missing phase2 analyzer script" in issue for issue in issues)


def test_run_all_research_gate_profile_wiring(monkeypatch, tmp_path):
    captured: list[tuple[str, list[str]]] = []

    def fake_run_stage(stage, script, base_args, run_id, **kwargs) -> bool:
        captured.append((stage, list(base_args)))
        return True

    monkeypatch.setattr(run_all, "DATA_ROOT", tmp_path / "data")
    monkeypatch.setattr(run_all, "_git_commit", lambda _project_root: "test-sha")
    monkeypatch.setattr(run_all, "_run_stage", fake_run_stage)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_all.py",
            "--symbols",
            "BTCUSDT",
            "--start",
            "2024-01-01",
            "--end",
            "2024-01-02",
            "--run_expectancy_robustness",
            "1",
            "--run_recommendations_checklist",
            "1",
            "--run_strategy_blueprint_compiler",
            "0",
            "--run_strategy_builder",
            "0",
            "--run_phase2_conditional",
            "0",
            "--mode",
            "research",
        ],
    )

    rc = run_all.main()
    assert rc == 0
    stage_map = {stage: args for stage, args in captured}
    robust_args = stage_map["validate_expectancy_traps"]
    checklist_args = stage_map["generate_recommendations_checklist"]
    assert _arg_value(robust_args, "--gate_profile") == "discovery"
    assert _arg_value(checklist_args, "--gate_profile") == "discovery"


def test_run_all_gate_profile_override_flows_to_research_stages(monkeypatch, tmp_path):
    captured: list[tuple[str, list[str]]] = []

    def fake_run_stage(stage, script, base_args, run_id, **kwargs) -> bool:
        captured.append((stage, list(base_args)))
        return True

    monkeypatch.setattr(run_all, "DATA_ROOT", tmp_path / "data")
    monkeypatch.setattr(run_all, "_git_commit", lambda _project_root: "test-sha")
    monkeypatch.setattr(run_all, "_run_stage", fake_run_stage)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_all.py",
            "--symbols",
            "BTCUSDT",
            "--start",
            "2024-01-01",
            "--end",
            "2024-01-02",
            "--run_expectancy_robustness",
            "1",
            "--run_recommendations_checklist",
            "1",
            "--run_strategy_blueprint_compiler",
            "0",
            "--run_strategy_builder",
            "0",
            "--run_phase2_conditional",
            "0",
            "--phase2_gate_profile",
            "promotion",
            "--mode",
            "research",
        ],
    )

    rc = run_all.main()
    assert rc == 0
    stage_map = {stage: args for stage, args in captured}
    robust_args = stage_map["validate_expectancy_traps"]
    checklist_args = stage_map["generate_recommendations_checklist"]
    assert _arg_value(robust_args, "--gate_profile") == "promotion"
    assert _arg_value(checklist_args, "--gate_profile") == "promotion"


def test_run_all_forwards_template_selection_to_event_level_phase2(monkeypatch, tmp_path):
    captured: list[tuple[str, list[str]]] = []

    def fake_run_stage(stage, script, base_args, run_id, **kwargs) -> bool:
        captured.append((stage, list(base_args)))
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
            "candidate_run",
            "--symbols",
            "BTCUSDT,ETHUSDT,SOLUSDT",
            "--start",
            "2026-01-01",
            "--end",
            "2026-01-31",
            "--templates",
            "continuation",
            "--runtime_invariants_mode",
            "off",
            "--run_phase2_conditional",
            "1",
            "--run_strategy_blueprint_compiler",
            "0",
            "--run_strategy_builder",
            "0",
            "--run_recommendations_checklist",
            "0",
            "--run_expectancy_robustness",
            "0",
            "--run_expectancy_analysis",
            "0",
            "--run_candidate_promotion",
            "0",
            "--run_profitable_selector",
            "0",
            "--run_interaction_lift",
            "0",
            "--run_promotion_audit",
            "0",
            "--run_edge_registry_update",
            "0",
            "--run_campaign_memory_update",
            "0",
            "--run_naive_entry_eval",
            "0",
        ],
    )

    rc = run_all.main()

    assert rc == 0
    phase2_stages = [
        args for stage, args in captured if stage.startswith("phase2_conditional_hypotheses__")
    ]
    assert phase2_stages
    assert all("--templates" in args for args in phase2_stages)
    assert all(args[args.index("--templates") + 1] == "continuation" for args in phase2_stages)


def test_run_all_template_only_selection_fans_out_across_event_chain(monkeypatch, tmp_path):
    captured: list[tuple[str, list[str]]] = []

    def fake_run_stage(stage, script, base_args, run_id, **kwargs) -> bool:
        captured.append((stage, list(base_args)))
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
            "candidate_run",
            "--symbols",
            "BTCUSDT",
            "--start",
            "2026-01-01",
            "--end",
            "2026-01-31",
            "--templates",
            "continuation",
            "--runtime_invariants_mode",
            "off",
            "--run_phase2_conditional",
            "1",
            "--run_bridge_eval_phase2",
            "0",
            "--run_candidate_promotion",
            "0",
            "--run_edge_candidate_universe",
            "0",
            "--run_discovery_quality_summary",
            "0",
            "--run_strategy_blueprint_compiler",
            "0",
            "--run_strategy_builder",
            "0",
            "--run_recommendations_checklist",
            "0",
            "--run_expectancy_robustness",
            "0",
            "--run_expectancy_analysis",
            "0",
            "--run_profitable_selector",
            "0",
            "--run_interaction_lift",
            "0",
            "--run_promotion_audit",
            "0",
            "--run_edge_registry_update",
            "0",
            "--run_campaign_memory_update",
            "0",
            "--run_naive_entry_eval",
            "0",
        ],
    )

    rc = run_all.main()

    assert rc == 0
    phase2_stage_names = [
        stage for stage, _ in captured if stage.startswith("phase2_conditional_hypotheses__")
    ]
    assert phase2_stage_names
    assert any("VOL_SHOCK" in stage for stage in phase2_stage_names)
    assert any("VOL_SPIKE" in stage for stage in phase2_stage_names)


def test_run_all_writes_research_comparison_report_when_baseline_is_configured(
    monkeypatch, tmp_path
):
    captured: list[tuple[str, str, str]] = []
    report_path = (
        tmp_path
        / "data"
        / "reports"
        / "research_comparison"
        / "candidate_run"
        / "vs_baseline_run"
        / "research_run_comparison.json"
    )

    def fake_run_stage(stage, script, base_args, run_id, **kwargs) -> bool:
        return True

    def fake_write_run_comparison_report(
        *,
        data_root,
        baseline_run_id,
        candidate_run_id,
        out_dir=None,
        report_out=None,
        summary_out=None,
        thresholds=None,
        drift_mode="warn",
    ):
        captured.append((str(data_root), baseline_run_id, candidate_run_id))
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps({"baseline_run_id": baseline_run_id, "candidate_run_id": candidate_run_id}),
            encoding="utf-8",
        )
        return report_path

    monkeypatch.setattr(run_all, "DATA_ROOT", tmp_path / "data")
    monkeypatch.setattr(run_all, "_git_commit", lambda _project_root: "test-sha")
    monkeypatch.setattr(run_all, "_run_stage", fake_run_stage)
    monkeypatch.setattr(run_all, "write_run_comparison_report", fake_write_run_comparison_report)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_all.py",
            "--run_id",
            "candidate_run",
            "--symbols",
            "BTCUSDT",
            "--start",
            "2024-01-01",
            "--end",
            "2024-01-02",
            "--runtime_invariants_mode",
            "off",
            "--research_compare_baseline_run_id",
            "baseline_run",
            "--run_strategy_blueprint_compiler",
            "0",
            "--run_strategy_builder",
            "0",
            "--run_recommendations_checklist",
            "0",
            "--run_expectancy_robustness",
            "0",
            "--run_expectancy_analysis",
            "0",
            "--run_candidate_promotion",
            "0",
            "--run_phase2_conditional",
            "0",
            "--run_profitable_selector",
            "0",
            "--run_interaction_lift",
            "0",
            "--run_promotion_audit",
            "0",
            "--run_edge_registry_update",
            "0",
            "--run_campaign_memory_update",
            "0",
            "--run_edge_candidate_universe",
            "0",
            "--run_discovery_quality_summary",
            "0",
            "--run_naive_entry_eval",
            "0",
        ],
    )

    rc = run_all.main()

    assert rc == 0
    assert captured == [(str(tmp_path / "data"), "baseline_run", "candidate_run")]
    manifest_path = tmp_path / "data" / "runs" / "candidate_run" / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["research_comparison_status"] == "written"
    assert manifest["research_comparison_baseline_run_id"] == "baseline_run"
    assert manifest["research_comparison_report_path"] == str(report_path)


def test_run_all_enforce_mode_fails_when_research_comparison_exceeds_threshold(
    monkeypatch, tmp_path
):
    report_path = (
        tmp_path
        / "data"
        / "reports"
        / "research_comparison"
        / "candidate_run"
        / "vs_baseline_run"
        / "research_run_comparison.json"
    )

    def fake_run_stage(stage, script, base_args, run_id, **kwargs) -> bool:
        return True

    def fake_write_run_comparison_report(
        *,
        data_root,
        baseline_run_id,
        candidate_run_id,
        out_dir=None,
        report_out=None,
        summary_out=None,
        thresholds=None,
        drift_mode="warn",
    ):
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(
                {
                    "baseline_run_id": baseline_run_id,
                    "candidate_run_id": candidate_run_id,
                    "assessment": {
                        "status": "fail",
                        "violation_count": 1,
                        "violations": ["promotion promoted_count delta=-4 exceeds 0"],
                    },
                }
            ),
            encoding="utf-8",
        )
        return report_path

    monkeypatch.setattr(run_all, "DATA_ROOT", tmp_path / "data")
    monkeypatch.setattr(run_all, "_git_commit", lambda _project_root: "test-sha")
    monkeypatch.setattr(run_all, "_run_stage", fake_run_stage)
    monkeypatch.setattr(run_all, "write_run_comparison_report", fake_write_run_comparison_report)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_all.py",
            "--run_id",
            "candidate_run",
            "--symbols",
            "BTCUSDT",
            "--start",
            "2024-01-01",
            "--end",
            "2024-01-02",
            "--runtime_invariants_mode",
            "off",
            "--research_compare_baseline_run_id",
            "baseline_run",
            "--research_compare_drift_mode",
            "enforce",
            "--run_strategy_blueprint_compiler",
            "0",
            "--run_strategy_builder",
            "0",
            "--run_recommendations_checklist",
            "0",
            "--run_expectancy_robustness",
            "0",
            "--run_expectancy_analysis",
            "0",
            "--run_candidate_promotion",
            "0",
            "--run_phase2_conditional",
            "0",
            "--run_profitable_selector",
            "0",
            "--run_interaction_lift",
            "0",
            "--run_promotion_audit",
            "0",
            "--run_edge_registry_update",
            "0",
            "--run_campaign_memory_update",
            "0",
            "--run_edge_candidate_universe",
            "0",
            "--run_discovery_quality_summary",
            "0",
            "--run_naive_entry_eval",
            "0",
        ],
    )

    rc = run_all.main()

    assert rc == 1
    manifest_path = tmp_path / "data" / "runs" / "candidate_run" / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["status"] == "failed"
    assert manifest["failed_stage"] == "research_comparison"
    assert manifest["research_comparison_assessment_status"] == "fail"
    assert manifest["research_comparison_violation_count"] == 1


def test_run_all_bridge_candidate_mask_override_flows_to_bridge_stage(monkeypatch, tmp_path):
    captured: list[tuple[str, list[str]]] = []

    def fake_run_stage(stage, script, base_args, run_id, **kwargs) -> bool:
        captured.append((stage, list(base_args)))
        return True

    monkeypatch.setattr(run_all, "DATA_ROOT", tmp_path / "data")
    monkeypatch.setattr(run_all, "_git_commit", lambda _project_root: "test-sha")
    monkeypatch.setattr(run_all, "_run_stage", fake_run_stage)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_all.py",
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
            "1",
            "--phase2_event_type",
            "LIQUIDITY_VACUUM",
            "--run_bridge_eval_phase2",
            "1",
            "--run_strategy_blueprint_compiler",
            "0",
            "--run_strategy_builder",
            "0",
            "--run_recommendations_checklist",
            "0",
            "--bridge_candidate_mask",
            "all",
        ],
    )

    rc = run_all.main()
    assert rc == 0
    stage_map = {stage: args for stage, args in captured}
    bridge_stage = next(stage for stage in stage_map if stage.startswith("bridge_evaluate_phase2"))
    bridge_args = stage_map[bridge_stage]
    assert _arg_value(bridge_args, "--candidate_mask") == "all"


def test_run_all_rejects_removed_atlas_flags(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(run_all, "DATA_ROOT", tmp_path / "data")
    monkeypatch.setattr(run_all, "_git_commit", lambda _project_root: "test-sha")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_all.py",
            "--symbols",
            "BTCUSDT",
            "--start",
            "2024-01-01",
            "--end",
            "2024-01-02",
            "--atlas_mode",
            "1",
        ],
    )
    rc = run_all.main()
    assert rc == 2
    assert "--atlas_mode has been removed" in capsys.readouterr().err


def test_run_all_wires_candidate_promotion_into_compiler(monkeypatch, tmp_path):
    captured: list[tuple[str, list[str]]] = []

    def fake_run_stage(stage, script, base_args, run_id, **kwargs) -> bool:
        captured.append((stage, list(base_args)))
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
            "r_promote",
            "--symbols",
            "BTCUSDT",
            "--start",
            "2024-01-01",
            "--end",
            "2024-01-02",
            "--run_phase2_conditional",
            "1",
            "--phase2_event_type",
            "LIQUIDITY_VACUUM",
            "--run_bridge_eval_phase2",
            "0",
            "--run_recommendations_checklist",
            "1",
            "--run_strategy_builder",
            "0",
            "--run_candidate_promotion",
            "1",
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

    stage_names = [stage for stage, _ in captured]
    assert "export_edge_candidates" in stage_names
    assert "generate_negative_control_summary" in stage_names
    assert "promote_candidates" in stage_names
    assert "update_edge_registry" in stage_names
    assert "generate_recommendations_checklist" in stage_names
    assert "compile_strategy_blueprints" not in stage_names
    assert stage_names.index("export_edge_candidates") < stage_names.index(
        "generate_negative_control_summary"
    )
    assert stage_names.index("generate_negative_control_summary") < stage_names.index(
        "promote_candidates"
    )
    assert stage_names.index("promote_candidates") < stage_names.index("update_edge_registry")
    assert stage_names.index("update_edge_registry") < stage_names.index(
        "generate_recommendations_checklist"
    )


def test_run_all_wires_export_edge_candidates_before_promotion(monkeypatch, tmp_path):
    captured: list[tuple[str, list[str]]] = []

    def fake_run_stage(stage, script, base_args, run_id, **kwargs) -> bool:
        captured.append((stage, list(base_args)))
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
            "r_export_promote",
            "--symbols",
            "BTCUSDT",
            "--start",
            "2024-01-01",
            "--end",
            "2024-01-02",
            "--run_phase2_conditional",
            "1",
            "--phase2_event_type",
            "LIQUIDITY_VACUUM",
            "--run_bridge_eval_phase2",
            "0",
            "--run_recommendations_checklist",
            "0",
            "--run_expectancy_analysis",
            "0",
            "--run_expectancy_robustness",
            "0",
            "--run_strategy_blueprint_compiler",
            "0",
            "--run_strategy_builder",
            "0",
            "--run_profitable_selector",
            "0",
            "--run_candidate_promotion",
            "1",
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

    stage_names = [stage for stage, _ in captured]
    assert "export_edge_candidates" in stage_names
    assert "generate_negative_control_summary" in stage_names
    assert "promote_candidates" in stage_names
    assert stage_names.index("export_edge_candidates") < stage_names.index(
        "generate_negative_control_summary"
    )
    assert stage_names.index("generate_negative_control_summary") < stage_names.index(
        "promote_candidates"
    )


def test_run_all_production_gate_profile_wiring(monkeypatch, tmp_path):
    captured: list[tuple[str, list[str]]] = []

    def fake_run_stage(stage, script, base_args, run_id, **kwargs) -> bool:
        captured.append((stage, list(base_args)))
        return True

    monkeypatch.setattr(run_all, "DATA_ROOT", tmp_path / "data")
    monkeypatch.setattr(run_all, "_git_commit", lambda _project_root: "test-sha")
    monkeypatch.setattr(run_all, "_run_stage", fake_run_stage)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_all.py",
            "--symbols",
            "BTCUSDT",
            "--start",
            "2024-01-01",
            "--end",
            "2024-01-02",
            "--run_expectancy_robustness",
            "1",
            "--run_recommendations_checklist",
            "1",
            "--run_strategy_blueprint_compiler",
            "0",
            "--run_strategy_builder",
            "0",
            "--run_phase2_conditional",
            "0",
            "--mode",
            "production",
        ],
    )

    rc = run_all.main()
    assert rc == 0
    stage_map = {stage: args for stage, args in captured}
    robust_args = stage_map["validate_expectancy_traps"]
    checklist_args = stage_map["generate_recommendations_checklist"]
    assert _arg_value(robust_args, "--gate_profile") == "promotion"
    assert _arg_value(checklist_args, "--gate_profile") == "promotion"


def test_run_all_unconditionally_blocks_strategy_blueprint_fallback(monkeypatch, capsys):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_all.py",
            "--symbols",
            "BTCUSDT",
            "--start",
            "2024-01-01",
            "--end",
            "2024-01-02",
            "--strategy_blueprint_allow_fallback",
            "1",
        ],
    )

    rc = run_all.main()
    captured = capsys.readouterr()
    assert rc == 1
    assert "INV_NO_FALLBACK_IN_MEASUREMENT" in captured.err


def test_run_all_blocks_override_flags_in_production_mode(monkeypatch, capsys):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_all.py",
            "--symbols",
            "BTCUSDT",
            "--start",
            "2024-01-01",
            "--end",
            "2024-01-02",
            "--mode",
            "production",
            "--strategy_blueprint_allow_naive_entry_fail",
            "1",
        ],
    )

    rc = run_all.main()
    captured = capsys.readouterr()
    assert rc == 1
    assert "strictly forbidden in production mode" in captured.err


def test_run_all_rejects_removed_legacy_internal_execution_flags(monkeypatch, capsys):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_all.py",
            "--symbols",
            "BTCUSDT",
            "--start",
            "2024-01-01",
            "--end",
            "2024-01-02",
            "--run_backtest",
            "1",
        ],
    )

    with pytest.raises(SystemExit) as exc:
        run_all.main()
    captured = capsys.readouterr()
    assert int(exc.value.code) == 2
    assert "unrecognized arguments: --run_backtest 1" in captured.err


def test_run_all_ci_override_guard_blocks_non_production_overrides(monkeypatch, tmp_path, capsys):
    executed: list[str] = []

    def fake_run_stage(stage, script, base_args, run_id, **kwargs) -> bool:
        executed.append(stage)
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
            "ci_override_guard_fail",
            "--symbols",
            "BTCUSDT",
            "--start",
            "2024-01-01",
            "--end",
            "2024-01-02",
            "--strategy_builder_allow_non_promoted",
            "1",
            "--ci_fail_on_non_production_overrides",
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
    captured = capsys.readouterr()
    assert rc == 1
    assert "CI override guard blocked run" in captured.err
    assert executed == []


def test_run_all_ci_override_guard_can_be_disabled(monkeypatch, tmp_path):
    executed: list[str] = []

    def fake_run_stage(stage, script, base_args, run_id, **kwargs) -> bool:
        executed.append(stage)
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
            "ci_override_guard_disabled",
            "--symbols",
            "BTCUSDT",
            "--start",
            "2024-01-01",
            "--end",
            "2024-01-02",
            "--strategy_builder_allow_non_promoted",
            "1",
            "--ci_fail_on_non_production_overrides",
            "0",
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
    assert executed


def test_run_all_explicitly_disabled_candidate_promotion_is_not_reenabled_by_legacy_alias(
    monkeypatch, tmp_path
):
    captured: list[tuple[str, list[str]]] = []

    def fake_run_stage(stage, script, base_args, run_id, **kwargs) -> bool:
        captured.append((stage, list(base_args)))
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
            "r_no_promote",
            "--symbols",
            "BTCUSDT",
            "--start",
            "2024-01-01",
            "--end",
            "2024-01-02",
            "--run_phase2_conditional",
            "1",
            "--phase2_event_type",
            "VOL_SHOCK",
            "--run_bridge_eval_phase2",
            "0",
            "--run_candidate_promotion",
            "0",
            "--run_edge_registry_update",
            "0",
            "--run_strategy_blueprint_compiler",
            "0",
            "--run_strategy_builder",
            "0",
            "--run_profitable_selector",
            "0",
            "--run_recommendations_checklist",
            "0",
            "--run_expectancy_analysis",
            "0",
            "--run_expectancy_robustness",
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
    stage_names = [stage for stage, _ in captured]
    assert "promote_candidates" not in stage_names
    assert "update_edge_registry" not in stage_names
