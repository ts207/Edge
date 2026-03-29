from __future__ import annotations

import sys
from typing import List


def _run_promotion_impl(argv: List[str] | None = None) -> int:
    from project.research.cli.promotion_cli import run_promotion_cli

    return int(run_promotion_cli(argv).exit_code)


def main(argv: List[str] | None = None) -> int:
    from project.research.cli.promotion_cli import run_promotion_cli

    return int(run_promotion_cli(argv).exit_code)


if __name__ == "__main__":
    sys.exit(main())
