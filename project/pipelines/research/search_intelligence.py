from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any, Dict

import pandas as pd

from project.core.config import get_data_root
from project.pipelines.research.experiment_engine import RegistryBundle
from project.research.knowledge.memory import (
    ensure_memory_store,
    read_memory_table,
)

_LOG = logging.getLogger(__name__)


def _safe_read_legacy_ledger(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_parquet(path)
    except Exception:
        return pd.DataFrame()


def _build_summary(program_id: str, tested_regions: pd.DataFrame, *, top_k: int) -> Dict[str, Any]:
    if tested_regions.empty:
        return {"program_id": program_id, "status": "no_data"}

    evaluated = tested_regions.copy()
    promoted = evaluated[evaluated["eval_status"].astype(str) == "promoted"]
    summary: Dict[str, Any] = {
        "program_id": program_id,
        "metrics": {
            "total_runs": int(evaluated["run_id"].nunique()),
            "total_regions": int(len(evaluated)),
            "status_counts": evaluated["eval_status"].astype(str).value_counts().to_dict(),
            "evaluated_share": 1.0,
            "promotion_rate": float(len(promoted) / max(len(evaluated), 1)),
        },
    }

    def _group_stats(column: str) -> Dict[str, Any]:
        if column not in evaluated.columns:
            return {}
        grouped = evaluated.groupby(column)
        out: Dict[str, Any] = {}
        for key, sub in grouped:
            promoted_share = float((sub["eval_status"].astype(str) == "promoted").mean())
            out[str(key)] = {
                "sample": int(len(sub)),
                "promotion_rate": promoted_share,
                "avg_after_cost_expectancy": float(pd.to_numeric(sub["after_cost_expectancy"], errors="coerce").mean()),
            }
        return out

    summary["win_rates"] = {
        "by_trigger_type": _group_stats("trigger_type"),
        "by_template": _group_stats("template_id"),
        "by_direction": _group_stats("direction"),
        "by_horizon": _group_stats("horizon"),
        "by_event_type": _group_stats("event_type"),
    }
    def _gate_rank(val) -> int:
        val = str(val).strip().lower()
        if val in ("pass", "true", "1", "1.0"): return 2
        if val in ("fail", "false", "0", "0.0"): return 1
        return 0
        
    ranked = evaluated.copy()
    if "gate_promo_statistical" in ranked.columns:
        ranked["_gate_rank"] = ranked["gate_promo_statistical"].apply(_gate_rank)
    else:
        ranked["_gate_rank"] = 0

    summary["top_performing_regions"] = (
        ranked.sort_values(
            ["_gate_rank", "after_cost_expectancy", "q_value"],
            ascending=[False, False, True],
        )
        .head(int(top_k))[
            [
                c
                for c in [
                    "run_id",
                    "candidate_id",
                    "event_type",
                    "template_id",
                    "direction",
                    "horizon",
                    "q_value",
                    "after_cost_expectancy",
                    "primary_fail_gate",
                ]
                if c in evaluated.columns
            ]
        ]
        .to_dict(orient="records")
    )
    return summary


def _build_frontier(
    registries: RegistryBundle,
    tested_regions: pd.DataFrame,
    failures: pd.DataFrame,
    *,
    untested_top_k: int,
    repair_top_k: int,
    exhausted_failure_threshold: int,
) -> Dict[str, Any]:
    events = registries.events.get("events", {})
    enabled_events = [eid for eid, meta in events.items() if meta.get("enabled", True)]
    tested_events = set(tested_regions.get("event_type", pd.Series(dtype="object")).astype(str).unique())
    untested_events = sorted(list(set(enabled_events) - tested_events))

    exhausted_events: list[str] = []
    if not tested_regions.empty and "event_type" in tested_regions.columns:
        fail_counts = (
            tested_regions[tested_regions["eval_status"].astype(str) != "promoted"]
            .groupby("event_type")
            .size()
        )
        exhausted_events = sorted(
            list(fail_counts[fail_counts >= int(exhausted_failure_threshold)].index.astype(str))
        )

    partial_families: Dict[str, str] = {}
    families: Dict[str, Dict[str, int]] = {}
    for eid, meta in events.items():
        family = str(meta.get("family", "unknown"))
        families.setdefault(family, {"total": 0, "tested": 0})
        families[family]["total"] += 1
        if eid in tested_events:
            families[family]["tested"] += 1
    for family, counts in families.items():
        if 0 < counts["tested"] < counts["total"]:
            partial_families[family] = f"{counts['tested']}/{counts['total']}"

    repair_candidates = []
    if not failures.empty:
        for stage, count in failures["stage"].astype(str).value_counts().head(int(repair_top_k)).items():
            repair_candidates.append(f"repair repeated failure in stage: {stage} ({int(count)})")

    next_moves = []
    if untested_events:
        next_moves.append(f"explore untested events: {untested_events[:int(untested_top_k)]}")
    if partial_families:
        next_moves.append(f"complete coverage for family: {next(iter(partial_families))}")
    next_moves.extend(repair_candidates[:int(repair_top_k)])

    return {
        "untested_registry_events": untested_events[:int(untested_top_k)],
        "exhausted_events_to_avoid": exhausted_events,
        "partially_explored_families": partial_families,
        "candidate_next_moves": next_moves,
    }


def update_search_intelligence(
    data_root: Path,
    registry_root: Path,
    program_id: str,
    *,
    summary_top_k: int = 10,
    frontier_untested_top_k: int = 3,
    frontier_repair_top_k: int = 2,
    exhausted_failure_threshold: int = 3,
) -> Dict[str, Any]:
    campaign_dir = data_root / "artifacts" / "experiments" / program_id
    campaign_dir.mkdir(parents=True, exist_ok=True)
    summary_path = campaign_dir / "campaign_summary.json"
    frontier_path = campaign_dir / "search_frontier.json"

    registries = RegistryBundle(registry_root)
    ensure_memory_store(program_id, data_root=data_root)
    tested_regions = read_memory_table(program_id, "tested_regions", data_root=data_root)
    failures = read_memory_table(program_id, "failures", data_root=data_root)

    if tested_regions.empty:
        legacy_ledger = _safe_read_legacy_ledger(campaign_dir / "tested_ledger.parquet")
        if not legacy_ledger.empty and "event_type" in legacy_ledger.columns:
            tested_regions = pd.DataFrame(
                {
                    "run_id": legacy_ledger.get("run_id", pd.Series(dtype="object")),
                    "event_type": legacy_ledger.get("event_type", pd.Series(dtype="object")),
                    "template_id": legacy_ledger.get("template_id", pd.Series(dtype="object")),
                    "direction": legacy_ledger.get("direction", pd.Series(dtype="object")),
                    "horizon": legacy_ledger.get("horizon", pd.Series(dtype="object")),
                    "trigger_type": legacy_ledger.get("trigger_type", pd.Series(dtype="object")),
                    "after_cost_expectancy": legacy_ledger.get("expectancy", pd.Series(dtype=float)),
                    "q_value": legacy_ledger.get("q_value", pd.Series(dtype=float)),
                    "eval_status": legacy_ledger.get("eval_status", pd.Series(dtype="object")),
                    "candidate_id": legacy_ledger.get("candidate_id", pd.Series(dtype="object")),
                    "gate_promo_statistical": False,
                    "primary_fail_gate": "",
                }
            )

    summary = _build_summary(program_id, tested_regions, top_k=summary_top_k)
    frontier = _build_frontier(
        registries,
        tested_regions,
        failures,
        untested_top_k=frontier_untested_top_k,
        repair_top_k=frontier_repair_top_k,
        exhausted_failure_threshold=exhausted_failure_threshold,
    )
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    frontier_path.write_text(json.dumps(frontier, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _LOG.info("Updated intelligence for %s from campaign memory.", program_id)
    return {"summary": summary, "frontier": frontier}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--program_id", required=True)
    parser.add_argument("--registry_root", default="project/configs/registries")
    parser.add_argument("--summary_top_k", type=int, default=10)
    parser.add_argument("--frontier_untested_top_k", type=int, default=3)
    parser.add_argument("--frontier_repair_top_k", type=int, default=2)
    parser.add_argument("--exhausted_failure_threshold", type=int, default=3)
    args = parser.parse_args()

    data_root = get_data_root()
    update_search_intelligence(
        data_root,
        Path(args.registry_root),
        args.program_id,
        summary_top_k=int(args.summary_top_k),
        frontier_untested_top_k=int(args.frontier_untested_top_k),
        frontier_repair_top_k=int(args.frontier_repair_top_k),
        exhausted_failure_threshold=int(args.exhausted_failure_threshold),
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
