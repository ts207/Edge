# Start Here

Edge is a governed event-driven crypto research platform. The repository is designed to test explicit claims under artifact, cost, and promotion discipline, then package only the claims that survive into canonical thesis objects.

The shortest correct mental model is:

`proposal -> validated config -> planned run -> artifacted execution -> statistical filtering -> promotion gates -> thesis class decision -> thesis store or rejection`

This is not a notebook sandbox. A run or thesis is good when it leaves:

- a bounded question
- a reproducible configuration
- a clean artifact trail
- a mechanical conclusion
- a statistical conclusion
- a promotion-class conclusion
- one next action

## What you should learn first

Before you run anything, understand:

1. the difference between `event`, `episode`, `family`, `template`, `state`, `regime`, and `thesis`
2. how the bounded experiment lane differs from the thesis bootstrap lane
3. how generated thesis artifacts differ from raw run artifacts
4. how `seed_promoted`, `paper_promoted`, and `production_promoted` differ

Read in this order:

1. [01_PROJECT_MODEL.md](01_PROJECT_MODEL.md)
2. [02_REPOSITORY_MAP.md](02_REPOSITORY_MAP.md)
3. [03_OPERATOR_WORKFLOW.md](03_OPERATOR_WORKFLOW.md)
4. [05_ARTIFACTS_AND_INTERPRETATION.md](05_ARTIFACTS_AND_INTERPRETATION.md)
5. [09_THESIS_BOOTSTRAP_AND_PROMOTION.md](09_THESIS_BOOTSTRAP_AND_PROMOTION.md)
6. [11_LIVE_THESIS_STORE_AND_OVERLAP.md](11_LIVE_THESIS_STORE_AND_OVERLAP.md)

## Source of truth rule

Use this precedence when sources disagree:

1. run artifacts and generated thesis artifacts
2. code
3. specs
4. hand-authored prose

That rule matters because a successful process exit does not prove a good run, and older prose can lag implementation.

## Canonical actions

Treat the repo as four operator actions:

1. `discover` — bounded proposal issuance and run execution
2. `package` — thesis bootstrap, empirical evidence, packaging, overlap
3. `validate` — contract, smoke, governance, and replay checks
4. `review` — diagnose, compare, and regime-report after a run

Everything else is support machinery.

## First day tasks

If you are new, do these in order:

1. read one completed run end to end from manifest to funnel summary
2. inspect the generated seed inventory under `docs/generated/promotion_seed_inventory.md`
3. inspect the current packaged thesis catalog under `docs/generated/seed_thesis_catalog.md` if present
4. run a proposal in `plan_only` mode
5. execute one narrow confirmatory slice

If you cannot explain what was tested, where hypotheses died, what thesis class the result supports, and whether the failure was mechanical, statistical, or packaging-related, you are not done reading.

## Canonical first run

Use exactly this order for operator work:

1. `edge operator preflight --proposal <proposal.yaml>`
2. `edge operator plan --proposal <proposal.yaml>`
3. `edge operator run --proposal <proposal.yaml>`

Do not start with `run_all` unless you already know the exact bounded slice and are intentionally bypassing the proposal surface.

## Review after a run

Use these commands after a bounded run when you need a structured follow-up surface:

1. `edge operator diagnose --run_id <run_id>`
2. `edge operator regime-report --run_id <run_id>`
3. `edge operator compare --run_ids <baseline_run,followup_run>`

## When to switch to thesis bootstrap

Use the bootstrap lane when:

- you already have a bounded claim worth queueing
- the thesis store is empty or sparse
- you need testing, empirical scoring, or packaging artifacts rather than another discovery run
- you are trying to populate `data/live/theses/` or regenerate `docs/generated/thesis_overlap_graph.*`

## What to ignore at first

Do not start from:

- raw loader internals
- sidecar registries and compatibility aliases
- long `make` target inventories
- migration notes
- low-level pipeline wrappers unless you already know why you need them
