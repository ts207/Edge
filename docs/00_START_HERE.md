# Start here

This repo is easiest to understand if you stop thinking in terms of scripts and start thinking in terms of **contracts**.

A bounded research cycle in Edge is:

`proposal -> preflight -> validated plan -> run -> run manifest -> candidate artifacts -> promotion artifacts -> diagnostics -> exported thesis batch`

A thesis packaging cycle is:

`seed inventory -> testing -> empirical evidence -> evidence bundle -> packaged thesis -> overlap graph -> live/runtime consumption`

That second lane is advanced maintenance work. A new operator should be able to use the repo without learning the bootstrap sequence first.

## What this repository is for

Edge exists to answer bounded market questions such as:

- under which event contracts does a pattern appear
- under which regimes does it survive
- whether it survives after costs, negative controls, and promotion gates
- whether the surviving claim is strong enough to package as a reusable thesis

The repo is not organized around ad hoc exploration. It is organized around explicit scope control and artifacted conclusions.

## First concepts to lock in

Before you run anything, understand these distinctions.

### Event versus episode

- **event**: a discrete trigger or condition firing at a timestamp
- **episode**: a higher-order sequence or stateful unfolding built from one or more events

### Candidate versus thesis

- **candidate**: a bounded statistical result produced by a run
- **thesis**: a packaged object with trigger, context, invalidation, governance, and evidence fields suitable for downstream consumption
- **thesis batch**: the runtime JSON file exported for one explicit run under `data/live/theses/<run_id>/promoted_theses.json`

### Promotion class versus deployment state

- **promotion class** answers how strong the evidence is
- **deployment state** answers where the thesis is allowed to be used right now

### Narrative docs versus generated docs

- narrative docs explain how the system works
- generated docs summarize current repo or artifact state

## Canonical actions

Treat the repo as four operator actions:

1. `discover`
2. `review`
3. `export`
4. `validate`

Treat `package` as an advanced bootstrap/governance lane rather than the default next step after every good run.

Use these aliases first:

```bash
make discover PROPOSAL=<proposal.yaml> DISCOVER_ACTION=preflight|plan|run
make export RUN_ID=<run_id>
make validate
make review RUN_ID=<run_id> REVIEW_ACTION=diagnose|regime-report
make review REVIEW_ACTION=compare RUN_IDS=<baseline_run,followup_run>
```

Everything else is either an implementation detail, an advanced surface, or maintenance machinery.

## First-day reading order

1. [01_PROJECT_MODEL.md](01_PROJECT_MODEL.md)
2. [02_REPOSITORY_MAP.md](02_REPOSITORY_MAP.md)
3. [03_OPERATOR_WORKFLOW.md](03_OPERATOR_WORKFLOW.md)
4. [04_COMMANDS_AND_ENTRY_POINTS.md](04_COMMANDS_AND_ENTRY_POINTS.md)
5. [05_ARTIFACTS_AND_INTERPRETATION.md](05_ARTIFACTS_AND_INTERPRETATION.md)
6. [06_QUALITY_GATES_AND_PROMOTION.md](06_QUALITY_GATES_AND_PROMOTION.md)
7. [09_THESIS_BOOTSTRAP_AND_PROMOTION.md](09_THESIS_BOOTSTRAP_AND_PROMOTION.md)
8. [11_LIVE_THESIS_STORE_AND_OVERLAP.md](11_LIVE_THESIS_STORE_AND_OVERLAP.md)

## First-day execution path

Start with one narrow proposal and do this exact sequence:

```bash
make discover PROPOSAL=<proposal.yaml> DISCOVER_ACTION=preflight
make discover PROPOSAL=<proposal.yaml> DISCOVER_ACTION=plan
make discover PROPOSAL=<proposal.yaml> DISCOVER_ACTION=run
make review RUN_ID=<run_id> REVIEW_ACTION=diagnose
make review RUN_ID=<run_id> REVIEW_ACTION=regime-report
```

If the run is meant to compare against a baseline slice, then also run:

```bash
make review REVIEW_ACTION=compare RUN_IDS=<baseline_run,followup_run>
```

If the work is ready for runtime consumption from one specific run, do this next:

```bash
make export RUN_ID=<run_id>
```

Only if you are intentionally maintaining legacy/bootstrap packaging artifacts should you move to the advanced packaging lane and run:

```bash
make package
```

## What to ignore initially

Do not begin with:

- raw ingest internals
- long `make` target inventories
- compatibility wrappers
- one-off builder scripts
- maintenance-only generated docs
- architecture migration references

Those matter later. They are not the learning path.

## Source-of-truth order

When sources disagree, use this precedence:

1. generated run artifacts and manifests
2. generated thesis artifacts
3. code and tests
4. authored specs
5. hand-written prose

That ordering matters because the repo contains generated inventories and a large amount of implementation detail. Older prose can drift.

## Definition of done for understanding a run

You understand a run only if you can answer all of these without guessing:

- what exact claim was tested
- what detectors, features, and states were required
- where the run manifest lives
- where phase-2 and promotion artifacts live
- why the result was kept, rejected, repaired, or promoted
- whether the failure was mechanical, statistical, regime-specific, or packaging-related
