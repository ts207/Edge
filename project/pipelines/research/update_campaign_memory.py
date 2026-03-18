from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict

import pandas as pd

from project.core.config import get_data_root
from project.pipelines.research.search_intelligence import update_search_intelligence
from project.research.knowledge.memory import (
    build_failures_snapshot,
    build_tested_regions_snapshot,
    compute_context_statistics,
    compute_event_statistics,
    compute_region_statistics,
    compute_template_statistics,
    ensure_memory_store,
    read_memory_table,
    write_memory_table,
)
from project.research.knowledge.reflection import build_run_reflection
from project.research.services.campaign_memory_rollup_service import write_campaign_memory_rollup
from project.specs.manifest import finalize_manifest, load_run_manifest, start_manifest

_LOG = logging.getLogger(__name__)


def _merge_by_keys(existing: pd.DataFrame, incoming: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    if existing.empty:
        return incoming.copy()
    if incoming.empty:
        return existing.copy()
    out = pd.concat([existing, incoming], ignore_index=True)
    present_keys = [key for key in keys if key in out.columns]
    if present_keys:
        out = out.drop_duplicates(subset=present_keys, keep="last").reset_index(drop=True)
    return out


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _build_belief_state(
    *,
    tested_regions: pd.DataFrame,
    failures: pd.DataFrame,
    reflection: Dict[str, Any],
    promising_top_k: int,
    avoid_top_k: int,
    repair_top_k: int,
) -> Dict[str, Any]:
    promising_regions = []
    if not tested_regions.empty:
        def _gate_rank(val) -> int:
            val = str(val).strip().lower()
            if val in ("pass", "true", "1", "1.0"): return 2
            if val in ("fail", "false", "0", "0.0"): return 1
            return 0
        
        ranked = tested_regions.copy()
        if "gate_promo_statistical" in ranked.columns:
            ranked["_gate_rank"] = ranked["gate_promo_statistical"].apply(_gate_rank)
        else:
            ranked["_gate_rank"] = 0

        ranked = ranked.sort_values(
            ["_gate_rank", "after_cost_expectancy", "q_value"],
            ascending=[False, False, True],
        ).head(int(promising_top_k))
        promising_regions = ranked[
            [c for c in ["event_type", "template_id", "direction", "horizon", "region_key"] if c in ranked.columns]
        ].to_dict(orient="records")

    avoid_regions = []
    if not tested_regions.empty:
        rejected = tested_regions[tested_regions["primary_fail_gate"].astype(str) != ""].head(int(avoid_top_k))
        avoid_regions = rejected[
            [c for c in ["event_type", "template_id", "primary_fail_gate", "region_key"] if c in rejected.columns]
        ].to_dict(orient="records")

    open_repairs = []
    if not failures.empty:
        open_repairs = failures[
            [c for c in ["stage", "failure_class", "failure_detail"] if c in failures.columns]
        ].head(int(repair_top_k)).to_dict(orient="records")

    return {
        "current_focus": str(reflection.get("recommended_next_action", "")),
        "avoid_regions": avoid_regions,
        "promising_regions": promising_regions,
        "open_repairs": open_repairs,
        "last_reflection_run_id": str(reflection.get("run_id", "")),
    }


def _build_next_actions(
    *,
    reflection: Dict[str, Any],
    tested_regions: pd.DataFrame,
    failures: pd.DataFrame,
    exploit_top_k: int,
    repair_top_k: int,
) -> Dict[str, Any]:
    exploit = []
    if not tested_regions.empty:
        def _gate_rank(val) -> int:
            val = str(val).strip().lower()
            if val in ("pass", "true", "1", "1.0"): return 2
            if val in ("fail", "false", "0", "0.0"): return 1
            return 0
            
        ranked_df = tested_regions.copy()
        if "gate_promo_statistical" in ranked_df.columns:
            ranked_df["_gate_rank"] = ranked_df["gate_promo_statistical"].apply(_gate_rank)
        else:
            ranked_df["_gate_rank"] = 0

        exploit = (
            ranked_df.sort_values(
                ["_gate_rank", "after_cost_expectancy", "q_value"],
                ascending=[False, False, True],
            )
            .head(int(exploit_top_k))[[c for c in ["event_type", "template_id", "direction", "horizon", "region_key"] if c in tested_regions.columns]]
            .to_dict(orient="records")
        )

    repair = []
    if not failures.empty:
        repair = failures.head(int(repair_top_k))[[c for c in ["stage", "failure_class", "failure_detail"] if c in failures.columns]].to_dict(orient="records")

    recommended_experiment = {}
    try:
        recommended_experiment = json.loads(str(reflection.get("recommended_next_experiment", "{}")))
    except json.JSONDecodeError:
        recommended_experiment = {}

    return {
        "repair": [
            {
                "reason": "mechanical failure detected",
                "priority": "high",
                "proposed_scope": row,
            }
            for row in repair
        ],
        "exploit": [
            {
                "reason": "best observed region by statistical and expectancy filters",
                "priority": "medium",
                "proposed_scope": row,
            }
            for row in exploit
        ],
        "explore_adjacent": (
            [
                {
                    "reason": str(reflection.get("recommended_next_action", "")),
                    "priority": "medium",
                    "proposed_scope": recommended_experiment,
                }
            ]
            if recommended_experiment
            else []
        ),
        "hold": [],
    }


def update_campaign_memory(
    *,
    run_id: str,
    program_id: str,
    data_root: Path,
    registry_root: Path,
    promising_top_k: int,
    avoid_top_k: int,
    repair_top_k: int,
    exploit_top_k: int,
    frontier_untested_top_k: int,
    frontier_repair_top_k: int,
    exhausted_failure_threshold: int,
) -> Dict[str, Any]:
    paths = ensure_memory_store(program_id, data_root=data_root)

    incoming_tested = build_tested_regions_snapshot(run_id=run_id, program_id=program_id, data_root=data_root)
    incoming_failures = build_failures_snapshot(run_id=run_id, program_id=program_id, data_root=data_root)
    reflection_row = build_run_reflection(run_id=run_id, program_id=program_id, data_root=data_root)
    reflection_df = pd.DataFrame([reflection_row])

    tested_regions = _merge_by_keys(
        read_memory_table(program_id, "tested_regions", data_root=data_root),
        incoming_tested,
        ["run_id", "candidate_id", "region_key"],
    )
    failures = _merge_by_keys(
        read_memory_table(program_id, "failures", data_root=data_root),
        incoming_failures,
        ["run_id", "stage", "failure_class", "artifact_path"],
    )
    reflections = _merge_by_keys(
        read_memory_table(program_id, "reflections", data_root=data_root),
        reflection_df,
        ["run_id"],
    )

    write_memory_table(program_id, "tested_regions", tested_regions, data_root=data_root)
    write_memory_table(program_id, "failures", failures, data_root=data_root)
    write_memory_table(program_id, "reflections", reflections, data_root=data_root)
    write_memory_table(program_id, "region_statistics", compute_region_statistics(tested_regions), data_root=data_root)
    write_memory_table(program_id, "event_statistics", compute_event_statistics(tested_regions), data_root=data_root)
    write_memory_table(program_id, "template_statistics", compute_template_statistics(tested_regions), data_root=data_root)
    write_memory_table(program_id, "context_statistics", compute_context_statistics(tested_regions), data_root=data_root)

    _write_json(
        paths.belief_state,
        _build_belief_state(
            tested_regions=tested_regions,
            failures=failures,
            reflection=reflection_row,
            promising_top_k=promising_top_k,
            avoid_top_k=avoid_top_k,
            repair_top_k=repair_top_k,
        ),
    )
    _write_json(
        paths.next_actions,
        _build_next_actions(
            reflection=reflection_row,
            tested_regions=tested_regions,
            failures=failures,
            exploit_top_k=exploit_top_k,
            repair_top_k=repair_top_k,
        ),
    )

    compatibility = update_search_intelligence(
        data_root,
        registry_root,
        program_id,
        summary_top_k=max(int(promising_top_k), int(exploit_top_k)),
        frontier_untested_top_k=int(frontier_untested_top_k),
        frontier_repair_top_k=int(frontier_repair_top_k),
        exhausted_failure_threshold=int(exhausted_failure_threshold),
    )
    rollup_path = write_campaign_memory_rollup(
        program_id=program_id,
        data_root=data_root,
    )
    return {
        "tested_regions_rows": int(len(incoming_tested)),
        "failures_rows": int(len(incoming_failures)),
        "reflection_written": True,
        "compatibility_summary_status": compatibility["summary"].get("status", "ok"),
        "memory_root": str(paths.root),
        "campaign_memory_rollup_path": str(rollup_path),
        "promising_top_k": int(promising_top_k),
        "repair_top_k": int(repair_top_k),
        "frontier_untested_top_k": int(frontier_untested_top_k),
        "exhausted_failure_threshold": int(exhausted_failure_threshold),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Update campaign memory from run artifacts.")
    parser.add_argument("--run_id", required=True)
    parser.add_argument("--program_id", default="")
    parser.add_argument("--data_root", default=None)
    parser.add_argument("--registry_root", default="project/configs/registries")
    parser.add_argument("--promising_top_k", type=int, default=5)
    parser.add_argument("--avoid_top_k", type=int, default=5)
    parser.add_argument("--repair_top_k", type=int, default=5)
    parser.add_argument("--exploit_top_k", type=int, default=3)
    parser.add_argument("--frontier_untested_top_k", type=int, default=3)
    parser.add_argument("--frontier_repair_top_k", type=int, default=2)
    parser.add_argument("--exhausted_failure_threshold", type=int, default=3)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    data_root = Path(args.data_root) if args.data_root else get_data_root()
    manifest_path = data_root / "runs" / str(args.run_id) / "run_manifest.json"
    if manifest_path.exists():
        try:
            run_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            run_manifest = {}
    else:
        run_manifest = load_run_manifest(str(args.run_id))
    program_id = str(args.program_id or run_manifest.get("program_id", "")).strip()
    if not program_id:
        _LOG.info("Skipping campaign memory update for run %s because no program_id was provided.", args.run_id)
        return 0

    manifest = start_manifest("update_campaign_memory", str(args.run_id), vars(args), [], [])
    try:
        diagnostics = update_campaign_memory(
            run_id=str(args.run_id),
            program_id=program_id,
            data_root=data_root,
            registry_root=Path(args.registry_root),
            promising_top_k=int(args.promising_top_k),
            avoid_top_k=int(args.avoid_top_k),
            repair_top_k=int(args.repair_top_k),
            exploit_top_k=int(args.exploit_top_k),
            frontier_untested_top_k=int(args.frontier_untested_top_k),
            frontier_repair_top_k=int(args.frontier_repair_top_k),
            exhausted_failure_threshold=int(args.exhausted_failure_threshold),
        )
        paths = ensure_memory_store(program_id, data_root=data_root)
        manifest["outputs"] = [
            {"path": str(paths.tested_regions), "artifact_type": "experiment.memory.tested_regions"},
            {"path": str(paths.reflections), "artifact_type": "experiment.memory.reflections"},
            {"path": str(paths.failures), "artifact_type": "experiment.memory.failures"},
            {
                "path": str(diagnostics.get("campaign_memory_rollup_path", "")),
                "artifact_type": "experiment.memory.rollup",
            },
        ]
        finalize_manifest(
            manifest,
            status="success",
            stats=diagnostics,
        )
        return 0
    except Exception as exc:
        finalize_manifest(manifest, status="failed", error=str(exc))
        raise


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sys.exit(main())
