# Repository Guidelines

## Project Structure & Module Organization
Core application code lives in `project/`. Use `project/pipelines/run_all.py` for end-to-end orchestration, `project/events/` for detector and registry logic, and `project/research/` for discovery and promotion workflows. Keep executable helpers in `scripts/`, reference material in `docs/`, and formal specs in `spec/`. Tests live under `tests/`, with focused suites such as `tests/events/`, `tests/strategy_dsl/`, and `tests/architecture/`. Local outputs are typically written to `data/` and should not be treated as source files.

## Build, Test, and Development Commands
Install the project in editable mode with `pip install -e .` or `pip install -e ".[nautilus]"` for the optional Nautilus surface. Use `make test` for the full pytest suite and `make test-fast` for the non-slow profile. Run `make discover-edges` for the main research discovery path, or `edge-run-all --run_id demo --symbols BTCUSDT --start 2024-01-01 --end 2024-01-31 --plan_only 1` to inspect pipeline plans without executing them. Check changed Python files with `make lint`, `make format-check`, and `make format`.

## Coding Style & Naming Conventions
Target Python 3.11. Follow 4-space indentation and Ruff defaults with the repo’s `line-length = 100`. Prefer explicit, domain-specific module names such as `event_scoring.py` or `phase2_candidate_discovery.py`. Use `snake_case` for functions, variables, and file names; reserve `UPPER_SNAKE_CASE` for constants and spec identifiers when the surrounding files already use it. Keep CLI entry points and pipeline stages explicit rather than hiding orchestration behind generic helpers.

## Testing Guidelines
Write pytest tests as `tests/**/test_*.py`. Regressions for event logic belong near `tests/events/`; import-boundary and repository-contract checks belong near `tests/architecture/`. Mark long-running coverage with `@pytest.mark.slow` so `make test-fast` can exclude it. Add or update tests whenever detector thresholds, pipeline contracts, or strategy DSL behavior changes.

## Commit & Pull Request Guidelines
Recent history follows short Conventional Commit prefixes such as `feat:` and `fix:`. Keep commit subjects imperative and scoped to the behavioral change, for example `fix: tighten FUNDING_FLIP threshold`. Pull requests should state the affected pipeline or detector surface, summarize risk, list the validation commands run, and attach artifacts or screenshots only when the change affects generated reports or operator-facing outputs.

## Configuration & Operations Notes
Prefer checked-in templates under `deploy/env/` and `deploy/systemd/` over ad hoc runtime configs. Do not commit secrets, generated `data/` outputs, or one-off experiment artifacts unless they are intentional fixtures or documented baselines.
