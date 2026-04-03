# Edge

Edge is a governed crypto research repository with one canonical operating path:

`single hypothesis proposal -> validated plan -> bounded run -> review -> export thesis batch -> explicit runtime selection`

The repo is designed to answer one bounded question at a time, preserve the artifact trail for that question, and separate research evidence from runtime permission.

## What is canonical now

- proposals are authored as one atomic operator-facing hypothesis
- operator proposals normalize into legacy `AgentProposal` before downstream processing
- runtime-facing thesis batches come from one explicit run export
- runtime selection is explicit through `strategy_runtime.thesis_path` or `strategy_runtime.thesis_run_id`
- `deployment_state` answers whether a thesis may monitor, paper trade, or trade live

## What the repository actually does

The codebase has four primary operator-facing actions:

1. `discover` — validate and run one bounded research slice
2. `review` — inspect one run or compare a bounded follow-up against a baseline
3. `export` — write one explicit runtime thesis batch from one run
4. `validate` — run contract, architecture, and repo-health checks

There is also one advanced maintenance lane:

- `package` — internal/bootstrap packaging and governance maintenance, not the canonical way to get a runtime batch from a run

## Preferred front door

Use these surfaces first:

```bash
make discover PROPOSAL=<proposal.yaml> DISCOVER_ACTION=preflight|plan|run
make review RUN_ID=<run_id> REVIEW_ACTION=diagnose|regime-report
make review REVIEW_ACTION=compare RUN_IDS=<baseline_run,followup_run>
make export RUN_ID=<run_id>
make validate
```

Direct CLI equivalents:

```bash
edge operator preflight --proposal <proposal.yaml>
edge operator explain --proposal <proposal.yaml>
edge operator plan --proposal <proposal.yaml>
edge operator run --proposal <proposal.yaml>
edge operator diagnose --run_id <run_id>
edge operator regime-report --run_id <run_id>
edge operator compare --run_ids <run_a,run_b>
```

## Fastest correct mental model

Read the repo in this order:

1. a proposal defines one bounded claim
2. the operator layer normalizes that proposal into `AgentProposal`
3. the proposal is translated into `experiment.yaml` plus `run_all` overrides
4. `run_all` produces run manifests, phase-2 reports, and promotion outputs
5. review determines repair, confirm, kill, or export
6. export writes a run-derived thesis batch under `data/live/theses/<run_id>/`
7. runtime consumes that batch only when selected explicitly, and trading is allowed only for `deployment_state=live_enabled`

## The one operator story

The intended user path is:

1. author one proposal like [`canonical_event_hypothesis_h24.yaml`](/home/irene/Edge/spec/proposals/canonical_event_hypothesis_h24.yaml)
2. inspect the normalized proposal with `edge operator explain`
3. preflight and plan the run
4. execute the run
5. review manifest, candidates, diagnostics, and promotion outputs
6. export the run if it deserves runtime-readable thesis objects
7. point runtime at that exported batch explicitly

That path is the teaching surface. Everything else is lower-level implementation or advanced maintenance.

## Repository shape

High-value top-level areas:

- `project/` — Python implementation
- `spec/` — authored domain and policy specs
- `docs/` — narrative docs, architecture references, generated inventories
- `data/` — local artifacts, reports, thesis batches, runtime state
- `deploy/` — live-engine deployment examples
- `agents/` and `plugins/` — specialist workflows and local tooling

Largest implementation surfaces:

- `project/research/` — proposal IO, search, promotion, reporting, export
- `project/pipelines/` — orchestration and stage planning
- `project/live/` — thesis retrieval, policy, decisioning, OMS, attribution
- `project/portfolio/` — overlap and risk-budget logic
- `project/tests/` — contracts, smoke, runtime, research, docs, architecture

## Documentation map

Start here:

1. [docs/00_START_HERE.md](docs/00_START_HERE.md)
2. [docs/01_PROJECT_MODEL.md](docs/01_PROJECT_MODEL.md)
3. [docs/02_REPOSITORY_MAP.md](docs/02_REPOSITORY_MAP.md)
4. [docs/03_OPERATOR_WORKFLOW.md](docs/03_OPERATOR_WORKFLOW.md)
5. [docs/04_COMMANDS_AND_ENTRY_POINTS.md](docs/04_COMMANDS_AND_ENTRY_POINTS.md)
6. [docs/05_ARTIFACTS_AND_INTERPRETATION.md](docs/05_ARTIFACTS_AND_INTERPRETATION.md)
7. [docs/06_QUALITY_GATES_AND_PROMOTION.md](docs/06_QUALITY_GATES_AND_PROMOTION.md)
8. [docs/09_THESIS_BOOTSTRAP_AND_PROMOTION.md](docs/09_THESIS_BOOTSTRAP_AND_PROMOTION.md)
9. [docs/11_LIVE_THESIS_STORE_AND_OVERLAP.md](docs/11_LIVE_THESIS_STORE_AND_OVERLAP.md)

Use [docs/README.md](docs/README.md) for the full map.

## Compatibility versus canonical use

Canonical:

- single-hypothesis proposal front door
- operator normalization to `AgentProposal`
- run-derived thesis export
- explicit runtime thesis selection
- `deployment_state` as the runtime permission field

Compatibility or advanced-only:

- legacy proposal shapes
- internal promotion vocabulary as the primary teaching surface
- bootstrap/package scripts as the default runtime-batch path
- implicit latest thesis resolution

## Ground rules

- learn the operator path before raw pipeline scripts
- inspect the run manifest before markdown summaries
- answer “can this trade?” from `deployment_state`, not promotion class
- treat `data/live/theses/index.json` as a catalog, not a runtime default selector
- use generated docs as inventory, not as proof by themselves
