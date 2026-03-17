from __future__ import annotations

import json
import os
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List

import pandas as pd

from project.core.config import get_data_root
from project.io.utils import ensure_dir, write_parquet
from project.specs.manifest import load_run_manifest

from project.research.knowledge.schemas import (
    FAILURE_COLUMNS,
    PROPOSAL_AUDIT_COLUMNS,
    REFLECTION_COLUMNS,
    TESTED_REGION_COLUMNS,
    canonical_json,
    region_key,
    stable_hash,
)

_TABLES = {
    "tested_regions": TESTED_REGION_COLUMNS,
    "region_statistics": [
        "region_key",
        "runs_tested",
        "times_evaluated",
        "times_promoted",
        "eval_rate",
        "promotion_rate",
        "avg_q_value",
        "avg_after_cost_expectancy",
        "avg_robustness_score",
        "dominant_fail_gate",
        "last_tested_at",
    ],
    "event_statistics": [
        "event_type",
        "runs_tested",
        "times_evaluated",
        "times_promoted",
        "avg_q_value",
        "avg_after_cost_expectancy",
        "dominant_fail_gate",
    ],
    "template_statistics": [
        "template_id",
        "runs_tested",
        "times_evaluated",
        "times_promoted",
        "avg_q_value",
        "avg_after_cost_expectancy",
        "dominant_fail_gate",
    ],
    "context_statistics": [
        "context_hash",
        "context_json",
        "runs_tested",
        "times_evaluated",
        "times_promoted",
        "avg_q_value",
        "avg_after_cost_expectancy",
        "dominant_fail_gate",
    ],
    "failures": FAILURE_COLUMNS,
    "proposals": PROPOSAL_AUDIT_COLUMNS,
    "reflections": REFLECTION_COLUMNS,
}


@dataclass(frozen=True)
class MemoryPaths:
    root: Path
    tested_regions: Path
    region_statistics: Path
    event_statistics: Path
    template_statistics: Path
    context_statistics: Path
    failures: Path
    proposals: Path
    reflections: Path
    belief_state: Path
    next_actions: Path
    proposals_dir: Path


def memory_paths(program_id: str, *, data_root: Path | None = None) -> MemoryPaths:
    resolved_data_root = Path(data_root) if data_root is not None else get_data_root()
    root = resolved_data_root / "artifacts" / "experiments" / str(program_id) / "memory"
    return MemoryPaths(
        root=root,
        tested_regions=root / "tested_regions.parquet",
        region_statistics=root / "region_statistics.parquet",
        event_statistics=root / "event_statistics.parquet",
        template_statistics=root / "template_statistics.parquet",
        context_statistics=root / "context_statistics.parquet",
        failures=root / "failures.parquet",
        proposals=root / "proposals.parquet",
        reflections=root / "reflections.parquet",
        belief_state=root / "belief_state.json",
        next_actions=root / "next_actions.json",
        proposals_dir=root / "proposals",
    )


def ensure_memory_store(program_id: str, *, data_root: Path | None = None) -> MemoryPaths:
    paths = memory_paths(program_id, data_root=data_root)
    paths.root.mkdir(parents=True, exist_ok=True)
    paths.proposals_dir.mkdir(parents=True, exist_ok=True)
    for table_name, columns in _TABLES.items():
        path = getattr(paths, table_name)
        if not path.exists():
            _write_memory_frame(pd.DataFrame(columns=columns), path)
    if not paths.belief_state.exists():
        paths.belief_state.write_text(
            json.dumps(
                {
                    "current_focus": "",
                    "avoid_regions": [],
                    "promising_regions": [],
                    "open_repairs": [],
                    "last_reflection_run_id": "",
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
    if not paths.next_actions.exists():
        paths.next_actions.write_text(
            json.dumps(
                {
                    "repair": [],
                    "exploit": [],
                    "explore_adjacent": [],
                    "hold": [],
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
    return paths


def read_memory_table(program_id: str, table_name: str, *, data_root: Path | None = None) -> pd.DataFrame:
    paths = ensure_memory_store(program_id, data_root=data_root)
    path = getattr(paths, table_name)
    return _read_best_available(path)


def write_memory_table(
    program_id: str,
    table_name: str,
    df: pd.DataFrame,
    *,
    data_root: Path | None = None,
) -> Path:
    paths = ensure_memory_store(program_id, data_root=data_root)
    path = getattr(paths, table_name)
    columns = _TABLES.get(table_name)
    out_df = df.copy()
    if columns is not None:
        for column in columns:
            if column not in out_df.columns:
                out_df[column] = None
        out_df = out_df.reindex(columns=columns)
    _write_memory_frame(out_df, path)
    return path


@contextmanager
def _canonical_parquet_write_mode() -> Iterable[None]:
    original = os.environ.get("BACKTEST_FORCE_CSV_FALLBACK")
    os.environ["BACKTEST_FORCE_CSV_FALLBACK"] = "0"
    try:
        yield
    finally:
        if original is None:
            os.environ.pop("BACKTEST_FORCE_CSV_FALLBACK", None)
        else:
            os.environ["BACKTEST_FORCE_CSV_FALLBACK"] = original


def _write_memory_frame(df: pd.DataFrame, path: Path) -> Path:
    ensure_dir(path.parent)
    with _canonical_parquet_write_mode():
        written_path, _ = write_parquet(df, path)
    return written_path


def _read_best_available(path: Path) -> pd.DataFrame:
    if path.exists():
        return pd.read_parquet(path)
    csv_path = path.with_suffix(".csv")
    if csv_path.exists():
        return pd.read_csv(csv_path)
    return pd.DataFrame()


def build_tested_regions_snapshot(
    *,
    run_id: str,
    program_id: str,
    data_root: Path | None = None,
) -> pd.DataFrame:
    resolved_data_root = Path(data_root) if data_root is not None else get_data_root()
    # Prioritize high-fidelity discovery metrics for research runs
    phase2_path = resolved_data_root / "reports" / "phase2" / run_id / "search_engine" / "phase2_candidates.parquet"
    promotion_path = resolved_data_root / "reports" / "promotions" / run_id / "promotion_statistical_audit.parquet"
    edge_path = resolved_data_root / "reports" / "edge_candidates" / run_id / "edge_candidates_normalized.parquet"
    
    df = _read_best_available(phase2_path)
    if df.empty:
        df = _read_best_available(promotion_path)
    if df.empty:
        df = _read_best_available(edge_path)
    if df.empty:
        # Fallback for old directory structure or specific event discovery
        discovery_paths = list((resolved_data_root / "reports" / "phase2" / run_id).glob("**/phase2_candidates.parquet"))
        for p in discovery_paths:
            df = _read_best_available(p)
            if not df.empty:
                break

    if df.empty:
        return pd.DataFrame(columns=TESTED_REGION_COLUMNS)

    records: List[Dict[str, Any]] = []
    for row in df.to_dict(orient="records"):
        context_raw = row.get("context_json", row.get("contexts", row.get("context", {})))
        if context_raw is None or context_raw == "":
            context_raw = {}
        context_blob = canonical_json(context_raw)
        payload = {
            "program_id": program_id,
            "symbol_scope": str(row.get("symbol", row.get("symbols", ""))).strip(),
            "event_type": str(row.get("event_type", row.get("event", ""))).strip(),
            "trigger_type": str(row.get("trigger_type", "EVENT")).strip().upper() or "EVENT",
            "template_id": str(row.get("template_id", row.get("template", ""))).strip(),
            "direction": str(row.get("direction", "")).strip(),
            "horizon": str(row.get("horizon", row.get("timeframe", ""))).strip(),
            "entry_lag": int(row.get("entry_lag", row.get("entry_lag_bars", 0)) or 0),
            "context_hash": str(row.get("context_hash", "")) or stable_hash((context_blob,)),
            "context_json": context_blob,
        }
        records.append(
            {
                "region_key": region_key(payload),
                "program_id": program_id,
                "run_id": run_id,
                "hypothesis_id": str(row.get("hypothesis_id", row.get("plan_row_id", ""))).strip(),
                "candidate_id": str(row.get("candidate_id", "")).strip(),
                "symbol_scope": payload["symbol_scope"],
                "event_type": payload["event_type"],
                "trigger_type": payload["trigger_type"],
                "template_id": payload["template_id"],
                "direction": payload["direction"],
                "horizon": payload["horizon"],
                "entry_lag": payload["entry_lag"],
                "context_hash": payload["context_hash"],
                "context_json": payload["context_json"],
                "eval_status": str(row.get("promotion_decision", row.get("eval_status", "evaluated"))).strip() or "evaluated",
                "train_n_obs": int(row.get("train_n_obs", row.get("sample_size", 0)) or 0),
                "validation_n_obs": int(row.get("validation_n_obs", row.get("validation_samples", 0)) or 0),
                "test_n_obs": int(row.get("test_n_obs", row.get("test_samples", 0)) or 0),
                "q_value": pd.to_numeric(row.get("q_value"), errors="coerce"),
                "mean_return_bps": pd.to_numeric(
                    row.get("mean_return_bps", row.get("bridge_validation_after_cost_bps", row.get("net_expectancy_bps"))),
                    errors="coerce",
                ),
                "after_cost_expectancy": pd.to_numeric(
                    row.get("after_cost_expectancy", row.get("after_cost_expectancy_per_trade", row.get("net_expectancy_bps"))),
                    errors="coerce",
                ),
                "stressed_after_cost_expectancy": pd.to_numeric(
                    row.get("stressed_after_cost_expectancy", row.get("stressed_after_cost_expectancy_per_trade", row.get("bridge_validation_stressed_after_cost_bps"))),
                    errors="coerce",
                ),
                "robustness_score": pd.to_numeric(
                    row.get("robustness_score", row.get("stability_score")),
                    errors="coerce",
                ),
                "gate_bridge_tradable": bool(row.get("gate_bridge_tradable") == "pass"),
                "gate_promo_statistical": bool(row.get("gate_promo_statistical") == "pass"),
                "gate_promo_retail_net_expectancy": bool(row.get("gate_promo_retail_net_expectancy") == "pass" or row.get("gate_promo_retail_net_expectancy") is True),
                "mechanical_status": "ok",
                "primary_fail_gate": str(row.get("promotion_fail_gate_primary", row.get("primary_fail_gate", ""))).strip(),
                "warning_count": int(row.get("warning_count", 0) or 0),
                "updated_at": str(row.get("updated_at", "")),
            }
        )
    return pd.DataFrame(records).reindex(columns=TESTED_REGION_COLUMNS)


def build_failures_snapshot(
    *,
    run_id: str,
    program_id: str,
    data_root: Path | None = None,
) -> pd.DataFrame:
    resolved_data_root = Path(data_root) if data_root is not None else get_data_root()
    manifest_path = resolved_data_root / "runs" / run_id / "run_manifest.json"
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            manifest = {}
    else:
        manifest = load_run_manifest(run_id)
    rows: List[Dict[str, Any]] = []
    failed_stage = str(manifest.get("failed_stage", "")).strip()
    if failed_stage:
        rows.append(
            {
                "run_id": run_id,
                "program_id": program_id,
                "stage": failed_stage,
                "failure_class": "run_failed_stage",
                "failure_detail": str(manifest.get("error_message", "")).strip(),
                "artifact_path": str(resolved_data_root / "runs" / run_id / f"{failed_stage}.json"),
                "is_mechanical": True,
                "is_repeated": False,
                "superseded_by_run_id": "",
            }
        )
    stage_dir = resolved_data_root / "runs" / run_id
    if stage_dir.exists():
        for path in sorted(stage_dir.glob("*.json")):
            if path.name == "run_manifest.json":
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if str(payload.get("status", "")).strip().lower() != "failed":
                continue
            rows.append(
                {
                    "run_id": run_id,
                    "program_id": program_id,
                    "stage": str(payload.get("stage", path.stem)),
                    "failure_class": "stage_failed",
                    "failure_detail": str(payload.get("error_message", payload.get("traceback", ""))).strip(),
                    "artifact_path": str(path),
                    "is_mechanical": True,
                    "is_repeated": False,
                    "superseded_by_run_id": "",
                }
            )
    return pd.DataFrame(rows).reindex(columns=FAILURE_COLUMNS)


def _dominant_fail_gate(series: pd.Series) -> str:
    cleaned = series.dropna().astype(str).str.strip()
    cleaned = cleaned[cleaned != ""]
    if cleaned.empty:
        return ""
    return str(cleaned.value_counts().idxmax())


def compute_region_statistics(tested_regions: pd.DataFrame) -> pd.DataFrame:
    if tested_regions.empty:
        return pd.DataFrame(columns=_TABLES["region_statistics"])
    grouped = tested_regions.groupby("region_key", dropna=False)
    out = grouped.agg(
        runs_tested=("run_id", "nunique"),
        times_evaluated=("candidate_id", "count"),
        times_promoted=("eval_status", lambda s: int((s.astype(str) == "promoted").sum())),
        avg_q_value=("q_value", "mean"),
        avg_after_cost_expectancy=("after_cost_expectancy", "mean"),
        avg_robustness_score=("robustness_score", "mean"),
        dominant_fail_gate=("primary_fail_gate", _dominant_fail_gate),
        last_tested_at=("updated_at", "max"),
    ).reset_index()
    out["eval_rate"] = out["times_evaluated"] / out["runs_tested"].clip(lower=1)
    out["promotion_rate"] = out["times_promoted"] / out["times_evaluated"].clip(lower=1)
    return out.reindex(columns=_TABLES["region_statistics"])


def _aggregate_dimension(tested_regions: pd.DataFrame, column: str, output_columns: List[str]) -> pd.DataFrame:
    if tested_regions.empty:
        return pd.DataFrame(columns=output_columns)
    grouped = tested_regions.groupby(column, dropna=False)
    out = grouped.agg(
        runs_tested=("run_id", "nunique"),
        times_evaluated=("candidate_id", "count"),
        times_promoted=("eval_status", lambda s: int((s.astype(str) == "promoted").sum())),
        avg_q_value=("q_value", "mean"),
        avg_after_cost_expectancy=("after_cost_expectancy", "mean"),
        dominant_fail_gate=("primary_fail_gate", _dominant_fail_gate),
    ).reset_index()
    return out.reindex(columns=output_columns)


def compute_event_statistics(tested_regions: pd.DataFrame) -> pd.DataFrame:
    return _aggregate_dimension(tested_regions, "event_type", _TABLES["event_statistics"])


def compute_template_statistics(tested_regions: pd.DataFrame) -> pd.DataFrame:
    return _aggregate_dimension(tested_regions, "template_id", _TABLES["template_statistics"])


def compute_context_statistics(tested_regions: pd.DataFrame) -> pd.DataFrame:
    if tested_regions.empty:
        return pd.DataFrame(columns=_TABLES["context_statistics"])
    grouped = tested_regions.groupby(["context_hash", "context_json"], dropna=False)
    out = grouped.agg(
        runs_tested=("run_id", "nunique"),
        times_evaluated=("candidate_id", "count"),
        times_promoted=("eval_status", lambda s: int((s.astype(str) == "promoted").sum())),
        avg_q_value=("q_value", "mean"),
        avg_after_cost_expectancy=("after_cost_expectancy", "mean"),
        dominant_fail_gate=("primary_fail_gate", _dominant_fail_gate),
    ).reset_index()
    return out.reindex(columns=_TABLES["context_statistics"])
