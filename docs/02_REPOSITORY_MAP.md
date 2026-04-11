# Repository Map

This document maps the current repository at the level a maintainer or operator actually needs. The repo has grown beyond a simple stage-package split, so this map emphasizes ownership and runtime boundaries rather than only directory names.

## Top-Level Layout

```text
Edge/
├── project/                  Main Python package
├── spec/                     Authored YAML contracts and proposals
├── docs/                     Hand-authored docs and generated references
├── data/                     Local artifacts, reports, runs, and thesis inventory
├── plugins/                  Repo-local plugin surfaces
└── Makefile                  Canonical repo task wrappers
```

## `project/` Directory Map

### Command and control

- `project/cli.py`
  Canonical CLI for `discover`, `validate`, `promote`, `deploy`, plus compatibility surfaces like `operator`, `pipeline`, `catalog`, and `ingest`.

- `project/pipelines/`
  Planner-owned orchestration, stage graph assembly, smoke flows, and run manifests.

- `project/operator/`
  Compatibility utilities for preflight, lint, explain, stability reports, and campaigns.

### Stage-oriented packages

- `project/discover/`
  Discover-stage entry helpers and integration surface.

- `project/validate/`
  Validate-stage entry helpers.

- `project/promote/`
  Promote-stage entry helpers.

- `project/deploy/`
  Deploy-facing support code.

### Research and evaluation core

- `project/research/`
  The largest research surface. Contains discovery, validation, promotion, search, reporting, benchmarks, trigger discovery, campaign support, and service-layer orchestration.

- `project/research/services/`
  Service-layer implementations for discovery, evaluation, promotion, run catalog, and reporting.

- `project/research/validation/`
  Validation bundle schemas, result writing, and evidence logic.

- `project/research/trigger_discovery/`
  Advanced proposal-generating trigger mining and adoption-state management.

### Runtime and live execution

- `project/live/`
  Thesis contracts, thesis store, deployment gate, live runner, drift/decay, reconciliation, kill switch, and runtime-specific helpers.

- `project/runtime/`
  Normalized runtime streams, replay, and invariants.

- `project/execution/`
  Backtest/runtime execution plumbing.

- `project/engine/`
  PnL, allocation, and other execution-model utilities.

### Domain, registry, and events

- `project/events/`
  Event families, adapters, detectors, scoring, registry helpers.

- `project/domain/`
  Compiled registry consumers, domain models, and promotion/domain read models.

- `project/spec_registry/` and `project/spec_validation/`
  Registry and spec validation surfaces.

### App and interface layers

- `project/apps/chatgpt/`
  ChatGPT app / MCP scaffold over canonical operator and reporting surfaces.

- `project/apps/pipeline/`
  App-oriented pipeline surface.

### Shared infrastructure

- `project/core/`
  Common config, exceptions, coercion, and utilities.

- `project/io/` and `project/infra/`
  I/O, orchestration helpers, and infrastructure scaffolding.

- `project/artifacts/`
  Canonical artifact path helpers.

### Testing and reliability support

- `project/tests/`
  The single pytest discovery tree for the repository.

- `project/reliability/`
  Reliability-oriented logic and tooling.

- `project/scripts/`
  Shell and Python entrypoint scripts for live engine, governance, artifact generation, and maintenance.

## `spec/` Directory Map

- `spec/proposals/`
  Bounded research proposal YAML files used by `discover`.

- `spec/campaigns/`
  Campaign contract specs for the compatibility operator campaign lane.

- `spec/events/`
  Authored event definitions and the compiled event registry surfaces.

- `spec/gates.yaml`
  Promotion and validation thresholds used by the canonical research lifecycle.

- `spec/templates/`
  Template and registry YAML surfaces referenced by the broader event/domain system.

## `docs/` Directory Map

- Hand-authored core docs:
  `00_overview.md`, `01_discover.md`, `02_validate.md`, `03_promote.md`, `04_deploy.md`

- Supporting references:
  `02_REPOSITORY_MAP.md`, `05_data_foundation.md`, `06_core_concepts.md`, `90_architecture.md`, `operator_command_inventory.md`

- Generated references:
  `docs/generated/`

Generated docs should be refreshed by repo generators, not hand-edited.

## Local-Only Scratch Paths

These top-level paths are intentionally local-only and should not be tracked:

- `tmp/` and `.tmp/`
  Proposal scratch, pytest residue, and local verification output.

- `live/persist/`
  Runtime persistence snapshots written by local runs.

- `artifacts/` and `logs/`
  Local runtime and debugging output.

## `data/` Directory Map

The repo currently uses several important data roots:

- `data/lake/`
  Raw, cleaned, and feature data.

- `data/reports/`
  Stage outputs, diagnostics, and research reports.

- `data/runs/`
  Run-specific manifests, runtime outputs, and checklists.

- `data/live/theses/`
  Exported runtime thesis inventory that deploy consumes.

- `data/research/programs/`
  Program memory and research coordination artifacts.

## Canonical Discovery Flow

The planner-owned research flow still looks like:

```text
ingest
  → build_cleaned
  → build_features
  → build_market_context
  → phase2_search_engine
  → validation bundle
  → promotion
  → export thesis batch
  → deploy
```

The key point is that `phase2_search_engine` is still the canonical planner-owned discovery stage and authoritative discovery engine, but the repo now has clearer downstream boundaries than older docs showed.

## Runtime Thesis Flow

The runtime-side path is:

```text
exported thesis batch
  → ThesisStore
  → DeploymentGate
  → reconciliation / drift / scoring / risk
  → OMS / execution
```

Only `live_enabled` theses are tradeable live.

## Event Registry Lineage

Event metadata travels through three linked surfaces:

1. `spec/events/*.yaml`
2. `spec/events/event_registry_unified.yaml`
3. `spec/domain/domain_graph.yaml`

Any change to event routing, ontology, runtime metadata, or trigger semantics should keep those three layers aligned.

## Plugin And App Boundaries

Two repo-local interface layers matter:

- `plugins/edge-agents/`
  Maintenance, operator, export, sync, and validation wrappers.

- `project/apps/chatgpt/`
  App/MCP layer that fronts canonical repo services.

Neither should be treated as the authority for thesis policy or research semantics. They are interface layers around the main repository model.
