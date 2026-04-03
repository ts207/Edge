# Standing Bounded Experiment Template

This document is the control template for bounded research work.

Use it to stay in the narrow research loop unless a change is truly structural.

---

## 1. Lane Selection

Use exactly one lane per run.

### Lane A: Change-Management Lane

Use this lane only when at least one of these changed materially:

- architecture boundaries
- artifact or schema contracts
- registry or routing semantics
- storage path semantics
- identity models or lineage rules

Required sequence:

1. target-state refresh
2. audit
3. plan
4. implementation
5. bounded experiment

Default verification floor:

- `make minimum-green-gate`
- targeted tests for the changed surface
- one bounded artifact reconciliation run

Stop condition:

- stop after the bounded experiment and leave a next action of `explore`, `repair`, `hold`, or `stop`

### Lane B: Research / Edge Lane

Use this lane for normal progress after the baseline is stable.

Required sequence:

1. bounded hypothesis proposal
2. experiment execution
3. result analysis
4. local fixes if obvious
5. promotion or rejection decision

Default verification floor:

- `make test-fast`
- targeted tests for any local fix touched by the experiment
- regime/routing or artifact validation only for the changed local surface

Stop condition:

- stop once the hypothesis is classified as `proposed`, `active`, `rejected`, or `archived`

Decision rule:

- if the defect changes how the system means something, routes something, names something, stores something, or joins something, use Lane A
- if the defect only changes one hypothesis loop, one local report inconsistency, one local schema mismatch, or one obvious bounded replay bug, stay in Lane B

---

## 2. Standing Research Loop

The default operating loop is one bounded regime-specific edge program at a time.

Recommended starting regimes:

- `LIQUIDITY_STRESS`
- `BASIS_FUNDING_DISLOCATION`
- `CROSS_ASSET_DESYNC`

Default program shape:

1. pick one regime
2. define one mechanism
3. define one trade expression
4. run one bounded campaign
5. inspect manifests, logs, and reports
6. patch only obvious local defects
7. decide `keep`, `modify`, or `kill`

Do not broaden the run by adding unrelated triggers, templates, or symbols to rescue a weak idea.

---

## 3. Required Run Artifacts

Every Lane B run should leave behind three operator-facing artifacts plus the normal pipeline outputs.

### A. `hypothesis.md`

Write this before execution. Use the template in `docs/templates/hypothesis_template.md`.

Required fields:

- hypothesis ID
- mechanism
- forced actor
- constraint
- distortion
- unwind path
- trigger regime
- trade expression
- entry logic
- exit logic
- invalidation
- cost assumptions
- expected horizon
- bounded symbol, timeframe, and date window

### B. Proposal YAML

Translate the hypothesis into one compact proposal.

Skeleton:

```yaml
program_id: bounded_edge_program
description: One bounded mechanism test.
run_mode: research
objective_name: retail_profitability
promotion_profile: research
symbols:
  - BTCUSDT
timeframe: 5m
start: "2022-11-01"
end: "2022-12-31"
hypothesis:
  trigger:
    type: event
    event_id: BASIS_DISLOC
  template: mean_reversion
  direction: short
  horizon_bars: 12
  entry_lag_bars: 1
search_control:
  max_hypotheses_total: 1
  max_hypotheses_per_template: 1
artifacts:
  write_candidate_table: true
  write_hypothesis_log: true
  write_reports: true
```

This operator-facing format is the only proposal shape that should be authored directly. The loader compiles it into the internal legacy `trigger_space` form.

### C. `experiment_review.md`

Write this after execution. Use the template in `docs/templates/experiment_review_template.md`.

Required fields:

- whether the mechanism matched the observed data
- net-of-cost outcome
- main failure modes
- data-quality issues
- regime/routing quality
- whether to keep, modify, or kill the idea

### D. Edge Registry Row

Maintain a tracked table such as `edge_registry.md`. Use `docs/templates/edge_registry_template.md`.

Required fields:

- hypothesis ID
- regime
- status
- evidence strength
- latest run IDs
- next action

---

## 4. Exact Operator Sequence

See [docs/03_OPERATOR_WORKFLOW.md](../03_OPERATOR_WORKFLOW.md) for the complete step-by-step sequence.

Key commands:

```bash
# Step 1: query memory
.venv/bin/python -m project.research.knowledge.query knobs
.venv/bin/python -m project.research.knowledge.query memory --program_id <program_id>

# Step 2: translate proposal
.venv/bin/python -m project.research.agent_io.proposal_to_experiment \
  --proposal /abs/path/to/proposal.yaml \
  --registry_root project/configs/registries \
  --config_path /tmp/experiment.yaml \
  --overrides_path /tmp/run_all_overrides.json

# Step 3: plan only
.venv/bin/python -m project.research.agent_io.execute_proposal \
  --proposal /abs/path/to/proposal.yaml \
  --run_id <run_id> \
  --registry_root project/configs/registries \
  --out_dir data/artifacts/experiments/<program_id>/proposals/<run_id> \
  --plan_only 1

# Step 4: execute
.venv/bin/python -m project.research.agent_io.issue_proposal \
  --proposal /abs/path/to/proposal.yaml \
  --registry_root project/configs/registries \
  --run_id <run_id> \
  --plan_only 0
```

---

## 5. Promotion Gates

Every new idea must pass these gates before it is treated as real.

### Gate 1: Mechanism

Can you state:

- forced actor
- constraint
- distortion
- unwind path
- tradable horizon

### Gate 2: Contract

Does the run populate:

- canonical regime
- subtype
- phase
- evidence mode
- routing profile
- comparison-compatible artifacts

### Gate 3: Cost

Does the idea survive:

- spread
- slippage
- funding or borrow when relevant
- realistic execution assumptions

### Gate 4: Robustness

Does it hold on:

- unseen future window
- related market
- stress versus non-stress split

### Gate 5: Operational Simplicity

Can the idea be run and monitored without creating a brittle machine?

Promotion rule:

- only promoted hypotheses move into later deployment-oriented work

---

## 6. Governance Cadence

### Every bounded experiment

Run:

- `python -m compileall -q project project/tests`
- `make test-fast`
- targeted tests for the changed area
- regime/routing or local artifact validation tied to the touched surface

### Weekly or every N runs

Run:

- comparison-service compatibility checks
- generated-doc drift checks
- run-comparison summaries
- null/default drift audit on candidate and promotion tables

Useful maintained surfaces:

- [docs/08_TESTING_AND_MAINTENANCE.md](../08_TESTING_AND_MAINTENANCE.md)
- [docs/12_AUDIT_RUN_SCHEDULE.md](../12_AUDIT_RUN_SCHEDULE.md)

### Monthly or after major refactors

Run the heavy lane again.

---

## 7. What Not To Do

Do not:

- rerun full audits after every small change
- reopen taxonomy or architecture weekly
- add ML before one rule-based edge loop survives
- widen into many simultaneous regimes
- treat green tests as research proof
- treat one profitable backtest as deployment proof

---

## 8. Default Next Stage

The default next stage is one bounded regime-specific edge program.

Recommended shape:

1. choose one regime
2. write `hypothesis.md`
3. create one compact proposal
4. plan the run
5. execute the run
6. write `experiment_review.md`
7. update the edge registry
8. decide `keep`, `modify`, or `kill`

Return point after every run:

- update memory
- record one next action
- stop
