from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from project.core.config import get_data_root
from project.research.services.promotion_readiness_service import (
    build_promotion_readiness_report,
    render_promotion_readiness_terminal,
    render_promotion_readiness_markdown,
)

def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}

def main() -> int:
    parser = argparse.ArgumentParser(description="Show combined promotion readiness report.")
    parser.add_argument("--review", help="Path to benchmark_review.json")
    parser.add_argument("--cert", help="Path to benchmark_certification.json")
    parser.add_argument("--conf-plan", help="Path to confirmatory_window_plan.json")
    parser.add_argument("--audit", help="Path to promotion_audit.parquet or .csv")
    parser.add_argument("--out-dir", help="Directory to save JSON and MD reports.")
    args = parser.parse_args()

    # Defaults
    data_root = get_data_root()
    DEFAULT_DIR = data_root / "reports" / "benchmarks" / "latest"
    review_path = Path(args.review) if args.review else DEFAULT_DIR / "benchmark_review.json"
    cert_path = Path(args.cert) if args.cert else DEFAULT_DIR / "benchmark_certification.json"
    
    if not review_path.exists():
        print(f"Error: Review file not found: {review_path}")
        return 1
    if not cert_path.exists():
        print(f"Error: Certification file not found: {cert_path}")
        return 1

    review = _load_json(review_path)
    cert = _load_json(cert_path)
    
    conf_plan = _load_json(Path(args.conf_plan)) if args.conf_plan else None
    
    promotion_audit = None
    if args.audit:
        audit_path = Path(args.audit)
        if audit_path.exists():
            import pandas as pd
            if audit_path.suffix == ".parquet":
                promotion_audit = pd.read_parquet(audit_path).to_dict(orient="records")
            else:
                promotion_audit = pd.read_csv(audit_path).to_dict(orient="records")

    report = build_promotion_readiness_report(
        benchmark_review=review,
        benchmark_certification=cert,
        confirmatory_plan=conf_plan,
        promotion_audit=promotion_audit,
    )

    print(render_promotion_readiness_terminal(report))

    if args.out_dir:
        out_dir = Path(args.out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "promotion_readiness.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
        (out_dir / "promotion_readiness.md").write_text(render_promotion_readiness_markdown(report), encoding="utf-8")
        print(f"Wrote reports to: {out_dir}")

    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
