# Project model

This document defines the stable mental model for the repository.

## System overview

Edge is a governed research-and-packaging system for event-driven crypto hypotheses.

At a high level, it does five things:

1. **defines domain contracts** for events, episodes, states, templates, regimes, and promotion rules
2. **turns proposals into bounded experiment plans**
3. **executes orchestrated pipeline stages** to produce candidate and promotion artifacts
4. **exports promoted run results into runtime thesis batches**
5. **serves packaged theses to live/runtime and portfolio logic**

That makes the repo neither purely backtest-only nor purely live-only. It is a bridge from governed research to packaged runtime inputs.

## Core objects

### Proposal

A proposal is the operator-facing contract for bounded research.

It specifies at least:

- `program_id`
- date window
- symbol scope
- timeframe
- one trigger
- one template
- one horizon
- one direction
- one entry lag
- objective and promotion profile

The proposal contract lives in `project/research/agent_io/proposal_schema.py`.

### Experiment plan

A validated plan is the translated form of a proposal. It resolves:

- required detectors
- required features
- required states
- estimated hypothesis count
- run-all overrides
- boundedness warnings or blocks

The translation path lives in `project/research/agent_io/proposal_to_experiment.py`.

### Event

An event is a discrete, timestamped trigger.

Examples in the repo include:

- `VOL_SHOCK`
- `LIQUIDATION_CASCADE`
- `BASIS_DISLOC`
- `LIQUIDITY_VACUUM`

Event specifications live primarily in `spec/events/` and the canonical registry surfaces.

### Episode

An episode is a structured multi-step process built from one or more events.

Episodes matter when the repo needs stateful semantics rather than single-bar semantics.

Episode contracts live in `spec/episodes/` and `project/episodes/`.

### Template

A template describes the shape of the claim being tested around a trigger.

Typical examples are continuation- or reversal-style hypothesis shapes. Templates constrain how the search surface is expanded.

Template and search-limit data come from the registry layer under `project/configs/registries/`.

### Candidate

A candidate is the structured output of phase-2 search or downstream promotion filtering.

It is not yet a packaged runtime thesis. It is still a research output that must survive additional gates.

### Promotion artifact

Promotion artifacts record whether a candidate survives promotion-oriented rules such as:

- q-value constraints
- sample quality
- stability
- sign consistency
- cost survival
- negative-control behavior
- coverage and support checks

The canonical service ownership for promotion logic is in `project/research/services/promotion_service.py`.

### Thesis

A thesis is a packaged object that downstream consumers can retrieve and reason over.

A promoted thesis contains fields such as:

- trigger clause
- confirmation clause
- context clause
- invalidation clause
- governance metadata
- evidence summary
- promotion class
- deployment state
- overlap metadata

Packaged theses live under `data/live/theses/` and the contract lives in `project/live/contracts/promoted_thesis.py`.

### Thesis batch

A thesis batch is the runtime JSON artifact exported for one explicit run.

Canonical path:

- `data/live/theses/<run_id>/promoted_theses.json`

## Lifecycle model

### Bounded discovery lifecycle

`proposal -> preflight -> plan -> run -> run manifest -> phase2 candidates -> promotion outputs -> diagnose/compare/regime report -> exported thesis batch`

This lifecycle is for answering a bounded question.

### Thesis packaging lifecycle

`candidate -> tested -> seed_promoted -> paper_promoted -> production_promoted`

This lifecycle is an internal governance ladder. Runtime should still consume an explicit exported batch and inspect deployment state directly.
For operator questions, the real permission model is:

- `monitor_only`
- `paper_only`
- `live_enabled`

The question "can this trade?" should be answered from deployment state, not from the internal promotion ladder.

## Subsystem roles

### Specs and registries

These surfaces define what the repo is allowed to talk about.

- `spec/` — domain specs and authored policies
- `project/configs/registries/` — runtime-friendly registry inputs for events, states, templates, detectors, and search limits
- `project/domain/` and `project/spec_registry/` — compiled/domain views of those specs

### Pipelines

These surfaces coordinate data preparation and stage execution.

- `project/pipelines/` — orchestration, stage planning, execution, provenance, wrappers
- `project/contracts/pipeline_registry.py` — stage-family and artifact contracts

### Research

These surfaces own search, evaluation, promotion, reporting, knowledge, and packaging.

- `project/research/`
- `project/research/services/`
- `project/research/agent_io/`

### Live/runtime

These surfaces consume packaged theses and current context.

- `project/live/`
- `project/portfolio/`
- `project/engine/`

## Current canonical surfaces

The repo has many modules, but only a small set should anchor your mental model.

Primary surfaces:

- `project.cli`
- `project.pipelines.run_all`
- `project.contracts.pipeline_registry`
- `project.research.services.*`
- `project.research.agent_io.*`
- `project.live.*`

Generated inventory for those surfaces exists in `docs/generated/system_map.md`.

## Design constraints that shape the docs

- Proposals bound the search surface before execution.
- Services own policy; wrappers should stay thin.
- Packaged theses are the runtime contract, not raw candidate rows.
- Quality is multi-stage; statistical survival alone is not enough.
- Generated inventories are important, but they are not the teaching surface.
