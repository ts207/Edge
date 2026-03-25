from __future__ import annotations

from argparse import Namespace
from typing import cast

import pytest

from project import PROJECT_ROOT
from project.core.exceptions import ContractViolationError
from project.pipelines.pipeline_defaults import DATA_ROOT, run_id_default, script_supports_flag
from project.pipelines.pipeline_planning import (
    _validate_negative_control_contract,
    build_parser,
    prepare_run_preflight,
)
from project.pipelines.stage_definitions import (
    ResolvedStageArtifactContract,
    build_stage_timeframe_artifact_mappings,
)
from project.pipelines.stage_dependencies import resolve_stage_artifact_contract
from project.pipelines.stages.core import build_core_stages


def _expected_feature_optional_inputs(timeframe: str) -> tuple[str, ...]:
    return (
        f"raw.perp.funding_{timeframe}",
        "raw.perp.liquidations",
        "raw.perp.open_interest",
    )


def _build_preflight(timeframes: str) -> dict[str, object]:
    parser = build_parser()
    args = parser.parse_args(
        [
            "--start",
            "2024-01-01",
            "--end",
            "2024-01-02",
            "--timeframes",
            timeframes,
        ]
    )
    return prepare_run_preflight(
        args=args,
        project_root=PROJECT_ROOT,
        data_root=DATA_ROOT,
        cli_flag_present=lambda _flag: False,
        run_id_default=run_id_default,
        script_supports_flag=script_supports_flag,
    )


def test_5m_plan_contracts_are_5m_compatible() -> None:
    preflight = _build_preflight("5m")
    contracts = cast(dict[str, ResolvedStageArtifactContract], preflight["artifact_contracts"])

    build_cleaned = contracts["build_cleaned_5m"]
    assert build_cleaned.inputs == ("raw.perp.ohlcv_5m",)
    assert build_cleaned.outputs == ("clean.perp.*",)

    ingest = contracts["ingest_binance_um_ohlcv_5m"]
    assert ingest.outputs == ("raw.perp.ohlcv_5m",)


def test_1m_plan_contracts_do_not_inject_5m_raw_tokens() -> None:
    preflight = _build_preflight("1m")
    contracts = cast(dict[str, ResolvedStageArtifactContract], preflight["artifact_contracts"])

    build_cleaned = contracts["build_cleaned_1m"]
    assert build_cleaned.inputs == ("raw.perp.ohlcv_1m",)
    assert "5m" not in " ".join(build_cleaned.inputs + build_cleaned.outputs)

    build_features = contracts["build_features_1m"]
    assert build_features.optional_inputs == _expected_feature_optional_inputs("1m")
    assert "5m" not in " ".join(build_features.optional_inputs)


def test_multi_timeframe_plan_contracts_are_resolved_per_timeframe() -> None:
    contract_1m, issues_1m = resolve_stage_artifact_contract(
        "build_cleaned_1m", ["--timeframe", "1m"]
    )
    contract_5m, issues_5m = resolve_stage_artifact_contract(
        "build_cleaned_5m", ["--timeframe", "5m"]
    )
    contract_15m, issues_15m = resolve_stage_artifact_contract(
        "build_cleaned_15m", ["--timeframe", "15m"]
    )
    assert issues_1m == []
    assert issues_5m == []
    assert issues_15m == []
    assert contract_1m is not None and contract_1m.inputs == ("raw.perp.ohlcv_1m",)
    assert contract_5m is not None and contract_5m.inputs == ("raw.perp.ohlcv_5m",)
    assert contract_15m is not None and contract_15m.inputs == ("raw.perp.ohlcv_15m",)

    feat_1m, feat_issues_1m = resolve_stage_artifact_contract(
        "build_features_1m", ["--timeframe", "1m"]
    )
    feat_5m, feat_issues_5m = resolve_stage_artifact_contract(
        "build_features_5m", ["--timeframe", "5m"]
    )
    feat_15m, feat_issues_15m = resolve_stage_artifact_contract(
        "build_features_15m", ["--timeframe", "15m"]
    )
    assert feat_issues_1m == []
    assert feat_issues_5m == []
    assert feat_issues_15m == []
    assert feat_1m is not None and feat_1m.optional_inputs == _expected_feature_optional_inputs(
        "1m"
    )
    assert feat_5m is not None and feat_5m.optional_inputs == _expected_feature_optional_inputs(
        "5m"
    )
    assert feat_15m is not None and feat_15m.optional_inputs == _expected_feature_optional_inputs(
        "15m"
    )


def test_combined_timeframe_preflight_resolves_stage_contracts_without_5m_leakage() -> None:
    preflight = _build_preflight("1m,5m,15m")
    contracts = cast(dict[str, ResolvedStageArtifactContract], preflight["artifact_contracts"])

    assert contracts["build_cleaned_1m"].inputs == ("raw.perp.ohlcv_1m",)
    assert contracts["build_cleaned_5m"].inputs == ("raw.perp.ohlcv_5m",)
    assert contracts["build_cleaned_15m"].inputs == ("raw.perp.ohlcv_15m",)

    assert contracts["build_features_1m"].optional_inputs == _expected_feature_optional_inputs("1m")
    assert contracts["build_features_5m"].optional_inputs == _expected_feature_optional_inputs("5m")
    assert contracts["build_features_15m"].optional_inputs == _expected_feature_optional_inputs(
        "15m"
    )

    for stage_name, contract in contracts.items():
        if "_5m" in stage_name:
            continue
        if "_1m" in stage_name or "_15m" in stage_name:
            tokens = " ".join(
                contract.inputs
                + contract.optional_inputs
                + contract.outputs
                + contract.external_inputs
            )
            assert "_5m" not in tokens


def test_preflight_rejects_unsupported_timeframe() -> None:
    with pytest.raises(ContractViolationError, match="Unsupported timeframe"):
        _build_preflight("2m")


def test_stage_contract_resolution_rejects_invalid_explicit_timeframe_flag() -> None:
    with pytest.raises(
        ContractViolationError,
        match="received invalid explicit --timeframe value '2m'",
    ):
        resolve_stage_artifact_contract("build_cleaned_5m", ["--timeframe", "2m"])


def test_negative_control_contract_helper_flags_missing_stage_for_strict_production_promotion(
) -> None:
    parser = build_parser()
    args = parser.parse_args(
        [
            "--mode",
            "production",
            "--run_phase2_conditional",
            "1",
            "--run_candidate_promotion",
            "1",
            "--candidate_promotion_allow_missing_negative_controls",
            "0",
        ]
    )

    issues = _validate_negative_control_contract(
        args=args,
        run_id="r1",
        stages={},
        data_root=DATA_ROOT,
    )
    assert any("negative-control evidence" in issue for issue in issues)


def test_preflight_plans_negative_control_stage_for_strict_production_promotion() -> None:
    parser = build_parser()
    args = parser.parse_args(
        [
            "--start",
            "2024-01-01",
            "--end",
            "2024-01-02",
            "--mode",
            "production",
            "--run_phase2_conditional",
            "1",
            "--run_candidate_promotion",
            "1",
            "--candidate_promotion_allow_missing_negative_controls",
            "0",
        ]
    )

    preflight = prepare_run_preflight(
        args=args,
        project_root=PROJECT_ROOT,
        data_root=DATA_ROOT,
        cli_flag_present=lambda _flag: False,
        run_id_default=run_id_default,
        script_supports_flag=script_supports_flag,
    )

    stage_names = list(cast(dict[str, object], preflight["stages"]).keys())
    assert "generate_negative_control_summary" in stage_names
    issues = cast(list[str], preflight["artifact_contract_issues"])
    assert not any("negative-control evidence" in issue for issue in issues)


def test_stage_timeframe_mapping_exposes_stage_script_timeframe_and_outputs() -> None:
    mappings = build_stage_timeframe_artifact_mappings()
    match = next(
        item
        for item in mappings
        if item.stage_name == "ingest_binance_um_ohlcv_5m" and item.timeframe == "5m"
    )
    assert match.script_path == "pipelines/ingest/ingest_binance_um_ohlcv.py"
    assert match.outputs == ("raw.perp.ohlcv_5m",)


def test_core_feature_stages_propagate_requested_time_window() -> None:
    args = Namespace(
        timeframes="5m",
        funding_scale="auto",
        feature_schema_version="v2",
        runtime_invariants_mode="off",
        runtime_max_events=250000,
        determinism_replay_checks=0,
        oms_replay_checks=0,
    )

    stages = build_core_stages(
        args=args,
        run_id="r1",
        symbols="BTCUSDT",
        start="2026-01-01",
        end="2026-01-03",
        force_flag="0",
        allow_missing_funding_flag="1",
        run_spot_pipeline=True,
        project_root=PROJECT_ROOT / "project",
    )

    stage_map = {stage_name: stage_args for stage_name, _script_path, stage_args in stages}

    for stage_name in ("build_features_5m", "build_features_5m_spot"):
        stage_args = stage_map[stage_name]
        assert "--start" in stage_args
        assert "--end" in stage_args
        assert stage_args[stage_args.index("--start") + 1] == "2026-01-01"
        assert stage_args[stage_args.index("--end") + 1] == "2026-01-03"
