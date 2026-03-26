"""Phase 1 Correlation Clustering CLI entrypoint."""

from __future__ import annotations

import sys
from typing import List, Optional


def main(argv: Optional[List[str]] = None) -> int:
    from project.research.phase1_correlation_clustering import main as _main
    
    # The target main doesn't take argv, it uses sys.argv
    # If we want to pass argv, we need to monkeypatch sys.argv or change the target
    if argv is not None:
        old_argv = sys.argv
        sys.argv = [sys.argv[0]] + list(argv)
        try:
            return _main()
        finally:
            sys.argv = old_argv
    return _main()


if __name__ == "__main__":
    sys.exit(main())
