from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from project import PROJECT_ROOT
from project.core.config import get_data_root
from project.research.services.benchmark_matrix_service import load_benchmark_matrix
from project.research.services.promotion_readiness_service import (
    build_promotion_readiness_report,
    render_promotion_readiness_terminal,
    write_promotion_readiness_report,
)

# Import main from run_benchmark_matrix to reuse orchestration
from project.scripts.run_benchmark_matrix import main as run_matrix_main


def _utc_now_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def find_historical_reviews(matrix_id: str, history_limit: int = 5) -> List[Path]:
    """
    Find existing benchmark_review.json files in history.
    ONLY finds reviews that passed certification.
    """
    data_root = get_data_root()
    bench_dir = data_root / "reports" / "benchmarks"
    h_path = bench_dir / "history"
    if not h_path.exists():
        return []

    # History dirs are named <matrix_id>_<timestamp>
    # We sort them by name descending (newest first)
    runs = sorted(
        [d for d in h_path.iterdir() if d.is_dir() and d.name.startswith(f"{matrix_id}_")],
        key=lambda x: x.name,
        reverse=True,
    )

    reviews = []
    for r in runs:
        review_file = r / "benchmark_review.json"
        cert_file = r / "benchmark_certification.json"
        if review_file.exists() and cert_file.exists():
            try:
                cert = json.loads(cert_file.read_text(encoding="utf-8"))
                if cert.get("passed"):
                    reviews.append(review_file)
            except Exception:
                continue

        if len(reviews) >= history_limit:
            break

    return reviews


def main() -> int:
    parser = argparse.ArgumentParser(description="Unified benchmark maintenance cycle.")
    parser.add_argument(
        "--matrix",
        default=str(PROJECT_ROOT.parent / "spec" / "benchmarks" / "research_family_matrix.yaml"),
        help="Path to benchmark matrix YAML.",
    )
    parser.add_argument("--execute", type=int, default=1, help="If 1, execute benchmark runs.")
    parser.add_argument(
        "--history-limit",
        type=int,
        default=5,
        help="Number of historical certified baselines to keep.",
    )
    args = parser.parse_args()

    data_root = get_data_root()
    timestamp = _utc_now_compact()

    # 1. Resolve output directory
    matrix = load_benchmark_matrix(Path(args.matrix))
    matrix_id = matrix.get("matrix_id", "matrix")

    bench_dir = data_root / "reports" / "benchmarks"

    # Use a temporary directory for dry-runs so they don't enter history
    if args.execute:
        target_dir = bench_dir / "history" / f"{matrix_id}_{timestamp}"
    else:
        target_dir = Path("/tmp") / f"benchmark_smoke_{matrix_id}_{timestamp}"

    latest_link = bench_dir / "latest"

    # Discover priors before we start the new run
    priors = find_historical_reviews(matrix_id=matrix_id, history_limit=args.history_limit)
    print(f"[cycle] Starting maintenance for {matrix_id}...")
    print(
        f"[cycle] Discovered {len(priors)} historical certified priors for multi-baseline comparison."
    )
    print(f"[cycle] Output target: {target_dir}")

    # 2. Run the matrix
    orig_argv = sys.argv
    matrix_argv = [
        "run_benchmark_matrix.py",
        "--matrix",
        args.matrix,
        "--execute",
        str(args.execute),
        "--out_dir",
        str(target_dir),
    ]
    if priors:
        matrix_argv.extend(["--priors"] + [str(p) for p in priors])

    sys.argv = matrix_argv
    try:
        matrix_exit = run_matrix_main()
    finally:
        sys.argv = orig_argv

    # 3. Generate Promotion Readiness Report
    review_path = target_dir / "benchmark_review.json"
    cert_path = target_dir / "benchmark_certification.json"
    cert_passed = False

    if review_path.exists() and cert_path.exists():
        review = json.loads(review_path.read_text(encoding="utf-8"))
        cert = json.loads(cert_path.read_text(encoding="utf-8"))
        cert_passed = bool(cert.get("passed"))

        report = build_promotion_readiness_report(
            benchmark_review=review,
            benchmark_certification=cert,
        )
        write_promotion_readiness_report(out_dir=target_dir, report=report)
        print(f"[cycle] Wrote readiness report: {target_dir / 'promotion_readiness.json'}")

        print("")
        print(render_promotion_readiness_terminal(report))
    else:
        print("[cycle] ERROR: Core benchmark artifacts not found. Skipping readiness report.")

    # 4. Update 'latest' pointer (ONLY if execute=1 AND certified passed)
    if args.execute and target_dir.exists() and cert_passed:
        if os.path.lexists(latest_link):
            if latest_link.is_symlink():
                latest_link.unlink()
            elif latest_link.is_dir():
                shutil.rmtree(latest_link)
            else:
                latest_link.unlink()

        try:
            latest_link.symlink_to(target_dir.relative_to(bench_dir), target_is_directory=True)
            print(f"[cycle] Updated latest pointer: {latest_link} -> {target_dir.name}")
        except Exception:
            shutil.copytree(target_dir, latest_link)
            print(f"[cycle] Copied results to latest pointer: {latest_link}")
    elif args.execute and not cert_passed:
        print(f"[cycle] WARNING: Certification FAILED. Latest pointer NOT updated.")

    # 5. History Cleanup (Retain only last N certified + prune uncertified)
    if args.execute:
        h_path = bench_dir / "history"
        if h_path.exists():
            all_history = sorted(
                [d for d in h_path.iterdir() if d.is_dir() and d.name.startswith(f"{matrix_id}_")],
                key=lambda x: x.name,
                reverse=True,
            )

            certified_runs = []
            uncertified_runs = []

            for d in all_history:
                cert_f = d / "benchmark_certification.json"
                passed = False
                if cert_f.exists():
                    try:
                        c_data = json.loads(cert_f.read_text(encoding="utf-8"))
                        if c_data.get("passed"):
                            passed = True
                    except Exception:
                        pass

                if passed:
                    certified_runs.append(d)
                else:
                    uncertified_runs.append(d)

            # Prune old certified
            if len(certified_runs) > args.history_limit:
                for d in certified_runs[args.history_limit :]:
                    print(f"[cycle] Cleaning up old certified history: {d.name}")
                    shutil.rmtree(d)

            # Prune uncertified: keep only if they are NEWER than the oldest retained certified run
            if certified_runs:
                oldest_retained_certified = certified_runs[
                    min(len(certified_runs), args.history_limit) - 1
                ].name
                for d in uncertified_runs:
                    if d.name < oldest_retained_certified:
                        print(f"[cycle] Cleaning up old uncertified run: {d.name}")
                        shutil.rmtree(d)
            else:
                # If zero certified exist, keep only last N uncertified to avoid unbounded growth
                if len(uncertified_runs) > args.history_limit:
                    for d in uncertified_runs[args.history_limit :]:
                        print(f"[cycle] Cleaning up old uncertified history: {d.name}")
                        shutil.rmtree(d)

    print("")
    print(f"CYCLE_OUTPUT_DIR: {target_dir}")
    print("[cycle] Maintenance cycle COMPLETE.")

    # Return non-zero if matrix failed OR certification failed
    return 1 if (matrix_exit != 0 or not cert_passed) else 0


if __name__ == "__main__":
    sys.exit(main())
