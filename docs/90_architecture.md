# Architecture

This document explains how the current Edge repo is structured architecturally. The four stages remain the public lifecycle, but the implementation is now a layered control plane with explicit runtime contracts and interface shells.

## Architectural Summary

The current repo has five major layers:

1. lifecycle command surface
2. planner and research services
3. artifact and registry contracts
4. runtime thesis and live execution
5. interface wrappers such as plugins and the ChatGPT app

The key architectural point is that Edge is no longer just "a few scripts that run in sequence." It is a contract-driven system whose stages communicate through persisted artifacts and typed runtime objects.

## Primary Control Plane

The most important architectural surfaces are:

- `project/cli.py`
  The canonical command router for lifecycle verbs and support planes.

- `project/pipelines/run_all.py`
  Planner-owned orchestration and stage graph execution.

- `project/research/services/`
  Discovery, evaluation, promotion, reporting, and run-catalog service layer.

- `project/live/`
  Runtime thesis store, live approval gate, runner, reconciliation, risk controls.

- `project/artifacts/catalog.py`
  Canonical artifact path helper layer.

## Layer 1: Lifecycle Commands

The public lifecycle is expressed as:

- `discover`
- `validate`
- `promote`
- `deploy`

These commands should be treated as the conceptual architecture.

Support commands exist too:

- `operator` for compatibility
- `catalog` for research operations and artifact intelligence
- `ingest` for raw data ingestion
- `pipeline` for deprecated orchestration compatibility

Those support surfaces should not be mistaken for separate business lifecycles.

## Layer 2: Research and Planner Services

The discovery/validation/promotion behavior is not owned solely by CLI handlers. The real execution model sits in service and planner layers.

### Discovery

- `project/research/phase2_search_engine.py`
- `project/research/services/candidate_discovery_service.py`
- `project/discover/`

### Validation

- `project/research/services/evaluation_service.py`
- `project/research/validation/`
- `project/validate/`

### Promotion and export

- `project/research/services/promotion_service.py`
- `project/research/live_export.py`
- `project/promote/`

These surfaces give the repo a proper separation between command routing and stage implementation.

## Layer 3: Artifact And Registry Contracts

Two contract families dominate the repo:

### Artifact contracts

Stages communicate through persisted artifacts rather than in-memory chaining.

That gives:

- auditability
- resumability
- clear failure boundaries
- easier compatibility handling for older runs

### Registry contracts

Event semantics are defined through the registry lineage:

1. authored event specs in `spec/events/*.yaml`
2. compiled registry in `spec/events/event_registry_unified.yaml`
3. projected domain graph in `spec/domain/domain_graph.yaml`

This is an architectural dependency of discovery, validation interpretation, and runtime trigger matching.

## Layer 4: Runtime Thesis Architecture

The runtime architecture is now more explicit than the earlier docs described.

The core path is:

```text
exported thesis batch
  → ThesisStore
  → DeploymentGate
  → reconciliation
  → scoring / drift / decay / allocation controls
  → OMS / execution
```

Important architectural invariants:

- runtime reads exported thesis batches from `data/live/theses/`
- `DeploymentGate` is the contract boundary for live approval metadata
- only `live_enabled` theses are tradeable live
- richer thesis lifecycle states exist even if launcher checks are conservative

## Layer 5: Interface Shells

The repo includes interface layers that should not redefine system policy.

### ChatGPT app

`project/apps/chatgpt/` is an MCP / ChatGPT-oriented interface around canonical operator, reporting, and dashboard behavior.

### Plugin wrappers

`plugins/edge-agents/` provides maintenance and operator wrapper scripts such as:

- proposal preflight / plan / run
- repo validation
- thesis export
- plugin sync
- ChatGPT app inspection

Architecturally, these are shells around the repo. They are not the source of truth for lifecycle behavior.

## Compatibility Boundary

Compatibility still matters. The repo intentionally keeps:

- `edge operator ...`

But the architecture should be documented as:

- stage verbs are canonical
- compatibility commands wrap those semantics
- generated docs and wrappers are downstream surfaces, not policy owners

## Why The Architecture Uses Persisted Boundaries

Persisted stage boundaries are a deliberate architectural choice.

They allow:

- stage reruns without recomputing everything
- stable handoff from research to runtime
- artifact audit and historical comparison
- live gating against typed thesis objects rather than ad hoc promotion tables

That separation is one of the most important "project updates" the docs now need to reflect clearly.
