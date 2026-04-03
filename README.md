# Edge

Edge is a proposal-driven crypto research and packaging repository.

The repo is built to move a bounded claim through a governed path:

`proposal -> validated experiment plan -> artifacted run -> promotion decision -> exported thesis batch -> live/runtime consumption`

This is not a loose notebook workspace. The default operating unit is a **bounded proposal** with explicit trigger scope, template scope, horizons, directions, contexts, and promotion intent.

## What the repository actually does

The codebase has four primary operator-facing actions:

1. `discover` — translate a proposal, validate it, and run a bounded research slice
2. `review` — diagnose a run, compare runs, or inspect regime stability
3. `export` — turn one specific promoted run into a runtime thesis batch
4. `validate` — run contract, governance, and minimum green gate checks

It also keeps one advanced maintenance lane:

- `package` — deprecated/internal bootstrap packaging for broader thesis governance work, not the canonical runtime-batch path

Behind those actions are three connected layers:

- **pipeline orchestration** in `project/pipelines/`
- **research and promotion logic** in `project/research/`
- **live/runtime consumption** in `project/live/` and `project/portfolio/`

## Fastest correct mental model

Use this sequence when reading the repo:

1. **Specs define the allowed domain.**
   `spec/` holds event, episode, regime, promotion, runtime, and search specifications.
2. **A proposal narrows the search surface.**
   `project/research/agent_io/proposal_schema.py` defines the proposal contract.
3. **The operator path turns the proposal into a validated plan.**
   `edge operator preflight|plan|run` is the canonical entry.
4. **`run_all` orchestrates the underlying stages.**
   `project/pipelines/run_all.py` coordinates ingest, core, research, runtime-invariant, and evaluation stages.
5. **Research services produce candidate and promotion artifacts.**
   `project/research/services/` is the canonical service layer.
6. **Promotion export creates runtime thesis batches from one run at a time.**
   `python -m project.research.export_promoted_theses --run_id <run_id>` writes the canonical runtime batch under `data/live/theses/<run_id>/`.
7. **The live layer consumes explicit thesis batches, not raw notes or implicit latest pointers.**
   `project/live/` and `project/portfolio/` work from packaged thesis objects and overlap metadata.

## Preferred front door

Use these surfaces first:

```bash
make discover PROPOSAL=<proposal.yaml> DISCOVER_ACTION=preflight|plan|run
make export RUN_ID=<run_id>
make validate
make review RUN_ID=<run_id> REVIEW_ACTION=diagnose|regime-report
make review REVIEW_ACTION=compare RUN_IDS=<baseline_run,followup_run>
```

Direct CLI equivalents:

```bash
edge operator preflight --proposal <proposal.yaml>
edge operator plan --proposal <proposal.yaml>
edge operator run --proposal <proposal.yaml>
edge operator diagnose --run_id <run_id>
edge operator regime-report --run_id <run_id>
edge operator compare --run_ids <run_a,run_b>
```

Use `run_all`, stage scripts, and packaging scripts directly only when you intentionally need advanced control.

## Current repo shape

High-value top-level areas:

- `project/` — Python implementation
- `spec/` — authored domain, search, runtime, and promotion specs
- `docs/` — canonical human docs, generated inventories, and maintenance references
- `data/` — lake, reports, live thesis store, and runtime artifacts
- `deploy/` — systemd and env examples for live engine surfaces
- `agents/` — analyst/compiler/coordinator playbooks
- `plugins/` — repo-local plugin surfaces and helper wrappers

Largest implementation surfaces in this snapshot:

- `project/research/` — research, search, promotion, reporting, knowledge, packaging
- `project/pipelines/` — orchestration, stage planning, ingestion, features, runtime invariants
- `project/events/` — event contracts, canonicalization, registries, detectors, ontology helpers
- `project/live/` — thesis retrieval, context building, scoring, OMS, policy, replay
- `project/tests/` — architecture, contracts, runtime, research, pipeline, strategy, docs, specs

## Canonical documents

Read these in order:

1. [docs/00_START_HERE.md](docs/00_START_HERE.md)
2. [docs/01_PROJECT_MODEL.md](docs/01_PROJECT_MODEL.md)
3. [docs/02_REPOSITORY_MAP.md](docs/02_REPOSITORY_MAP.md)
4. [docs/03_OPERATOR_WORKFLOW.md](docs/03_OPERATOR_WORKFLOW.md)
5. [docs/04_COMMANDS_AND_ENTRY_POINTS.md](docs/04_COMMANDS_AND_ENTRY_POINTS.md)
6. [docs/05_ARTIFACTS_AND_INTERPRETATION.md](docs/05_ARTIFACTS_AND_INTERPRETATION.md)
7. [docs/06_QUALITY_GATES_AND_PROMOTION.md](docs/06_QUALITY_GATES_AND_PROMOTION.md)
8. [docs/09_THESIS_BOOTSTRAP_AND_PROMOTION.md](docs/09_THESIS_BOOTSTRAP_AND_PROMOTION.md)
9. [docs/11_LIVE_THESIS_STORE_AND_OVERLAP.md](docs/11_LIVE_THESIS_STORE_AND_OVERLAP.md)
10. [docs/10_APPS_PLUGINS_AND_AGENTS.md](docs/10_APPS_PLUGINS_AND_AGENTS.md)

Use [docs/README.md](docs/README.md) as the full index.

## Generated inventory versus narrative docs

The repo contains two different doc classes:

- **narrative docs** in `docs/*.md` that explain structure, workflow, and operating rules
- **generated docs** in `docs/generated/` that reflect current inventory or current artifact state

Do not confuse them.

Narrative docs answer: *how the system works and how to use it correctly.*
Generated docs answer: *what the current repo or artifact state looks like right now.*

Important generated docs already present in this snapshot include:

- `docs/generated/system_map.md`
- `docs/generated/event_contract_reference.md`
- `docs/generated/promotion_seed_inventory.md` for advanced bootstrap maintenance
- `docs/generated/thesis_empirical_summary.md`
- `docs/generated/seed_thesis_catalog.md` for advanced bootstrap maintenance
- `docs/generated/seed_thesis_packaging_summary.md` for advanced bootstrap maintenance
- `docs/generated/thesis_overlap_graph.md`
- `docs/generated/founding_thesis_evidence_summary.md`
- `docs/generated/structural_confirmation_summary.md`
- `docs/generated/shadow_live_thesis_summary.md`

## Synthetic demo

This snapshot now includes a proposal example at:

- `spec/proposals/demo_synthetic_fast.yaml`

Use it with:

```bash
make synthetic-demo
```

or:

```bash
python -m project.scripts.run_demo_synthetic_proposal --plan_only 1
```

## Ground rules

- Learn the operator path before low-level scripts.
- Treat proposals and exported thesis batches as first-class contracts.
- Prefer canonical service and CLI surfaces over compatibility wrappers.
- Do not treat exit status alone as proof that a run is good.
- Do not answer "can this trade?" from promotion class. Inspect `deployment_state` first.
- Do not rely on an implicit latest thesis batch for runtime selection.
- Do not treat generated markdown as a substitute for understanding the code path that produced it.
