# Operator Workflow

The repository is designed for disciplined research loops, not ad hoc command execution.

Canonical loop:

`observe -> retrieve memory -> define objective -> propose -> plan -> execute -> evaluate -> reflect -> adapt`

Default policy:

- use the change-management lane only for structural changes to architecture, schemas, routing semantics, storage semantics, or identity lineage
- use the bounded experiment lane for normal progress
- follow [docs/templates/bounded_experiment_template.md](/home/irene/Edge/docs/templates/bounded_experiment_template.md) for the standing research loop, required artifacts, promotion gates, and governance cadence

---

## Preferred Workflow

### 1. Query knowledge first

Use maintained knowledge surfaces before creating a new run:

```bash
.venv/bin/python -m project.research.knowledge.query knobs
.venv/bin/python -m project.research.knowledge.query memory --program_id btc_campaign
.venv/bin/python -m project.research.knowledge.query static --event VOL_SHOCK
```

This tells you:

- current knobs
- prior campaign memory
- static event information

### 2. Translate proposal to repo-native config

```bash
.venv/bin/python -m project.research.agent_io.proposal_to_experiment \
  --proposal /abs/path/to/proposal.yaml \
  --registry_root project/configs/registries \
  --config_path /tmp/experiment.yaml \
  --overrides_path /tmp/run_all_overrides.json
```

Use this when you want to inspect the exact config that a proposal becomes.

### 3. Plan before execution

```bash
.venv/bin/python -m project.research.agent_io.execute_proposal \
  --proposal /abs/path/to/proposal.yaml \
  --run_id btc_vol_shock_probe \
  --registry_root project/configs/registries \
  --out_dir data/artifacts/experiments/btc_campaign/proposals/btc_vol_shock_probe \
  --plan_only 1
```

This is the default safe mode. Read the plan. Confirm the date range, symbols, trigger scope, search surface, and output locations.

Reject the plan and narrow it further if any of these are true:

- multiple unrelated trigger families enter the plan
- more than one template family enters the plan without an explicit reason
- symbol or date scope expanded beyond the stated hypothesis
- output locations or promotion profile are not what the hypothesis expects

### 4. Execute one bounded run

Only after the plan looks right, execute.

Good run shape:

- one symbol or very small symbol set
- one timeframe
- one event or one narrow family
- one main template family
- one bounded date range

Use the proposal path or the direct CLI path:

```bash
.venv/bin/python -m project.research.agent_io.issue_proposal \
  --proposal /abs/path/to/proposal.yaml \
  --registry_root project/configs/registries \
  --run_id <planned_run_id> \
  --plan_only 0
```

### 5. Evaluate the run on three layers

Every meaningful run needs:

1. mechanical conclusion
2. statistical conclusion
3. deployment conclusion

Do not collapse these into a single yes/no answer.

---

## Exact Operating Sequence

### Step 1. Retrieve existing memory and static context

```bash
.venv/bin/python -m project.research.knowledge.query knobs
.venv/bin/python -m project.research.knowledge.query memory --program_id <program_id>
.venv/bin/python -m project.research.knowledge.query static --event <event_type>
```

Use this to avoid repeating already-tested regions and to verify the candidate mechanism is grounded in an existing event/regime family.

### Step 2. Write the mechanism and hypothesis

Fill in:

- `docs/templates/hypothesis_template.md`
- the mechanism section of `docs/templates/experiment_review_template.md` before running anything

Hard scope rule:

- one regime
- one mechanism
- one tradable expression
- one template family
- one primary event family

### Step 3. Draft the proposal

Create a proposal YAML that stays inside `project.research.agent_io.proposal_schema.AgentProposal`.

Required proposal characteristics:

- `trigger_space.canonical_regimes` contains exactly one regime
- `templates` contains only the intended template family
- `symbols`, `timeframe`, `start`, `end`, `horizons_bars`, `directions`, and `entry_lags` are explicit
- any knob overrides are proposal-settable only

### Step 4. Plan before executing

```bash
.venv/bin/python -m project.research.agent_io.issue_proposal \
  --proposal /abs/path/to/proposal.yaml \
  --registry_root project/configs/registries \
  --plan_only 1
```

Review:

- validated hypothesis count
- required detectors
- required features
- required states
- whether the plan still matches the intended bounded mechanism

Stop if the validated plan widens beyond the intended mechanism or regime.

### Step 5. Execute the bounded run

```bash
.venv/bin/python -m project.research.agent_io.issue_proposal \
  --proposal /abs/path/to/proposal.yaml \
  --registry_root project/configs/registries \
  --run_id <planned_run_id> \
  --plan_only 0
```

### Step 6. Review artifacts in strict order

Read in this order:

1. `data/runs/<run_id>/run_manifest.json`
2. `data/reports/phase2/<run_id>/search_engine/phase2_diagnostics.json`
3. `data/reports/phase2/<run_id>/search_engine/phase2_candidates.parquet`
4. `data/reports/promotions/<run_id>/promotion_diagnostics.json`
5. promotion tables and evidence bundles
6. blueprint/spec artifacts if any candidate was promoted
7. comparison report if there is a directly relevant baseline run

Do not jump directly to headline metrics.

### Step 7. Produce the decision

Use `docs/templates/experiment_review_template.md` and end with exactly one:

- `keep`
- `modify`
- `kill`

The next step must remain bounded. No open-ended follow-on search.

### Step 8. Update the edge registry

Write one new or updated row using `docs/templates/edge_registry_template.md`.

Required fields:

- hypothesis id
- regime
- status
- evidence strength
- latest run id
- cost survivability
- execution realism
- drift sensitivity
- next action

---

## Comparison Rule

Run comparison is allowed only when the baseline is directly comparable:

- same regime
- same mechanism family
- same tradable expression
- only one intentional change

```bash
.venv/bin/python project/scripts/compare_research_runs.py \
  --baseline_run_id <baseline_run_id> \
  --candidate_run_id <candidate_run_id>
```

Self-comparison is not a substantive review.

---

## Direct CLI Workflow

If you are not using the proposal layer, [project/pipelines/run_all.py](/home/irene/Edge/project/pipelines/run_all.py) is the end-to-end orchestrator.

Useful direct controls from `run_all --help`:

- `--symbols`
- `--start`
- `--end`
- `--mode {research,production,certification}`
- `--phase2_event_type`
- `--templates`
- `--horizons`
- `--directions`
- `--contexts`
- `--phase2_gate_profile`
- `--search_spec`

Use direct CLI only when you already know the exact bounded slice you want.

---

## Synthetic Workflow

Synthetic data is for:

- detector truth recovery
- infrastructure validation
- negative controls
- stress calibration

It is not direct evidence of live tradability.

Maintained synthetic commands:

```bash
python3 -m project.scripts.generate_synthetic_crypto_regimes \
  --suite_config project/configs/synthetic_dataset_suite.yaml \
  --run_id synthetic_suite
python3 -m project.scripts.run_golden_synthetic_discovery
python3 -m project.scripts.run_fast_synthetic_certification
python3 -m project.scripts.validate_synthetic_detector_truth \
  --run_id golden_synthetic_discovery
```

---

## Stop Conditions

Stop immediately if:

- the plan widened beyond one regime/mechanism/expression
- you cannot describe the claim in one sentence
- artifacts are missing or contradictory
- schema validation fails
- the result only survives after rationalizing away costs
- the next proposed step is broader rather than sharper

When that happens, split the work into smaller runs instead of adding more knobs.
