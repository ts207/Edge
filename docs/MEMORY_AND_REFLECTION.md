# Memory And Reflection

Memory stops the system from repeating avoidable work.

Reflection turns one run into reusable decision support for the next run.

## Purpose

Use memory to:

- avoid rerunning failed regions under new wording
- retain fragile system facts
- distinguish market conclusions from system conclusions
- prioritize the next best experiment

## Memory Classes

### Structural Memory

Facts about how the repository behaves.

Examples:

- a stage contract requires normalized candidates
- a quality report is emitted at a specific path
- a promotion fallback uses the same normalized contract as the canonical path

### Experimental Memory

Facts about what was tested and what happened.

Examples:

- one family-template-context region survived costs in one period
- a narrow slice failed in validation despite attractive train metrics

### Negative Memory

Facts about what should be avoided.

Examples:

- a broad noisy run pattern repeatedly produces low-trust output
- a region repeatedly fails retail net expectancy after costs

### Action Memory

Facts about what the next justified move should be.

Examples:

- rerun a narrow slice after a generator change
- stop re-testing a family-template region until live data coverage improves

## Reflection Questions

After each meaningful run, answer:

1. what prior belief did this test
2. what evidence increased or decreased that belief
3. was the result market-driven or system-driven
4. what reusable rule should be remembered
5. what exact next action is justified

## Write Rules

- store facts, not impressions
- include run ids and scope
- separate system issues from market conclusions
- record both positive and negative findings
- prefer short, high-signal entries over narrative dumps
- reference exact artifact families when that fact will matter later

## Retrieval Rules

Before any new experiment, retrieve memory for:

- the same event or family
- the same template
- the same symbol or timeframe
- the same context
- the same fail gate

If prior memory shows repeated clean failure with no material new condition, do not rerun by default.

## Reinforcement Rules

Increase priority for experiments that:

- resolve a known ambiguity
- build on positive post-cost evidence
- reduce uncertainty with a small run
- validate a recent code or contract fix

Decrease priority for experiments that:

- duplicate prior unsuccessful slices
- broaden scope without adding information
- depend on known-broken contracts
- create warning-heavy output without changing the decision

## Reflection Schema

Each reflection should minimally include:

- `objective`
- `run_scope`
- `mechanical_status`
- `statistical_status`
- `primary_findings`
- `primary_failures`
- `belief_update`
- `next_action`

## Memory Hygiene

Supersede or downgrade memories that are:

- invalidated by code changes
- contradicted by cleaner reruns
- too vague to guide future selection

Do not silently erase history when a superseded record is more informative than no record.

## Synthetic Memory

Synthetic runs should also store:

- generator profile
- noise scale
- truth-map path
- whether the result survived another profile or only one synthetic world

If a synthetic result does not survive a profile change, record it as simulator-specific, not as a general market belief.
