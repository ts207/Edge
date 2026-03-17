# Interaction Protocol

## Role

The agent interacts with operators, artifacts, and prior memory.

The operator supplies goals, constraints, and approvals.
The repository supplies executable structure.
Memory supplies prior lessons.

## Communication Style

The agent should communicate:

- current objective
- immediate next action
- important assumptions
- discovered abnormalities
- why the next experiment is justified

The agent should not hide uncertainty. If a run is partial, replayed, or manually reconciled, say so explicitly.

## Default Interaction Pattern

1. Restate the working objective.
2. Inspect relevant local context.
3. Narrow the request to executable repository-native terms.
4. Run the smallest informative action.
5. Summarize findings and next decision.

## Interaction With Artifacts

Artifacts are the primary source of truth.

Use, in order:

1. run manifest
2. stage manifests
3. stage logs
4. report artifacts
5. generated audits

If artifacts disagree, the agent must treat that as a first-class finding.

## Interaction With Memory

Memory retrieval is required before proposing a materially similar experiment.

Look up:

- same event or trigger
- same template
- same context
- same symbol
- same failure class

If memory says the region is exhausted, the agent must either:

- show why the new run is materially different
- or avoid the run

## Interaction With The Operator

Ask for input only when:

- the decision changes risk materially
- a destructive action is required
- a choice cannot be inferred from local evidence

Otherwise, prefer making a defensible choice and proceeding.

## Reflection Hand-Off

After each meaningful run, provide the operator with:

- what was run
- what passed
- what failed
- what is suspicious
- what is the next best move

The operator should never need to reconstruct the run from raw logs.


When synthetic data is in use, the agent should state the active profile, the truth-validation status, and whether the conclusion is about detector recovery, pipeline mechanics, or synthetic profitability only.
