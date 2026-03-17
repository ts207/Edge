"""
Phase 2 Search Engine Stage.

Generates hypotheses from spec/search_space.yaml, evaluates them against the
wide feature table, and writes bridge-compatible candidates to the output directory.

This stage runs in parallel with phase2_candidate_discovery.py.
Both write the same bridge schema to different directories.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Optional

import pandas as pd

from project import PROJECT_ROOT
from project.specs.ontology import MATERIALIZED_STATE_COLUMNS_BY_ID
from project.specs.gates import load_gates_spec, select_phase2_gate_spec
from project.research.search.profile import resolve_search_profile
from project.research.search.generator import generate_hypotheses_with_audit
from project.research.search.evaluator import evaluate_hypothesis_batch, evaluated_records_from_metrics
from project.research.search.bridge_adapter import hypotheses_to_bridge_candidates, split_bridge_candidates
from project.io.utils import ensure_dir, write_parquet
from project.research.search.distributed_runner import run_distributed_search
from project.pipelines.research._family_event_utils import load_features
from project.research.services.phase2_diagnostics import build_search_engine_diagnostics
from project.research.services.reporting_service import write_json_report
from project.research.validation import assign_split_labels

log = logging.getLogger(__name__)


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
                lambda value: json.dumps(value, sort_keys=True)
                if isinstance(value, (dict, list, tuple))
                else value
            )
    return frame


def _write_hypothesis_audit_artifacts(out_dir: Path, symbol: str, audit: dict) -> None:
    audit_dir = out_dir / "hypotheses" / str(symbol).upper()
    ensure_dir(audit_dir)
    write_parquet(_normalize_audit_frame(audit.get("generated_rows", [])), audit_dir / "generated_hypotheses.parquet")
    write_parquet(_normalize_audit_frame(audit.get("rejected_rows", [])), audit_dir / "rejected_hypotheses.parquet")
    write_parquet(_normalize_audit_frame(audit.get("feasible_rows", [])), audit_dir / "feasible_hypotheses.parquet")


def _write_evaluation_artifacts(out_dir: Path, symbol: str, metrics: pd.DataFrame, gate_failures: pd.DataFrame) -> None:
    audit_dir = out_dir / "hypotheses" / str(symbol).upper()
    ensure_dir(audit_dir)
    write_parquet(evaluated_records_from_metrics(metrics), audit_dir / "evaluated_hypotheses.parquet")
    write_parquet(gate_failures, audit_dir / "gate_failures.parquet")


def _normalize_search_feature_columns(features: pd.DataFrame) -> pd.DataFrame:
    if features.empty:
        return features

    out = features.copy()

    # Materialize canonical state ids as direct search columns when market_context
    # already exposes a concrete source column for them.
    for state_id, source_col in MATERIALIZED_STATE_COLUMNS_BY_ID.items():
        canonical_col = str(state_id).strip().lower()
        if canonical_col in out.columns or source_col not in out.columns:
            continue
        out[canonical_col] = pd.to_numeric(out[source_col], errors="coerce").fillna(0.0)

    # carry_state contexts are defined in the domain registry as funding_pos/neg,
    # while market_context exposes a signed carry_state_code.
    if "carry_state_code" in out.columns:
        carry_code = pd.to_numeric(out["carry_state_code"], errors="coerce").fillna(0.0)
        if "funding_positive" not in out.columns:
            out["funding_positive"] = (carry_code > 0).astype(float)
        if "funding_negative" not in out.columns:
            out["funding_negative"] = (carry_code < 0).astype(float)

    # Trend structure states are emitted as bull/bear/chop regimes in market_context.
    if "chop_state" not in out.columns and "chop_regime" in out.columns:
        out["chop_state"] = pd.to_numeric(out["chop_regime"], errors="coerce").fillna(0.0)
    if "trending_state" not in out.columns:
        bull_source = out["bull_trend_regime"] if "bull_trend_regime" in out.columns else pd.Series(0.0, index=out.index)
        bear_source = out["bear_trend_regime"] if "bear_trend_regime" in out.columns else pd.Series(0.0, index=out.index)
        bull = pd.to_numeric(bull_source, errors="coerce").fillna(0.0)
        bear = pd.to_numeric(bear_source, errors="coerce").fillna(0.0)
        out["trending_state"] = ((bull > 0) | (bear > 0)).astype(float)

    return out


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
    experiment_config: Optional[str] = None,
    registry_root: str | Path = "project/configs/registries",
) -> int:
    """
    Core logic. Returns exit code (0=success, 1=failure).
    Separated from main() for testability.
    """
    log.info("Starting Phase 2 Search Engine (run_id=%s, search_spec=%s, experiment_config=%s)", run_id, search_spec, experiment_config)
    ensure_dir(out_dir)
    output_path = out_dir / "phase2_candidates.parquet"
    diagnostics_path = out_dir / "phase2_diagnostics.json"
    symbols_requested = [s.strip().upper() for s in str(symbols).split(",") if s.strip()]
    timeframe = str(timeframe or "5m").strip().lower() or "5m"
    search_profile = resolve_search_profile(
        discovery_profile=discovery_profile,
        search_spec=search_spec,
        min_n=min_n,
        min_t_stat=min_t_stat,
    )
    resolved_search_spec = str(search_profile["search_spec"])
    resolved_min_n = int(search_profile["min_n"])
    resolved_min_t_stat = float(search_profile["min_t_stat"])
    phase2_gates = select_phase2_gate_spec(
        load_gates_spec(PROJECT_ROOT.parent),
        mode="research",
        gate_profile=str(gate_profile or "auto"),
    )
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
        from project.pipelines.research.experiment_engine import build_experiment_plan
        experiment_plan = build_experiment_plan(Path(experiment_config), Path(registry_root))
        log.info("Loaded experiment plan with %d hypotheses", len(experiment_plan.hypotheses))

    for symbol in symbols_requested:
        log.info("Processing symbol %s...", symbol)
        
        # 1a. Load features
        features = load_features(run_id, symbol, timeframe=timeframe, data_root=data_root)
        if features.empty:
            log.warning("Empty feature table for %s", symbol)
            continue
        features = _normalize_search_feature_columns(features)
            
        log.info("Loaded features for %s: %d rows, %d columns", symbol, len(features), len(features.columns))
        max_feature_columns = max(max_feature_columns, int(len(features.columns)))

        # 1b. Merge event flags from registry
        from project.events.event_flags import load_registry_flags
        log.info("Loading event flags for %s from registry...", symbol)
        event_flags = load_registry_flags(data_root=data_root, run_id=run_id)
        sym_flags = pd.DataFrame()
        if not event_flags.empty:
            # Filter for current symbol
            sym_flags = event_flags[event_flags["symbol"] == symbol].copy()
            if not sym_flags.empty:
                log.info("Merging %d event flag columns for %s", len(sym_flags.columns) - 2, symbol)
                max_event_flag_columns_merged = max(
                    max_event_flag_columns_merged,
                    max(0, int(len(sym_flags.columns) - 2)),
                )
                features = pd.merge(
                    features,
                    sym_flags,
                    on=["timestamp", "symbol"],
                    how="left"
                )
                # Fill NAs with False for the new boolean flag columns
                flag_cols = [c for c in sym_flags.columns if c not in ["timestamp", "symbol"]]
                features[flag_cols] = features[flag_cols].fillna(False)

        if "split_label" not in features.columns:
            features = assign_split_labels(features, time_col="timestamp")

        total_feature_rows += int(len(features))
        total_event_flag_rows += int(len(sym_flags))

        # 2. Generate hypotheses
        if experiment_plan:
            hypotheses = experiment_plan.hypotheses
            generation_audit = {"counts": {"feasible": len(hypotheses)}}
            log.info("Using %d hypotheses from experiment plan for %s", len(hypotheses), symbol)
        else:
            log.info("Generating hypotheses from spec for %s: %s", symbol, resolved_search_spec)
            hypotheses, generation_audit = generate_hypotheses_with_audit(
                resolved_search_spec,
                features=features,
            )
            _write_hypothesis_audit_artifacts(out_dir, symbol, generation_audit)
            log.info("Generated %d hypotheses for %s", len(hypotheses), symbol)
            
        total_hypotheses_generated += int(len(hypotheses))
        total_feasible_hypotheses += int(generation_audit.get("counts", {}).get("feasible", len(hypotheses)))
        total_rejected_hypotheses += int(generation_audit.get("counts", {}).get("rejected", 0))
        for reason, count in dict(generation_audit.get("rejection_reason_counts", {})).items():
            aggregated_rejection_reasons[str(reason)] = aggregated_rejection_reasons.get(str(reason), 0) + int(count)

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
                    rejection_reason_counts=dict(generation_audit.get("rejection_reason_counts", {})),
                    metrics_rows=0,
                    valid_metrics_rows=0,
                    rejected_invalid_metrics=0,
                    rejected_by_min_n=0,
                    rejected_by_min_t_stat=0,
                    bridge_candidates_rows=0,
                    multiplicity_discoveries=0,
                    min_t_stat=resolved_min_t_stat,
                    min_n=resolved_min_n,
                )
            )
            continue

        # 3. Evaluate in chunks
        log.info("Evaluating hypotheses batch for %s (chunk_size=%d)...", symbol, chunk_size)
        metrics = run_distributed_search(
            hypotheses, 
            features, 
            chunk_size=chunk_size,
            min_sample_size=resolved_min_n
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
                    feasible_hypotheses=int(generation_audit.get("counts", {}).get("feasible", len(hypotheses))),
                    rejected_hypotheses=int(generation_audit.get("counts", {}).get("rejected", 0)),
                    rejection_reason_counts=dict(generation_audit.get("rejection_reason_counts", {})),
                    metrics_rows=0,
                    valid_metrics_rows=0,
                    rejected_invalid_metrics=0,
                    rejected_by_min_n=0,
                    rejected_by_min_t_stat=0,
                    bridge_candidates_rows=0,
                    multiplicity_discoveries=0,
                    min_t_stat=resolved_min_t_stat,
                    min_n=resolved_min_n,
                )
            )
            continue
            
        valid_mask = metrics.get("valid", pd.Series(False, index=metrics.index)).fillna(False).astype(bool) if not metrics.empty else pd.Series(dtype=bool)
        valid_metrics_rows = int(valid_mask.sum())
        rejected_invalid_metrics = max(0, int(len(metrics)) - valid_metrics_rows)
        rejected_by_min_n = int((valid_mask & (pd.to_numeric(metrics.get("n", 0), errors="coerce").fillna(0) < int(resolved_min_n))).sum())
        rejected_by_min_t_stat = int((valid_mask & (pd.to_numeric(metrics.get("n", 0), errors="coerce").fillna(0) >= int(resolved_min_n)) & (pd.to_numeric(metrics.get("t_stat", 0.0), errors="coerce").abs().fillna(0.0) < float(resolved_min_t_stat))).sum())
        
        # 4. Convert to bridge candidates
        candidates, gate_failures = split_bridge_candidates(
            metrics,
            min_t_stat=resolved_min_t_stat,
            min_n=resolved_min_n,
        )
        _write_evaluation_artifacts(out_dir, symbol, metrics, gate_failures)
        candidates = hypotheses_to_bridge_candidates(
            metrics,
            min_t_stat=resolved_min_t_stat,
            min_n=resolved_min_n,
        )
        
        if not candidates.empty:
            candidates["symbol"] = symbol
            if "candidate_id" in candidates.columns:
                candidates["candidate_id"] = (
                    symbol + "::" + candidates["candidate_id"].astype(str)
                )
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
                feasible_hypotheses=int(generation_audit.get("counts", {}).get("feasible", len(hypotheses))),
                rejected_hypotheses=int(generation_audit.get("counts", {}).get("rejected", 0)),
                rejection_reason_counts=dict(generation_audit.get("rejection_reason_counts", {})),
                metrics_rows=int(len(metrics)),
                valid_metrics_rows=valid_metrics_rows,
                rejected_invalid_metrics=rejected_invalid_metrics,
                rejected_by_min_n=rejected_by_min_n,
                rejected_by_min_t_stat=rejected_by_min_t_stat,
                bridge_candidates_rows=int(len(candidates)),
                multiplicity_discoveries=0, # Computed globally
                min_t_stat=resolved_min_t_stat,
                min_n=resolved_min_n,
            )
        )

    # 5. Aggregate and final processing
    final_df = pd.concat(all_candidates, ignore_index=True) if all_candidates else pd.DataFrame()
    
    if not final_df.empty and "p_value" in final_df.columns and "family_id" in final_df.columns:
        from project.research.multiplicity import apply_multiplicity_controls
        try:
            max_q = multiplicity_max_q
        except Exception:
            max_q = 0.05
        final_df = apply_multiplicity_controls(final_df, max_q=max_q, mode="research")
        log.info(
            "Multiplicity: %d discoveries out of %d candidates",
            int(final_df.get("is_discovery", pd.Series(False)).sum()),
            len(final_df),
        )

    log.info("Search engine produced %d total bridge candidates", len(final_df))

    # 6. Write output
    write_parquet(final_df, output_path)
    
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
    parser.add_argument("--chunk_size", type=int, default=500)
    parser.add_argument("--min_t_stat", type=float, default=1.5)
    parser.add_argument("--min_n", type=int, default=30)
    parser.add_argument("--experiment_config", default=None, help="Path to experiment config for tracking.")
    parser.add_argument("--program_id", default=None, help="Program ID for experiment tracking.")
    parser.add_argument("--registry_root", default="project/configs/registries", help="Root for event registries.")

    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    from project.core.config import get_data_root
    data_root = Path(args.data_root) if args.data_root else get_data_root()
    out_dir = data_root / "reports" / "phase2" / args.run_id / "search_engine"

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
        experiment_config=args.experiment_config,
        registry_root=args.registry_root,
    )


if __name__ == "__main__":
    sys.exit(main())
