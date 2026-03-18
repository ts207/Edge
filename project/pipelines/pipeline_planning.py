from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Mapping

from project import PROJECT_ROOT
from project.pipelines.pipeline_defaults import (
    DATA_ROOT,
    as_flag,
    run_id_default,
    script_supports_flag,
)

from project.pipelines.pipeline_provenance import (
    objective_spec_metadata,
    resolve_objective_name,
    resolve_retail_profile_name,
    retail_profile_metadata,
)

from project.core.timeframes import normalize_timeframe
from project.pipelines.stage_dependencies import resolve_stage_artifact_contract
from project.pipelines.stage_definitions import ResolvedStageArtifactContract
from project.specs.ontology import ontology_spec_hash
from project.pipelines.planner import build_pipeline_plan
from project.events.phase2 import PHASE2_EVENT_CHAIN
from project.pipelines.effective_config import resolve_effective_args


def build_parser() -> argparse.ArgumentParser:
    """Builds the ArgumentParser for run_all.py with all necessary flags."""
    parser = argparse.ArgumentParser(
        description="Run discovery-first pipeline.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    # Core Pipeline Flags
    parser.add_argument("--run_id", help="Unique ID for this pipeline run.")
    parser.add_argument("--experiment_config", help="Path to an experiment YAML config.")
    parser.add_argument("--registry_root", default="project/configs/registries", help="Path to platform-owned registries.")
    parser.add_argument("--override", action="append", default=[], help="Override config keys.")
    parser.add_argument(
        "--symbols", default="dynamic", help="Comma-separated symbols or 'dynamic'."
    )
    parser.add_argument("--start", help="Start date (YYYY-MM-DD).")
    parser.add_argument("--end", help="End date (YYYY-MM-DD).")
    parser.add_argument("--force", type=int, default=0, help="Force re-run of stages.")
    parser.add_argument(
        "--mode", choices=["research", "production", "certification"], default="research"
    )
    parser.add_argument("--config", action="append", default=[], help="Additional YAML configs.")

    # Ingest / Data Flags
    parser.add_argument("--skip_ingest_ohlcv", type=int, default=0)
    parser.add_argument("--skip_ingest_funding", type=int, default=0)
    parser.add_argument("--skip_ingest_spot_ohlcv", type=int, default=0)
    parser.add_argument("--funding_scale", choices=["auto", "decimal", "percent", "bps"], default="auto")
    parser.add_argument("--enable_cross_venue_spot_pipeline", type=int, default=1)
    parser.add_argument("--allow_missing_funding", type=int, default=0)
    parser.add_argument("--allow_constant_funding", type=int, default=0)
    parser.add_argument("--allow_funding_timestamp_rounding", type=int, default=0)
    parser.add_argument("--run_ingest_liquidation_snapshot", type=int, default=0)
    parser.add_argument("--run_ingest_open_interest_hist", type=int, default=0)
    # LT-002: Hardcoded Open Interest to only use 5m archive to prevent API trailing gaps and distribution mismatches
    parser.add_argument(
        "--timeframes", default="5m", help="Comma-separated list of timeframes (e.g., '1m,5m,15m')"
    )

    # Concept / Strategy Flags
    parser.add_argument("--concept", default="", help="Path to a Unified ControlSpec YAML file.")
    parser.add_argument("--objective_name", default="")
    parser.add_argument("--objective_spec", default=None)
    parser.add_argument("--retail_profile", default="")
    parser.add_argument("--retail_profiles_spec", default=None)
    parser.add_argument("--allow_ontology_hash_mismatch", type=int, default=0)
    parser.add_argument("--run_ontology_consistency_audit", type=int, default=1)
    parser.add_argument("--ontology_consistency_fail_on_missing", type=int, default=1)

    # Hypothesis / Research Flags
    parser.add_argument("--hypothesis_datasets", default="auto")
    parser.add_argument("--hypothesis_max_fused", type=int, default=24)

    # Phase 2 Flags
    parser.add_argument("--run_phase2_conditional", type=int, default=0)
    parser.add_argument("--phase2_event_type", default="VOL_SHOCK")
    parser.add_argument("--events", nargs="+", help="Explicit subset of event IDs to run.")
    parser.add_argument("--templates", nargs="+", help="Explicit subset of strategy templates to run.")
    parser.add_argument("--horizons", nargs="+", help="Explicit subset of horizons (e.g., 5m, 15m) to run.")
    parser.add_argument("--directions", nargs="+", help="Explicit subset of directions (e.g., long, short) to run.")
    parser.add_argument("--contexts", nargs="+", help="Explicit subset of contexts (e.g., session=open) to run.")
    parser.add_argument("--entry_lags", nargs="+", type=int, help="Explicit subset of entry lags (bars) to run.")
    parser.add_argument("--sequence_max_gap", type=int, help="Max gap for event sequences.")
    parser.add_argument("--program_id", help="Program ID for experiment campaign tracking.")
    parser.add_argument("--search_budget", type=int, help="Limit total candidate expansions.")

    parser.add_argument("--phase2_max_conditions", type=int, default=20)
    parser.add_argument("--phase2_max_actions", type=int, default=9)
    parser.add_argument("--phase2_min_regime_stable_splits", type=int, default=2)
    parser.add_argument("--phase2_require_phase1_pass", type=int, default=1)
    parser.add_argument("--phase2_min_ess", type=float, default=150.0)
    parser.add_argument("--phase2_ess_max_lag", type=int, default=24)
    parser.add_argument("--phase2_multiplicity_k", type=float, default=1.0)
    parser.add_argument("--phase2_parameter_curvature_max_penalty", type=float, default=0.50)
    parser.add_argument("--phase2_delay_grid_bars", default="0,4,8,16,30")
    parser.add_argument("--phase2_min_delay_positive_ratio", type=float, default=0.60)
    parser.add_argument("--phase2_min_delay_robustness_score", type=float, default=0.60)
    parser.add_argument("--phase2_shift_labels_k", type=int, default=0)
    parser.add_argument(
        "--phase2_cost_calibration_mode", choices=["static", "tob_regime"], default="static"
    )
    parser.add_argument("--phase2_cost_min_tob_coverage", type=float, default=0.60)
    parser.add_argument("--phase2_cost_tob_tolerance_minutes", type=int, default=10)
    parser.add_argument(
        "--phase2_gate_profile", choices=["auto", "discovery", "promotion", "synthetic"], default="auto"
    )
    parser.add_argument("--discovery_profile", choices=["standard", "synthetic"], default="standard")
    parser.add_argument(
        "--discovery-mode", choices=["search"], default="search",
        help="Canonical discovery path. Only the search-backed discovery engine is supported."
    )
    parser.add_argument("--search_spec", default="spec/search_space.yaml", help="Search spec name or path (default: spec/search_space.yaml).")
    parser.add_argument("--search_min_n", type=int, default=30, help="Min sample size for new search engine discovery.")

    # Bridge / Eval Flags
    parser.add_argument("--run_bridge_eval_phase2", type=int, default=1)
    parser.add_argument("--bridge_edge_cost_k", type=float, default=2.0)
    parser.add_argument("--bridge_stressed_cost_multiplier", type=float, default=1.5)
    parser.add_argument("--bridge_min_validation_trades", type=int, default=20)
    parser.add_argument("--bridge_train_frac", type=float, default=0.6)
    parser.add_argument("--bridge_validation_frac", type=float, default=0.2)
    parser.add_argument("--bridge_embargo_days", type=int, default=1)
    parser.add_argument(
        "--bridge_candidate_mask", choices=["auto", "research", "final", "all"], default="auto"
    )
    parser.add_argument("--run_discovery_quality_summary", type=int, default=1)
    parser.add_argument("--run_naive_entry_eval", type=int, default=1)
    parser.add_argument("--naive_min_trades", type=int, default=20)
    parser.add_argument("--naive_min_expectancy_after_cost", type=float, default=0.0)
    parser.add_argument("--naive_max_drawdown", type=float, default=1.0)

    # Execution / Performance Flags
    parser.add_argument("--max_analyzer_workers", type=int, default=8)
    parser.add_argument("--market_context_workers", type=int, default=1)
    parser.add_argument("--analyzer_symbol_workers", type=int, default=1)
    parser.add_argument("--phase2_parallel_workers", type=int, default=1)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--performance_mode", type=int, default=0)
    parser.add_argument("--enable_event_stage_cache", type=int, default=1)
    parser.add_argument("--resume_from_failed_stage", type=int, default=0)
    parser.add_argument("--feature_schema_version", default="", help="Leave empty for canonical default.")

    # Strategy / Promotion Flags
    parser.add_argument("--run_candidate_promotion", type=int, default=1)
    parser.add_argument("--run_recommendations_checklist", type=int, default=1)
    parser.add_argument("--run_expectancy_analysis", type=int, default=0)
    parser.add_argument("--run_expectancy_robustness", type=int, default=0)
    parser.add_argument("--run_strategy_builder", type=int, default=0)
    parser.add_argument("--strategy_builder_top_k_per_event", type=int, default=2)
    parser.add_argument("--strategy_builder_max_candidates", type=int, default=20)
    parser.add_argument("--strategy_builder_include_alpha_bundle", type=int, default=1)
    parser.add_argument("--strategy_builder_allow_non_promoted", type=int, default=0)
    parser.add_argument("--strategy_builder_allow_missing_candidate_detail", type=int, default=0)
    parser.add_argument("--strategy_builder_enable_fractional_allocation", type=int, default=1)
    parser.add_argument("--run_strategy_blueprint_compiler", type=int, default=0)
    parser.add_argument("--strategy_blueprint_max_per_event", type=int, default=5)
    parser.add_argument("--strategy_blueprint_min_events_floor", type=int, default=20)
    parser.add_argument("--strategy_blueprint_allow_fallback", type=int, default=0)
    parser.add_argument("--strategy_blueprint_allow_non_executable_conditions", type=int, default=0)
    parser.add_argument("--strategy_blueprint_allow_naive_entry_fail", type=int, default=0)
    parser.add_argument("--strategy_blueprint_ignore_checklist", type=int, default=0)
    parser.add_argument("--strategy_builder_ignore_checklist", type=int, default=0)
    parser.add_argument("--run_profitable_selector", type=int, default=0)
    parser.add_argument("--run_interaction_lift", type=int, default=0)
    parser.add_argument("--run_promotion_audit", type=int, default=1)
    parser.add_argument("--run_edge_registry_update", type=int, default=0)
    parser.add_argument("--run_campaign_memory_update", type=int, default=1)
    parser.add_argument("--campaign_memory_promising_top_k", type=int, default=5)
    parser.add_argument("--campaign_memory_avoid_top_k", type=int, default=5)
    parser.add_argument("--campaign_memory_repair_top_k", type=int, default=5)
    parser.add_argument("--campaign_memory_exploit_top_k", type=int, default=3)
    parser.add_argument("--campaign_memory_frontier_untested_top_k", type=int, default=3)
    parser.add_argument("--campaign_memory_frontier_repair_top_k", type=int, default=2)
    parser.add_argument("--campaign_memory_exhausted_failure_threshold", type=int, default=3)
    parser.add_argument("--run_edge_candidate_universe", type=int, default=0)
    parser.add_argument("--strict_recommendations_checklist", type=int, default=0)
    parser.add_argument("--auto_continue_on_keep_research", type=int, default=0)
    parser.add_argument("--ci_fail_on_non_production_overrides", type=int, default=0)
    parser.add_argument("--candidate_promotion_max_q_value", type=float, default=None)
    parser.add_argument(
        "--candidate_promotion_profile",
        choices=["auto", "research", "deploy"],
        default="auto",
    )
    parser.add_argument("--candidate_promotion_min_events", type=int, default=20)
    parser.add_argument("--candidate_promotion_min_stability_score", type=float, default=0.60)
    parser.add_argument("--candidate_promotion_min_sign_consistency", type=float, default=0.60)
    parser.add_argument("--candidate_promotion_min_cost_survival_ratio", type=float, default=0.50)
    parser.add_argument("--candidate_promotion_min_tob_coverage", type=float, default=0.60)
    parser.add_argument(
        "--candidate_promotion_max_negative_control_pass_rate", type=float, default=0.10
    )
    parser.add_argument("--candidate_promotion_require_hypothesis_audit", type=int, default=1)
    parser.add_argument(
        "--candidate_promotion_allow_missing_negative_controls", type=int, default=0
    )
    parser.add_argument("--promotion_allow_fallback_evidence", type=int, default=0)

    # Runtime Invariants / Replay Flags
    parser.add_argument(
        "--runtime_invariants_mode", choices=["off", "audit", "enforce"], default="audit"
    )
    parser.add_argument("--emit_run_hash", type=int, default=0)
    parser.add_argument("--determinism_replay_checks", type=int, default=0)
    parser.add_argument("--oms_replay_checks", type=int, default=0)
    parser.add_argument("--runtime_max_events", type=int, default=250000)
    parser.add_argument(
        "--research_compare_baseline_run_id",
        default="",
        help="Optional baseline research run_id for automatic phase2/promotion diagnostic comparison.",
    )
    parser.add_argument(
        "--research_compare_drift_mode",
        choices=["off", "warn", "enforce"],
        default="warn",
        help="How to treat research comparison drift when a baseline run is configured.",
    )
    parser.add_argument("--research_compare_max_phase2_candidate_count_delta_abs", type=float, default=10.0)
    parser.add_argument("--research_compare_max_phase2_survivor_count_delta_abs", type=float, default=2.0)
    parser.add_argument("--research_compare_max_phase2_zero_eval_rows_increase", type=float, default=0.0)
    parser.add_argument("--research_compare_max_phase2_survivor_q_value_increase", type=float, default=0.05)
    parser.add_argument("--research_compare_max_phase2_survivor_estimate_bps_drop", type=float, default=3.0)
    parser.add_argument("--research_compare_max_promotion_promoted_count_delta_abs", type=float, default=2.0)
    parser.add_argument("--research_compare_max_reject_reason_shift_abs", type=float, default=3.0)
    parser.add_argument("--research_compare_max_edge_tradable_count_delta_abs", type=float, default=2.0)
    parser.add_argument("--research_compare_max_edge_candidate_count_delta_abs", type=float, default=2.0)
    parser.add_argument("--research_compare_max_edge_after_cost_positive_validation_count_delta_abs", type=float, default=2.0)
    parser.add_argument("--research_compare_max_edge_median_resolved_cost_bps_delta_abs", type=float, default=0.25)
    parser.add_argument("--research_compare_max_edge_median_expectancy_bps_delta_abs", type=float, default=0.25)
    parser.add_argument("--phase2_min_validation_n_obs", type=int, default=None)
    parser.add_argument("--phase2_min_test_n_obs", type=int, default=None)
    parser.add_argument("--phase2_min_total_n_obs", type=int, default=None)

    # Execution Flow / Smoke Flags
    parser.add_argument(
        "--dry_run", type=int, default=0, help="Plan and manifest only, no execution."
    )
    parser.add_argument("--plan_only", type=int, default=0, help="Exit after printing the plan.")
    parser.add_argument("--smoke", type=int, default=0, help="Run a minimal single-symbol slice.")
    parser.add_argument("--fees_bps", type=float, default=None)
    parser.add_argument("--slippage_bps", type=float, default=None)
    parser.add_argument("--cost_bps", type=float, default=None)

    return parser


def resolve_experiment_context(
    parser: argparse.ArgumentParser,
    raw_argv: List[str],
    **kwargs
) -> Tuple[argparse.Namespace, Dict, str, Path]:
    """Resolves effective configuration and experiment context."""
    experiment_id = "default"
    experiment_results_dir = kwargs.get("data_root", Path("/tmp")) / "experiments" / experiment_id
    args, resolved_config = resolve_effective_args(parser, raw_argv)
    return args, resolved_config, experiment_id, experiment_results_dir


def parse_symbols_csv(symbols_csv: str) -> List[str]:
    """Parses a comma-separated string of symbols into a list of unique symbols."""
    out: List[str] = []
    seen = set()
    for raw in str(symbols_csv).split(","):
        symbol = raw.strip().upper()
        if symbol and symbol not in seen:
            out.append(symbol)
            seen.add(symbol)
    return out


def parse_timeframes_csv(timeframes_csv: str) -> List[str]:
    """Parse comma-separated timeframe input to canonical, unique values."""
    out: List[str] = []
    seen = set()
    for raw in str(timeframes_csv or "").split(","):
        token = str(raw).strip()
        if not token:
            continue
        normalized = normalize_timeframe(token)
        if normalized not in seen:
            out.append(normalized)
            seen.add(normalized)
    if not out:
        out.append(normalize_timeframe("5m"))
    return out


def resolve_pipeline_artifact_contracts(
    stages: Mapping[str, Any],
) -> tuple[Dict[str, ResolvedStageArtifactContract], List[str]]:
    """Resolve artifact contracts for each planned stage."""
    resolved: Dict[str, ResolvedStageArtifactContract] = {}
    issues: List[str] = []
    for stage_name, stage_def in stages.items():
        contract, contract_issues = resolve_stage_artifact_contract(
            stage_name,
            list(getattr(stage_def, "args", [])),
        )
        if contract is not None:
            resolved[stage_name] = contract
        if contract_issues:
            issues.extend(contract_issues)
    return resolved, issues


def compute_stage_instance_ids(
    stages: List[Tuple[str, Path, List[str]]] | Mapping[str, Any],
) -> List[str]:
    """Computes unique instance IDs for stages, handling multiple occurrences of the same stage."""
    from project.pipelines.execution_engine import stage_instance_base

    counts: Dict[str, int] = {}
    out: List[str] = []

    if isinstance(stages, Mapping):
        # For DAG, stage names are already unique keys
        return list(stages.keys())

    for stage, _, base_args in stages:
        base = stage_instance_base(stage, base_args)
        n = counts.get(base, 0) + 1
        counts[base] = n
        out.append(base if n == 1 else f"{base}__{n}")
    return out


def load_historical_universe(project_root: Path) -> List[str]:
    """Loads symbols from spec/historical_universe.csv."""
    path = project_root / "spec" / "historical_universe.csv"
    if not path.exists():
        return ["BTCUSDT"]
    try:
        import pandas as pd

        df = pd.read_csv(path)
        if "symbol" in df.columns:
            return [
                str(s).strip().upper() for s in df["symbol"].dropna().unique() if str(s).strip()
            ]
    except Exception:
        pass
    return ["BTCUSDT"]


def collect_startup_non_production_overrides(
    *,
    args: argparse.Namespace,
    existing_manifest_path: Path,
    allow_ontology_hash_mismatch: bool,
    existing_ontology_hash: str,
    ontology_hash: str,
) -> List[str]:
    """Collects overrides that are considered non-production."""
    overrides = []
    if (
        allow_ontology_hash_mismatch
        and existing_ontology_hash
        and existing_ontology_hash != ontology_hash
    ):
        overrides.append(
            f"allow_ontology_hash_mismatch: {existing_ontology_hash} -> {ontology_hash}"
        )

    if args.mode not in {"production", "research"}:
        overrides.append(f"mode: {args.mode}")

    override_fields = (
        "strategy_builder_allow_non_promoted",
        "strategy_builder_allow_missing_candidate_detail",
        "strategy_blueprint_allow_fallback",
        "strategy_blueprint_allow_non_executable_conditions",
        "strategy_blueprint_allow_naive_entry_fail",
        "promotion_allow_fallback_evidence",
    )
    for field in override_fields:
        raw = getattr(args, field, 0)
        try:
            enabled = bool(int(raw or 0))
        except (TypeError, ValueError):
            enabled = bool(raw)
        if enabled:
            overrides.append(f"{field}: {raw}")

    return overrides


def prepare_run_preflight(
    *,
    args: argparse.Namespace,
    project_root: Path,
    data_root: Path,
    cli_flag_present: Any,
    run_id_default: Any,
    script_supports_flag: Any,
) -> Dict[str, object]:
    """Performs preflight checks and plans the pipeline execution."""
    run_id = args.run_id or run_id_default()

    # Resolve Symbols
    if args.symbols == "dynamic":
        parsed_symbols = load_historical_universe(project_root)
    else:
        parsed_symbols = parse_symbols_csv(args.symbols)

    if not args.start or not args.end:
        print(
            "ERROR: --start and --end date flags are required for all pipeline runs.",
            file=sys.stderr,
        )
        return {"exit_code": 2, "run_id": run_id}

    args.timeframes = ",".join(parse_timeframes_csv(getattr(args, "timeframes", "5m")))

    if bool(int(getattr(args, "performance_mode", 0) or 0)):
        if not cli_flag_present("--runtime_invariants_mode"):
            args.runtime_invariants_mode = "off"
        if not cli_flag_present("--emit_run_hash"):
            args.emit_run_hash = 0
    if str(getattr(args, "mode", "research")).strip().lower() in {"production", "certification"}:
        if not cli_flag_present("--run_phase2_conditional"):
            args.run_phase2_conditional = 1
    if (
        int(getattr(args, "run_phase2_conditional", 0) or 0)
        and getattr(args, "templates", None)
        and not getattr(args, "events", None)
        and not cli_flag_present("--phase2_event_type")
    ):
        # Template-only runs should fan out over the canonical event chain unless the user
        # explicitly pins a single event family. Otherwise the parser default of VOL_SHOCK
        # silently narrows the run and breaks calibration parity with event-level reruns.
        args.phase2_event_type = "all"

    expectancy_script = project_root / "pipelines" / "research" / "analyze_conditional_expectancy.py"
    expectancy_tail_requested = any(
        int(getattr(args, attr, 0) or 0)
        for attr in (
            "run_expectancy_analysis",
            "run_expectancy_robustness",
            "run_recommendations_checklist",
            "run_strategy_blueprint_compiler",
            "run_strategy_builder",
        )
    )
    if expectancy_tail_requested and not expectancy_script.exists():
        print(
            "WARNING: Disabling recommendations checklist and expectancy robustness "
            "because analyze_conditional_expectancy.py is unavailable.",
            file=sys.stderr,
        )
        args.run_expectancy_analysis = 0
        args.run_expectancy_robustness = 0
        args.run_recommendations_checklist = 0
        args.run_strategy_blueprint_compiler = 0
        args.run_strategy_builder = 0

    if int(getattr(args, "run_recommendations_checklist", 0)):
        if not cli_flag_present("--run_expectancy_analysis"):
            args.run_expectancy_analysis = 1
        if not cli_flag_present("--run_expectancy_robustness"):
            args.run_expectancy_robustness = 1
    if int(getattr(args, "run_candidate_promotion", 0)) and int(
        getattr(args, "run_phase2_conditional", 0)
    ):
        if not cli_flag_present("--run_edge_registry_update"):
            args.run_edge_registry_update = 1

    # Resolve Metadata
    objective_name = resolve_objective_name(args.objective_name)
    objective_spec, objective_spec_hash, objective_spec_path = objective_spec_metadata(
        objective_name, args.objective_spec
    )

    retail_profile_name = resolve_retail_profile_name(args.retail_profile)
    retail_profile, retail_profile_spec_hash, retail_profile_spec_path = retail_profile_metadata(
        retail_profile_name, args.retail_profiles_spec
    )
    args.phase2_gate_profile_resolved = (
        str(getattr(args, "phase2_gate_profile", "auto") or "auto").strip().lower()
    )

    # Build Plan
    stages = build_pipeline_plan(
        args=args,
        run_id=run_id,
        symbols=",".join(parsed_symbols),
        start=args.start,
        end=args.end,
        force_flag=as_flag(args.force),
        allow_missing_funding_flag=as_flag(args.allow_missing_funding),
        run_spot_pipeline=bool(args.enable_cross_venue_spot_pipeline),
        research_gate_profile="discovery" if args.mode == "research" else "promotion",
        project_root=project_root,
        data_root=data_root,
        phase2_event_chain=PHASE2_EVENT_CHAIN,
        script_supports_flag=script_supports_flag,
        retail_profile_name=retail_profile_name,
    )
    artifact_contracts, artifact_contract_issues = resolve_pipeline_artifact_contracts(stages)

    return {
        "exit_code": None,
        "run_id": run_id,
        "stages": stages,
        "parsed_symbols": parsed_symbols,
        "ontology_hash": ontology_spec_hash(project_root.parent),
        "runtime_invariants_mode": args.runtime_invariants_mode,
        "emit_run_hash_requested": bool(args.emit_run_hash),
        "determinism_replay_checks_requested": bool(args.determinism_replay_checks),
        "oms_replay_checks_requested": bool(args.oms_replay_checks),
        "objective_name": objective_name,
        "objective_spec_hash": objective_spec_hash,
        "objective_spec_path": objective_spec_path,
        "retail_profile_name": retail_profile_name,
        "retail_profile": retail_profile,
        "retail_profile_spec_hash": retail_profile_spec_hash,
        "retail_profile_spec_path": retail_profile_spec_path,
        "runtime_invariants_status": "configured",
        "artifact_contracts": artifact_contracts,
        "artifact_contract_issues": artifact_contract_issues,
        "execution_requested": True,
        "search_spec": getattr(args, "search_spec", "spec/search_space.yaml"),
        "research_compare_baseline_run_id": str(
            getattr(args, "research_compare_baseline_run_id", "") or ""
        ).strip(),
        "research_compare_drift_mode": str(getattr(args, "research_compare_drift_mode", "warn") or "warn").strip(),
        "research_compare_thresholds": {
            "max_phase2_candidate_count_delta_abs": float(getattr(args, "research_compare_max_phase2_candidate_count_delta_abs", 10.0)),
            "max_phase2_survivor_count_delta_abs": float(getattr(args, "research_compare_max_phase2_survivor_count_delta_abs", 2.0)),
            "max_phase2_zero_eval_rows_increase": float(getattr(args, "research_compare_max_phase2_zero_eval_rows_increase", 0.0)),
            "max_phase2_survivor_q_value_increase": float(getattr(args, "research_compare_max_phase2_survivor_q_value_increase", 0.05)),
            "max_phase2_survivor_estimate_bps_drop": float(getattr(args, "research_compare_max_phase2_survivor_estimate_bps_drop", 3.0)),
            "max_promotion_promoted_count_delta_abs": float(getattr(args, "research_compare_max_promotion_promoted_count_delta_abs", 2.0)),
            "max_reject_reason_shift_abs": float(getattr(args, "research_compare_max_reject_reason_shift_abs", 3.0)),
            "max_edge_tradable_count_delta_abs": float(getattr(args, "research_compare_max_edge_tradable_count_delta_abs", 2.0)),
            "max_edge_candidate_count_delta_abs": float(getattr(args, "research_compare_max_edge_candidate_count_delta_abs", 2.0)),
            "max_edge_after_cost_positive_validation_count_delta_abs": float(getattr(args, "research_compare_max_edge_after_cost_positive_validation_count_delta_abs", 2.0)),
            "max_edge_median_resolved_cost_bps_delta_abs": float(getattr(args, "research_compare_max_edge_median_resolved_cost_bps_delta_abs", 0.25)),
            "max_edge_median_expectancy_bps_delta_abs": float(getattr(args, "research_compare_max_edge_median_expectancy_bps_delta_abs", 0.25)),
        },
        "normalized_timeframes_csv": args.timeframes,
        "start": args.start,
        "end": args.end,
    }
