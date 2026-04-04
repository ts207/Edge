# Start here

The repo becomes simple if you lock in three ideas early:

1. the normal operating unit is one bounded hypothesis
2. downstream code still runs on normalized `AgentProposal`
3. runtime consumes one explicit thesis batch from one explicit run

Everything else is detail.

## The shortest correct story

The normal path is:

`proposal -> preflight -> explain/plan -> run -> review -> export thesis batch -> explicit runtime selection`

The bootstrap/package lane exists, but it is advanced maintenance work. A new operator should not need it to understand or use the repo.

## What to memorize first

- the canonical example is [`spec/proposals/canonical_event_hypothesis.yaml`](/home/irene/Edge/spec/proposals/canonical_event_hypothesis.yaml)
- operator proposals are authored as one atomic hypothesis, then normalized into `AgentProposal`
- `make export RUN_ID=<run_id>` is the canonical bridge from a run to a runtime thesis batch
- `deployment_state` answers whether something may monitor, paper trade, or trade live

## Treat the repo as four operator actions

1. `discover`
2. `review`
3. `export`
4. `validate`

`package` is real, but it is an advanced bootstrap/governance lane rather than the default answer to “what do I do after a good run?”

## First-day commands

Use these first:

```bash
make discover PROPOSAL=<proposal.yaml> DISCOVER_ACTION=preflight
make discover PROPOSAL=<proposal.yaml> DISCOVER_ACTION=plan
make discover PROPOSAL=<proposal.yaml> DISCOVER_ACTION=run
make review RUN_ID=<run_id> REVIEW_ACTION=diagnose
make review RUN_ID=<run_id> REVIEW_ACTION=regime-report
make export RUN_ID=<run_id>
make validate
```

If the run is a bounded follow-up against a baseline, also use:

```bash
make review REVIEW_ACTION=compare RUN_IDS=<baseline_run,followup_run>
```

## First-day reading order

1. [01_PROJECT_MODEL.md](01_PROJECT_MODEL.md)
2. [02_REPOSITORY_MAP.md](02_REPOSITORY_MAP.md)
3. [03_OPERATOR_WORKFLOW.md](03_OPERATOR_WORKFLOW.md)
4. [04_COMMANDS_AND_ENTRY_POINTS.md](04_COMMANDS_AND_ENTRY_POINTS.md)
5. [05_ARTIFACTS_AND_INTERPRETATION.md](05_ARTIFACTS_AND_INTERPRETATION.md)
6. [06_QUALITY_GATES_AND_PROMOTION.md](06_QUALITY_GATES_AND_PROMOTION.md)
7. [11_LIVE_THESIS_STORE_AND_OVERLAP.md](11_LIVE_THESIS_STORE_AND_OVERLAP.md)
8. [09_THESIS_BOOTSTRAP_AND_PROMOTION.md](09_THESIS_BOOTSTRAP_AND_PROMOTION.md) only if you need the advanced packaging lane

## First-day execution path

Start from the canonical example or a similar one-hypothesis proposal.

1. run `edge operator explain --proposal <proposal.yaml>` to inspect the normalized proposal and resolved experiment summary
2. run preflight to catch schema, data, and writable-root problems
3. run plan to inspect the exact experiment bundle
4. run the proposal to create a durable artifacted run
5. inspect manifest, phase-2 outputs, and promotion outputs
6. export only if the run deserves a runtime-readable batch

## What not to learn first

Ignore these until the operator path is clear:

- raw pipeline stage internals
- legacy proposal authoring shape
- bootstrap builder scripts
- generated inventories as if they were primary teaching docs
- compatibility helpers that exist only to preserve old paths

## Source-of-truth order

When sources disagree, use this order:

1. run-scoped artifacts and manifests
2. exported thesis-batch artifacts
3. code and tests
4. authored specs
5. prose

That order prevents stale prose and stale generated docs from driving decisions.
