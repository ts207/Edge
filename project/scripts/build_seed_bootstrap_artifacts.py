from __future__ import annotations

import argparse
from pathlib import Path

from project.research.seed_bootstrap import (
    build_promotion_seed_inventory,
    build_thesis_bootstrap_baseline,
    write_seed_promotion_policy_artifacts,
)

DOCS = Path("docs/generated")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build seed/bootstrap baseline artifacts with optional explicit thesis lineage."
    )
    source = parser.add_mutually_exclusive_group(required=False)
    source.add_argument("--thesis_run_id", help="Optional explicit promoted thesis run id for baseline context.")
    source.add_argument("--thesis_path", help="Optional explicit promoted_theses.json path for baseline context.")
    parser.add_argument("--docs_dir", default=str(DOCS), help="Output docs directory.")
    parser.add_argument("--data_root", default=None, help="Optional data root for run id resolution.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    docs_dir = Path(args.docs_dir)

    build_thesis_bootstrap_baseline(
        docs_dir=docs_dir,
        data_root=args.data_root,
        thesis_run_id=args.thesis_run_id,
        thesis_path=args.thesis_path,
    )
    build_promotion_seed_inventory(docs_dir=docs_dir)
    write_seed_promotion_policy_artifacts(docs_dir=docs_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
