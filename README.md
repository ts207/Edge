# Edge

Edge is a governed event-driven crypto research platform.

The repository now supports the full path from:

`event contract -> bounded experiment -> evidence bundle -> promoted thesis -> thesis store -> overlap-aware live/runtime input`

The operating unit is still a bounded hypothesis, but the downstream output is no longer just a candidate row. The repo now carries:

- an authoritative event contract and maturity layer
- a canonical campaign contract
- episode contracts and episode registry support
- staged thesis promotion classes (`candidate`, `tested`, `seed_promoted`, `paper_promoted`, `production_promoted`)
- a canonical thesis store under `data/live/theses/`
- overlap-aware portfolio artifacts generated from packaged theses

## Current Repo Model

Use this mental model first:

1. **Event contracts** define what happened and whether it is trigger-, confirm-, context-, or research-only material.
2. **Bounded proposals** test a single regime/mechanism slice.
3. **Evidence bundles** decide whether a thesis is still only exploratory, seed-promotable, paper-promotable, or not promotable.
4. **Promoted theses** are the canonical live-consumable objects.
5. **Overlap graphs** and live retrieval consume packaged theses, not raw event rows.

## Pipeline

The end-to-end orchestrator is `project/pipelines/run_all.py`.

At a high level the run flow is defined in `project/pipelines/stages/`:

1. `ingest` & `core`
   - build cleaned bars
   - build features & market context
   - validate missing data & integrity
2. `runtime_invariants`
   - materializes replay stream
   - causal lane ticks & replay validation
3. `research`
   - phase1 event analysis & correlation
   - phase2 search engine / hypothesis generation
   - edge candidate export & naive entry evaluation
   - promote candidates & negative controls
   - memory update & registry management
   - expectancy trappedness checklist
4. `evaluation`
   - strategy blueprint compilation
   - strategy candidate packaging
   - profitable strategy selection

The source of truth for stage families and artifact contracts is `project/contracts/pipeline_registry.py`.

## Repo Layout

There are three different configuration layers:

- `spec/` — YAML domain specs: events, episodes, campaigns, promotion policies, ontology, grammar, proposals
- `project/configs/` — runnable workflow configs, live configs, synthetic suites, registry defaults, retail profiles
- `project/` — Python implementation

High-value code surfaces:

- `project/events/` — detectors, families, registries, ontology helpers
- `project/episodes/` — episode registry and episode contract loaders
- `project/research/` — proposal I/O, discovery, promotion, diagnostics, knowledge memory, thesis bootstrap, packaging
- `project/live/` — thesis retrieval, context building, decisioning, attribution, OMS integration
- `project/portfolio/` and `project/engine/` — overlap-aware risk allocation and budget controls
- `project/scripts/` — maintained artifact builders and bootstrap utilities
- `project/tests/` — architecture, smoke, contracts, regressions, replay, runtime, docs, domain, strategy, synthetic truth

## Operator surface

Treat the repo as four actions:

1. `discover`
2. `package`
3. `validate`
4. `review`

Preferred front door:

- `edge operator preflight --proposal <proposal.yaml>`
- `edge operator plan --proposal <proposal.yaml>`
- `edge operator run --proposal <proposal.yaml>`
- `edge operator diagnose --run_id <run_id>`
- `edge operator regime-report --run_id <run_id>`
- `edge operator compare --run_ids <baseline_run,followup_run>`

Use broad `make` targets and direct `run_all` entrypoints only when you already know the exact bounded slice or need workflow maintenance.

## Thesis Bootstrap Surface

When the thesis store is empty or sparse, use the thesis bootstrap scripts instead of trying to jump directly to live deployment:

```bash
python -m project.scripts.build_seed_bootstrap_artifacts
python -m project.scripts.build_seed_testing_artifacts
python -m project.scripts.build_seed_empirical_artifacts
python -m project.scripts.build_founding_thesis_evidence
python -m project.scripts.build_seed_packaging_artifacts
python -m project.scripts.build_structural_confirmation_artifacts
python -m project.scripts.build_thesis_overlap_artifacts
./project/scripts/regenerate_artifacts.sh
```

These surfaces produce the founding thesis queue, testing scorecards, empirical summaries, canonical thesis store, seed thesis cards, and overlap graph.

## Quality Model

A run or thesis is only trustworthy when:

- manifests reconcile
- artifacts exist and validate
- costs are accounted for
- promotion evidence is explicit
- drift checks stay within tolerance
- replay / determinism expectations remain intact
- thesis packaging lineage is visible
- promotion class and deployment state are not conflated

Exit status alone is not sufficient.

## Generated Artifacts

Do not treat hand-authored docs as live inventory.

Use `docs/generated/` for current generated surfaces, especially:

- `event_contract_completeness.{md,json}`
- `event_tiers.md`
- `promotion_seed_inventory.{md,csv}`
- `thesis_testing_scorecards.{csv,json}`
- `thesis_empirical_scorecards.{csv,json}`
- `seed_thesis_catalog.md`
- `seed_thesis_packaging_summary.{md,json}`
- `thesis_overlap_graph.{md,json}`
- `founding_thesis_evidence_summary.{md,json}`
- `structural_confirmation_summary.{md,json}`

## Canonical operator flow

- `edge operator preflight --proposal <proposal.yaml>`
- `edge operator plan --proposal <proposal.yaml>`
- `edge operator run --proposal <proposal.yaml>`
- `edge operator diagnose --run_id <run_id>`
- `edge operator regime-report --run_id <run_id>`
- `edge operator compare --run_ids <baseline_run,followup_run>`

Use the bootstrap scripts only when you are moving from tested claims into canonical thesis objects.

## Documentation

- [docs/README.md](docs/README.md) — full doc index
- [docs/00_START_HERE.md](docs/00_START_HERE.md) — shortest canonical repo entry
- [docs/03_OPERATOR_WORKFLOW.md](docs/03_OPERATOR_WORKFLOW.md) — canonical research loop + thesis bootstrap lane
- [docs/04_COMMANDS_AND_ENTRY_POINTS.md](docs/04_COMMANDS_AND_ENTRY_POINTS.md) — command reference
- [docs/06_QUALITY_GATES_AND_PROMOTION.md](docs/06_QUALITY_GATES_AND_PROMOTION.md) — gate policy + promotion classes
- [docs/09_THESIS_BOOTSTRAP_AND_PROMOTION.md](docs/09_THESIS_BOOTSTRAP_AND_PROMOTION.md) — founding thesis workflow
- [docs/11_LIVE_THESIS_STORE_AND_OVERLAP.md](docs/11_LIVE_THESIS_STORE_AND_OVERLAP.md) — packaged thesis store + overlap graph
- [docs/AGENT_CONTRACT.md](docs/AGENT_CONTRACT.md) — agent operating contract

## Fast synthetic demo

This repository includes a proposal-driven synthetic demo path that does not require a populated `data/lake/` checkout.

- Proposal spec: `spec/proposals/demo_synthetic_fast.yaml`
- Direct command: `python -m project.scripts.run_demo_synthetic_proposal --plan_only 1`
- Make target: `make synthetic-demo`

Synthetic proposals can now carry explicit pipeline overlays through `config_overlays`, plus `discovery_profile`, `phase2_gate_profile`, and `search_spec`, so synthetic routing is selected by configuration rather than by filename or description alone.
