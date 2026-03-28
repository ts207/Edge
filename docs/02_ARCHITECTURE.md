# Architecture Reference

## Control Plane

The primary control plane is the `run_all` orchestrator:

- `project/pipelines/run_all.py`
- `project/pipelines/pipeline_planning.py`
- `project/pipelines/pipeline_execution.py`
- `project/pipelines/pipeline_provenance.py`
- `project/pipelines/pipeline_audit.py`
- `project/pipelines/pipeline_summary.py`

Responsibility split:

- planning
  - parse CLI and experiment overlays
  - resolve stage list
  - compute effective behavior
  - validate artifact contracts
- execution
  - materialize bootstrap state
  - seed / resume manifests
  - execute stage scripts
  - collect timings and postflight checks
- provenance and audit
  - run hashes, fingerprints, spec hashes, invariant status, comparison output

## Stage Family Architecture

Stage families are declared in code, not in docs:

- `ingest`
- `core`
- `runtime_invariants`
- `phase1_analysis`
- `phase2_event_registry`
- `phase2_discovery`
- `promotion`
- `research_quality`
- `strategy_packaging`

Each family maps stage name patterns to script patterns. Artifact token contracts are resolved from the same registry.

This makes the architecture contract-driven instead of depending on fragile prose diagrams.

## Package Topology

The current `project/` tree is wider than older docs implied.

High-level topology:

- `apps/`
  - app-facing pipeline adapters
- `artifacts/`
  - artifact helpers and baselines
- `compilers/`
  - compilation support code
- `contracts/`
  - schemas and pipeline contract declarations
- `core/`
  - foundational helpers, config, exceptions, timeframes
- `domain/`
  - domain registry and typed definitions
- `engine/`
  - strategy execution / simulation machinery
- `eval/`
  - evaluation helpers and suites
- `events/`
  - detectors, families, registries, mapping, deconfliction
- `execution/`
  - backtest and runtime execution logic
- `experiments/`
  - experiment-oriented code
- `features/`
  - canonical feature computation and helpers
- `infra/`
  - orchestration and IO support
- `io/`
  - parquet and utility IO helpers
- `live/`
  - live ingest and runtime support
- `pipelines/`
  - stage entry points and orchestration
- `portfolio/`
  - portfolio and allocation logic
- `reliability/`
  - smoke workflows and regression assertions
- `research/`
  - agent I/O, knowledge, services, validation, recommendations, search
- `runtime/`
  - runtime-specific helpers
- `schemas/`
  - schema definitions
- `spec_registry/`
  - YAML loading access layer
- `spec_validation/`
  - ontology / grammar / search validation
- `specs/`
  - spec hashing and code-side spec helpers
- `strategy/`
  - DSL, runtime, models, templates
- `synthetic_truth/`
  - synthetic-truth tooling
- `tests/`
  - repository test suite

## Event and Ontology Layer

`project/events/` now contains more than detector implementations.

Important sub-areas:

- `detectors/`
  - concrete detector implementations
- `families/`
  - family/grouped detector surfaces
- `registries/`
  - registry support
- `event_specs.py`
  - loaded event spec access
- `ontology_mapping.py`
  - mapping from raw events to canonical structures
- `ontology_deconfliction.py`
  - deconfliction rules
- `phase2.py`
  - phase-2 event chain definitions

The architecture intentionally separates:

- raw detector materialization
- canonical mapping
- executable event registry construction
- routing into discovery / promotion workflows

## Research Layer

`project/research/` is the operator-facing intelligence layer.

Major responsibilities:

- proposal schema and translation
- memory store and query
- candidate discovery services
- promotion services
- run comparison and drift logic
- validation and evidence bundles
- robustness and recommendations

This is where the repository moves from "pipeline outputs exist" to "a research claim is interpretable and promotable."

## Reliability Layer

`project/reliability/` provides:

- smoke dataset generation
- smoke execution wrappers
- artifact schema validation
- storage fallback checks
- bundle policy consistency checks

This layer underpins the smoke CLI and the workflow gate tests.

## Live Runtime Layer

The live surface is split across:

- `project/live/`
- `project/scripts/run_live_engine.py`
- `project/configs/live_paper.yaml`
- `project/configs/live_production.yaml`

The runtime script validates:

- environment naming
- snapshot path expectations
- Binance venue connectivity
- account snapshot normalization
- runtime configuration integrity

The live engine is not just a script runner. It includes explicit environment validation and venue preflight logic.

## Architecture Source of Truth

If you need live, generated architecture summaries, use:

- `docs/generated/system_map.md`
- `docs/generated/system_map.json`
- `docs/generated/architecture_metrics.json`

If those need to be refreshed, regenerate them via the maintenance scripts instead of editing docs to match memory.
