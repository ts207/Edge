from __future__ import annotations

from project.research.cli.candidate_discovery_cli import (
    build_candidate_discovery_parser,
    candidate_discovery_config_from_namespace,
    run_candidate_discovery_cli,
)

if __name__ == "__main__":
    import sys
    sys.exit(int(run_candidate_discovery_cli(sys.argv[1:]).exit_code))
