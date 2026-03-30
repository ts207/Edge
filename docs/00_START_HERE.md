# Start Here

Edge is a research platform for event-driven alpha discovery in crypto markets. The repository is designed to test explicit claims under artifact, cost, and promotion discipline.

The shortest correct mental model is:

`proposal -> validated config -> planned run -> artifacted execution -> statistical filtering -> promotion gates -> candidate or rejection`

This is not a notebook sandbox. A run is good when it leaves:

- a bounded question
- a reproducible configuration
- a clean artifact trail
- a mechanical conclusion
- a statistical conclusion
- a deployment conclusion
- one next action

## What You Should Learn First

Before you run anything, understand:

1. the difference between `event`, `family`, `template`, `state`, and `regime`
2. how the pipeline is staged and where artifacts land
3. how proposal-driven research differs from direct CLI execution
4. how phase-2 filtering differs from bridge/promotion filtering

Read in this order:

1. [01_PROJECT_MODEL.md](01_PROJECT_MODEL.md)
2. [02_REPOSITORY_MAP.md](02_REPOSITORY_MAP.md)
3. [03_OPERATOR_WORKFLOW.md](03_OPERATOR_WORKFLOW.md)
4. [05_ARTIFACTS_AND_INTERPRETATION.md](05_ARTIFACTS_AND_INTERPRETATION.md)

## Source Of Truth Rule

Use this precedence when sources disagree:

1. run artifacts
2. code
3. specs
4. hand-authored prose

That rule matters because a successful process exit does not prove a good run, and older prose can lag implementation.

## First Day Tasks

If you are new, do these in order:

1. read one completed run end to end from manifest to funnel summary
2. run a proposal in `plan_only` mode
3. execute one narrow confirmatory slice

If you cannot explain what was tested, where hypotheses died, and whether the failure was mechanical, statistical, or deployment-related, you are not done reading.

