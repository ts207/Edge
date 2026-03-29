"""
Phase 2 Candidate Discovery CLI entrypoint.

The execution engine statically scans stage scripts for dangerous passthrough
flags before launch. This wrapper intentionally forwards `--experiment_config`
to the underlying CLI.

This is a compatibility-only entrypoint and is no longer scheduled as the
authoritative phase-2 discovery stage for new runs.
"""

from __future__ import annotations

import argparse
import sys
from typing import List, Optional


def _make_parser() -> argparse.ArgumentParser:
    from project.research.cli.candidate_discovery_cli import (
        build_candidate_discovery_parser,
    )

    return build_candidate_discovery_parser()


def _run_candidate_discovery_impl(argv: Optional[List[str]] = None) -> int:
    from project.research.cli.candidate_discovery_cli import run_candidate_discovery_cli

    return int(run_candidate_discovery_cli(argv).exit_code)


def main(argv: Optional[List[str]] = None) -> int:
    from project.research.cli.candidate_discovery_cli import run_candidate_discovery_cli

    return int(run_candidate_discovery_cli(argv).exit_code)


if __name__ == "__main__":
    sys.exit(main())
