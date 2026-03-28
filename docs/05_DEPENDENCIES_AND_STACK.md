# Dependencies and Technical Stack

## Runtime Requirement

The package requires Python `>=3.11`.

Build system:

- `setuptools>=69`
- `wheel`

Package metadata and console-script entry points live in `pyproject.toml`.

## Core Python Dependencies

Numerics and data:

- `numpy`
- `pandas`
- `pyarrow`
- `numba`

Statistics and modeling:

- `scikit-learn`
- `scipy`
- `statsmodels`

Validation and modeling:

- `pydantic`
- `pandera`
- `PyYAML`

HTTP / async / connectivity:

- `requests`
- `aiohttp`
- `websockets`

Graph / structure utilities:

- `networkx`

## Development Tooling

Declared dev dependency:

- `pyright`

Repository tooling also expects:

- `pytest`
- `ruff`
- `make` for the maintained Linux/WSL operator workflow

## Storage and Artifact Format

Primary storage format:

- Parquet

Supporting code:

- `project/io/`
- `project/io/parquet_compat.py`
- artifact validation in `project/reliability/`

The repo uses manifest-tracked file outputs rather than a database-first design for core run artifacts.

## Execution and Orchestration Stack

Main orchestration patterns:

- Python `argparse` CLIs
- installed console scripts from `pyproject.toml`
- `Makefile` targets for maintained workflows
- GitHub Actions tiers for CI

Important orchestration entry points:

- `project/cli.py`
- `project/pipelines/run_all.py`
- `project/research/agent_io/*.py`
- `project/scripts/*.py`

## CI Stack

Current workflow tiers:

- `tier1.yml`
  - structural fast gate
- `tier2.yml`
  - deterministic workflow gate
- `tier3.yml`
  - broad correctness gate

Those workflows run combinations of:

- compile checks
- architecture tests
- spec validation
- generated artifact drift checks
- smoke workflows
- replay/runtime determinism checks
- full pytest
- Pyright

## Live Runtime Stack

The live/runtime surface uses:

- `aiohttp` for venue preflight/account queries
- environment-variable based runtime binding
- YAML config loading via `project.spec_registry`
- Binance-specific validation and account normalization in `project/scripts/run_live_engine.py`

## Research and Reliability Stack

Research:

- proposal schema / translation / planning under `project/research/agent_io`
- knowledge and memory under `project/research/knowledge`
- candidate and promotion services under `project/research/services`

Reliability:

- smoke CLI in `project/reliability/cli_smoke.py`
- regression and artifact assertions in `project/reliability/`
- generated audits in `project/scripts/*audit*.py`

## Operator Environment Notes

The maintained command examples assume a Unix-like shell or WSL environment where:

- `.venv/bin/python` exists
- `make` is available
- repo-relative paths behave like normal POSIX paths

The repo can still be invoked from other environments, but the documentation examples and Makefile targets are optimized for Linux/WSL.
