# Edge

Edge is a research-to-runtime system for event-anchored crypto alpha work.

The canonical operating model is:

`discover → validate → promote → deploy`

That four-stage story is the public front door, but the repository now includes a broader control plane around it:

- a canonical stage CLI in `project/cli.py`
- a planner-owned orchestration layer in `project/pipelines/run_all.py` for legacy bundle flows
- a compatibility `operator` surface for older bounded-research workflows
- an explicit thesis export step that writes runtime inventory under `data/live/theses/`
- a gated live runtime with thesis-state validation, approval metadata, kill switches, and reconciliation
- an MCP / ChatGPT app interface in `project/apps/chatgpt/` that fronts canonical repo surfaces instead of redefining policy
- a repo hygiene gate that keeps `tmp/`, `live/persist/`, `logs/`, and top-level scratch files local-only

## System Model

### Discover
Discovery turns a bounded proposal YAML into a candidate table. A proposal freezes the research claim, anchor, context, and search scope before execution.

- Input: proposal / Structured Hypothesis
- Main output: discovery artifacts under `data/reports/phase2/<run_id>/`
- Key object: Candidate

### Validate
Validation is the falsification stage. It takes discovery outputs and writes the canonical bundle that downstream promotion reads.

- Input: discovery run ID
- Main output: `data/reports/validation/<run_id>/validation_bundle.json`
- Key object: Validated Candidate

### Promote
Promotion decides which validated candidates are worth inventorying. It applies governance, retail-profile, and readiness logic and assigns a deployment state.

- Input: validation bundle
- Main output: promotion artifacts under `data/reports/promotions/<run_id>/`
- Key object: Promoted Thesis

### Deploy
Deployment consumes exported thesis batches. Paper and live execution are explicit runtime operations, not side effects of promotion.

- Input: `data/live/theses/<run_id>/promoted_theses.json`
- Main output: runtime sessions, audit logs, and trade/execution state
- Key object: live thesis batch

## Core Concepts

- Anchor: the event or transition that defines the hypothesis entry condition.
- Filter: contextual predicates that narrow where the Anchor is valid.
- Sampling Policy: the rules that decide how episodes are sampled from an event.
- Candidate: a concrete hypothesis instance that survives discovery ranking.
- Validated Candidate: a Candidate that survives validation gates and bundle construction.
- Thesis: the packaged runtime-facing object produced by promotion and export.

Edge is event-first. The repo is not organized around free-form strategy authoring as the default. It is organized around Anchors, Filters, evidence bundles, artifact lineage, and a thesis store.

## Canonical Commands

Use the stage verbs first:

```bash
make discover PROPOSAL=spec/proposals/<proposal>.yaml DISCOVER_ACTION=plan
make discover PROPOSAL=spec/proposals/<proposal>.yaml DISCOVER_ACTION=run
make validate RUN_ID=<run_id>
make promote RUN_ID=<run_id> SYMBOLS=BTCUSDT,ETHUSDT
make export RUN_ID=<run_id>
make deploy-paper RUN_ID=<run_id>
make check-hygiene
```

Direct CLI equivalents:

```bash
python -m project.cli discover plan --proposal spec/proposals/<proposal>.yaml
python -m project.cli discover run --proposal spec/proposals/<proposal>.yaml
python -m project.cli validate run --run_id <run_id>
python -m project.cli promote run --run_id <run_id> --symbols BTCUSDT,ETHUSDT
python -m project.cli promote export --run_id <run_id>
python -m project.cli deploy paper --run_id <run_id> --config project/configs/live_paper.yaml
```

## What Changed

The current repo update that older docs did not explain clearly is:

- `discover`, `validate`, `promote`, and `deploy` are the canonical lifecycle verbs
- `operator` still exists, but it is a deprecated compatibility façade
- `pipeline run-all` still exists, but it is not the preferred public surface
- `promote export` is the bridge into runtime inventory and writes `data/live/theses/<run_id>/`
- thesis lifecycle and runtime permissioning are now explicit through `deployment_state`, approval metadata, and `DeploymentGate`
- advanced trigger discovery exists under `discover triggers ...`, but it is proposal-generating research, not a shortcut into live inventory
- the ChatGPT app and plugin layers are interface shells over canonical repo behavior, not separate engines
- `project/tests/` is the only supported pytest root; `tmp/` and `live/persist/` are local scratch, not tracked repo surfaces

## Artifact Flow

The most important lineage is:

1. Proposal YAML in `spec/proposals/`
2. Discovery artifacts in `data/reports/phase2/<run_id>/`
3. Validation bundle in `data/reports/validation/<run_id>/`
4. Promotion artifacts in `data/reports/promotions/<run_id>/`
5. Exported thesis batch in `data/live/theses/<run_id>/promoted_theses.json`
6. Runtime consumption by `project/live/`

This boundary matters operationally:

- `promote run` does not start trading
- `promote export` does not bypass deployment gates
- `deploy live` is blocked unless the exported batch contains `live_enabled` theses

## Repository Surfaces

- `project/cli.py`: canonical stage CLI plus compatibility commands
- `project/pipelines/`: planner-owned orchestration, manifests, stage graph, smoke flows
- `project/research/`: discovery, validation, promotion, reporting, trigger discovery, campaign tools
- `project/live/`: thesis contracts, deployment gate, live runner, reconciliation, kill switch, scoring
- `project/tests/`: single repo test tree for pytest discovery
- `project/events/` and `spec/events/`: authored event definitions and compiled registry surfaces
- `project/apps/chatgpt/`: app / MCP scaffold around canonical operator workflows
- `plugins/edge-agents/`: repo-local plugin scripts for maintenance, validation, hygiene, and operator ergonomics

## Documentation

Start with:

- [docs/README.md](docs/README.md)
- [docs/00_overview.md](docs/00_overview.md)
- [docs/01_discover.md](docs/01_discover.md)
- [docs/02_validate.md](docs/02_validate.md)
- [docs/03_promote.md](docs/03_promote.md)
- [docs/04_deploy.md](docs/04_deploy.md)

Then use:

- [docs/02_REPOSITORY_MAP.md](docs/02_REPOSITORY_MAP.md)
- [docs/05_data_foundation.md](docs/05_data_foundation.md)
- [docs/06_core_concepts.md](docs/06_core_concepts.md)
- [docs/operator_command_inventory.md](docs/operator_command_inventory.md)
- [docs/90_architecture.md](docs/90_architecture.md)

## Compatibility Note

Legacy commands remain available for migration support:

- `edge operator ...`
- `edge pipeline run-all`

They are wrappers around the current model. New documentation and maintenance work should teach the stage verbs and the export/runtime boundary first.
