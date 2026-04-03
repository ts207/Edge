# Operator Surface Baseline

This document records the reduced operator-facing execution surface.

## Canonical

Use one command family for normal research issuance, one review family, and one explicit export bridge:

- `edge operator preflight`
- `edge operator plan`
- `edge operator run`
- `edge operator diagnose`
- `edge operator regime-report`
- `edge operator compare`
- `python -m project.research.export_promoted_theses --run_id <run_id>`

`edge` and `edge-backtest` point to the same CLI surface. `backtest` remains an alias.

Treat thesis bootstrap builders as advanced maintenance surfaces, not the default front door.

## Transitional

These remain valid, but they are not the recommended front door for normal operator work:

- `python -m project.research.agent_io.proposal_to_experiment`
- `python -m project.research.agent_io.execute_proposal`
- `python -m project.research.agent_io.issue_proposal`
- `python -m project.pipelines.run_all`

Use them when you need direct inspection of internal boundaries or already know the exact bounded slice.

## Deprecated As Primary Operator Entry

These are still maintained for compatibility or specialized workflows, but should not be the first command an operator reaches for:

- broad `make` orchestration targets for routine bounded research
- direct `run_all` invocation for proposal-shaped work
- ad hoc shell wrappers around proposal compilation and run issuance
- low-level loader / sidecar tooling
- migration notes and compatibility registries as a way to understand normal workflow

## Current decision

The repo keeps its existing engines and wrappers, but the preferred workflow is now:

`discover -> review -> export -> validate`

with bounded research issuance anchored on:

`preflight -> plan -> run`

That is the stable operator contract for local research work.
