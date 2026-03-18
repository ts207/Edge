# Agent System Instructions

This file defines the repository-local operating rules for coding agents working in this repo.

Use it together with [CLAUDE.md](./CLAUDE.md). `CLAUDE.md` explains how research should be run. This file explains how an implementation agent should work safely inside the codebase.

## Core Role

You are modifying and maintaining a research platform.

Priorities:

1. preserve contract correctness
2. keep research behavior attributable
3. prefer narrow, reversible changes
4. update tests when behavior changes
5. keep docs aligned with real repo behavior

Do not optimize for superficial output volume.

## Project Structure

Core code lives in `project/`.

Important areas:

- `project/pipelines/`: orchestration and stage entrypoints
- `project/events/`: detector logic, family logic, registry-facing event behavior
- `project/features/`: shared feature and regime helpers
- `project/research/`: discovery, evaluation, promotion, diagnostics
- `project/contracts/`: artifact and stage contracts
- `project/scripts/`: operator and maintenance entrypoints
- `docs/`: maintained operator and reference docs
- `tests/`: regression and contract coverage

Generated outputs under `data/` are not source files unless explicitly maintained as fixtures or baselines.

## Working Rules

When making changes:

- inspect the local code before assuming behavior
- preserve backward-compatible surfaces when possible
- keep stage and artifact contracts explicit
- prefer canonical shared helpers over new local duplicates
- treat generated diagnostics as outputs, not authored policy

If a change affects:

- detector semantics
- pipeline contracts
- feature definitions
- search or promotion behavior

then update or add tests.

## Build And Validation Commands

Typical commands:

```bash
pip install -e .
pip install -e ".[nautilus]"
make test
make test-fast
make lint
make format-check
make format
make discover-edges
```

Useful plan-only example:

```bash
edge-run-all --run_id demo --symbols BTCUSDT --start 2024-01-01 --end 2024-01-31 --plan_only 1
```

Use the narrowest validation slice that credibly checks the changed behavior.

## Coding Style

- target Python 3.11
- 4-space indentation
- Ruff defaults
- repo line length `100`
- explicit, domain-specific names over vague generic names
- `snake_case` for functions, variables, and file names
- `UPPER_SNAKE_CASE` for constants and spec identifiers where appropriate

Keep CLI entrypoints and stage boundaries explicit. Do not hide orchestration behind ambiguous helper layers.

## Testing Rules

Write pytest tests as `tests/**/test_*.py`.

Place regressions near the owned surface:

- event logic: `tests/events/`
- pipeline behavior: `tests/pipelines/`
- architecture and contract rules: `tests/architecture/`, `tests/contracts/`
- research behavior: `tests/research/`

Mark long-running coverage with `@pytest.mark.slow` when appropriate so `make test-fast` remains useful.

## Change Discipline

Before broad refactors:

- identify the contract you are changing
- identify the tests that pin it
- keep the write set focused

When editing docs:

- prefer maintained operator docs over ad hoc notes
- keep `CLAUDE.md`, `AGENTS.md`, and `GEMINI.md` aligned on core policy
- do not describe repo behavior that is not actually implemented

## Commits And PRs

Prefer short conventional subjects such as:

- `feat: add context-quality report`
- `fix: tighten funding persistence subtype handling`

PRs should state:

- the affected surface
- the behavioral risk
- the validation commands run
- any artifact or operator-facing impact

## Config And Operations Notes

- prefer checked-in templates under `deploy/`
- do not commit secrets
- do not commit one-off `data/` outputs unless they are intentional fixtures or documented baselines
- do not silently rewrite or remove maintained baselines without updating the related docs and tests
