from __future__ import annotations
from project.core.config import get_data_root

import argparse
import json
import os
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from project import PROJECT_ROOT
from project.research.services.benchmark_matrix_service import (
    build_benchmark_summary,
    load_benchmark_matrix,
    write_benchmark_summary,
)
from project.research.services.benchmark_review_service import (
    build_benchmark_review,
    write_benchmark_review,
)
from project.research.services.benchmark_governance_service import (
    certify_benchmark_review,
    load_acceptance_thresholds,
    write_certification_report,
)
from project.research.services.context_mode_comparison_service import (
    build_context_mode_comparison_payload,
    write_context_mode_comparison_report,
)
from project.research.services.live_data_foundation_service import write_live_data_foundation_report
from project.research.services.run_comparison_service import write_run_matrix_summary_report

REPO_ROOT = PROJECT_ROOT.parent
DATA_ROOT = get_data_root()


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def _subprocess_env() -> Dict[str, str]:
    env = os.environ.copy()
    repo_root = str(REPO_ROOT)
    existing = str(env.get("PYTHONPATH", "")).strip()
    env["PYTHONPATH"] = f"{repo_root}:{existing}" if existing else repo_root
    return env


def _resolve_repo_path(path_like: str) -> Path:
    raw = str(path_like).strip()
    path = Path(raw)
    if path.is_absolute():
        return path
    repo_path = REPO_ROOT / raw
    return repo_path if repo_path.exists() else path


def _generate_post_run_reports(
    *,
    run: Dict[str, Any],
    data_root: Path,
) -> Dict[str, str]:
    reports_cfg = run.get("post_reports", {})
    if not isinstance(reports_cfg, dict):
        return {}

    generated: Dict[str, str] = {}
    run_id = str(run.get("run_id", "")).strip()
    market = str(run.get("market", "perp")).strip() or "perp"
    timeframe = str(run.get("timeframe", "5m")).strip() or "5m"
    symbols = [s.strip().upper() for s in str(run.get("symbols", "")).split(",") if s.strip()]
    primary_symbol = symbols[0] if symbols else ""

    live_cfg = reports_cfg.get("live_foundation")
    if isinstance(live_cfg, dict) and bool(live_cfg.get("enabled", True)) and primary_symbol:
        config_path = (
            _resolve_repo_path(str(live_cfg.get("config", "")).strip())
            if str(live_cfg.get("config", "")).strip()
            else None
        )
        out_path = write_live_data_foundation_report(
            data_root=data_root,
            run_id=run_id,
            symbol=primary_symbol,
            timeframe=timeframe,
            market=market,
            feature_schema_version=str(live_cfg.get("feature_schema_version", "v2")).strip()
            or "v2",
            config_path=config_path,
        )
        generated["live_foundation"] = str(out_path)

    context_cfg = reports_cfg.get("context_comparison")
    if isinstance(context_cfg, dict) and bool(context_cfg.get("enabled", True)) and symbols:
        search_space_raw = str(context_cfg.get("search_space_path", "")).strip()
        search_space_path = _resolve_repo_path(search_space_raw) if search_space_raw else None
        payload = build_context_mode_comparison_payload(
            data_root=data_root,
            run_id=run_id,
            symbols=symbols,
            timeframe=timeframe,
            min_sample_size=int(context_cfg.get("min_sample_size", 30)),
            search_space_path=search_space_path,
        )
        report_dir = data_root / "reports" / "context_mode_comparison" / run_id
        out_path = write_context_mode_comparison_report(
            out_path=report_dir / "context_mode_comparison.json",
            comparison=payload,
        )
        generated["context_mode_comparison"] = str(out_path)

    return generated


def _completed_run_ids(rows: List[Dict[str, Any]]) -> List[str]:
    run_ids: List[str] = []
    for row in rows:
        status = str(row.get("status", "")).strip()
        if status not in {"success", "failed"}:
            continue
        run_id = str(row.get("run_id", "")).strip()
        if run_id and run_id not in run_ids:
            run_ids.append(run_id)
    return run_ids


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a reproducible benchmark matrix for run_all.py."
    )
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
        "--priors",
        nargs="*",
        help="List of paths to prior benchmark_review.json files.",
    )
    parser.add_argument(
        "--out_dir",
        default=None,
        help="Output directory. Defaults to data/reports/benchmarks/<matrix_id>_<timestamp>.",
    )
    parser.add_argument(
        "--execute", type=int, default=0, help="If 1, execute commands. If 0, dry-run only."
    )
    parser.add_argument("--fail_fast", type=int, default=1, help="If 1, stop on first failed run.")
    args = parser.parse_args()

    matrix_path = Path(args.matrix).resolve()
    run_all_path = Path(args.run_all).resolve()
    matrix = load_benchmark_matrix(matrix_path)
    matrix_id = str(matrix.get("matrix_id", "matrix")).strip() or "matrix"
    run_defs = matrix.get("runs", [])
    defaults = matrix.get("defaults", {})
    if not isinstance(defaults, dict):
        defaults = {}

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_dir = (
        Path(args.out_dir).resolve()
        if args.out_dir
        else DATA_ROOT / "reports" / "benchmarks" / f"{matrix_id}_{timestamp}"
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
            "generated_reports": {},
        }

        if execute:
            row["started_at"] = _utc_now_iso()
            t0 = time.perf_counter()
            result = subprocess.run(cmd, cwd=REPO_ROOT, env=_subprocess_env())
            row["finished_at"] = _utc_now_iso()
            row["duration_sec"] = round(time.perf_counter() - t0, 3)
            row["returncode"] = int(result.returncode)
            row["status"] = "success" if result.returncode == 0 else "failed"
            if result.returncode == 0:
                row["generated_reports"] = _generate_post_run_reports(
                    run=run,
                    data_root=DATA_ROOT,
                )
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

    summary = build_benchmark_summary(matrix=matrix, manifest=manifest)
    summary_paths = write_benchmark_summary(out_dir=out_dir, summary=summary)
    review = build_benchmark_review(summary=summary)
    review_paths = write_benchmark_review(out_dir=out_dir, review=review)

    # Certification
    prior_review = None
    if args.priors:
        prior_review = []
        for p in args.priors:
            ppath = Path(p).resolve()
            if ppath.exists():
                try:
                    prior_review.append(json.loads(ppath.read_text(encoding="utf-8")))
                except Exception:
                    pass
    else:
        prior_path = (
            Path(matrix.get("prior_baseline", "")).resolve()
            if matrix.get("prior_baseline")
            else None
        )
        if prior_path and prior_path.exists():
            try:
                prior_review = json.loads(prior_path.read_text(encoding="utf-8"))
            except Exception:
                pass

    thresholds_path = REPO_ROOT / "spec" / "benchmarks" / "benchmark_acceptance_thresholds.yaml"
    thresholds = load_acceptance_thresholds(thresholds_path)

    cert = certify_benchmark_review(
        current_review=review,
        prior_review=prior_review,
        acceptance_thresholds=thresholds,
        execution_manifest=manifest,
    )
    cert_paths = write_certification_report(out_dir=out_dir, cert=cert)

    matrix_summary_json = None
    matrix_summary_markdown = None
    completed_run_ids = _completed_run_ids(command_rows)
    if execute and completed_run_ids:
        matrix_summary_json = write_run_matrix_summary_report(
            data_root=DATA_ROOT,
            baseline_run_id=completed_run_ids[0],
            candidate_run_ids=completed_run_ids[1:],
            out_dir=out_dir,
            drift_mode="warn",
        )
        matrix_summary_markdown = out_dir / "research_run_matrix_summary.md"

    manifest["benchmark_summary_json"] = str(summary_paths["json"])
    manifest["benchmark_summary_markdown"] = str(summary_paths["markdown"])
    manifest["benchmark_review_json"] = str(review_paths["json"])
    manifest["benchmark_review_markdown"] = str(review_paths["markdown"])
    manifest["benchmark_certification_json"] = str(cert_paths["json"])
    manifest["benchmark_certification_markdown"] = str(cert_paths["markdown"])
    manifest["certification_passed"] = bool(cert["passed"])
    if matrix_summary_json is not None:
        manifest["research_run_matrix_summary_json"] = str(matrix_summary_json)
    if matrix_summary_markdown is not None:
        manifest["research_run_matrix_summary_markdown"] = str(matrix_summary_markdown)

    manifest_path = out_dir / "matrix_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    print(f"[matrix] wrote manifest: {manifest_path}")
    print(f"[matrix] wrote summary: {summary_paths['json']}")
    print(f"[matrix] wrote review: {review_paths['json']}")
    print(f"[matrix] wrote certification: {cert_paths['json']}")
    if matrix_summary_json is not None:
        print(f"[matrix] wrote research matrix summary: {matrix_summary_json}")

    if not cert["passed"]:
        print(
            f"[matrix] WARNING: Benchmark certification FAILED with {cert['issue_count']} issues."
        )

    if not execute:
        print("[matrix] dry-run only. Re-run with --execute 1 to run commands.")

    return 1 if (failures > 0 or not cert["passed"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
