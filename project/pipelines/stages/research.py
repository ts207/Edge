import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Mapping, Tuple

from project.events.config import ComposedEventConfig, compose_event_config
from project.pipelines.stages.utils import script_supports_flag
from project.pipelines.research.registry_validation import (
    validate_agent_selections,
    filter_event_chain,
)
from project.pipelines.research.experiment_engine import build_experiment_plan

_LOG = logging.getLogger(__name__)

_LEGACY_PROMOTION_DEFAULTS = {
    "max_q_value": 0.20,
    "min_events": 20,
    "min_stability_score": 0.60,
    "min_sign_consistency": 0.60,
    "min_cost_survival_ratio": 0.50,
    "min_tob_coverage": 0.60,
    "max_negative_control_pass_rate": 0.10,
}

_PROFILE_PROMOTION_DEFAULTS = {
    "research": {
        "max_q_value": 0.15,
        "min_events": 50,
        "min_stability_score": 0.50,
        "min_sign_consistency": 0.55,
        "min_cost_survival_ratio": 0.50,
        "min_tob_coverage": 0.50,
        "max_negative_control_pass_rate": 0.10,
    },
    "deploy": {
        "max_q_value": 0.10,
        "min_events": 100,
        "min_stability_score": 0.60,
        "min_sign_consistency": 0.67,
        "min_cost_survival_ratio": 0.75,
        "min_tob_coverage": 0.60,
        "max_negative_control_pass_rate": 0.01,
    },
}

def _upsert_cli_flag(base_args: List[str], flag: str, value: str) -> None:
    try:
        idx = base_args.index(flag)
    except ValueError:
        base_args.extend([flag, value])
        return
    if idx + 1 < len(base_args):
        base_args[idx + 1] = value
    else:
        base_args.append(value)

def _to_cli_value(value: Any) -> str:
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (list, tuple, set)):
        return ",".join(str(v) for v in value)
    if isinstance(value, dict):
        return json.dumps(value, sort_keys=True)
    return str(value)

def _event_runtime_overrides(args: Any, event_type: str) -> Mapping[str, Any]:
    mapping = getattr(args, "event_parameter_overrides", None)
    if not isinstance(mapping, dict):
        return {}
    payload = mapping.get(str(event_type).strip().upper(), {})
    return payload if isinstance(payload, dict) else {}


def _resolve_candidate_promotion_profile(args: Any) -> str:
    configured = str(getattr(args, "candidate_promotion_profile", "auto")).strip().lower()
    if configured in {"research", "deploy"}:
        return configured
    mode = str(getattr(args, "mode", "research")).strip().lower()
    return "deploy" if mode in {"production", "certification"} else "research"


def _resolve_candidate_promotion_thresholds(args: Any) -> Dict[str, float]:
    profile = _resolve_candidate_promotion_profile(args)
    profile_defaults = _PROFILE_PROMOTION_DEFAULTS[profile]

    resolved = {
        "max_q_value": float(
            getattr(args, "candidate_promotion_max_q_value", _LEGACY_PROMOTION_DEFAULTS["max_q_value"])
            if getattr(args, "candidate_promotion_max_q_value", None) is not None
            else profile_defaults["max_q_value"]
        ),
        "min_events": int(getattr(args, "candidate_promotion_min_events", _LEGACY_PROMOTION_DEFAULTS["min_events"])),
        "min_stability_score": float(
            getattr(args, "candidate_promotion_min_stability_score", _LEGACY_PROMOTION_DEFAULTS["min_stability_score"])
        ),
        "min_sign_consistency": float(
            getattr(args, "candidate_promotion_min_sign_consistency", _LEGACY_PROMOTION_DEFAULTS["min_sign_consistency"])
        ),
        "min_cost_survival_ratio": float(
            getattr(args, "candidate_promotion_min_cost_survival_ratio", _LEGACY_PROMOTION_DEFAULTS["min_cost_survival_ratio"])
        ),
        "min_tob_coverage": float(
            getattr(args, "candidate_promotion_min_tob_coverage", _LEGACY_PROMOTION_DEFAULTS["min_tob_coverage"])
        ),
        "max_negative_control_pass_rate": float(
            getattr(
                args,
                "candidate_promotion_max_negative_control_pass_rate",
                _LEGACY_PROMOTION_DEFAULTS["max_negative_control_pass_rate"],
            )
        ),
    }

    for key, legacy_default in _LEGACY_PROMOTION_DEFAULTS.items():
        if key == "max_q_value":
            continue
        current_value = resolved[key]
        if current_value == legacy_default:
            replacement = profile_defaults[key]
            resolved[key] = int(replacement) if isinstance(legacy_default, int) else float(replacement)
    return resolved

def _apply_event_parameters_to_phase1_args(
    *,
    phase1_args: List[str],
    phase1_script: Path,
    event_type: str,
    args: Any,
) -> ComposedEventConfig:
    cfg = compose_event_config(
        event_type=event_type,
        runtime_overrides=_event_runtime_overrides(args, event_type),
    )
    for key, value in cfg.parameters.items():
        if value is None:
            continue
        flag = f"--{key}"
        if not script_supports_flag(phase1_script, flag):
            continue
        _upsert_cli_flag(phase1_args, flag, _to_cli_value(value))
    return cfg

def build_research_stages(
    args,
    run_id: str,
    symbols: str,
    start: str,
    end: str,
    research_gate_profile: str,
    project_root: Path,
    data_root: Path,
    phase2_event_chain: List[Tuple[str, str, List[str]]],
) -> List[Tuple[str, Path, List[str]]]:
    # 1. Check for Experiment Config (New Two-Layer Model)
    experiment_plan = None
    if getattr(args, "experiment_config", None):
        registry_root = Path(getattr(args, "registry_root", "project/configs/registries"))
        # We need the program_id to build the out_dir, but we don't have it until we parse the config.
        # We can read the config manually or just let build_experiment_plan handle it.
        # Let's peek at the config just for the program_id.
        import yaml
        with open(args.experiment_config, "r") as f:
            cfg = yaml.safe_load(f)
            prog_id = cfg.get("program_id", "unknown_program")
            
        out_dir = data_root / "artifacts" / "experiments" / prog_id / run_id
        experiment_plan = build_experiment_plan(Path(args.experiment_config), registry_root, out_dir=out_dir)
        _LOG.info(f"Loaded experiment plan for program: {experiment_plan.program_id} with {experiment_plan.estimated_hypothesis_count} hypotheses.")
    active_program_id = (
        str(experiment_plan.program_id).strip()
        if experiment_plan is not None
        else str(getattr(args, "program_id", "") or "").strip()
    )

    # Validate agent selections (legacy fallback)
    if experiment_plan:
        agent_selections = {"events": None, "templates": None, "horizons": None}
    else:
        agent_selections = validate_agent_selections(
            events=getattr(args, "events", None),
            templates=getattr(args, "templates", None),
            horizons=getattr(args, "horizons", None),
        )

    stages: List[Tuple[str, Path, List[str]]] = []
    gate_profile_raw = str(
        getattr(args, "phase2_gate_profile_resolved", getattr(args, "phase2_gate_profile", "auto"))
    ).strip().lower()
    gate_profile = research_gate_profile if gate_profile_raw == "auto" else gate_profile_raw

    timeframes_str = getattr(args, "timeframes", "5m")
    timeframes = [tf.strip() for tf in timeframes_str.split(",") if tf.strip()]
    if not timeframes:
        timeframes = ["5m"]
    primary_timeframe = timeframes[0]
        
    concept_file = str(getattr(args, "concept", "")).strip()
    discovery_mode = "search"

    if int(args.run_phase2_conditional):
        selected_chain = phase2_event_chain
        
        if experiment_plan:
            # Filter chain by events required by ANY hypothesis trigger
            required_event_ids = set()
            for h in experiment_plan.hypotheses:
                t = h.trigger
                if t.trigger_type == "event" and t.event_id:
                    required_event_ids.add(t.event_id)
                elif t.trigger_type == "sequence" and t.events:
                    required_event_ids.update(t.events)
                elif t.trigger_type == "interaction":
                    if t.left: required_event_ids.add(t.left)
                    if t.right: required_event_ids.add(t.right)
                elif t.trigger_type in ["state", "transition", "feature_predicate"]:
                    # These can be evaluated at ANY event timestamp. 
                    # If the experiment has ONLY these, we might need a default event trigger.
                    # For now, we assume they accompany some event-based chain or use all.
                    pass
            
            if not required_event_ids:
                # If no explicit events, we fallback to the whole chain to allow regime/state evaluation
                selected_chain = phase2_event_chain
            else:
                selected_chain = [x for x in phase2_event_chain if x[0] in required_event_ids]
        elif concept_file:
            import yaml
            with open(concept_file, "r") as f:
                concept_spec = yaml.safe_load(f)
            c_event_type = concept_spec.get("event_definition", {}).get("event_type", "DYNAMIC_EVENT")
            
            # Replace the standard chain with the dynamic concept chain
            selected_chain = [
                (c_event_type, "analyze_dynamic_events.py", ["--concept_file", concept_file])
            ]
            
        elif agent_selections["events"]:
            selected_chain = filter_event_chain(phase2_event_chain, agent_selections["events"])
        elif args.phase2_event_type != "all":
            selected_chain = [x for x in phase2_event_chain if x[0] == args.phase2_event_type]

        for event_type, script_name, extra_args in selected_chain:
            for tf in timeframes:
                phase1_script = project_root / "pipelines" / "research" / script_name
                phase1_args = [
                    "--run_id", run_id,
                    "--symbols", symbols,
                    "--event_type", event_type,
                    "--timeframe", tf,
                ]
                if extra_args:
                    phase1_args.extend(extra_args)
                    
                if script_supports_flag(phase1_script, "--seed"):
                    phase1_args.extend(["--seed", str(int(args.seed))])

                composed_cfg = _apply_event_parameters_to_phase1_args(
                    phase1_args=phase1_args,
                    phase1_script=phase1_script,
                    event_type=event_type,
                    args=args,
                )
                stages.append((f"analyze_events__{event_type}_{tf}", phase1_script, phase1_args))

                registry_stage_name = f"build_event_registry__{event_type}_{tf}"
                stages.append(
                    (
                        registry_stage_name,
                        project_root / "pipelines" / "research" / "build_event_registry.py",
                        [
                            "--run_id", run_id,
                            "--symbols", symbols,
                            "--event_type", event_type,
                            "--timeframe", tf,
                        ],
                    )
                )

                canonical_stage_name = f"canonicalize_event_episodes__{event_type}_{tf}"
                stages.append(
                    (
                        canonical_stage_name,
                        project_root / "pipelines" / "research" / "canonicalize_event_episodes.py",
                        [
                            "--run_id", run_id,
                            "--timeframe", tf,
                            "--event_type", event_type,
                            "--merge_gap_bars", str(int(composed_cfg.parameters.get("merge_gap_bars", 1))),
                            "--cooldown_bars", str(int(composed_cfg.parameters.get("cooldown_bars", 0))),
                            "--anchor_rule", str(composed_cfg.parameters.get("anchor_rule", "max_intensity")),
                            "--min_occurrences", str(int(composed_cfg.parameters.get("min_occurrences", 0))),
                        ],
                    )
                )

        stages.append(
            (
                "phase1_correlation_clustering",
                project_root / "pipelines" / "research" / "phase1_correlation_clustering.py",
                [
                    "--run_id", run_id,
                    "--symbols", symbols,
                    "--correlation_threshold", "0.85",
                ],
            )
        )

        for event_type, _, _ in selected_chain:
            for tf in timeframes:
                phase2_stage_name = f"phase2_conditional_hypotheses__{event_type}_{tf}"
                phase2_args = [
                    "--run_id", run_id,
                    "--event_type", event_type,
                    "--symbols", symbols,
                    "--timeframe", tf,
                    "--shift_labels_k", str(int(args.phase2_shift_labels_k)),
                    "--mode", str(args.mode),
                    "--gate_profile", gate_profile,
                    "--cost_calibration_mode", str(args.phase2_cost_calibration_mode),
                    "--cost_min_tob_coverage", str(float(args.phase2_cost_min_tob_coverage)),
                    "--cost_tob_tolerance_minutes", str(int(args.phase2_cost_tob_tolerance_minutes)),
                    "--retail_profile", str(args.retail_profile),
                ]
                if getattr(args, "phase2_min_validation_n_obs", None) is not None:
                    phase2_args.extend(["--min_validation_n_obs", str(int(args.phase2_min_validation_n_obs))])
                if getattr(args, "phase2_min_test_n_obs", None) is not None:
                    phase2_args.extend(["--min_test_n_obs", str(int(args.phase2_min_test_n_obs))])
                if getattr(args, "phase2_min_total_n_obs", None) is not None:
                    phase2_args.extend(["--min_total_n_obs", str(int(args.phase2_min_total_n_obs))])
                if concept_file:
                    phase2_args.extend(["--concept_file", concept_file])
                
                # Pass agent selections if present
                if experiment_plan:
                    phase2_args.extend(["--experiment_config", str(args.experiment_config)])
                    phase2_args.extend(["--program_id", experiment_plan.program_id])
                else:
                    if agent_selections["templates"]:
                        phase2_args.extend(["--templates"] + agent_selections["templates"])
                    if agent_selections["horizons"]:
                        phase2_args.extend(["--horizons"] + agent_selections["horizons"])
                    if getattr(args, "directions", None):
                        phase2_args.extend(["--directions"] + args.directions)
                    if getattr(args, "entry_lags", None):
                        phase2_args.extend(["--entry_lags"] + [str(l) for l in args.entry_lags])
                    if getattr(args, "program_id", None):
                        phase2_args.extend(["--program_id", str(args.program_id)])
                    if getattr(args, "search_budget", None):
                        phase2_args.extend(["--search_budget", str(args.search_budget)])

                stages.append(
                    (
                        phase2_stage_name,
                        project_root / "pipelines" / "research" / "phase2_candidate_discovery.py",
                        phase2_args,
                    )
                )



                if int(args.run_bridge_eval_phase2):
                    bridge_stage_name = f"bridge_evaluate_phase2__{event_type}_{tf}"
                    stages.append(
                        (
                            bridge_stage_name,
                            project_root / "pipelines" / "research" / "bridge_evaluate_phase2.py",
                            [
                                "--run_id", run_id,
                                "--event_type", event_type,
                                "--symbols", symbols,
                                "--timeframe", tf,
                                "--start", start,
                                "--end", end,
                                "--train_frac", str(float(args.bridge_train_frac)),
                                "--validation_frac", str(float(args.bridge_validation_frac)),
                                "--embargo_days", str(int(args.bridge_embargo_days)),
                                "--edge_cost_k", str(float(args.bridge_edge_cost_k)),
                                "--stressed_cost_multiplier", str(float(args.bridge_stressed_cost_multiplier)),
                                "--min_validation_trades", str(int(args.bridge_min_validation_trades)),
                                "--mode", str(args.mode),
                                "--candidate_mask", str(args.bridge_candidate_mask),
                                "--retail_profile", str(args.retail_profile),
                            ],
                        )
                    )


    if discovery_mode == "search" and int(args.run_phase2_conditional):
        search_args = [
            "--run_id", run_id,
            "--symbols", symbols,
            "--data_root", str(data_root),
            "--timeframe", primary_timeframe,
            "--discovery_profile", str(getattr(args, "discovery_profile", "standard")),
            "--gate_profile", str(getattr(args, "phase2_gate_profile", "auto")),
            "--search_spec", getattr(args, "search_spec", "spec/search_space.yaml"),
            "--min_n", str(int(getattr(args, "search_min_n", 30))),
            "--registry_root", str(getattr(args, "registry_root", "project/configs/registries")),
        ]
        if getattr(args, "search_budget", None):
            search_args.extend(["--search_budget", str(int(args.search_budget))])
        if experiment_plan:
            search_args.extend(["--experiment_config", str(args.experiment_config)])
            search_args.extend(["--program_id", experiment_plan.program_id])

        stages.append(
            (
                "phase2_search_engine",
                project_root / "pipelines" / "research" / "phase2_search_engine.py",
                search_args,
            )
        )

    if int(args.run_phase2_conditional) and int(args.run_discovery_quality_summary):
        stages.append(
            (
                "summarize_discovery_quality",
                project_root / "pipelines" / "research" / "summarize_discovery_quality.py",
                ["--run_id", run_id],
            )
        )

    if not experiment_plan:
        if int(args.run_naive_entry_eval) and int(args.run_phase2_conditional):
            stages.append(
                (
                    "evaluate_naive_entry",
                    project_root / "pipelines" / "research" / "evaluate_naive_entry.py",
                    [
                        "--run_id", run_id,
                        "--symbols", symbols,
                        "--min_trades", str(int(args.naive_min_trades)),
                        "--min_expectancy_after_cost", str(float(args.naive_min_expectancy_after_cost)),
                        "--max_drawdown", str(float(args.naive_max_drawdown)),
                        "--retail_profile", str(args.retail_profile),
                    ],
                )
            )

    if int(args.run_phase2_conditional) and (
        int(getattr(args, "run_edge_candidate_universe", 0))
        or int(args.run_candidate_promotion)
        or (int(getattr(args, "run_campaign_memory_update", 0)) and bool(active_program_id))
    ):
        stages.append(
            (
                "export_edge_candidates",
                project_root / "pipelines" / "research" / "export_edge_candidates.py",
                [
                    "--run_id", run_id,
                    "--symbols", symbols,
                ],
            )
        )

    if not experiment_plan:
        if int(args.run_candidate_promotion) and int(args.run_phase2_conditional):
            promotion_profile = _resolve_candidate_promotion_profile(args)
            promotion_thresholds = _resolve_candidate_promotion_thresholds(args)
            promote_args = [
                "--run_id", run_id,
                "--retail_profile", str(args.retail_profile),
                "--promotion_profile", promotion_profile,
            ]
            promote_args.extend(["--max_q_value", str(float(promotion_thresholds["max_q_value"]))])
            
            promote_args.extend([
                "--min_events", str(int(promotion_thresholds["min_events"])),
                "--min_stability_score", str(float(promotion_thresholds["min_stability_score"])),
                "--min_sign_consistency", str(float(promotion_thresholds["min_sign_consistency"])),
                "--min_cost_survival_ratio", str(float(promotion_thresholds["min_cost_survival_ratio"])),
                "--min_tob_coverage", str(float(promotion_thresholds["min_tob_coverage"])),
                "--max_negative_control_pass_rate", str(float(promotion_thresholds["max_negative_control_pass_rate"])),
                "--require_hypothesis_audit", str(int(args.candidate_promotion_require_hypothesis_audit)),
                "--allow_missing_negative_controls", str(int(args.candidate_promotion_allow_missing_negative_controls)),
            ])
            
            stages.append(
                (
                    "promote_candidates",
                    project_root / "pipelines" / "research" / "promote_candidates.py",
                    promote_args,
                )
            )

        if int(args.run_edge_registry_update) and int(args.run_candidate_promotion) and int(args.run_phase2_conditional):
            registry_args = ["--run_id", run_id]
            if script_supports_flag(project_root / "pipelines" / "research" / "update_edge_registry.py", "--retail_profile"):
                registry_args.extend(["--retail_profile", str(args.retail_profile)])

            stages.append(
                (
                    "update_edge_registry",
                    project_root / "pipelines" / "research" / "update_edge_registry.py",
                    registry_args,
                )
            )

    if (
        int(getattr(args, "run_campaign_memory_update", 0))
        and int(args.run_phase2_conditional)
        and bool(active_program_id)
    ):
        stages.append(
            (
                "update_campaign_memory",
                project_root / "pipelines" / "research" / "update_campaign_memory.py",
                [
                    "--run_id", run_id,
                    "--program_id", active_program_id,
                    "--data_root", str(data_root),
                    "--registry_root", str(getattr(args, "registry_root", "project/configs/registries")),
                    "--promising_top_k", str(int(getattr(args, "campaign_memory_promising_top_k", 5))),
                    "--avoid_top_k", str(int(getattr(args, "campaign_memory_avoid_top_k", 5))),
                    "--repair_top_k", str(int(getattr(args, "campaign_memory_repair_top_k", 5))),
                    "--exploit_top_k", str(int(getattr(args, "campaign_memory_exploit_top_k", 3))),
                    "--frontier_untested_top_k", str(int(getattr(args, "campaign_memory_frontier_untested_top_k", 3))),
                    "--frontier_repair_top_k", str(int(getattr(args, "campaign_memory_frontier_repair_top_k", 2))),
                    "--exhausted_failure_threshold", str(int(getattr(args, "campaign_memory_exhausted_failure_threshold", 3))),
                ],
            )
        )

    if int(args.run_expectancy_analysis):
        expectancy_script = project_root / "pipelines" / "research" / "analyze_conditional_expectancy.py"
        expectancy_args = ["--run_id", run_id, "--symbols", symbols]
        if script_supports_flag(expectancy_script, "--retail_profile"):
            expectancy_args.extend(["--retail_profile", str(args.retail_profile)])
            
        if expectancy_script.exists():
            stages.append(
                (
                    "analyze_conditional_expectancy",
                    expectancy_script,
                    expectancy_args,
                )
            )

        if int(args.run_expectancy_robustness):
            stages.append(
                (
                    "validate_expectancy_traps",
                    project_root / "pipelines" / "research" / "validate_expectancy_traps.py",
                    [
                        "--run_id", run_id,
                        "--symbols", symbols,
                        "--gate_profile", gate_profile,
                        "--retail_profile", str(args.retail_profile),
                    ],
                )
            )

        if int(args.run_recommendations_checklist):
            stages.append(
                (
                    "generate_recommendations_checklist",
                    project_root / "pipelines" / "research" / "generate_recommendations_checklist.py",
                    [
                        "--run_id", run_id, 
                        "--gate_profile", gate_profile,
                        "--retail_profile", str(args.retail_profile),
                    ],
                )
            )

        if int(args.run_interaction_lift):
            stages.append(
                (
                    "analyze_interaction_lift",
                    project_root / "pipelines" / "research" / "analyze_interaction_lift.py",
                    ["--run_id", run_id],
                )
            )



    # The event-conditioned discovery stage is already added in the loop above.
    # If discovery_mode == 'search', we might want to prune it, but for safety in this 
    # incremental PR we keep it and just focus on wiring the new ones.
    # The Retirement Criterion (Option B) says we run both and compare first.

    if experiment_plan:
        discovery_stages = [s[0] for s in stages if s[0].startswith("phase2_conditional_hypotheses__")]
        if discovery_mode == "search":
             discovery_stages.append("phase2_search_engine")
             
        # finalize_experiment must run AFTER all discovery stages
        # The pipeline planner will handle the dependency if we add it to the name or something?
        # Actually, the planner uses _resolve_dependencies which looks for patterns.
        # But finalized_experiment doesn't follow a standard pattern yet.
        
        # I'll just name it so it matches a dependency pattern if one exists,
        # or I'll change the planner to support explicit dependencies.
        
        # Wait, the planner uses _resolve_dependencies(name, all_stage_names).
        # Let's check that.
        
        stages.append(
            (
                "finalize_experiment",
                project_root / "pipelines" / "research" / "finalize_experiment.py",
                [
                    "--run_id", run_id,
                    "--program_id", experiment_plan.program_id,
                    "--data_root", str(data_root),
                ],
            )
        )

    return stages
