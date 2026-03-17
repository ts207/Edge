# Memory And Reflection

## Purpose

Memory prevents the agent from repeating bad experiments, forgetting fragile system facts, or overstating weak evidence.

Reflection converts run outcomes into reusable knowledge.

## Memory Classes

### Structural Memory

Facts about how the repository behaves.

Examples:

- export requires normalized edge candidate artifacts
- explicit contexts should not generate unconditional duplicates
- top-level manifests may need reconciliation after manual tail replay

### Experimental Memory

Facts about what was tested and what happened.

Examples:

- low-liquidity basis continuation on BTC 15m survived cost in the Jan 2026 slice
- search-engine candidates were once orphaned from promotion

### Negative Memory

Facts about what should be avoided.

Examples:

- broad noisy runs with stale manifests create low-trust outputs
- a region consistently fails retail net expectancy despite good raw q-values

### Action Memory

Facts about what to do next.

Examples:

- rerun narrow slice after generator contract change
- escalate only after validation/test counts survive export

## Reflection Questions

After each meaningful loop, answer:

1. What prior belief did this test?
2. What evidence increased or decreased that belief?
3. Was the outcome market-driven or system-driven?
4. What should be remembered as a reusable rule?
5. What exact next experiment is justified?

## Memory Write Rules

- Store concrete facts, not vague impressions.
- Include run ids, scopes, and failure classes.
- Separate system issues from research conclusions.
- Record both positive and negative results.
- Prefer short, high-signal observations over narrative dumps.

## Retrieval Heuristics

Before any new experiment, retrieve memory for:

- same trigger or event family
- same template
- same symbol and timeframe
- same context
- same primary fail gate

If prior memory shows repeated failure with no material new condition, avoid rerunning.

## Reinforcement Heuristics

Increase priority for experiments that:

- address a previously unresolved ambiguity
- build on positive, cost-surviving evidence
- reduce uncertainty with a small run
- validate a recent code-path fix

Decrease priority for experiments that:

- duplicate prior unsuccessful slices
- broaden scope without adding information
- depend on known-broken contracts
- produce noisy logs without decision value

## Reflection Output Schema

Each reflection should minimally capture:

- `objective`
- `run_scope`
- `mechanical_status`
- `statistical_status`
- `primary_findings`
- `primary_failures`
- `belief_update`
- `next_action`

## Memory Hygiene

Prune or downgrade memories that are:

- invalidated by code changes
- contradicted by cleaner re-runs
- too vague to guide future selection

Do not delete history silently. Mark it as superseded when possible.


## Synthetic Memory

Synthetic runs should additionally store:

- generator profile
- noise scale
- truth-map path
- whether the finding survived another profile or only one world

A synthetic result that fails to survive a profile change should be stored as a simulator-specific finding, not a general market belief.
