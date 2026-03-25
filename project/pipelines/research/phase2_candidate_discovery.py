"""Phase 2 Candidate Discovery CLI entrypoint."""

from __future__ import annotations

import argparse
import sys
from typing import List, Optional


def _make_parser() -> argparse.ArgumentParser:
    from project.pipelines.research.cli.candidate_discovery_cli import (
        build_candidate_discovery_parser,
    )

    return build_candidate_discovery_parser()


def _run_candidate_discovery_impl(argv: Optional[List[str]] = None) -> int:
    from project.pipelines.research.cli.candidate_discovery_cli import run_candidate_discovery_cli

    return int(run_candidate_discovery_cli(argv).exit_code)


def main(argv: Optional[List[str]] = None) -> int:
    from project.pipelines.research.cli.candidate_discovery_cli import run_candidate_discovery_cli

    return int(run_candidate_discovery_cli(argv).exit_code)


if __name__ == "__main__":
    sys.exit(main())
