from __future__ import annotations

from project.research.cli.promotion_cli import (
    build_promotion_parser,
    promotion_config_from_namespace,
    run_promotion_cli,
)

if __name__ == "__main__":
    import sys
    sys.exit(int(run_promotion_cli(sys.argv[1:]).exit_code))
