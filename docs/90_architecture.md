# Architecture

This document describes the internal structure of the Edge repository and how it implements the four-stage model.

## Current State

The repo's operational front door is not a set of isolated stage packages. The primary control plane is:

* `project/cli.py` for canonical stage verbs and deprecated compatibility verbs
* `project/pipelines/run_all.py` for planner-owned orchestration and run manifests
* `project/research/phase2_search_engine.py` for canonical phase-2 discovery
* `project/live/runner.py` for runtime session execution
* `spec/events/*.yaml` -> `spec/events/event_registry_unified.yaml` -> `spec/domain/domain_graph.yaml` for event metadata lineage

## Module Map

### 1. Control Plane
* `project/cli.py`: Canonical `discover`, `validate`, `promote`, `deploy` entrypoint plus deprecated `operator` compatibility surface.
* `project/pipelines/`: Planner-owned orchestration, stage assembly, provenance, manifests, and pipeline bookkeeping.
* `project/operator/`: Proposal preflight, explain/lint helpers, campaign support, and bounded operator utilities.

### 2. Research Core
* `project/research/phase2_search_engine.py`: Canonical planner-owned phase-2 discovery stage.
* `project/research/agent_io/`: Proposal handling and experiment execution.
* `project/research/services/`: Evaluation, promotion, reporting, and run-comparison services.
* `project/research/validation/`: Statistical tests, regimes, and evidence bundles.
* `project/research/promotion/`: Gate evaluators and decision logic.

### 3. Runtime Core
* `project/live/`: Execution engine, OMS, thesis store, deployment gate, and live safeguards.
* `project/runtime/`: Runtime-facing replay, invariants, normalized events, and OMS replay support.
* `project/live/contracts/`: Data models for promoted theses and trade intents.

### 4. Infrastructure
* `project/io/`: Parquet and CSV utilities.
* `project/core/`: Configuration, logging, and common exceptions.
* `project/domain/`: Compiled domain registry and graph-backed read model.
* `project/events/`: Event detectors, authored event specs, and registry-sidecar tooling.

## Artifact Boundaries

Stages communicate through persisted artifacts. This gives:

1. Isolation: a failure in one stage does not corrupt another stage's state.
2. Auditability: every deployment can be traced through a concrete artifact chain.
3. Resumability: stages can be re-run independently if data or logic changes.

## Event Registry Path

Event metadata moves through three layers:

1. Authored per-event specs in `spec/events/*.yaml`
2. Canonical compiled event registry in `spec/events/event_registry_unified.yaml`
3. Runtime/read-model projection in `spec/domain/domain_graph.yaml`

Changes to event ontology, routing, or runtime metadata should update those layers through the repo generators rather than by editing generated files manually.

## Compatibility Layer

`project/cli.py` still exposes deprecated `operator` and `pipeline` surfaces for compatibility. Those commands are wrappers around the stage-based model and should not be documented as the primary architecture.
