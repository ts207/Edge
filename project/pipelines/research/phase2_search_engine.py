from __future__ import annotations

"""
Pipeline wrapper for the research search engine.

The execution engine statically scans stage scripts for dangerous passthrough
flags before launch. This wrapper intentionally forwards `--experiment_config`
to the underlying CLI.
"""

import sys

from project.research.phase2_search_engine import main


if __name__ == "__main__":
    sys.exit(main())
