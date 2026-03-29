# Edge

Edge is a research platform for event-driven alpha discovery in crypto markets.

It is built to test explicit claims under artifact, cost, and promotion discipline. The repository is not a generic notebook sandbox and not a "run a backtest, inspect Sharpe, move on" stack. The operating unit is a bounded hypothesis carried through a reproducible pipeline.

## Core Model

Edge turns:

`proposal -> validated experiment config -> planned run -> artifacted execution -> gated promotion decision -> strategy candidate / live runtime input`

The platform is centered on:

- event definitions and ontology mapping
- canonical regimes and template legality
- proposal-driven discovery
- manifest-tracked pipeline execution
- promotion gates before deployment-oriented outputs
- replay, determinism, and artifact reconciliation checks

## Pipeline

The end-to-end orchestrator is `project/pipelines/run_all.py`.

At a high level the run flow is:

1. `ingest`
2. `core`
   - cleaned bars
   - features
   - market context
   - microstructure rollups
   - coverage / integrity checks
3. `runtime_invariants`
   - replay stream materialization
   - causal lane ticks
   - optional replay checks
4. `phase1_analysis`
   - detector execution
   - event episode creation
5. `phase2_event_registry`
   - canonicalization
   - executable event registry build
6. `phase2_discovery`
   - conditional hypothesis generation / search
   - bridge evaluation
   - discovery quality summary
7. `promotion`
   - naive entry evaluation
   - negative controls
   - candidate promotion
   - edge registry / campaign memory updates
8. `research_quality`
   - expectancy analysis
   - trap validation
   - recommendations checklist
9. `strategy_packaging`
   - blueprint compilation
   - strategy candidate construction
   - profitable strategy selection

The source of truth for stage families and artifact contracts is `project/contracts/pipeline_registry.py`.

## Repo Layout

There are three different "configuration" layers and they serve different purposes:

- `spec/`
  - YAML domain specs: events, ontology, grammar, objectives, search, runtime, templates, benchmarks, proposals
- `project/configs/`
  - runnable workflow configs, live configs, synthetic suites, registry defaults, retail profiles
- `project/`
  - Python implementation

High-value code surfaces:

- `project/pipelines/`
  - pipeline entry points and orchestration
- `project/research/`
  - proposal I/O, discovery, promotion, diagnostics, knowledge memory
- `project/events/`
  - detectors, families, registries, ontology helpers
- `project/strategy/`
  - DSL, template compatibility, executable strategy models
- `project/live/` and `project/scripts/run_live_engine.py`
  - live runtime support
- `project/reliability/`
  - smoke workflows, regression assertions, artifact validation
- `project/contracts/`
  - stage families, artifact token contracts, schemas
- `project/tests/`
  - architecture, smoke, contracts, regressions, replay, runtime, docs, domain, strategy, synthetic truth

## Current Command Surface

Installed console scripts from `pyproject.toml`:

- `backtest`
- `edge-backtest`
- `edge-run-all`
- `edge-live-engine`
- `edge-phase2-discovery` via `project.research.cli.candidate_discovery_cli`
- `edge-promote` via `project.research.cli.promotion_cli`
- `edge-smoke`
- `compile-strategy-blueprints` via `project.research.compile_strategy_blueprints`
- `build-strategy-candidates` via `project.research.build_strategy_candidates`
- `ontology-consistency-audit`

Maintained `make` targets:

- `make discover-target EVENT=<EVENT> SYMBOLS=<SYMBOLS>`
- `make discover-edges`
- `make discover-blueprints`
- `make run`
- `make baseline`
- `make golden-workflow`
- `make golden-certification`
- `make benchmark-maintenance-smoke`
- `make benchmark-maintenance`
- `make minimum-green-gate`
- `make test`
- `make test-fast`
- `make lint`
- `make format-check`

## Proposal-Driven Research

The proposal toolchain lives in `project/research/agent_io/`.

Typical bounded loop:

```bash
.venv/bin/python -m project.research.knowledge.query knobs
.venv/bin/python -m project.research.knowledge.query memory --program_id btc_campaign

.venv/bin/python -m project.research.agent_io.proposal_to_experiment \
  --proposal /abs/path/to/proposal.yaml \
  --registry_root project/configs/registries \
  --config_path /tmp/experiment.yaml \
  --overrides_path /tmp/run_all_overrides.json

.venv/bin/python -m project.research.agent_io.issue_proposal \
  --proposal /abs/path/to/proposal.yaml \
  --registry_root project/configs/registries \
  --plan_only 1
```

The plan-first rule is enforced socially and operationally. Material runs should be inspected before execution.

## Generated Artifacts

Do not treat hand-authored docs as live inventory.

Use `docs/generated/` for current generated surfaces:

- `system_map.{md,json}`
- `detector_coverage.{md,json}`
- `ontology_audit.json`
- `event_ontology_mapping.{md,json}`
- `canonical_to_raw_event_map.{md,json}`
- `context_tag_catalog.{md,json}`
- `composite_event_catalog.{md,json}`
- `strategy_construct_catalog.{md,json}`
- `event_ontology_audit.{md,json}`
- `regime_routing_audit.{md,json}`
- `architecture_metrics.json`

Those files are the authoritative inventory and audit outputs for current detector coverage, ontology health, routing, and generated architecture summaries.

## Quality Model

A run is only trustworthy when:

- manifests reconcile
- artifacts exist and validate
- costs are accounted for
- promotion evidence is explicit
- drift checks stay within tolerance
- replay / determinism expectations remain intact

Exit status alone is not sufficient.

## Read Next

- [docs/README.md](/home/irene/Edge/docs/README.md)
- [docs/03_OPERATOR_WORKFLOW.md](/home/irene/Edge/docs/03_OPERATOR_WORKFLOW.md)
- [docs/04_COMMANDS_AND_ENTRY_POINTS.md](/home/irene/Edge/docs/04_COMMANDS_AND_ENTRY_POINTS.md)
- [docs/06_QUALITY_GATES_AND_PROMOTION.md](/home/irene/Edge/docs/06_QUALITY_GATES_AND_PROMOTION.md)
- [docs/08_TESTING_AND_MAINTENANCE.md](/home/irene/Edge/docs/08_TESTING_AND_MAINTENANCE.md)
