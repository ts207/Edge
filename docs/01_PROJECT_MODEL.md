# Project model

This document defines the stable mental model for the repository.

## System boundary

Edge is a governed bridge from bounded research to explicit runtime inputs.

It does five things:

1. define the allowed domain through specs, registries, and contracts
2. accept one operator-facing proposal as a bounded hypothesis
3. normalize that proposal into `AgentProposal` and translate it into a validated experiment plan
4. execute the plan and write durable run and promotion artifacts
5. export one run-derived thesis batch for explicit runtime consumption

The repo is not a notebook workspace and it is not a live trading engine by itself. It is the controlled path between research claims and runtime-readable thesis objects.

## Canonical lifecycle

Research lifecycle:

`single hypothesis proposal -> normalized AgentProposal -> validated plan -> run -> review -> export thesis batch`

Runtime lifecycle:

`explicit thesis batch selection -> deployment-state check -> runtime retrieval -> decisioning -> optional trade submission`

These are connected, but not identical. A good run is not automatically a live tradable thesis.

## Core objects

### Operator proposal

The operator-facing proposal is authored as one atomic hypothesis. It states:

- `program_id`
- `description`
- `start`, `end`
- one symbol
- one timeframe
- one trigger
- one template
- one direction
- one horizon
- one entry lag
- optional contexts, overlays, and bounded-baseline metadata

Canonical example:

- [`spec/proposals/canonical_event_hypothesis_h24.yaml`](/home/irene/Edge/spec/proposals/canonical_event_hypothesis_h24.yaml)

### Normalized `AgentProposal`

The new front door compiles into the legacy internal `AgentProposal`. This is the compatibility bridge that lets downstream code stay unchanged while the operator path is simplified.

### Experiment plan

The proposal translator resolves:

- required detectors
- required features
- required states
- estimated hypothesis count
- `experiment.yaml`
- `run_all_overrides.json`

The validated plan is the executable research contract.

### Run

A run is the durable execution unit identified by `run_id`. It owns:

- proposal memory
- `data/runs/<run_id>/run_manifest.json`
- phase-2 outputs
- promotion outputs
- operator review outputs

### Candidate

A candidate is a research result that survived enough of the search/evaluation path to be reviewed. It is not yet a runtime contract.

### Packaged thesis

A packaged thesis is a governed object with trigger, context, invalidation, evidence, and governance metadata. Runtime consumes packaged theses, not raw candidate rows.

### Thesis batch

A thesis batch is the exported runtime file for one run:

- `data/live/theses/<run_id>/promoted_theses.json`

This run-level batch is the canonical runtime input.

## Evidence versus permission

Two fields answer different questions:

- `promotion_class` answers how strong the evidence is
- `deployment_state` answers where the thesis may be used right now

Operator-facing permission should be read from deployment state:

- `monitor_only`
- `paper_only`
- `live_enabled`

The question “can this trade?” should be answerable from `deployment_state` alone.

## Subsystem roles

### Specs and registries

These define the domain and the allowed search/runtime vocabulary:

- `spec/`
- `project/configs/registries/`
- `project/domain/`
- `project/spec_registry/`

### Operator and proposal IO

These own proposal loading, normalization, validation, issuance, and translation:

- `project/cli.py`
- `project/operator/`
- `project/research/agent_io/`

### Pipelines

These own stage planning, orchestration, provenance, and manifest writing:

- `project/pipelines/`
- `project/contracts/pipeline_registry.py`

### Research and promotion

These own candidate generation, evaluation, promotion, reporting, export, and packaging:

- `project/research/`
- `project/research/services/`

### Runtime and portfolio

These consume exported thesis batches and current market context:

- `project/live/`
- `project/portfolio/`
- `project/engine/`

## Stable invariants

- one operator proposal should describe one bounded claim
- all operator proposals normalize to `AgentProposal` before downstream processing
- runtime thesis batches are run-derived and selected explicitly
- `data/live/theses/index.json` is a catalog, not a runtime default selector
- `deployment_state=live_enabled` is the only state that may reach trading runtime

## What remains compatibility-only

- legacy proposal authoring shapes
- internal promotion ladder as a primary teaching surface
- bootstrap/package flows as the default way to create runtime thesis input
- implicit latest thesis resolution
