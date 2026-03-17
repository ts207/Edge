from __future__ import annotations

import concurrent.futures
import hashlib
import json
import os
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from functools import lru_cache
from json import JSONDecodeError
from pathlib import Path
from typing import Callable, Dict, List, Mapping, Sequence, Tuple
from project.pipelines.planner import StageDefinition

from project import PROJECT_ROOT
from project.pipelines.pipeline_defaults import DATA_ROOT
from project.specs.manifest import validate_stage_manifest_contract

StageLaunch = Tuple[str, str, Path, List[str]]
WorkerArgs = Tuple[str, str, Path, List[str], str]
WorkerResult = Tuple[str, str, bool, float, Dict[str, object]]
StageTiming = Tuple[str, str, float, Dict[str, object]]
PartitionMapFn = Callable[[str, Sequence[object]], object]
PartitionReduceFn = Callable[[List[object]], object]

_RUNNING_STAGE_PROCS: Dict[Tuple[str, str], subprocess.Popen[str]] = {}
_RUNNING_STAGE_PROCS_LOCK = threading.Lock()
_STAGE_OUTPUT_LOCK = threading.Lock()

def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _base_args_to_parameters(base_args: List[str]) -> Dict[str, object]:
    """Best-effort CLI arg decoding for synthesized stage manifests."""
    params: Dict[str, object] = {}
    idx = 0
    while idx < len(base_args):
        token = str(base_args[idx])
        if token.startswith("--"):
            key = token[2:]
            value: object = True
            if idx + 1 < len(base_args) and not str(base_args[idx + 1]).startswith("--"):
                value = str(base_args[idx + 1])
                idx += 1
            params[key] = value
        idx += 1
    return params

def _required_stage_manifest_enabled() -> bool:
    return str(os.environ.get("BACKTEST_REQUIRE_STAGE_MANIFEST", "0")).strip() in {
        "1",
        "true",
        "TRUE",
        "yes",
        "YES",
    }

def _validate_stage_manifest_on_disk(
    manifest_path: Path,
    *,
    allow_failed_minimal: bool,
) -> tuple[bool, str]:
    if not manifest_path.exists():
        return False, f"missing stage manifest: {manifest_path}"
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, JSONDecodeError) as exc:
        return False, f"invalid manifest JSON ({manifest_path}): {exc}"
    if not isinstance(payload, dict):
        return False, f"manifest payload must be an object: {manifest_path}"
    try:
        validate_stage_manifest_contract(
            payload, allow_failed_minimal=allow_failed_minimal
        )
    except ValueError as exc:
        return False, f"manifest schema validation failed ({manifest_path}): {exc}"
    return True, ""

def _synthesize_stage_manifest_if_missing(
    *,
    manifest_path: Path,
    stage: str,
    stage_instance_id: str,
    run_id: str,
    script_path: Path,
    base_args: List[str],
    log_path: Path,
    status: str,
    error: str | None = None,
    input_hash: str | None = None,
) -> None:
    if manifest_path.exists():
        return
    payload: Dict[str, object] = {
        "run_id": run_id,
        "stage": stage,
        "stage_name": stage,
        "stage_instance_id": stage_instance_id,
        "pipeline_session_id": str(os.environ.get("BACKTEST_PIPELINE_SESSION_ID", "")).strip() or None,
        "started_at": _utc_now_iso(),
        "finished_at": _utc_now_iso(),
        "ended_at": _utc_now_iso(),
        "status": status,
        "error": error,
        "parameters": {
            "script_path": str(script_path),
            "argv": list(base_args),
            **_base_args_to_parameters(base_args),
        },
        "inputs": [],
        "outputs": [{"path": str(log_path)}],
        "stats": {"synthesized_manifest": True},
        "input_parquet_hashes": {"files": {}, "truncated": False, "max_files": 32},
        "input_artifact_hashes": {"files": {}, "truncated": False, "max_files": 256},
        "output_artifact_hashes": {"files": {}, "truncated": False, "max_files": 256},
        "spec_hashes": {},
        "ontology_spec_hash": "",
    }
    if input_hash:
        payload["input_hash"] = input_hash
    tmp = manifest_path.with_suffix(manifest_path.suffix + ".tmp")
    try:
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        tmp.replace(manifest_path)
    except OSError:
        try:
            if tmp.exists():
                tmp.unlink()
        except OSError:
            pass

def _register_running_stage_proc(
    run_id: str, stage_instance_id: str, proc: subprocess.Popen[str]
) -> None:
    with _RUNNING_STAGE_PROCS_LOCK:
        _RUNNING_STAGE_PROCS[(run_id, stage_instance_id)] = proc

def _unregister_running_stage_proc(run_id: str, stage_instance_id: str) -> None:
    with _RUNNING_STAGE_PROCS_LOCK:
        _RUNNING_STAGE_PROCS.pop((run_id, stage_instance_id), None)

def _terminate_stage_process(
    run_id: str, stage_instance_id: str, proc: subprocess.Popen[str], grace_sec: float = 5.0
) -> None:
    if proc.poll() is not None:
        return
    try:
        if os.name == "posix":
            os.killpg(proc.pid, signal.SIGTERM)
        else:
            proc.terminate()
    except (OSError, ProcessLookupError, PermissionError):
        pass
    try:
        proc.wait(timeout=max(0.1, float(grace_sec)))
        return
    except subprocess.TimeoutExpired:
        pass
    try:
        if os.name == "posix":
            os.killpg(proc.pid, signal.SIGKILL)
        else:
            proc.kill()
    except (OSError, ProcessLookupError, PermissionError):
        pass
    try:
        proc.wait(timeout=max(0.1, float(grace_sec)))
    except subprocess.TimeoutExpired:
        pass

def terminate_stage_instances(run_id: str, stage_instance_ids: Sequence[str]) -> None:
    with _RUNNING_STAGE_PROCS_LOCK:
        proc_items = [
            (stage_instance_id, _RUNNING_STAGE_PROCS.get((run_id, stage_instance_id)))
            for stage_instance_id in stage_instance_ids
        ]
    for stage_instance_id, proc in proc_items:
        if proc is None:
            continue
        _terminate_stage_process(run_id, stage_instance_id, proc)

def _script_supports_log_path(script_path: Path) -> bool:
    try:
        # Include mtime in cache key to avoid staleness in long-lived processes
        return _script_supports_log_path_cached(script_path, script_path.stat().st_mtime)
    except OSError:
        return False

@lru_cache(maxsize=2048)
def _script_supports_log_path_cached(script_path: Path, mtime: float) -> bool:
    try:
        return "--log_path" in script_path.read_text(encoding="utf-8")
    except OSError:
        return False

@lru_cache(maxsize=2048)
def _script_supports_flag_cached(script_path: Path, flag: str, mtime: float) -> bool:
    import re
    try:
        content = script_path.read_text(encoding="utf-8")
        # Match the flag ONLY if it is not preceded by a '#' on the same line
        # Use lookbehind/lookahead to ensure the flag is not part of a larger word
        # and handle the leading dashes correctly.
        pattern = rf"^(?!.*#).*(?<![\w-]){re.escape(flag)}(?![\w-])"
        return bool(re.search(pattern, content, re.MULTILINE))
    except OSError:
        return False


_DANGEROUS_GLOBAL_FLAGS = {"--config", "--experiment_config", "--override"}


def _filter_unsupported_flags(script_path: Path, base_args: List[str]) -> List[str]:
    """Filters out CLI flags that the script does not explicitly support (naive string check)."""
    try:
        mtime = script_path.stat().st_mtime
    except OSError:
        return base_args

    out = []
    idx = 0
    while idx < len(base_args):
        token = str(base_args[idx])
        if token.startswith("--"):
            # Only filter out 'dangerous' global flags if they are not explicitly mentioned in the script.
            # Core flags like --run_id and --symbols are always passed to avoid breaking scripts
            # that delegate their argument parsing to other modules.
            if token in _DANGEROUS_GLOBAL_FLAGS and not _script_supports_flag_cached(script_path, token, mtime):
                # Skip flag and its potential value
                if idx + 1 < len(base_args) and not str(base_args[idx + 1]).startswith("--"):
                    idx += 1
            else:
                out.append(token)
                if idx + 1 < len(base_args) and not str(base_args[idx + 1]).startswith("--"):
                    out.append(base_args[idx + 1])
                    idx += 1
        else:
            out.append(token)
        idx += 1
    return out


def _flag_value(args: List[str], flag: str) -> str | None:
    try:
        idx = args.index(flag)
    except ValueError:
        return None
    if idx + 1 >= len(args):
        return None
    return str(args[idx + 1]).strip()

def stage_instance_base(stage: str, base_args: List[str]) -> str:
    event_type = _flag_value(base_args, "--event_type")
    if event_type and stage in {
        "build_event_registry",
        "phase2_conditional_hypotheses",
        "bridge_evaluate_phase2",
    }:
        return f"{stage}_{event_type}"
    return stage

def _collect_project_module_hashes(script_path: Path) -> str:
    """
    Parse ``script_path`` for direct ``project.*`` imports and hash their source files.

    Only hashes files for modules directly named in the script's import statements
    (not transitive imports). Missing files are recorded deterministically.
    Returns a single SHA256 digest over all found module hashes, sorted for stability.
    """
    import ast as _ast

    try:
        source = script_path.read_text(encoding="utf-8", errors="replace")
        tree = _ast.parse(source)
    except (OSError, SyntaxError):
        return "parse_error"

    # Collect all project.* module names referenced in top-level imports
    project_modules: set[str] = set()
    for node in _ast.walk(tree):
        if isinstance(node, _ast.Import):
            for alias in node.names:
                if alias.name.startswith("project."):
                    project_modules.add(alias.name)
        elif isinstance(node, _ast.ImportFrom):
            if node.module and node.module.startswith("project."):
                project_modules.add(node.module)

    if not project_modules:
        return "no_project_imports"

    # Walk up from script location to find the repo root (dir containing 'project/')
    repo_root = script_path.resolve().parent
    for _ in range(8):
        if (repo_root / "project").is_dir():
            break
        repo_root = repo_root.parent
    else:
        return "repo_root_not_found"

    # Hash each module file
    hashes: list[str] = []
    for module in sorted(project_modules):
        rel_path = module.replace(".", "/") + ".py"
        abs_path = repo_root / rel_path
        try:
            content = abs_path.read_bytes()
            hashes.append(hashlib.sha256(content).hexdigest())
        except OSError:
            hashes.append(f"missing:{module}")

    combined = "|".join(hashes)
    return hashlib.sha256(combined.encode()).hexdigest()
 
def _manifest_declared_outputs_exist(
    manifest_path: Path,
    payload: Mapping[str, object],
) -> bool:
    outputs = payload.get("outputs")
    if not isinstance(outputs, list) or not outputs:
        return False
    for row in outputs:
        if not isinstance(row, dict):
            return False
        raw_path = str(row.get("path", "")).strip()
        if not raw_path:
            return False
        candidate = Path(raw_path)
        if candidate.is_absolute():
            if not candidate.exists():
                return False
            continue
        if not (manifest_path.parent / candidate).exists() and not (PROJECT_ROOT.parent / candidate).exists():
            return False
    return True


def compute_stage_input_hash(
    script_path: Path,
    base_args: List[str],
    run_id: str,
    *,
    cache_context: Mapping[str, object] | None = None,
) -> str:
    """Hash the stage command + script content + directly-imported module content."""
    try:
        script_hash = hashlib.sha256(script_path.read_bytes()).hexdigest()
    except OSError:
        script_hash = "unknown"
    module_hash = _collect_project_module_hashes(script_path)
    context_payload = json.dumps(dict(cache_context or {}), sort_keys=True, default=str)
    payload = f"{script_path}:{script_hash}:{module_hash}:{' '.join(base_args)}:{run_id}:{context_payload}"
    return hashlib.sha256(payload.encode()).hexdigest()

def is_phase2_stage(stage_name: str) -> bool:
    return stage_name == "phase2_conditional_hypotheses" or stage_name.startswith(
        "phase2_conditional_hypotheses_"
    )

def _emit_buffered_stage_output(stage_instance_id: str, stage: str, text: str) -> None:
    payload = str(text or "").rstrip()
    if not payload:
        return
    prefix = f"[{stage_instance_id}]"
    with _STAGE_OUTPUT_LOCK:
        print(f"{prefix} buffered output ({stage})")
        for line in payload.splitlines():
            print(f"{prefix} {line}")

def run_stage(
    stage: str,
    script_path: Path,
    base_args: List[str],
    run_id: str,
    *,
    data_root: Path,
    strict_recommendations_checklist: bool,
    feature_schema_version: str,
    current_pipeline_session_id: str | None,
    current_stage_instance_id: str | None,
    stage_cache_meta: Dict[str, Dict[str, object]],
    max_attempts: int = 1,
    retry_backoff_sec: float = 0.0,
) -> bool:
    runs_dir = data_root / "runs" / run_id
    runs_dir.mkdir(parents=True, exist_ok=True)
    stage_instance_id = current_stage_instance_id or stage_instance_base(stage, base_args)
    log_path = runs_dir / f"{stage_instance_id}.log"
    manifest_path = runs_dir / f"{stage_instance_id}.json"

    # Stage output caching: skip if manifest exists with matching input_hash.
    # Enable globally with BACKTEST_STAGE_CACHE=1, or for phase2 only with
    # BACKTEST_EVENT_STAGE_CACHE=1.
    stage_cache_enabled = bool(int(os.environ.get("BACKTEST_STAGE_CACHE", "0")))
    event_stage_cache_enabled = bool(
        int(os.environ.get("BACKTEST_EVENT_STAGE_CACHE", "0"))
    ) and is_phase2_stage(stage)
    cache_enabled = stage_cache_enabled or event_stage_cache_enabled
    cache_context = {
        "feature_schema_version": str(feature_schema_version or ""),
        "pipeline_session_id": str(current_pipeline_session_id or ""),
        "require_stage_manifest": _required_stage_manifest_enabled(),
    }
    if cache_enabled:
        input_hash = compute_stage_input_hash(
            script_path,
            base_args,
            run_id,
            cache_context=cache_context,
        )
        if manifest_path.exists():
            try:
                cached = json.loads(manifest_path.read_text(encoding="utf-8"))
                outputs_ok = _manifest_declared_outputs_exist(manifest_path, cached)
                if (
                    cached.get("input_hash") == input_hash
                    and cached.get("status") == "success"
                    and outputs_ok
                ):
                    print(f"[CACHE HIT] {stage} (input_hash={input_hash}) — skipping.")
                    stage_cache_meta[stage_instance_id] = {
                        "cache_enabled": True,
                        "cache_scope": "global" if stage_cache_enabled else "phase2_only",
                        "cache_key": input_hash,
                        "cache_hit": True,
                        "cache_reason": "input_hash_match",
                    }
                    return True
            except (OSError, UnicodeDecodeError, JSONDecodeError, AttributeError, TypeError, ValueError):
                pass
        stage_cache_meta[stage_instance_id] = {
            "cache_enabled": True,
            "cache_scope": "global" if stage_cache_enabled else "phase2_only",
            "cache_key": input_hash,
            "cache_hit": False,
            "cache_reason": "miss_or_invalid_manifest_or_outputs",
        }
    else:
        input_hash = None
        stage_cache_meta[stage_instance_id] = {
            "cache_enabled": False,
            "cache_scope": "disabled",
            "cache_key": None,
            "cache_hit": False,
            "cache_reason": "disabled",
        }

    filtered_args = _filter_unsupported_flags(script_path, base_args)
    cmd = [sys.executable, str(script_path)] + filtered_args
    if _script_supports_log_path(script_path):
        cmd.extend(["--log_path", str(log_path)])
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT.parent) + os.pathsep + env.get("PYTHONPATH", "")
    env["BACKTEST_RUN_ID"] = run_id
    env["BACKTEST_STAGE_INSTANCE_ID"] = stage_instance_id
    env["BACKTEST_FEATURE_SCHEMA_VERSION"] = feature_schema_version
    if current_pipeline_session_id:
        env["BACKTEST_PIPELINE_SESSION_ID"] = current_pipeline_session_id

    allowed_nonzero = {}
    if not strict_recommendations_checklist:
        allowed_nonzero["generate_recommendations_checklist"] = {1}
    if stage.startswith("bridge_evaluate_phase2"):
        allowed_nonzero[stage] = {1}
    accepted_codes = {0} | allowed_nonzero.get(stage, set())
    attempts = max(1, int(max_attempts))
    backoff_sec = max(0.0, float(retry_backoff_sec))

    # Run the stage script with per-stage output buffering.
    # This keeps parallel logs readable and emits each stage block atomically.
    result_returncode: int | None = None
    for attempt in range(1, attempts + 1):
        popen_kwargs: Dict[str, object] = {
            "env": env,
            "stdout": subprocess.PIPE,
            "stderr": subprocess.STDOUT,
            "text": True,
            "encoding": "utf-8",
            "errors": "replace",
            "bufsize": 1,
        }
        if os.name == "posix":
            # New process-group allows fail-fast cancellation to terminate
            # every subprocess spawned by a stage worker.
            popen_kwargs["start_new_session"] = True
        elif os.name == "nt" and hasattr(subprocess, "CREATE_NEW_PROCESS_GROUP"):
            popen_kwargs["creationflags"] = getattr(
                subprocess, "CREATE_NEW_PROCESS_GROUP"
            )
        proc = subprocess.Popen(cmd, **popen_kwargs)  # type: ignore[arg-type]
        _register_running_stage_proc(run_id, stage_instance_id, proc)
        stage_output = ""
        try:
            stdout_text, _ = proc.communicate()
            stage_output = str(stdout_text or "")
            if proc.returncode is not None:
                result_returncode = int(proc.returncode)
            else:
                result_returncode = int(proc.wait())
        finally:
            _unregister_running_stage_proc(run_id, stage_instance_id)
        if stage_output:
            with log_path.open("a", encoding="utf-8") as handle:
                handle.write(stage_output)
                if not stage_output.endswith("\n"):
                    handle.write("\n")
            _emit_buffered_stage_output(stage_instance_id, stage, stage_output)

        if result_returncode not in accepted_codes:
            print(
                f"\nERROR: Stage {stage} failed with exit code {result_returncode}",
                file=sys.stderr,
            )

        if result_returncode in accepted_codes:
            require_manifest = _required_stage_manifest_enabled()
            if not manifest_path.exists():
                if require_manifest:
                    error = (
                        "stage manifest missing on success while "
                        "BACKTEST_REQUIRE_STAGE_MANIFEST=1"
                    )
                    _synthesize_stage_manifest_if_missing(
                        manifest_path=manifest_path,
                        stage=stage,
                        stage_instance_id=stage_instance_id,
                        run_id=run_id,
                        script_path=script_path,
                        base_args=base_args,
                        log_path=log_path,
                        status="failed",
                        error=error,
                        input_hash=input_hash,
                    )
                    print(f"Stage failed: {stage} ({error})", file=sys.stderr)
                    return False
                _synthesize_stage_manifest_if_missing(
                    manifest_path=manifest_path,
                    stage=stage,
                    stage_instance_id=stage_instance_id,
                    run_id=run_id,
                    script_path=script_path,
                    base_args=base_args,
                    log_path=log_path,
                    status="success",
                    input_hash=input_hash,
                )
            valid_manifest, validation_error = _validate_stage_manifest_on_disk(
                manifest_path, allow_failed_minimal=False
            )
            if not valid_manifest:
                print(validation_error, file=sys.stderr)
                if require_manifest:
                    _synthesize_stage_manifest_if_missing(
                        manifest_path=manifest_path,
                        stage=stage,
                        stage_instance_id=stage_instance_id,
                        run_id=run_id,
                        script_path=script_path,
                        base_args=base_args,
                        log_path=log_path,
                        status="failed",
                        error=validation_error,
                        input_hash=input_hash,
                    )
                return False
            # Stamp input_hash into stage manifest on success for future cache reads.
            manifest_payload: Dict[str, object] | None = None
            if input_hash and manifest_path.exists():
                try:
                    mdata = json.loads(manifest_path.read_text(encoding="utf-8"))
                    mdata["input_hash"] = input_hash
                    manifest_path.write_text(json.dumps(mdata, indent=2), encoding="utf-8")
                    if isinstance(mdata, dict):
                        manifest_payload = mdata
                except (OSError, UnicodeDecodeError, JSONDecodeError, TypeError, ValueError) as exc:
                    print(f"[WARN] Failed to stamp input_hash into {manifest_path}: {exc}", file=sys.stderr)

            if manifest_payload is None and manifest_path.exists():
                try:
                    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
                    if isinstance(payload, dict):
                        manifest_payload = payload
                except (OSError, UnicodeDecodeError, JSONDecodeError) as exc:
                    print(f"[WARN] Failed to load manifest {manifest_path}: {exc}", file=sys.stderr)
                    manifest_payload = None

            if (
                manifest_payload is not None
                and str(os.environ.get("BACKTEST_EXPERIMENT_STORE", "0")).strip()
                in {"1", "true", "TRUE"}
            ):
                try:
                    from project.io.experiment_store import upsert_stage_manifest

                    upsert_stage_manifest(
                        data_root=data_root,
                        run_id=run_id,
                        stage_instance_id=stage_instance_id,
                        manifest_path=manifest_path,
                        payload=manifest_payload,
                    )
                except (ImportError, OSError, ValueError) as exc:
                    print(f"[WARN] Failed to write to experiment store: {exc}", file=sys.stderr)
            return True

        if attempt < attempts:
            print(
                f"[RETRY] Stage {stage} attempt {attempt}/{attempts} failed; retrying...",
                file=sys.stderr,
            )
            if backoff_sec > 0.0:
                time.sleep(backoff_sec)

    assert result_returncode is not None
    _synthesize_stage_manifest_if_missing(
        manifest_path=manifest_path,
        stage=stage,
        stage_instance_id=stage_instance_id,
        run_id=run_id,
        script_path=script_path,
        base_args=base_args,
        log_path=log_path,
        status="failed",
        error=f"exit_code={result_returncode}",
        input_hash=input_hash,
    )
    print(f"Stage failed: {stage}", file=sys.stderr)
    print(f"Stage log: {log_path}", file=sys.stderr)
    print(f"Stage manifest: {manifest_path}", file=sys.stderr)
    return False

def partition_items(
    items: Sequence[object],
    *,
    key_fn: Callable[[object], str],
) -> Dict[str, List[object]]:
    """
    Deterministically partition items by key while preserving input order
    within each partition.
    """
    out: Dict[str, List[object]] = {}
    for item in items:
        key = str(key_fn(item))
        out.setdefault(key, []).append(item)
    return out

def run_partition_map_reduce(
    partitions: Dict[str, Sequence[object]],
    *,
    map_fn: PartitionMapFn,
    reduce_fn: PartitionReduceFn,
    max_workers: int = 1,
) -> Tuple[object, Dict[str, object]]:
    """
    Execute a deterministic map-reduce over partitioned artifacts.

    - Map execution may run in parallel.
    - Reduce input order is stable (sorted by partition key).
    """
    results: Dict[str, object] = {}
    keys = sorted(str(key) for key in partitions.keys())
    workers = max(1, min(int(max_workers), max(1, len(keys))))
    if workers <= 1:
        for key in keys:
            results[key] = map_fn(key, list(partitions.get(key, ())))
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(map_fn, key, list(partitions.get(key, ()))): key
                for key in keys
            }
            for fut in concurrent.futures.as_completed(futures):
                key = futures[fut]
                results[key] = fut.result()
    ordered_results = [results[key] for key in sorted(results.keys())]
    reduced = reduce_fn(ordered_results)
    return reduced, results

def run_stages_parallel(
    stages: Sequence[StageLaunch],
    run_id: str,
    max_workers: int,
    *,
    worker_fn: Optional[Callable[[WorkerArgs], WorkerResult]] = None,
    continue_on_failure: bool = False,
) -> Tuple[bool, List[StageTiming]]:
    """Run a batch of independent stages in parallel using subprocess workers.

    Returns (all_ok, [(stage_instance, stage_name, elapsed_sec, cache_meta), ...])
    in completion order.
    """
    timings: List[StageTiming] = []
    all_ok = True
    effective_workers = max(1, min(max_workers, len(stages)))
    if effective_workers <= 1:
        for stage_instance_id, stage_name, script, base_args in stages:
            stage_inst, stage_nm, ok, elapsed, cache_meta = worker_fn(
                (stage_instance_id, stage_name, script, base_args, run_id)
            )
            timings.append((stage_inst, stage_nm, elapsed, cache_meta))
            if not ok:
                all_ok = False
                if not continue_on_failure:
                    break
        return all_ok, timings

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=effective_workers) as pool:
            args_list = [(s[0], s[1], s[2], s[3], run_id) for s in stages]
            futures = {pool.submit(worker_fn, a): a[0] for a in args_list}
            pending_stage_ids = set(futures.values())
            for fut in concurrent.futures.as_completed(futures):
                stage_instance_id, stage_name, ok, elapsed, cache_meta = fut.result()
                pending_stage_ids.discard(stage_instance_id)
                timings.append((stage_instance_id, stage_name, elapsed, cache_meta))
                if not ok:
                    all_ok = False
                    if not continue_on_failure:
                        # Cancel pending futures and terminate running stage subprocesses.
                        terminate_stage_instances(run_id, sorted(pending_stage_ids))
                        for remaining in futures:
                            remaining.cancel()
                        break
    except (PermissionError, OSError) as exc:
        print(
            f"[WARN] ThreadPool unavailable ({exc}). Falling back to sequential stage execution.",
            file=sys.stderr,
        )
        timings = []
        all_ok = True
        for stage_instance_id, stage_name, script, base_args in stages:
            stage_inst, stage_nm, ok, elapsed, cache_meta = worker_fn(
                (stage_instance_id, stage_name, script, base_args, run_id)
            )
            timings.append((stage_inst, stage_nm, elapsed, cache_meta))
            if not ok:
                all_ok = False
                if not continue_on_failure:
                    break
    return all_ok, timings

def run_dag(
    plan: Mapping[str, StageDefinition],
    run_id: str,
    max_workers: int,
    *,
    worker_fn: Optional[Callable[[WorkerArgs], WorkerResult]] = None,
    completed_already: set[str] | None = None,
    continue_on_failure: bool = False,
) -> Tuple[bool, List[StageTiming]]:
    """
    Execute a pipeline DAG in parallel.
    
    Returns (all_ok, timings)
    """
    timings: List[StageTiming] = []
    completed = set(completed_already or [])
    failed: set[str] = set()
    running: Dict[concurrent.futures.Future, str] = {}
    
    all_ok = True
    
    # Task execution router
    def _execute_task_or_subprocess(stage_name: str, script: Union[str, Path], args: List[str], rid: str) -> bool:
        path_str = str(script)
        if ":" in path_str or (path_str.startswith("project.") and not path_str.endswith(".py")):
            import importlib
            try:
                mod_name, func_name = path_str.rsplit(":", 1) if ":" in path_str else (path_str, "run_task")
                mod = importlib.import_module(mod_name)
                func = getattr(mod, func_name)
                return func(rid, args) == 0
            except (ImportError, AttributeError, TypeError, ValueError) as e:
                print(f"[DAG] Task {stage_name} failed: {e}")
                return False
        
        # Fallback to subprocess using the execution engine directly.
        return run_stage(
            stage=stage_name,
            script_path=Path(path_str),
            base_args=args,
            run_id=rid,
            data_root=DATA_ROOT,
            strict_recommendations_checklist=False,
            feature_schema_version=str(os.environ.get("BACKTEST_FEATURE_SCHEMA_VERSION", "v2") or "v2"),
            current_pipeline_session_id=str(os.environ.get("BACKTEST_PIPELINE_SESSION_ID", "")).strip() or None,
            current_stage_instance_id=stage_name,
            stage_cache_meta={},
        )

    if worker_fn is None:
        def default_worker(args_tuple: WorkerArgs) -> WorkerResult:
            inst_id, name, script, args, rid = args_tuple
            start_ts = time.time()
            ok = _execute_task_or_subprocess(name, script, args, rid)
            return inst_id, name, ok, time.time() - start_ts, {}
        worker_fn = default_worker

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        while len(completed) + len(failed) < len(plan):
            # 1. Find ready stages
            ready = []
            for name, stage in plan.items():
                if name in completed or name in failed:
                    continue
                
                # Check if already running (by stage name)
                if any(stage_name == name for stage_name in running.values()):
                    continue
                
                # Check dependencies
                if all(dep in completed for dep in stage.depends_on):
                    ready.append(stage)
            
            # 2. Launch ready stages
            for stage in ready:
                if len(running) >= max_workers:
                    break
                print(f"[DAG] Launching {stage.name} (deps={stage.depends_on})")
                
                # Use a unique key for the future to stage name mapping
                fut = pool.submit(worker_fn, (stage.name, stage.name, stage.script_path, stage.args, run_id))
                running[fut] = stage.name
            
            if not running:
                if len(completed) + len(failed) < len(plan):
                    unmet = [n for n in plan if n not in completed and n not in failed]
                    print(f"ERROR: DAG deadlock detected. Unmet stages: {unmet}", file=sys.stderr)
                    return False, timings
                break

            # 3. Wait for progress
            done, _ = concurrent.futures.wait(
                running.keys(), return_when=concurrent.futures.FIRST_COMPLETED
            )
            
            for fut in done:
                stage_instance_id = running.pop(fut)
                try:
                    # Result tuple: (instance_id, name, ok, elapsed, cache_meta)
                    res_inst, res_name, ok, elapsed, cache_meta = fut.result()
                    timings.append((res_inst, res_name, elapsed, cache_meta))
                    if ok:
                        completed.add(res_inst)
                    else:
                        print(f"[DAG] Stage {res_inst} failed.")
                        failed.add(res_inst)
                        all_ok = False
                        if not continue_on_failure:
                            terminate_stage_instances(run_id, list(running.values()))
                            return False, timings
                except (
                    concurrent.futures.CancelledError,
                    concurrent.futures.TimeoutError,
                    RuntimeError,
                    ValueError,
                    TypeError,
                ) as e:
                    print(f"[DAG] Execution error in {stage_instance_id}: {e}")
                    failed.add(stage_instance_id)
                    all_ok = False
                    if not continue_on_failure:
                        return False, timings
                        
    return all_ok, timings
