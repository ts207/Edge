from __future__ import annotations

import sys
from pathlib import Path

from project.research.seed_package import package_seed_promoted_theses

DOCS = Path("docs/generated")


def main() -> None:
    print(
        "Deprecated/internal bootstrap packaging surface. "
        "For canonical runtime thesis batches, use "
        "'python -m project.research.export_promoted_theses --run_id <run_id>'.",
        file=sys.stderr,
    )
    package_seed_promoted_theses(docs_dir=DOCS)


if __name__ == "__main__":
    main()
