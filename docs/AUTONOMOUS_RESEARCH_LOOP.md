# Autonomous Research Loop

## Purpose

The agent exists to turn market observations into constrained experiments, learn from the results, and improve the next experimental batch without drifting outside the repository's safety and contract boundaries.

The system is not a chat bot with occasional analysis. It is an iterative research worker with memory, explicit hypotheses, bounded experimentation, artifact-driven evaluation, and reflective adaptation.

## Operating Cycle

The canonical loop is:

1. Observe current state.
2. Retrieve relevant prior memory.
3. Form a research objective.
4. Generate or refine hypotheses.
5. Select the smallest useful experiment set.
6. Execute the run.
7. Evaluate outputs against statistical, operational, and governance gates.
8. Write reflective memory.
9. Decide whether to exploit, explore, repair, or stop.

Each loop must produce durable artifacts. If the loop does not leave behind a decision trace, it did not happen.

## Agent Responsibilities

- Maintain awareness of current repository contracts.
- Use existing pipeline stages and registries instead of inventing side channels.
- Prefer narrow, attributable runs over broad, ambiguous runs.
- Treat failed runs as learning signals, not noise.
- Convert repeated failure modes into explicit constraints or repair tasks.
- Preserve comparability across runs by recording configuration, intent, and outcome.

## Loop Phases

### 1. Observe

Collect:

- latest run manifests
- stage manifests
- discovery and promotion summaries
- audit outputs
- feature integrity reports
- relevant prior experiment memories

The observation phase should answer:

- What was tried?
- What failed?
- What looked promising?
- What was inconclusive?
- What broke mechanically vs statistically?

### 2. Retrieve Memory

Before proposing a new run, retrieve prior observations for:

- same symbol
- same event or trigger family
- same template
- same context or regime
- same failure class

The agent should bias toward memory-backed iteration instead of repeating already-rejected regions.

### 3. Form Objective

An objective must be explicit and testable.

Good:

- test whether basis dislocation continuation under low liquidity survives costs
- verify whether prior promotion failure was due to missing split counts or weak economics
- isolate one regime-conditioned trigger with enough validation and test coverage

Bad:

- find alpha
- run some experiments
- explore more things

### 4. Generate Hypotheses

Hypotheses must be represented in repository-native terms:

- trigger
- direction
- horizon
- template
- context
- entry lag

The agent should favor hypotheses that are:

- explainable from artifacts
- searchable by registry/spec
- easy to compare against prior runs
- narrow enough to falsify

### 5. Select Experiment Batch

Batch selection must balance:

- exploitation of strongest prior signal
- exploration of adjacent but meaningfully distinct regions
- mechanical verification when the system changed

Default batch composition:

- 1 exploit experiment
- 1 adjacent exploration experiment
- 1 repair or verification experiment if infrastructure changed

Do not mix too many objectives in one batch.

### 6. Execute

Use repository entrypoints that preserve stage contracts and artifacts.

Preferred execution order:

- targeted stage replay for repair verification
- narrow search-engine slice for hypothesis isolation
- full pipeline run only when the path is mechanically stable

### 7. Evaluate

Every run must be evaluated on three axes:

- statistical quality
- execution quality
- contract integrity

Statistical quality includes:

- sample counts by split
- multiplicity-adjusted significance
- after-cost expectancy
- stress survival
- robustness/regime stability

Execution quality includes:

- stage completion
- absence of stale manifests
- absence of missing artifact contracts
- acceptable warning surface

Contract integrity includes:

- input/output presence
- field propagation
- consistency between stage and top-level manifests

### 8. Reflect

Reflection is mandatory after material runs, fixes, or surprising failures.

Reflection should answer:

- What belief was tested?
- What changed in belief strength?
- What was learned about the market?
- What was learned about the system?
- What should be tried next?
- What should no longer be tried?

### 9. Adapt

The agent must explicitly choose one outcome:

- exploit
- explore
- repair
- hold
- stop

That choice should be justified from memory and current evidence, not intuition alone.

## Reinforcement Policy

The agent reinforces actions that consistently lead to:

- reproducible positive post-cost results
- robust validation/test support
- low orchestration friction
- clear explanatory structure

The agent penalizes actions that repeatedly lead to:

- contract breakage
- stale bookkeeping
- duplicated search regions
- statistically weak but operationally expensive runs
- high warning noise with low informational value

## Escalation Rules

Escalate from narrow to broad only when:

- the narrow path produced coherent outputs
- the target has enough support to justify a larger run
- the system path is mechanically stable

De-escalate to repair mode when:

- manifests and logs disagree
- promotion consumes malformed candidate contracts
- split labeling or counts are suspect
- warning floods obscure true failures

## Definition Of Done For A Loop

A loop is complete only when all of the following exist:

- a run or replay artifact set
- a concrete evaluation
- a written reflection
- a next action choice
- an updated memory record


## Synthetic Research Branch

When the active dataset is synthetic, the loop changes slightly:

1. freeze the generator profile and suite before inspecting results
2. preserve the truth map and generation manifest with the run
3. validate detector truth before interpreting discovery misses
4. compare findings across at least one additional synthetic profile before strengthening belief
5. separate detector recovery success from strategy profitability claims

Agent-driven synthetic research should optimize for mechanism recovery, falsification, and promotion robustness, not just headline synthetic PnL.
