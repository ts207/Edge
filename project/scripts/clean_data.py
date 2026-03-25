from __future__ import annotations

import argparse
import logging
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path

from project.core.config import get_data_root


def main() -> int:
    parser = argparse.ArgumentParser(description="Clean up old data artifacts.")
    parser.add_argument(
        "--days", type=int, default=14, help="Delete run artifacts older than this many days"
    )
    parser.add_argument(
        "--dry_run", action="store_true", help="Print what would be deleted without deleting"
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    data_root = get_data_root()
    cutoff_date = datetime.now() - timedelta(days=args.days)

    dirs_to_clean = ["runs", "reports", "events", "research", "lake/runs"]

    deleted_count = 0
    for dir_name in dirs_to_clean:
        target_dir = data_root / dir_name
        if target_dir.exists() and target_dir.is_dir():
            for sub_dir in target_dir.iterdir():
                if sub_dir.is_dir():
                    mtime = datetime.fromtimestamp(sub_dir.stat().st_mtime)
                    if mtime < cutoff_date:
                        logging.info(f"Deleting {sub_dir} (last modified {mtime})")
                        if not args.dry_run:
                            shutil.rmtree(sub_dir, ignore_errors=True)
                        deleted_count += 1

    if deleted_count == 0:
        logging.info("No old data artifacts found to clean.")
    else:
        logging.info(f"Cleaned {deleted_count} directories.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
