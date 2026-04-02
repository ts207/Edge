from __future__ import annotations

import contextlib
import json
import shutil
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

import pandas as pd

from project import PROJECT_ROOT
from project.artifacts import run_manifest_path
from project.core.config import get_data_root
from project.operator.preflight import run_preflight
from project.operator.proposal_tools import explain_proposal, lint_proposal
from project.operator.stability import (
    build_negative_result_diagnostics,
    build_regime_split_report,
    build_time_slice_report,
)
from project.research.agent_io.issue_proposal import issue_proposal
from project.research.agent_io.proposal_to_experiment import translate_and_validate_proposal


def _path_or_none(value: str | None) -> Path | None:
    if value is None:
        return None
    text = str(value).strip()
    return Path(text) if text else None


@contextmanager
def _scratch_dir(preferred: str | None) -> Iterator[Path]:
    preferred_path = _path_or_none(preferred)
    if preferred_path is not None:
        preferred_path.mkdir(parents=True, exist_ok=True)
        yield preferred_path
        return
    with tempfile.TemporaryDirectory(prefix="edge_chatgpt_") as tmp_dir:
        yield Path(tmp_dir)


def _resolve_data_root(value: str | None) -> Path:
    return _path_or_none(value) or get_data_root()


def _read_json_dict(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_table(path: Path) -> pd.DataFrame:
    if path.exists():
        try:
            return pd.read_parquet(path)
        except Exception:
            pass
    csv_path = path.with_suffix(".csv")
    if csv_path.exists():
        try:
            return pd.read_csv(csv_path)
        except Exception:
            pass
    return pd.DataFrame()


def _clean_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, dict):
        return {str(key): _clean_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_clean_value(item) for item in value]
    if hasattr(value, "item"):
        try:
            return _clean_value(value.item())
        except Exception:
            pass
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            pass
    if isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _sort_records(records: list[dict[str, Any]], *keys: str) -> list[dict[str, Any]]:
    return sorted(
        records,
        key=lambda row: tuple(str(row.get(key) or "") for key in keys),
        reverse=True,
    )


def _repo_root() -> Path:
    return PROJECT_ROOT.parent


def _coerce_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _normalize_timeout_sec(value: Any) -> int:
    if value is None:
        return 300
    try:
        normalized = int(value)
    except (TypeError, ValueError):
        return 300
    return max(15, min(3600, normalized))


def _normalize_limit(value: Any) -> int:
    if value is None:
        return 8
    try:
        normalized = int(value)
    except (TypeError, ValueError):
        return 8
    return max(1, min(24, normalized))


def _parse_json_like(value: Any) -> Any:
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        if text[:1] in {"{", "["}:
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return value
    return value


def _normalize_summary(value: Any) -> dict[str, Any]:
    candidate = _parse_json_like(value)
    if candidate is None:
        return {}
    if isinstance(candidate, dict):
        return _clean_value(candidate)
    if isinstance(candidate, list):
        with contextlib.suppress(TypeError, ValueError):
            return _clean_value(dict(candidate))
        return {"items": _clean_value(candidate)}
    return {"text": _clean_value(candidate)}


def _normalize_sections(value: Any) -> list[dict[str, Any]]:
    candidate = _parse_json_like(value)
    if candidate is None:
        return []
    if isinstance(candidate, dict):
        if "heading" in candidate or "body" in candidate:
            return [
                {
                    "heading": str(candidate.get("heading") or "Details"),
                    "body": str(_clean_value(candidate.get("body")) or ""),
                }
            ]
        return [
            {
                "heading": str(key),
                "body": str(_clean_value(item) or ""),
            }
            for key, item in candidate.items()
        ]
    if isinstance(candidate, list):
        normalized: list[dict[str, Any]] = []
        for index, item in enumerate(candidate, start=1):
            if isinstance(item, dict):
                heading = item.get("heading") or item.get("title") or item.get("label") or f"Section {index}"
                body = item.get("body")
                if body is None:
                    body = item.get("text")
                if body is None:
                    body = item.get("content")
                if body is None:
                    body = json.dumps(_clean_value(item), sort_keys=True)
                normalized.append({"heading": str(heading), "body": str(_clean_value(body) or "")})
                continue
            normalized.append(
                {
                    "heading": f"Section {index}",
                    "body": str(_clean_value(item) or ""),
                }
            )
        return normalized
    return [{"heading": "Details", "body": str(_clean_value(candidate) or "")}]


def _memory_root(program_id: str, data_root: Path) -> Path:
    return data_root / "artifacts" / "experiments" / str(program_id) / "memory"


def _dashboard_status(run_summary: dict[str, Any]) -> str | None:
    status = str(run_summary.get("status") or "").strip().lower()
    if status in {"success", "executed", "completed"}:
        return "pass"
    if status in {"warning", "warn"} or str(run_summary.get("mechanical_outcome") or "").strip().lower() == "warning_only":
        return "warn"
    if status in {"failed", "error", "aborted_stale_run"}:
        return "fail"
    return None


def _limit_frame(df: pd.DataFrame, *, sort_by: str, limit: int) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    if sort_by in out.columns:
        out = out.sort_values(by=sort_by, ascending=False, na_position="last")
    return out.head(limit)


def _project_program_ids(data_root: Path, run_summaries: list[dict[str, Any]]) -> list[str]:
    program_ids = {
        str(run.get("program_id") or "").strip()
        for run in run_summaries
        if str(run.get("program_id") or "").strip()
    }
    experiments_root = data_root / "artifacts" / "experiments"
    if experiments_root.exists():
        for path in sorted(experiments_root.iterdir()):
            if path.is_dir() and (path / "memory").exists():
                program_ids.add(path.name)
    return sorted(program_ids)


def _proposal_records(program_id: str, data_root: Path, *, limit: int) -> tuple[int, list[dict[str, Any]]]:
    proposals_path = _memory_root(program_id, data_root) / "proposals.parquet"
    proposals = _read_table(proposals_path)
    if proposals.empty:
        return 0, []
    for column in (
        "run_id",
        "status",
        "issued_at",
        "objective_name",
        "promotion_profile",
        "symbols",
        "experiment_type",
        "allowed_change_field",
        "baseline_run_id",
        "decision",
        "mutation_type",
        "plan_only",
        "dry_run",
        "returncode",
        "proposal_path",
    ):
        if column not in proposals.columns:
            proposals[column] = None
    rows = _limit_frame(proposals, sort_by="issued_at", limit=limit)[
        [
            "run_id",
            "status",
            "issued_at",
            "objective_name",
            "promotion_profile",
            "symbols",
            "experiment_type",
            "allowed_change_field",
            "baseline_run_id",
            "decision",
            "mutation_type",
            "plan_only",
            "dry_run",
            "returncode",
            "proposal_path",
        ]
    ].to_dict("records")
    return int(len(proposals.index)), [_clean_value(row) for row in rows]


def _memory_snapshot(program_id: str, data_root: Path, *, limit: int) -> dict[str, Any]:
    root = _memory_root(program_id, data_root)
    belief_state = _read_json_dict(root / "belief_state.json")
    next_actions = _read_json_dict(root / "next_actions.json")
    reflections = _read_table(root / "reflections.parquet")
    evidence = _read_table(root / "evidence_ledger.parquet")

    if not reflections.empty:
        for column in (
            "created_at",
            "run_id",
            "run_status",
            "market_findings",
            "system_findings",
            "recommended_next_action",
            "recommended_next_experiment",
            "confidence",
        ):
            if column not in reflections.columns:
                reflections[column] = None
        reflection_rows = _limit_frame(reflections, sort_by="created_at", limit=limit)[
            [
                "created_at",
                "run_id",
                "run_status",
                "market_findings",
                "system_findings",
                "recommended_next_action",
                "recommended_next_experiment",
                "confidence",
            ]
        ].to_dict("records")
    else:
        reflection_rows = []

    if not evidence.empty:
        for column in (
            "updated_at",
            "run_id",
            "verdict",
            "recommended_next_action",
            "recommended_next_experiment",
            "terminal_status",
            "promoted_count",
            "candidate_count",
            "negative_diagnosis",
        ):
            if column not in evidence.columns:
                evidence[column] = None
        evidence_rows = _limit_frame(evidence, sort_by="updated_at", limit=limit)[
            [
                "updated_at",
                "run_id",
                "verdict",
                "recommended_next_action",
                "recommended_next_experiment",
                "terminal_status",
                "promoted_count",
                "candidate_count",
                "negative_diagnosis",
            ]
        ].to_dict("records")
    else:
        evidence_rows = []

    return {
        "available": root.exists(),
        "belief_state": _clean_value(belief_state),
        "next_actions": _clean_value(next_actions),
        "recent_reflections": [_clean_value(row) for row in reflection_rows],
        "recent_evidence": [_clean_value(row) for row in evidence_rows],
        "paths": {
            "root": str(root),
            "belief_state": str(root / "belief_state.json"),
            "next_actions": str(root / "next_actions.json"),
            "proposals": str(root / "proposals.parquet"),
        },
    }


def _run_summary(manifest: dict[str, Any], run_id_hint: str | None = None) -> dict[str, Any]:
    run_id = str(manifest.get("run_id") or run_id_hint or "").strip()
    symbols = manifest.get("normalized_symbols") or []
    if not isinstance(symbols, list):
        symbols = []
    return _clean_value(
        {
            "run_id": run_id,
            "program_id": manifest.get("program_id"),
            "status": manifest.get("status") or manifest.get("run_status"),
            "mechanical_outcome": manifest.get("mechanical_outcome"),
            "checklist_decision": manifest.get("checklist_decision"),
            "failed_stage": manifest.get("failed_stage"),
            "objective_name": manifest.get("objective_name"),
            "objective_id": manifest.get("objective_id"),
            "promotion_profile": manifest.get("promotion_profile"),
            "experiment_type": manifest.get("experiment_type"),
            "start": manifest.get("start"),
            "end": manifest.get("end"),
            "finished_at": manifest.get("finished_at"),
            "started_at": manifest.get("started_at"),
            "planned_stage_count": manifest.get("planned_stage_count"),
            "completed_stage_count": manifest.get("completed_stage_count"),
            "artifact_count": manifest.get("artifact_count"),
            "candidate_count": manifest.get("candidate_count") or manifest.get("exported_candidate_count"),
            "promoted_count": manifest.get("promoted_count"),
            "normalized_symbols": symbols,
            "normalized_timeframes": manifest.get("normalized_timeframes") or [],
            "symbols_label": ", ".join(str(symbol) for symbol in symbols[:4]),
        }
    )


def _recent_run_summaries(data_root: Path, *, program_id: str | None = None, limit: int) -> list[dict[str, Any]]:
    runs_root = data_root / "runs"
    if not runs_root.exists():
        return []
    records: list[dict[str, Any]] = []
    for manifest_path in sorted(runs_root.glob("*/run_manifest.json")):
        manifest = _read_json_dict(manifest_path)
        if not manifest:
            continue
        summary = _run_summary(manifest, manifest_path.parent.name)
        if program_id and str(summary.get("program_id") or "").strip() != str(program_id).strip():
            continue
        records.append(summary)
    return _sort_records(records, "finished_at", "started_at", "run_id")[:limit]


def _selected_run_snapshot(run_id: str | None, data_root: Path) -> dict[str, Any]:
    resolved_run_id = str(run_id or "").strip()
    if not resolved_run_id:
        return {}
    manifest = _read_json_dict(run_manifest_path(resolved_run_id, data_root))
    if not manifest:
        return {}
    summary = _run_summary(manifest, resolved_run_id)
    summary["effective_behavior"] = _clean_value(manifest.get("effective_behavior") or {})
    summary["objective_hard_gates"] = _clean_value(manifest.get("objective_hard_gates") or {})
    summary["paths"] = _clean_value(
        {
            "manifest": str(run_manifest_path(resolved_run_id, data_root)),
            "effective_config": manifest.get("effective_config_path"),
            "objective_spec": manifest.get("objective_spec_path"),
            "experiment_config": (
                (manifest.get("config_resolution") or {}).get("experiment_config_path")
                if isinstance(manifest.get("config_resolution"), dict)
                else None
            ),
        }
    )
    summary["planned_stage_instances"] = _clean_value(list(manifest.get("planned_stage_instances") or [])[:12])
    return summary


def _parse_codex_events(stdout: str) -> dict[str, Any]:
    thread_id = ""
    last_agent_message = ""
    usage: dict[str, Any] = {}
    event_types: list[str] = []

    for line in str(stdout or "").splitlines():
        text = str(line).strip()
        if not text or not text.startswith("{"):
            continue
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            continue
        event_type = str(payload.get("type") or "").strip()
        if event_type:
            event_types.append(event_type)
        if event_type == "thread.started":
            thread_id = str(payload.get("thread_id") or thread_id)
        elif event_type == "item.completed":
            item = payload.get("item") if isinstance(payload.get("item"), dict) else {}
            if str(item.get("type") or "").strip() == "agent_message":
                last_agent_message = str(item.get("text") or last_agent_message)
        elif event_type == "turn.completed" and isinstance(payload.get("usage"), dict):
            usage = dict(payload["usage"])

    return {
        "thread_id": thread_id or None,
        "last_agent_message": last_agent_message,
        "usage": _clean_value(usage),
        "event_types": event_types,
    }


def _snapshot_operator_state(data_root: Path) -> dict[str, Any]:
    recent_runs = _recent_run_summaries(data_root, limit=50)
    proposal_counts: dict[str, int] = {}
    for program_id in _project_program_ids(data_root, recent_runs):
        proposal_count, _ = _proposal_records(program_id, data_root, limit=1)
        proposal_counts[str(program_id)] = int(proposal_count)
    return {
        "data_root": str(data_root),
        "recent_run_ids": [
            str(run.get("run_id"))
            for run in recent_runs
            if str(run.get("run_id") or "").strip()
        ],
        "proposal_counts": proposal_counts,
    }


def _diff_operator_state(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    before_run_ids = {
        str(run_id)
        for run_id in list(before.get("recent_run_ids") or [])
        if str(run_id).strip()
    }
    after_run_ids = [
        str(run_id)
        for run_id in list(after.get("recent_run_ids") or [])
        if str(run_id).strip()
    ]
    new_run_ids = [run_id for run_id in after_run_ids if run_id not in before_run_ids]

    before_counts = {
        str(program_id): int(count)
        for program_id, count in dict(before.get("proposal_counts") or {}).items()
    }
    after_counts = {
        str(program_id): int(count)
        for program_id, count in dict(after.get("proposal_counts") or {}).items()
    }
    proposal_memory_changes: list[dict[str, Any]] = []
    for program_id in sorted(set(before_counts) | set(after_counts)):
        before_count = int(before_counts.get(program_id, 0))
        after_count = int(after_counts.get(program_id, 0))
        if after_count > before_count:
            proposal_memory_changes.append(
                {
                    "program_id": program_id,
                    "before_count": before_count,
                    "after_count": after_count,
                    "delta": after_count - before_count,
                }
            )

    return {
        "data_root": str(after.get("data_root") or before.get("data_root") or ""),
        "new_run_ids": new_run_ids,
        "proposal_memory_changes": proposal_memory_changes,
        "dashboard_changed": bool(new_run_ids or proposal_memory_changes),
    }


def invoke_codex_operator(
    *,
    task: str,
    sandbox: str = "workspace-write",
    model: str | None = None,
    profile: str | None = None,
    timeout_sec: int = 300,
) -> dict[str, Any]:
    codex_path = shutil.which("codex")
    if codex_path is None:
        raise RuntimeError("The `codex` CLI is not installed or not on PATH.")
    normalized_timeout_sec = _normalize_timeout_sec(timeout_sec)
    resolved_data_root = _resolve_data_root(None)
    before_state = _snapshot_operator_state(resolved_data_root)

    with tempfile.NamedTemporaryFile(prefix="edge_codex_last_", suffix=".txt", delete=False) as handle:
        last_message_path = Path(handle.name)

    command = [
        codex_path,
        "exec",
        "--json",
        "--color",
        "never",
        "--ephemeral",
        "--sandbox",
        str(sandbox),
        "--cd",
        str(_repo_root()),
        "--output-last-message",
        str(last_message_path),
    ]
    if model:
        command.extend(["--model", str(model)])
    if profile:
        command.extend(["--profile", str(profile)])
    command.append(str(task))

    completed: subprocess.CompletedProcess[str] | None = None
    timeout_hit = False
    stdout_text = ""
    stderr_text = ""
    try:
        completed = subprocess.run(
            command,
            cwd=str(_repo_root()),
            capture_output=True,
            text=True,
            check=False,
            timeout=normalized_timeout_sec,
        )
        stdout_text = _coerce_text(completed.stdout)
        stderr_text = _coerce_text(completed.stderr).strip()
    except subprocess.TimeoutExpired as exc:
        timeout_hit = True
        stdout_text = _coerce_text(getattr(exc, "stdout", None) or getattr(exc, "output", None))
        stderr_text = _coerce_text(getattr(exc, "stderr", None)).strip()

    parsed = _parse_codex_events(stdout_text)
    try:
        last_message_file = last_message_path.read_text(encoding="utf-8").strip()
    except OSError:
        last_message_file = ""
    finally:
        with contextlib.suppress(OSError):
            last_message_path.unlink()

    final_message = last_message_file or str(parsed.get("last_agent_message") or "")
    after_state = _snapshot_operator_state(resolved_data_root)
    post_run_probe = _diff_operator_state(before_state, after_state)

    return {
        "status": (
            "timeout"
            if timeout_hit
            else "success" if completed and completed.returncode == 0 else "failed"
        ),
        "exit_code": None if completed is None else int(completed.returncode),
        "task": str(task),
        "sandbox": str(sandbox),
        "model": str(model) if model else None,
        "profile": str(profile) if profile else None,
        "timeout_sec": normalized_timeout_sec,
        "timed_out": timeout_hit,
        "repo_root": str(_repo_root()),
        "thread_id": parsed.get("thread_id"),
        "final_message": final_message,
        "stderr": stderr_text or None,
        "usage": parsed.get("usage") or {},
        "event_types": list(parsed.get("event_types") or []),
        "post_run_probe": post_run_probe,
    }


def get_operator_dashboard(
    *,
    program_id: str | None = None,
    run_id: str | None = None,
    data_root: str | None = None,
    limit: int = 8,
) -> dict[str, Any]:
    resolved_data_root = _resolve_data_root(data_root)
    normalized_limit = _normalize_limit(limit)
    initial_runs = _recent_run_summaries(resolved_data_root, limit=200)
    selected_run = _selected_run_snapshot(run_id, resolved_data_root)

    requested_program = str(program_id or "").strip() or str(selected_run.get("program_id") or "").strip()
    program_ids = _project_program_ids(resolved_data_root, initial_runs)

    program_cards: list[dict[str, Any]] = []
    for candidate_program in program_ids:
        proposal_count, candidate_proposals = _proposal_records(candidate_program, resolved_data_root, limit=1)
        candidate_runs = [row for row in initial_runs if str(row.get("program_id") or "") == candidate_program]
        latest_run = candidate_runs[0] if candidate_runs else {}
        memory = _memory_snapshot(candidate_program, resolved_data_root, limit=min(normalized_limit, 3))
        next_actions = memory.get("next_actions") if isinstance(memory.get("next_actions"), dict) else {}
        belief_state = memory.get("belief_state") if isinstance(memory.get("belief_state"), dict) else {}
        program_cards.append(
            _clean_value(
                {
                    "program_id": candidate_program,
                    "proposal_count": proposal_count,
                    "recent_run_count": len(candidate_runs),
                    "latest_proposal_at": (candidate_proposals[0].get("issued_at") if candidate_proposals else None),
                    "latest_run_id": latest_run.get("run_id"),
                    "latest_run_status": latest_run.get("status"),
                    "latest_run_finished_at": latest_run.get("finished_at") or latest_run.get("started_at"),
                    "repair_count": len(list((next_actions or {}).get("repair") or [])),
                    "exploit_count": len(list((next_actions or {}).get("exploit") or [])),
                    "promising_region_count": len(list((belief_state or {}).get("promising_regions") or [])),
                }
            )
        )

    program_cards = _sort_records(program_cards, "latest_run_finished_at", "latest_proposal_at", "program_id")
    active_program_id = requested_program or (program_cards[0]["program_id"] if program_cards else "")
    recent_runs = _recent_run_summaries(
        resolved_data_root,
        program_id=active_program_id or None,
        limit=normalized_limit,
    )
    proposal_count = 0
    recent_proposals: list[dict[str, Any]] = []
    memory: dict[str, Any] = {}
    if active_program_id:
        proposal_count, recent_proposals = _proposal_records(
            active_program_id,
            resolved_data_root,
            limit=normalized_limit,
        )
        memory = _memory_snapshot(active_program_id, resolved_data_root, limit=normalized_limit)

    if not selected_run and recent_runs:
        selected_run = _selected_run_snapshot(str(recent_runs[0].get("run_id") or ""), resolved_data_root)

    current_status = _dashboard_status(selected_run or {})
    subtitle = (
        f"Memory and prior results at {resolved_data_root}"
        if active_program_id
        else f"No program selected. Showing available Edge history at {resolved_data_root}"
    )

    return {
        "layout": "dashboard",
        "title": active_program_id or "Edge Operator Dashboard",
        "status": current_status,
        "subtitle": subtitle,
        "summary": {
            "active_program": active_program_id or "none",
            "known_programs": len(program_cards),
            "recent_runs": len(recent_runs),
            "recent_proposals": proposal_count,
            "selected_run": selected_run.get("run_id") or "none",
        },
        "data_root": str(resolved_data_root),
        "active_program_id": active_program_id or None,
        "programs": program_cards,
        "memory": memory,
        "recent_proposals": recent_proposals,
        "recent_runs": recent_runs,
        "selected_run": selected_run,
        "source_tool": "edge_get_operator_dashboard",
    }


def preflight_proposal(
    *,
    proposal: str,
    registry_root: str = "project/configs/registries",
    data_root: str | None = None,
    out_dir: str | None = None,
    json_output: str | None = None,
) -> dict[str, Any]:
    with _scratch_dir(out_dir) as scratch_dir:
        return run_preflight(
            proposal_path=proposal,
            registry_root=registry_root,
            data_root=data_root,
            out_dir=scratch_dir,
            json_output=json_output,
        )


def explain_proposal_summary(
    *,
    proposal: str,
    registry_root: str = "project/configs/registries",
    data_root: str | None = None,
    out_dir: str | None = None,
) -> dict[str, Any]:
    with _scratch_dir(out_dir) as scratch_dir:
        return explain_proposal(
            proposal_path=proposal,
            registry_root=registry_root,
            data_root=data_root,
            out_dir=scratch_dir,
        )


def lint_proposal_summary(
    *,
    proposal: str,
    registry_root: str = "project/configs/registries",
    data_root: str | None = None,
    out_dir: str | None = None,
) -> dict[str, Any]:
    with _scratch_dir(out_dir) as scratch_dir:
        return lint_proposal(
            proposal_path=proposal,
            registry_root=registry_root,
            data_root=data_root,
            out_dir=scratch_dir,
        )


def preview_plan(
    *,
    proposal: str,
    registry_root: str = "project/configs/registries",
    data_root: str | None = None,
    out_dir: str | None = None,
    include_experiment_config: bool = True,
) -> dict[str, Any]:
    del data_root
    with _scratch_dir(out_dir) as scratch_dir:
        translated = translate_and_validate_proposal(
            proposal,
            registry_root=Path(registry_root),
            out_dir=scratch_dir,
            config_path=scratch_dir / "proposal_preview.yaml",
        )
    payload = {
        "proposal": translated["proposal"],
        "validated_plan": translated["validated_plan"],
        "run_all_overrides": translated["run_all_overrides"],
        "ephemeral": True,
    }
    if include_experiment_config:
        payload["experiment_config"] = translated["experiment_config"]
    return payload


def issue_plan(
    *,
    proposal: str,
    registry_root: str = "project/configs/registries",
    data_root: str | None = None,
    run_id: str | None = None,
    check: bool = False,
) -> dict[str, Any]:
    return issue_proposal(
        proposal,
        registry_root=Path(registry_root),
        data_root=_path_or_none(data_root),
        run_id=run_id,
        plan_only=True,
        dry_run=False,
        check=check,
    )


def issue_run(
    *,
    proposal: str,
    registry_root: str = "project/configs/registries",
    data_root: str | None = None,
    run_id: str | None = None,
    check: bool = False,
) -> dict[str, Any]:
    return issue_proposal(
        proposal,
        registry_root=Path(registry_root),
        data_root=_path_or_none(data_root),
        run_id=run_id,
        plan_only=False,
        dry_run=False,
        check=check,
    )


def get_negative_result_diagnostics(
    *,
    run_id: str,
    program_id: str | None = None,
    data_root: str | None = None,
) -> dict[str, Any]:
    return build_negative_result_diagnostics(
        run_id=run_id,
        program_id=program_id,
        data_root=_path_or_none(data_root),
    )


def get_regime_report(
    *,
    run_id: str,
    data_root: str | None = None,
) -> dict[str, Any]:
    return build_regime_split_report(
        run_id=run_id,
        data_root=_path_or_none(data_root),
    )


def compare_runs(
    *,
    run_ids: list[str],
    program_id: str | None = None,
    data_root: str | None = None,
) -> dict[str, Any]:
    return build_time_slice_report(
        run_ids=run_ids,
        program_id=program_id,
        data_root=_path_or_none(data_root),
    )


def render_operator_summary(
    *,
    dashboard: dict[str, Any] | None = None,
    title: str | None = None,
    status: str | None = None,
    subtitle: str | None = None,
    summary: dict[str, Any] | None = None,
    sections: list[dict[str, str]] | None = None,
    source_tool: str | None = None,
) -> dict[str, Any]:
    normalized_dashboard = _parse_json_like(dashboard)
    if isinstance(normalized_dashboard, dict) and normalized_dashboard:
        payload = dict(normalized_dashboard)
        payload.setdefault("layout", "dashboard")
        payload.setdefault("widget", "operator_dashboard")
        payload.setdefault("source_tool", source_tool or payload.get("source_tool"))
        payload["summary"] = _normalize_summary(payload.get("summary"))
        payload["sections"] = _normalize_sections(payload.get("sections"))
        return payload

    return {
        "title": title,
        "status": status,
        "subtitle": subtitle,
        "summary": _normalize_summary(summary),
        "sections": _normalize_sections(sections),
        "source_tool": source_tool,
        "widget": "operator_dashboard",
    }
