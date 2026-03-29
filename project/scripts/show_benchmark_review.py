from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, List

from project.core.config import get_data_root


def _benchmark_roots(data_root: Path) -> list[Path]:
    return [
        data_root / "reports" / "benchmarks",
        data_root / "reports" / "perf_benchmarks",
    ]


def _history_review_candidates(root: Path, matrix_id: str | None = None) -> List[Path]:
    history_dir = root / "history"
    if not history_dir.exists():
        return []
    runs = [
        d
        for d in history_dir.iterdir()
        if d.is_dir() and (not matrix_id or d.name.startswith(f"{matrix_id}_"))
    ]
    runs.sort(key=lambda path: path.name, reverse=True)
    reviews: List[Path] = []
    for run_dir in runs:
        review_file = run_dir / "benchmark_review.json"
        if review_file.exists():
            reviews.append(review_file)
    return reviews


def find_latest_review(data_root: Path) -> Path | None:
    for root in _benchmark_roots(data_root):
        latest_link = root / "latest" / "benchmark_review.json"
        if latest_link.exists():
            return latest_link
        history_reviews = _history_review_candidates(root)
        if history_reviews:
            return history_reviews[0]

    # Check /tmp/
    tmp_path = Path("/tmp")
    candidates = list(tmp_path.glob("**/benchmark_review.json"))
    if candidates:
        candidates.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        return candidates[0]

    return None


def find_historical_reviews(matrix_id: str, limit: int = 5) -> List[Path]:
    reviews = []
    data_root = get_data_root()
    seen: set[Path] = set()
    for root in _benchmark_roots(data_root):
        for review_file in _history_review_candidates(root, matrix_id=matrix_id):
            resolved = review_file.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            reviews.append(review_file)
            if len(reviews) >= limit:
                return reviews
    return reviews


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Show the latest benchmark review in the terminal."
    )
    parser.add_argument("--path", help="Path to benchmark_review.json. If omitted, find latest.")
    parser.add_argument(
        "--compare-history",
        type=int,
        default=0,
        help="Number of historical runs to compare side-by-side.",
    )
    args = parser.parse_args()

    data_root = get_data_root()
    review_path: Path | None = None

    if args.path:
        review_path = Path(args.path)
    else:
        review_path = find_latest_review(data_root)

    if not review_path or not review_path.exists():
        print("Error: Could not find benchmark_review.json")
        return 1

    print(f"Loading review from: {review_path}")
    try:
        review = json.loads(review_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Error: Failed to parse review JSON: {e}")
        return 1

    cert_path = review_path.parent / "benchmark_certification.json"
    cert = None
    if cert_path.exists():
        try:
            cert = json.loads(cert_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    # Simple terminal output
    print("\n" + "=" * 80)
    print(f"BENCHMARK REVIEW: {review.get('matrix_id', 'unknown')}")
    if cert:
        status_str = "PASS" if cert.get("passed") else "FAIL"
        print(f"CERTIFICATION: {status_str} ({cert.get('issue_count', 0)} issues)")
    print("=" * 80)

    status_counts = review.get("status_counts", {})
    print("\nSTATUS COUNTS:")
    for status, count in sorted(status_counts.items()):
        print(f"  - {status}: {count}")

    slices = review.get("slices", [])
    if slices:
        print("\nSLICES:")

        # Historical comparison?
        matrix_id = review.get("matrix_id", "matrix")
        historical_paths = (
            find_historical_reviews(matrix_id, limit=args.compare_history + 1)
            if args.compare_history > 0
            else []
        )
        # Exclude current review if it's in history
        historical_paths = [p for p in historical_paths if p.resolve() != review_path.resolve()]
        historical_paths = historical_paths[: args.compare_history]

        historical_reviews = []
        for hp in historical_paths:
            try:
                historical_reviews.append(json.loads(hp.read_text(encoding="utf-8")))
            except Exception:
                pass

        # Header
        if not historical_reviews:
            header = f"{'Family':<25} | {'Event':<15} | {'Status':<15} | {'Foundation':<10} | {'Hard':<5} | {'Conf':<5}"
            print(header)
            print("-" * len(header))
            for s in slices:
                family = s.get("family", "")[:25]
                event = s.get("event_type", "")[:15]
                status = s.get("benchmark_status", "")[:15]
                found = s.get("live_foundation_readiness", "")[:10]
                hard = s.get("hard_evaluated_rows", 0)
                conf = s.get("confidence_evaluated_rows", 0)
                print(
                    f"{family:<25} | {event:<15} | {status:<15} | {found:<10} | {hard:<5} | {conf:<5}"
                )
        else:
            # Comparison Header
            header = f"{'Family':<25} | {'Event':<15} | {'Current (Hard)':<15}"
            for i, hr in enumerate(historical_reviews):
                # Use timestamp from path if possible
                ts = hr.get("created_at_utc", f"Past {i + 1}")[:10]
                header += f" | {ts:<15}"
            print(header)
            print("-" * len(header))

            for s in slices:
                bid = s.get("benchmark_id")
                family = s.get("family", "")[:25]
                event = s.get("event_type", "")[:15]
                hard = s.get("hard_evaluated_rows", 0)

                row_str = f"{family:<25} | {event:<15} | {hard:<15}"
                for hr in historical_reviews:
                    hs = next(
                        (hs for hs in hr.get("slices", []) if hs.get("benchmark_id") == bid), {}
                    )
                    h_hard = hs.get("hard_evaluated_rows", "-")
                    row_str += f" | {h_hard:<15}"
                print(row_str)

    if cert and cert.get("issues"):
        print("\nCERTIFICATION ISSUES:")
        for issue in cert["issues"]:
            print(
                f"  - [{issue.get('severity').upper()}] {issue.get('benchmark_id')}: {issue.get('message')}"
            )

    print("\n" + "=" * 80 + "\n")
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
