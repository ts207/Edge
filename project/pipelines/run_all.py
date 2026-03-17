from __future__ import annotations

import os
import sys
import time
import hashlib
from fnmatch import fnmatch
from typing import Dict, List, Tuple, Optional, Any

from project import PROJECT_ROOT
from project.pipelines.pipeline_defaults import (
    DATA_ROOT,
    utc_now_iso,
    run_id_default,
    build_timing_map,
    script_supports_flag,
)
from project.pipelines.pipeline_provenance import (
    data_fingerprint,
    feature_schema_metadata,
    git_commit,
    write_run_manifest,
    read_run_manifest,
    maybe_emit_run_hash,
    refresh_runtime_lineage_fields,
    claim_map_hash,
    config_digest,
    build_initial_run_manifest,
    resolve_existing_manifest_state,
)
from project.pipelines.pipeline_planning import (
    build_parser,
    resolve_experiment_context,
    prepare_run_preflight,
    compute_stage_instance_ids,
)
from project.pipelines.run_all_bootstrap import build_run_bootstrap_state
from project.pipelines.effective_config import build_effective_config_payload, write_effective_config
from project.pipelines.pipeline_execution import (
    execute_pipeline_stages,
    seed_run_manifest,
    finalize_run_manifest,
    run_stage as _run_stage,
)
from project.pipelines.run_all_support import (
    argv_flag_present,
    argv_flag_truthy,
    evaluate_startup_guards,
    fail_run,
)
from project.pipelines.run_all_finalize import (
    finalize_successful_run,
    handle_runtime_postflight,
)
from project.research.services.run_comparison_service import write_run_comparison_report
from project.pipelines.pipeline_provenance import write_run_manifest as _write_run_manifest
from project.events.phase2 import PHASE2_EVENT_CHAIN
from project.events.event_specs import EVENT_REGISTRY_SPECS

def _validate_phase2_event_chain() -> List[str]:
    import project.events.detectors.registry as _det_reg
    _det_reg.load_all_detectors()
    issues = []
    for etype, script, _ in PHASE2_EVENT_CHAIN:
        if etype not in EVENT_REGISTRY_SPECS:
            issues.append(f"Missing event spec/registry entry for {etype}")
        script_path = PROJECT_ROOT / "pipelines" / "research" / str(script)
        if not script_path.exists():
            issues.append(f"Missing phase2 analyzer script for {etype}: {script}")
        if _det_reg.get_detector(etype) is None:
            issues.append(f"No registered detector for {etype}")
    return issues

from project.pipelines.pipeline_audit import (
    apply_run_terminal_audit,
    load_checklist_decision,
    run_runtime_postflight_audit,
    apply_runtime_postflight_to_manifest,
    enforce_runtime_postflight,
    emit_failure_messages,
    record_non_production_overrides,
)
from project.pipelines.pipeline_summary import (
    write_run_kpi_scorecard,
    print_artifact_summary,
)

_git_commit = git_commit

from project.specs.utils import get_spec_hashes
from project.specs.ontology import (
    ontology_spec_hash,
    ontology_component_hash_fields,
    ontology_component_hashes,
)
from project.specs.invariants import (
    validate_runtime_invariants_specs as _validate_runtime_invariants_specs_impl,
)

validate_runtime_invariants_specs = _validate_runtime_invariants_specs_impl
_run_runtime_postflight_audit = run_runtime_postflight_audit
_refresh_runtime_lineage_fields = refresh_runtime_lineage_fields

def _data_fingerprint(
    symbols: List[str],
    run_id: str,
    *,
    runtime_invariants: Dict[str, object] | None = None,
    objective_profile: Dict[str, object] | None = None,
    effective_config_hash: str | None = None,
) -> Tuple[str, Dict[str, object]]:
    digest, lineage = data_fingerprint(
        symbols,
        run_id,
        project_root=PROJECT_ROOT,
        data_root=DATA_ROOT,
        runtime_invariants=runtime_invariants,
        objective_profile=objective_profile,
        effective_config_hash=effective_config_hash,
    )
    lake = lineage.get("lake", {}) if isinstance(lineage, dict) else {}
    if isinstance(lake, dict):
        lineage.setdefault("file_count", int(lake.get("file_count", 0) or 0))
        lineage.setdefault("lake_digest", str(lake.get("digest", "")))
    return digest, lineage

def _run_all_impl(raw_argv: List[str] | None = None) -> int:
    # Synchronize environment with current DATA_ROOT for downstream helpers
    os.environ["BACKTEST_DATA_ROOT"] = str(DATA_ROOT)
    raw_argv = list(raw_argv if raw_argv is not None else sys.argv[1:])

    if "--atlas_mode" in raw_argv or any(str(x).startswith("--atlas_mode=") for x in raw_argv):
        print("--atlas_mode has been removed", file=sys.stderr)
        return 2
    if argv_flag_truthy(raw_argv, "--run_hypothesis_generator"):
        print("--run_hypothesis_generator has been removed", file=sys.stderr)
        return 2

    parser = build_parser()
    
    def write_run_manifest_internal(run_id: str, manifest: Dict[str, Any]) -> None:
        _write_run_manifest(run_id, manifest)
    
    args, resolved_config, experiment_id, experiment_results_dir = resolve_experiment_context(
        parser,
        raw_argv,
        data_root=DATA_ROOT,
        run_id_default=run_id_default,
    )

    preflight = prepare_run_preflight(
        args=args,
        project_root=PROJECT_ROOT,
        data_root=DATA_ROOT,
        cli_flag_present=lambda flag: argv_flag_present(raw_argv, flag),
        run_id_default=run_id_default,
        script_supports_flag=script_supports_flag,
    )
    if preflight.get("exit_code") is not None:
        return int(preflight["exit_code"])
    artifact_contract_issues = list(preflight.get("artifact_contract_issues", []))
    if artifact_contract_issues:
        print("Artifact contract resolution failed:", file=sys.stderr)
        for issue in artifact_contract_issues:
            print(f" - {issue}", file=sys.stderr)
        return 2

    run_id = str(preflight["run_id"])
    stages = preflight["stages"]
    planned_stage_instances = compute_stage_instance_ids(stages)
    runtime_invariants_mode = str(preflight["runtime_invariants_mode"])
    
    if bool(args.plan_only):
        print(f"Plan for run {run_id}:")
        for s in planned_stage_instances:
            print(f" - {s}")
        return 0

    # Initialize state
    stage_timings: List[Tuple[str, float]] = []
    stage_instance_timings: List[Tuple[str, float]] = []
    pipeline_session_id = hashlib.sha256(f"{run_id}:{time.time_ns()}".encode()).hexdigest()
    
    try:
        bootstrap = build_run_bootstrap_state(
            args=args,
            preflight=preflight,
            resolved_config=resolved_config,
            run_id=run_id,
            stages=stages,
            planned_stage_instances=planned_stage_instances,
            pipeline_session_id=pipeline_session_id,
            data_root=DATA_ROOT,
            data_fingerprint_fn=_data_fingerprint,
            git_commit_fn=_git_commit,
        )
    except Exception as exc:
        print(f"Run bootstrap failed: {exc}", file=sys.stderr)
        return 2
    feature_schema_version = bootstrap.feature_schema_version
    existing_manifest = bootstrap.existing_manifest
    resume_from_index = bootstrap.resume_from_index
    non_production_overrides = bootstrap.non_production_overrides
    run_manifest = bootstrap.run_manifest

    seed_run_manifest(
        run_manifest=run_manifest,
        run_id=run_id,
        existing_manifest=existing_manifest,
        resume_from_failed_stage=bool(int(args.resume_from_failed_stage)),
        write_run_manifest=write_run_manifest_internal,
    )

    record_non_production_overrides(
        run_manifest=run_manifest,
        run_id=run_id,
        non_production_overrides=non_production_overrides,
        write_run_manifest=write_run_manifest_internal,
    )

    runtime_spec_issues: List[str] = []
    if runtime_invariants_mode != "off":
        runtime_spec_issues = list(validate_runtime_invariants_specs(PROJECT_ROOT.parent))
        if runtime_spec_issues:
            run_manifest["runtime_invariants_validation_ok"] = False
            run_manifest["runtime_invariants_status"] = "invalid_spec"
            run_manifest["runtime_invariants_validation_issues"] = runtime_spec_issues
            write_run_manifest_internal(run_id, run_manifest)
            if runtime_invariants_mode == "enforce":
                finalize_run_manifest(
                    run_manifest=run_manifest,
                    status="failed",
                    stage_timings=stage_timings,
                    stage_instance_timings=stage_instance_timings,
                    failed_stage="runtime_invariants_preflight",
                    failed_stage_instance="runtime_invariants_preflight",
                )
                write_run_manifest_internal(run_id, run_manifest)
                return 1

    startup_guard_error = evaluate_startup_guards(
        args=args,
        non_production_overrides=non_production_overrides,
    )
    if startup_guard_error:
        return fail_run(
            run_manifest=run_manifest,
            run_id=run_id,
            stage_timings=stage_timings,
            stage_instance_timings=stage_instance_timings,
            write_run_manifest=write_run_manifest_internal,
            finalize_run_manifest=finalize_run_manifest,
            failed_stage="startup_guard",
            message=startup_guard_error,
        )

    if bool(args.dry_run):
        run_manifest["dry_run"] = True
        finalize_run_manifest(
            run_manifest=run_manifest,
            status="success",
            stage_timings=[],
            stage_instance_timings=[],
        )
        write_run_manifest_internal(run_id, run_manifest)
        print(f"Dry run for {run_id} completed (manifest finalized).")
        return 0

    execution_requested = bool(preflight.get("execution_requested", True))
    last_stage_cache_meta = run_manifest.get("stage_cache_meta", {})

    # Unified DAG Execution (handles parallelism, dependencies, and timing)
    stage_execution = execute_pipeline_stages(
        args=args,
        run_id=run_id,
        stages=stages,
        planned_stage_instances=planned_stage_instances,
        resume_from_index=resume_from_index,
        execution_requested=execution_requested,
        run_manifest=run_manifest,
        stage_timings=stage_timings,
        stage_instance_timings=stage_instance_timings,
        write_run_manifest=write_run_manifest_internal,
        write_run_kpi_scorecard=write_run_kpi_scorecard,
        apply_run_terminal_audit=apply_run_terminal_audit,
        load_checklist_decision=load_checklist_decision,
        last_stage_cache_meta=last_stage_cache_meta,
        feature_schema_version=feature_schema_version,
        current_pipeline_session_id=pipeline_session_id,
        run_stage_fn=_run_stage,
    )
    
    if str(stage_execution.get("status")) != "ok":
        if str(stage_execution.get("reason")) == "terminal_manifest_guard":
            print("Terminal run manifest detected; aborting remaining stages", file=sys.stderr)
        finalize_run_manifest(
            run_manifest=run_manifest,
            status="failed",
            stage_timings=stage_timings,
            stage_instance_timings=stage_instance_timings,
            checklist_decision=stage_execution.get("checklist_decision"),
            auto_continue_applied=bool(stage_execution.get("auto_continue_applied")),
            auto_continue_reason=str(stage_execution.get("auto_continue_reason")),
            non_production_overrides=list(stage_execution.get("non_production_overrides", [])),
            failed_stage=stage_execution.get("failed_stage"),
            failed_stage_instance=stage_execution.get("failed_stage_instance"),
        )
        write_run_manifest_internal(run_id, run_manifest)
        return 1

    postflight_exit = handle_runtime_postflight(
        run_manifest=run_manifest,
        run_id=run_id,
        runtime_invariants_mode=runtime_invariants_mode,
        preflight=preflight,
        stage_execution=stage_execution,
        stage_timings=stage_timings,
        stage_instance_timings=stage_instance_timings,
        refresh_runtime_lineage_fields=_refresh_runtime_lineage_fields,
        run_runtime_postflight_audit=_run_runtime_postflight_audit,
        apply_runtime_postflight_to_manifest=apply_runtime_postflight_to_manifest,
        enforce_runtime_postflight=enforce_runtime_postflight,
        emit_failure_messages=emit_failure_messages,
        finalize_run_manifest=finalize_run_manifest,
        write_run_manifest=write_run_manifest_internal,
    )
    if postflight_exit is not None:
        return int(postflight_exit)

    return finalize_successful_run(
        run_manifest=run_manifest,
        run_id=run_id,
        preflight=preflight,
        stage_execution=stage_execution,
        stage_timings=stage_timings,
        stage_instance_timings=stage_instance_timings,
        finalize_run_manifest=finalize_run_manifest,
        apply_run_terminal_audit=apply_run_terminal_audit,
        maybe_emit_run_hash=maybe_emit_run_hash,
        write_run_manifest=write_run_manifest_internal,
        write_run_kpi_scorecard=write_run_kpi_scorecard,
        print_artifact_summary=print_artifact_summary,
        write_run_comparison_report=write_run_comparison_report,
        data_root=DATA_ROOT,
    )



def main(argv: List[str] | None = None) -> int:
    return _run_all_impl(list(argv if argv is not None else sys.argv[1:]))
if __name__ == "__main__":
    sys.exit(main())
