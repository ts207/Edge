# Operator Surface Baseline

This document records the reduced operator-facing execution surface.

## Canonical

Use one command family for normal research issuance and one packaging lane for thesis work:

- `edge operator preflight`
- `edge operator plan`
- `edge operator run`
- thesis bootstrap builders for packaging and overlap refresh

`edge` and `edge-backtest` point to the same CLI surface. `backtest` remains an alias.

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

`discover -> package -> validate -> review`

with bounded research issuance anchored on:

`preflight -> plan -> run`

That is the stable operator contract for local research work.
