from __future__ import annotations
import json
import sys
from pathlib import Path

import pytest

import project.pipelines.run_all as run_all


def _arg_value(args: list[str], flag: str) -> str:
    return args[args.index(flag) + 1]


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
