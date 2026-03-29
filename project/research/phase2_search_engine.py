"""
Phase 2 Search Engine Stage.

Generates hypotheses from spec/search_space.yaml, evaluates them against the
wide feature table, and writes bridge-compatible candidates to the output directory.

This is the authoritative phase-2 discovery stage for new runs.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Optional

import pandas as pd
import yaml

from project import PROJECT_ROOT
from project.domain.compiled_registry import get_domain_registry
from project.spec_registry import load_yaml_path
from project.specs.gates import load_gates_spec, select_bridge_gate_spec, select_phase2_gate_spec
from project.research.search.profile import resolve_search_profile
from project.research.search.generator import generate_hypotheses_with_audit
from project.research.search.evaluator import (
    evaluate_hypothesis_batch,
    evaluated_records_from_metrics,
)
from project.research.search.bridge_adapter import (
    hypotheses_to_bridge_candidates,
    split_bridge_candidates,
)
from project.io.utils import ensure_dir, write_parquet
from project.research.search.distributed_runner import run_distributed_search
from project.research._family_event_utils import load_features as load_features
from project.research.search.search_feature_utils import (
    normalize_search_feature_columns,
    prepare_search_features_for_symbol,
)
from project.research.services.phase2_diagnostics import build_search_engine_diagnostics
from project.research.services.reporting_service import write_json_report
from project.research.services.pathing import (
    phase2_candidates_path,
    phase2_diagnostics_path,
    phase2_hypotheses_dir,
    phase2_run_dir,
)
from project.research.regime_routing import annotate_regime_metadata
from project.spec_validation.search import validate_search_spec_doc

log = logging.getLogger(__name__)

_DEFAULT_BROAD_SEARCH_SPECS = {
    "",
    "full",
    "search_space.yaml",
    "spec/search_space.yaml",
}


def _is_default_broad_search_spec(search_spec: str) -> bool:
    return str(search_spec or "").strip() in _DEFAULT_BROAD_SEARCH_SPECS


def _load_search_spec_doc(search_spec: str) -> dict:
    raw = str(search_spec or "").strip()
    if raw.endswith((".yaml", ".yml")):
        path = Path(raw)
        if not path.is_absolute():
            path = PROJECT_ROOT.parent / path
        doc = load_yaml_path(path)
    else:
        from project.spec_validation import loaders

        doc = loaders.load_search_spec(raw)
    if not isinstance(doc, dict):
        raise ValueError(f"Search spec must resolve to a mapping: {search_spec}")
    validate_search_spec_doc(doc, source=str(search_spec))
    return dict(doc)


def _write_event_scoped_search_spec(
    *,
    search_spec: str,
    phase2_event_type: str,
    out_dir: Path,
) -> str:
    event_type = str(phase2_event_type or "").strip().upper()
    if not event_type or event_type == "ALL" or not _is_default_broad_search_spec(search_spec):
        return str(search_spec)

    base_doc = _load_search_spec_doc(search_spec)
    narrowed = dict(base_doc)
    registry = get_domain_registry()
    event_row = registry.event_row(event_type)
    metadata = dict(narrowed.get("metadata") or {})
    metadata["auto_scope"] = f"event:{event_type}"
    metadata["auto_scope_source"] = "phase2_event_type"
    narrowed["metadata"] = metadata
    narrowed["events"] = [event_type]
    event_templates = event_row.get("templates", [])
    if isinstance(event_templates, (list, tuple)) and event_templates:
        narrowed["templates"] = [str(item) for item in event_templates if str(item).strip()]
    event_horizons = event_row.get("horizons", [])
    if isinstance(event_horizons, (list, tuple)) and event_horizons:
        narrowed["horizons"] = [str(item) for item in event_horizons if str(item).strip()]
    if "max_candidates_per_run" in event_row:
        narrowed["max_candidates_per_run"] = int(event_row["max_candidates_per_run"])
    narrowed.pop("states", None)
    narrowed.pop("transitions", None)
    narrowed.pop("feature_predicates", None)
    narrowed["include_sequences"] = False
    narrowed["include_interactions"] = False
    triggers = dict(narrowed.get("triggers") or {})
    triggers["events"] = [event_type]
    triggers.pop("states", None)
    triggers.pop("transitions", None)
    triggers.pop("feature_predicates", None)
    narrowed["triggers"] = triggers

    ensure_dir(out_dir)
    resolved_spec_path = out_dir / f"resolved_search_spec__{event_type}.yaml"
    resolved_spec_path.write_text(
        yaml.safe_dump(narrowed, sort_keys=False),
        encoding="utf-8",
    )
    return str(resolved_spec_path)


def _normalize_audit_frame(rows: list[dict]) -> pd.DataFrame:
    frame = pd.DataFrame(rows or [])
    if frame.empty:
        return frame
    for column in frame.columns:
        if frame[column].dtype != "object":
            continue
        sample = next(
            (
                value
                for value in frame[column]
                if value is not None and not (isinstance(value, float) and pd.isna(value))
            ),
            None,
        )
        if isinstance(sample, (dict, list, tuple)):
            frame[column] = frame[column].map(
                lambda value: (
                    json.dumps(value, sort_keys=True)
                    if isinstance(value, (dict, list, tuple))
                    else value
                )
            )
    return frame


def _annotate_candidate_regime_metadata(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty or "event_type" not in frame.columns:
        return frame
    return annotate_regime_metadata(frame)


# Phase 4.2 — regime-conditional candidate discovery signal columns
_REGIME_CANDIDATE_COLUMNS = [
    "event_type",
    "template_id",
    "direction",
    "horizon",
    "trigger_key",
    "t_stat",
    "mean_return_bps",
    "robustness_score",
    "context_json",
]


def _write_regime_conditional_candidates(
    final_df: pd.DataFrame,
    out_dir: Path,
    *,
    weak_t_stat_upper: float = 1.5,
    min_t_stat_lower: float = 0.5,
    min_mean_return_bps: float = 0.0,
    top_k: int = 20,
) -> None:
    """Phase 4.2 — Write regime_conditional_candidates.parquet.

    Identifies hypotheses that were weak overall (t_stat < weak_t_stat_upper)
    but had positive mean_return_bps, indicating potential regime-specific alpha.
    These are surfaced as an explore_adjacent discovery signal so the campaign
    controller can propose targeted context-conditioned follow-up runs.

    The file is written to ``out_dir/regime_conditional_candidates.parquet``.
    If no qualifying candidates exist an empty schema file is written so
    downstream readers can always expect the artefact.
    """
    rcc_path = out_dir / "regime_conditional_candidates.parquet"

    empty = pd.DataFrame(columns=_REGIME_CANDIDATE_COLUMNS)

    if final_df is None or final_df.empty:
        write_parquet(empty, rcc_path)
        return

    t_col = "t_stat" if "t_stat" in final_df.columns else None
    ret_col = "mean_return_bps" if "mean_return_bps" in final_df.columns else None

    if t_col is None or ret_col is None:
        write_parquet(empty, rcc_path)
        return

    t_num = pd.to_numeric(final_df[t_col], errors="coerce").fillna(0.0)
    ret_num = pd.to_numeric(final_df[ret_col], errors="coerce").fillna(0.0)

    mask = (
        (t_num >= min_t_stat_lower)
        & (t_num < weak_t_stat_upper)
        & (ret_num > min_mean_return_bps)
    )
    weak_positive = final_df[mask].copy()

    if weak_positive.empty:
        write_parquet(empty, rcc_path)
        return

    # Sort by mean_return_bps descending — highest-signal near-misses first
    weak_positive = weak_positive.sort_values(ret_col, ascending=False).head(top_k)

    # Emit only the columns we need; fill missing with empty string / NaN
    out_rows = []
    for _, row in weak_positive.iterrows():
        # Extract event_type from trigger_key ("event:EVTNAME" → "EVTNAME")
        tkey = str(row.get("trigger_key", ""))
        if tkey.startswith("event:"):
            event_type = tkey[len("event:"):]
        elif tkey.startswith("state:"):
            event_type = tkey[len("state:"):]
        else:
            event_type = tkey

        out_rows.append({
            "event_type": event_type,
            "template_id": str(row.get("template_id", "")),
            "direction": str(row.get("direction", "")),
            "horizon": str(row.get("horizon", "")),
            "trigger_key": tkey,
            "t_stat": float(row.get(t_col, 0.0)),
            "mean_return_bps": float(row.get(ret_col, 0.0)),
            "robustness_score": float(row.get("robustness_score", 0.0)),
            "context_json": str(row.get("context_json", "") or ""),
        })

    rcc_df = pd.DataFrame(out_rows, columns=_REGIME_CANDIDATE_COLUMNS)
    write_parquet(rcc_df, rcc_path)
    log.info(
        "Phase 4.2: wrote %d regime_conditional_candidates to %s",
        len(rcc_df), rcc_path,
    )


def _write_hypothesis_audit_artifacts(out_dir: Path, symbol: str, audit: dict) -> None:
    audit_dir = out_dir / str(symbol).upper()
    ensure_dir(audit_dir)
    write_parquet(
        _normalize_audit_frame(audit.get("generated_rows", [])),
        audit_dir / "generated_hypotheses.parquet",
    )
    write_parquet(
        _normalize_audit_frame(audit.get("rejected_rows", [])),
        audit_dir / "rejected_hypotheses.parquet",
    )
    write_parquet(
        _normalize_audit_frame(audit.get("feasible_rows", [])),
        audit_dir / "feasible_hypotheses.parquet",
    )


def _write_evaluation_artifacts(
    out_dir: Path, symbol: str, metrics: pd.DataFrame, gate_failures: pd.DataFrame
) -> None:
    audit_dir = out_dir / "hypotheses" / str(symbol).upper()
    ensure_dir(audit_dir)
    write_parquet(
        evaluated_records_from_metrics(metrics), audit_dir / "evaluated_hypotheses.parquet"
    )
    write_parquet(gate_failures, audit_dir / "gate_failures.parquet")


def _normalize_search_feature_columns(features: pd.DataFrame) -> pd.DataFrame:
    return normalize_search_feature_columns(features)


def run(
    run_id: str,
    symbols: str,
    data_root: Path,
    out_dir: Path,
    *,
    timeframe: str = "5m",
    discovery_profile: str = "standard",
    gate_profile: str = "auto",
    search_spec: str = "full",
    chunk_size: int = 500,
    min_t_stat: float = 1.5,
    min_n: int = 30,
    search_budget: Optional[int] = None,
    experiment_config: Optional[str] = None,
    registry_root: str | Path = "project/configs/registries",
    use_context_quality: bool = True,
    phase2_event_type: str = "",
) -> int:
    """
    Core logic. Returns exit code (0=success, 1=failure).
    Separated from main() for testability.
    """
    log.info(
        "Starting Phase 2 Search Engine (run_id=%s, search_spec=%s, experiment_config=%s)",
        run_id,
        search_spec,
        experiment_config,
    )
    ensure_dir(out_dir)
    output_path = phase2_candidates_path(data_root=data_root, run_id=run_id)
    diagnostics_path = phase2_diagnostics_path(data_root=data_root, run_id=run_id)
    symbols_requested = [s.strip().upper() for s in str(symbols).split(",") if s.strip()]
    timeframe = str(timeframe or "5m").strip().lower() or "5m"
    search_profile = resolve_search_profile(
        discovery_profile=discovery_profile,
        search_spec=search_spec,
        min_n=min_n,
        min_t_stat=min_t_stat,
    )
    resolved_search_spec = _write_event_scoped_search_spec(
        search_spec=str(search_profile["search_spec"]),
        phase2_event_type=phase2_event_type,
        out_dir=out_dir,
    )
    resolved_min_n = int(search_profile["min_n"])
    resolved_min_t_stat = float(search_profile["min_t_stat"])
    phase2_gates = select_phase2_gate_spec(
        load_gates_spec(PROJECT_ROOT.parent),
        mode="research",
        gate_profile=str(gate_profile or "auto"),
    )
    bridge_gates = select_bridge_gate_spec(load_gates_spec(PROJECT_ROOT.parent))
    multiplicity_max_q = float(phase2_gates.get("max_q_value", 0.05))

    # 1. Load data and evaluate symbols
    all_candidates = []
    symbol_diagnostics = []

    total_feature_rows = 0
    total_event_flag_rows = 0
    total_hypotheses_generated = 0
    total_feasible_hypotheses = 0
    total_rejected_hypotheses = 0
    total_metrics_rows = 0
    total_valid_metrics_rows = 0
    total_rejected_invalid_metrics = 0
    total_rejected_by_min_n = 0
    total_rejected_by_min_t_stat = 0
    total_bridge_candidates_rows = 0
    aggregated_rejection_reasons: dict[str, int] = {}

    max_feature_columns = 0
    max_event_flag_columns_merged = 0

    # Load experiment plan if provided
    experiment_plan = None
    if experiment_config:
        from project.research.experiment_engine import build_experiment_plan

        experiment_plan = build_experiment_plan(Path(experiment_config), Path(registry_root))
        log.info("Loaded experiment plan with %d hypotheses", len(experiment_plan.hypotheses))

    for symbol in symbols_requested:
        log.info("Processing symbol %s...", symbol)

        # 1a. Load and prepare search feature frame
        features = prepare_search_features_for_symbol(
            run_id=run_id,
            symbol=symbol,
            timeframe=timeframe,
            data_root=data_root,
            load_features_fn=load_features,
        )
        if features.empty:
            log.warning("Empty feature table for %s", symbol)
            continue

        log.info(
            "Loaded features for %s: %d rows, %d columns",
            symbol,
            len(features),
            len(features.columns),
        )
        max_feature_columns = max(max_feature_columns, int(len(features.columns)))
        sym_flags = features[
            [c for c in features.columns if c.endswith(("_event", "_active", "_signal"))]
        ].copy()
        if not sym_flags.empty:
            max_event_flag_columns_merged = max(
                max_event_flag_columns_merged, int(len(sym_flags.columns))
            )

        total_feature_rows += int(len(features))
        total_event_flag_rows += int(len(features)) if not sym_flags.empty else 0

        # 2. Generate hypotheses
        if experiment_plan:
            hypotheses = experiment_plan.hypotheses
            generation_audit = {"counts": {"feasible": len(hypotheses)}}
            log.info("Using %d hypotheses from experiment plan for %s", len(hypotheses), symbol)
        else:
            log.info("Generating hypotheses from spec for %s: %s", symbol, resolved_search_spec)
            hypotheses, generation_audit = generate_hypotheses_with_audit(
                resolved_search_spec,
                max_hypotheses=int(search_budget) if search_budget is not None else None,
                features=features,
            )
            _write_hypothesis_audit_artifacts(
                phase2_hypotheses_dir(data_root=data_root, run_id=run_id),
                symbol,
                generation_audit,
            )
            log.info("Generated %d hypotheses for %s", len(hypotheses), symbol)

        total_hypotheses_generated += int(len(hypotheses))
        total_feasible_hypotheses += int(
            generation_audit.get("counts", {}).get("feasible", len(hypotheses))
        )
        total_rejected_hypotheses += int(generation_audit.get("counts", {}).get("rejected", 0))
        for reason, count in dict(generation_audit.get("rejection_reason_counts", {})).items():
            aggregated_rejection_reasons[str(reason)] = aggregated_rejection_reasons.get(
                str(reason), 0
            ) + int(count)

        if not hypotheses:
            log.warning("No hypotheses generated for %s", symbol)
            _write_evaluation_artifacts(out_dir, symbol, pd.DataFrame(), pd.DataFrame())
            symbol_diagnostics.append(
                build_search_engine_diagnostics(
                    run_id=run_id,
                    discovery_profile=str(search_profile["discovery_profile"]),
                    search_spec=resolved_search_spec,
                    timeframe=timeframe,
                    symbols_requested=symbols_requested,
                    primary_symbol=symbol,
                    feature_rows=int(len(features)),
                    feature_columns=int(len(features.columns)),
                    event_flag_rows=int(len(sym_flags)),
                    event_flag_columns_merged=max(0, int(len(sym_flags.columns) - 2)),
                    hypotheses_generated=0,
                    feasible_hypotheses=0,
                    rejected_hypotheses=int(generation_audit.get("counts", {}).get("rejected", 0)),
                    rejection_reason_counts=dict(
                        generation_audit.get("rejection_reason_counts", {})
                    ),
                    metrics_rows=0,
                    valid_metrics_rows=0,
                    rejected_invalid_metrics=0,
                    rejected_by_min_n=0,
                    rejected_by_min_t_stat=0,
                    bridge_candidates_rows=0,
                    multiplicity_discoveries=0,
                    min_t_stat=resolved_min_t_stat,
                    min_n=resolved_min_n,
                    search_budget=search_budget,
                    use_context_quality=use_context_quality,
                )
            )
            continue

        # 3. Evaluate in chunks
        log.info("Evaluating hypotheses batch for %s (chunk_size=%d)...", symbol, chunk_size)
        metrics = run_distributed_search(
            hypotheses,
            features,
            chunk_size=chunk_size,
            min_sample_size=resolved_min_n,
            use_context_quality=use_context_quality,
        )

        if metrics.empty:
            log.warning("No metrics returned for %s", symbol)
            _write_evaluation_artifacts(out_dir, symbol, pd.DataFrame(), pd.DataFrame())
            symbol_diagnostics.append(
                build_search_engine_diagnostics(
                    run_id=run_id,
                    discovery_profile=str(search_profile["discovery_profile"]),
                    search_spec=resolved_search_spec,
                    timeframe=timeframe,
                    symbols_requested=symbols_requested,
                    primary_symbol=symbol,
                    feature_rows=int(len(features)),
                    feature_columns=int(len(features.columns)),
                    event_flag_rows=int(len(sym_flags)),
                    event_flag_columns_merged=max(0, int(len(sym_flags.columns) - 2)),
                    hypotheses_generated=int(len(hypotheses)),
                    feasible_hypotheses=int(
                        generation_audit.get("counts", {}).get("feasible", len(hypotheses))
                    ),
                    rejected_hypotheses=int(generation_audit.get("counts", {}).get("rejected", 0)),
                    rejection_reason_counts=dict(
                        generation_audit.get("rejection_reason_counts", {})
                    ),
                    metrics_rows=0,
                    valid_metrics_rows=0,
                    rejected_invalid_metrics=0,
                    rejected_by_min_n=0,
                    rejected_by_min_t_stat=0,
                    bridge_candidates_rows=0,
                    multiplicity_discoveries=0,
                    min_t_stat=resolved_min_t_stat,
                    min_n=resolved_min_n,
                    search_budget=search_budget,
                    use_context_quality=use_context_quality,
                )
            )
            continue

        valid_mask = (
            metrics.get("valid", pd.Series(False, index=metrics.index)).fillna(False).astype(bool)
            if not metrics.empty
            else pd.Series(dtype=bool)
        )
        valid_metrics_rows = int(valid_mask.sum())
        rejected_invalid_metrics = max(0, int(len(metrics)) - valid_metrics_rows)
        rejected_by_min_n = int(
            (
                valid_mask
                & (
                    pd.to_numeric(metrics.get("n", 0), errors="coerce").fillna(0)
                    < int(resolved_min_n)
                )
            ).sum()
        )
        rejected_by_min_t_stat = int(
            (
                valid_mask
                & (
                    pd.to_numeric(metrics.get("n", 0), errors="coerce").fillna(0)
                    >= int(resolved_min_n)
                )
                & (
                    pd.to_numeric(metrics.get("t_stat", 0.0), errors="coerce").abs().fillna(0.0)
                    < float(resolved_min_t_stat)
                )
            ).sum()
        )

        # 4. Convert to bridge candidates
        candidates, gate_failures = split_bridge_candidates(
            metrics,
            min_t_stat=resolved_min_t_stat,
            min_n=resolved_min_n,
        )
        _write_evaluation_artifacts(out_dir, symbol, metrics, gate_failures)
        candidate_universe = hypotheses_to_bridge_candidates(
            metrics,
            symbol=symbol,
            min_t_stat=resolved_min_t_stat,
            min_n=resolved_min_n,
            bridge_min_t_stat=float(bridge_gates.get("search_bridge_min_t_stat", 2.0)),
            bridge_min_robustness_score=float(
                bridge_gates.get("search_bridge_min_robustness_score", 0.7)
            ),
            bridge_min_regime_stability_score=float(
                bridge_gates.get("search_bridge_min_regime_stability_score", 0.6)
            ),
            bridge_min_stress_survival=float(
                bridge_gates.get("search_bridge_min_stress_survival", 0.5)
            ),
            bridge_stress_cost_buffer_bps=float(
                bridge_gates.get("search_bridge_stress_cost_buffer_bps", 2.0)
            ),
            prefilter_min_n=True,
            prefilter_min_t_stat=False,
        )

        if (
            not candidate_universe.empty
            and "p_value" in candidate_universe.columns
            and "family_id" in candidate_universe.columns
        ):
            from project.research.multiplicity import apply_multiplicity_controls

            candidate_universe = apply_multiplicity_controls(
                candidate_universe,
                max_q=multiplicity_max_q,
                mode="research",
                min_sample_size=resolved_min_n,
            )

        if not candidate_universe.empty:
            candidates = candidate_universe[
                candidate_universe["gate_search_min_t_stat"].fillna(False).astype(bool)
            ].copy()
        else:
            candidates = candidate_universe

        if not candidates.empty:
            if "candidate_id" in candidates.columns:
                candidates["candidate_id"] = symbol + "::" + candidates["candidate_id"].astype(str)
            all_candidates.append(candidates)
        total_metrics_rows += int(len(metrics))
        total_valid_metrics_rows += valid_metrics_rows
        total_rejected_invalid_metrics += rejected_invalid_metrics
        total_rejected_by_min_n += rejected_by_min_n
        total_rejected_by_min_t_stat += rejected_by_min_t_stat
        total_bridge_candidates_rows += int(len(candidates))

        symbol_diagnostics.append(
            build_search_engine_diagnostics(
                run_id=run_id,
                discovery_profile=str(search_profile["discovery_profile"]),
                search_spec=resolved_search_spec,
                timeframe=timeframe,
                symbols_requested=symbols_requested,
                primary_symbol=symbol,
                feature_rows=int(len(features)),
                feature_columns=int(len(features.columns)),
                event_flag_rows=int(len(sym_flags)),
                event_flag_columns_merged=max(0, int(len(sym_flags.columns) - 2)),
                hypotheses_generated=int(len(hypotheses)),
                feasible_hypotheses=int(
                    generation_audit.get("counts", {}).get("feasible", len(hypotheses))
                ),
                rejected_hypotheses=int(generation_audit.get("counts", {}).get("rejected", 0)),
                rejection_reason_counts=dict(generation_audit.get("rejection_reason_counts", {})),
                metrics_rows=int(len(metrics)),
                valid_metrics_rows=valid_metrics_rows,
                rejected_invalid_metrics=rejected_invalid_metrics,
                rejected_by_min_n=rejected_by_min_n,
                rejected_by_min_t_stat=rejected_by_min_t_stat,
                bridge_candidates_rows=int(len(candidates)),
                multiplicity_discoveries=0,  # Computed globally
                min_t_stat=resolved_min_t_stat,
                min_n=resolved_min_n,
                search_budget=search_budget,
                use_context_quality=use_context_quality,
            )
        )

    # 5. Aggregate and final processing
    final_df = pd.concat(all_candidates, ignore_index=True) if all_candidates else pd.DataFrame()

    if not final_df.empty and "is_discovery" in final_df.columns:
        log.info(
            "Multiplicity: %d discoveries out of %d candidates",
            int(final_df.get("is_discovery", pd.Series(False)).sum()),
            len(final_df),
        )

    log.info("Search engine produced %d total bridge candidates", len(final_df))

    final_df = _annotate_candidate_regime_metadata(final_df)

    # 6. Write output
    write_parquet(final_df, output_path)

    # Phase 4.2 — Write regime_conditional_candidates.parquet.
    # Surfaces hypotheses that were weak overall (t_stat < 1.5) but had positive
    # mean_return_bps — these are candidates for regime-specific alpha that the
    # campaign controller can target with a context-conditioned follow-up run.
    # The controller reads this artefact in _build_next_actions() and injects
    # matching entries into the explore_adjacent queue.
    _write_regime_conditional_candidates(final_df, out_dir)

    main_diag = build_search_engine_diagnostics(
        run_id=run_id,
        discovery_profile=str(search_profile["discovery_profile"]),
        search_spec=resolved_search_spec,
        timeframe=timeframe,
        symbols_requested=symbols_requested,
        primary_symbol="" if len(symbols_requested) != 1 else symbols_requested[0],
        feature_rows=total_feature_rows,
        feature_columns=int(final_df.shape[1]) if not final_df.empty else 0,
        event_flag_rows=total_event_flag_rows,
        event_flag_columns_merged=max_event_flag_columns_merged,
        hypotheses_generated=total_hypotheses_generated,
        feasible_hypotheses=total_feasible_hypotheses,
        rejected_hypotheses=total_rejected_hypotheses,
        rejection_reason_counts=aggregated_rejection_reasons,
        metrics_rows=total_metrics_rows,
        valid_metrics_rows=total_valid_metrics_rows,
        rejected_invalid_metrics=total_rejected_invalid_metrics,
        rejected_by_min_n=total_rejected_by_min_n,
        rejected_by_min_t_stat=total_rejected_by_min_t_stat,
        bridge_candidates_rows=total_bridge_candidates_rows,
        multiplicity_discoveries=0,
        min_t_stat=resolved_min_t_stat,
        min_n=resolved_min_n,
        search_budget=search_budget,
        use_context_quality=use_context_quality,
    )
    if symbol_diagnostics:
        main_diag["symbol_diagnostics"] = symbol_diagnostics
    if not final_df.empty and "is_discovery" in final_df.columns:
        main_diag["multiplicity_discoveries"] = int(final_df["is_discovery"].sum())
    if symbol_diagnostics:
        main_diag["event_flag_columns_merged"] = int(
            max(int(diag.get("event_flag_columns_merged", 0) or 0) for diag in symbol_diagnostics)
        )
        main_diag["feature_columns"] = int(
            max(int(diag.get("feature_columns", 0) or 0) for diag in symbol_diagnostics)
        )

    write_json_report(main_diag, diagnostics_path)
    log.info("Wrote candidates to %s", output_path)
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Search engine hypothesis discovery stage")
    parser.add_argument("--run_id", required=True)
    parser.add_argument("--symbols", required=True)
    parser.add_argument("--data_root", default=None)
    parser.add_argument("--timeframe", default="5m")
    parser.add_argument("--discovery_profile", default="standard")
    parser.add_argument("--gate_profile", default="auto")
    parser.add_argument("--search_spec", default="spec/search_space.yaml")
    parser.add_argument("--phase2_event_type", default="")
    parser.add_argument("--chunk_size", type=int, default=500)
    parser.add_argument("--min_t_stat", type=float, default=1.5)
    parser.add_argument("--min_n", type=int, default=30)
    parser.add_argument("--search_budget", type=int, default=None)
    parser.add_argument("--use_context_quality", type=int, default=1)
    parser.add_argument(
        "--experiment_config", default=None, help="Path to experiment config for tracking."
    )
    parser.add_argument("--program_id", default=None, help="Program ID for experiment tracking.")
    parser.add_argument(
        "--registry_root", default="project/configs/registries", help="Root for event registries."
    )

    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    from project.core.config import get_data_root

    data_root = Path(args.data_root) if args.data_root else get_data_root()
    out_dir = phase2_run_dir(data_root=data_root, run_id=args.run_id)

    return run(
        run_id=args.run_id,
        symbols=args.symbols,
        data_root=data_root,
        out_dir=out_dir,
        timeframe=args.timeframe,
        discovery_profile=args.discovery_profile,
        gate_profile=args.gate_profile,
        search_spec=args.search_spec,
        chunk_size=args.chunk_size,
        min_t_stat=args.min_t_stat,
        min_n=args.min_n,
        search_budget=args.search_budget,
        use_context_quality=bool(int(args.use_context_quality)),
        experiment_config=args.experiment_config,
        registry_root=args.registry_root,
        phase2_event_type=args.phase2_event_type,
    )


if __name__ == "__main__":
    sys.exit(main())
