from __future__ import annotations
from project.core.config import get_data_root

import argparse
import json
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import yaml
from project import PROJECT_ROOT
REPO_ROOT = PROJECT_ROOT.parent
DATA_ROOT = get_data_root()

def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _load_matrix(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Benchmark matrix not found: {path}")
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Benchmark matrix must be a YAML mapping.")
    runs = payload.get("runs", [])
    if not isinstance(runs, list) or not runs:
        raise ValueError("Benchmark matrix must define a non-empty 'runs' list.")
    for idx, run in enumerate(runs):
        if not isinstance(run, dict):
            raise ValueError(f"Run entry at index {idx} must be a mapping.")
        for key in ("run_id", "symbols", "start", "end"):
            value = str(run.get(key, "")).strip()
            if not value:
                raise ValueError(f"Run entry at index {idx} is missing required key '{key}'.")
    return payload

def _build_run_command(
    *,
    run: Dict[str, Any],
    defaults: Dict[str, Any],
    python_exe: str,
    run_all_path: Path,
) -> List[str]:
    default_flags = defaults.get("flags", {})
    if not isinstance(default_flags, dict):
        default_flags = {}
    run_flags = run.get("flags", {})
    if not isinstance(run_flags, dict):
        run_flags = {}
    merged_flags: Dict[str, Any] = dict(default_flags)
    merged_flags.update(run_flags)

    mode = str(run.get("mode", defaults.get("mode", "research"))).strip() or "research"

    cmd: List[str] = [
        str(python_exe),
        str(run_all_path),
        "--run_id",
        str(run["run_id"]),
        "--symbols",
        str(run["symbols"]),
        "--start",
        str(run["start"]),
        "--end",
        str(run["end"]),
        "--mode",
        mode,
    ]

    reserved = {"run_id", "symbols", "start", "end", "mode", "flags", "extra_args"}
    for key, value in sorted(merged_flags.items(), key=lambda item: str(item[0])):
        cli_key = str(key).strip()
        if not cli_key or cli_key in reserved:
            continue
        cmd.extend([f"--{cli_key}", str(value)])

    extra_args = run.get("extra_args", [])
    if isinstance(extra_args, list):
        cmd.extend([str(x) for x in extra_args])

    return cmd

def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)

def main() -> int:
    parser = argparse.ArgumentParser(description="Run a reproducible benchmark matrix for run_all.py.")
    parser.add_argument(
        "--matrix",
        default=str(REPO_ROOT / "spec" / "benchmarks" / "retail_m0_matrix.yaml"),
        help="Path to benchmark matrix YAML.",
    )
    parser.add_argument(
        "--run_all",
        default=str(PROJECT_ROOT / "pipelines" / "run_all.py"),
        help="Path to run_all.py.",
    )
    parser.add_argument(
        "--python",
        default=sys.executable,
        help="Python executable for run_all invocations.",
    )
    parser.add_argument(
        "--out_dir",
        default=None,
        help="Output directory. Defaults to data/reports/perf_benchmarks/<matrix_id>_<timestamp>.",
    )
    parser.add_argument("--execute", type=int, default=0, help="If 1, execute commands. If 0, dry-run only.")
    parser.add_argument("--fail_fast", type=int, default=1, help="If 1, stop on first failed run.")
    args = parser.parse_args()

    matrix_path = Path(args.matrix).resolve()
    run_all_path = Path(args.run_all).resolve()
    matrix = _load_matrix(matrix_path)
    matrix_id = str(matrix.get("matrix_id", "matrix")).strip() or "matrix"
    run_defs = matrix.get("runs", [])
    defaults = matrix.get("defaults", {})
    if not isinstance(defaults, dict):
        defaults = {}

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_dir = (
        Path(args.out_dir).resolve()
        if args.out_dir
        else DATA_ROOT / "reports" / "perf_benchmarks" / f"{matrix_id}_{timestamp}"
    )
    _ensure_dir(out_dir)

    command_rows: List[Dict[str, Any]] = []
    failures = 0
    execute = bool(int(args.execute))
    fail_fast = bool(int(args.fail_fast))

    for run in run_defs:
        cmd = _build_run_command(
            run=run,
            defaults=defaults,
            python_exe=str(args.python),
            run_all_path=run_all_path,
        )
        row: Dict[str, Any] = {
            "run_id": str(run["run_id"]),
            "symbols": str(run["symbols"]),
            "start": str(run["start"]),
            "end": str(run["end"]),
            "command": cmd,
            "command_shell": shlex.join(cmd),
            "status": "planned",
            "started_at": None,
            "finished_at": None,
            "duration_sec": None,
            "returncode": None,
        }

        if execute:
            row["started_at"] = _utc_now_iso()
            t0 = time.perf_counter()
            result = subprocess.run(cmd)
            row["finished_at"] = _utc_now_iso()
            row["duration_sec"] = round(time.perf_counter() - t0, 3)
            row["returncode"] = int(result.returncode)
            row["status"] = "success" if result.returncode == 0 else "failed"
            if result.returncode != 0:
                failures += 1
                if fail_fast:
                    command_rows.append(row)
                    break
        else:
            row["status"] = "dry_run"

        command_rows.append(row)

    manifest = {
        "created_at_utc": _utc_now_iso(),
        "matrix_id": matrix_id,
        "matrix_path": str(matrix_path),
        "run_all_path": str(run_all_path),
        "python_executable": str(args.python),
        "execute": execute,
        "fail_fast": fail_fast,
        "planned_runs": len(run_defs),
        "completed_rows": len(command_rows),
        "failures": int(failures),
        "results": command_rows,
    }

    manifest_path = out_dir / "matrix_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    print(f"[matrix] wrote manifest: {manifest_path}")
    if not execute:
        print("[matrix] dry-run only. Re-run with --execute 1 to run commands.")

    return 1 if failures > 0 else 0

if __name__ == "__main__":
    raise SystemExit(main())
