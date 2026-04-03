# Operator Workflow

The repository is designed for disciplined research loops, not ad hoc command execution.

There are now two connected operator lanes:

1. **bounded experiment lane**
   - `observe -> retrieve memory -> preflight -> plan -> execute -> evaluate -> reflect -> adapt`
2. **thesis bootstrap lane**
   - `seed inventory -> score -> empirical evidence -> package -> thesis store -> overlap graph`

Default policy:

- use the change-management lane only for structural changes to architecture, schemas, routing semantics, storage semantics, or identity lineage
- use the bounded experiment lane for normal progress on a hypothesis
- use the thesis bootstrap lane only when you are turning tested claims into canonical thesis objects
- follow [docs/templates/bounded_experiment_template.md](templates/bounded_experiment_template.md) for the standing research loop, required artifacts, promotion gates, and governance cadence

## Operator actions

Reduce the visible repo surface to four actions:

1. `discover`
   - `edge operator preflight`
   - `edge operator plan`
   - `edge operator run`
2. `package`
   - thesis bootstrap builders
   - thesis overlap / structural confirmation builders
3. `validate`
   - contract verification
   - smoke workflows
   - governance and replay checks
4. `review`
   - `edge operator diagnose`
   - `edge operator regime-report`
   - `edge operator compare`

Everything else is internal or maintenance-oriented.

---

## Preferred bounded experiment workflow

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

### 2. Run preflight before plan

```bash
edge operator preflight   --proposal /abs/path/to/proposal.yaml   --registry_root project/configs/registries
```

Preflight is the default gate for local operator work. It validates proposal translation, checks the search spec, inspects local raw data coverage, and verifies that artifacts can be written.

### 3. Translate proposal to repo-native config

```bash
.venv/bin/python -m project.research.agent_io.proposal_to_experiment   --proposal /abs/path/to/proposal.yaml   --registry_root project/configs/registries   --config_path /tmp/experiment.yaml   --overrides_path /tmp/run_all_overrides.json
```

Use this when you want to inspect the exact config that a proposal becomes.

### 4. Plan before execution

Canonical command:

```bash
edge operator plan   --proposal /abs/path/to/proposal.yaml
```

Equivalent internal command:

```bash
.venv/bin/python -m project.research.agent_io.execute_proposal   --proposal /abs/path/to/proposal.yaml   --run_id btc_vol_shock_probe   --registry_root project/configs/registries   --out_dir data/artifacts/experiments/btc_campaign/proposals/btc_vol_shock_probe   --plan_only 1
```

This is the default safe mode. Read the plan. Confirm the date range, symbols, trigger scope, search surface, and output locations.

Reject the plan and narrow it further if any of these are true:

- multiple unrelated trigger families enter the plan
- more than one template family enters the plan without an explicit reason
- symbol or date scope expanded beyond the stated hypothesis
- output locations or promotion profile are not what the hypothesis expects

### 5. Execute one bounded run

Only after the plan looks right, execute.

Good run shape:

- one symbol or very small symbol set
- one timeframe
- one event or one narrow family
- one main template family
- one bounded date range

Canonical command:

```bash
edge operator run   --proposal /abs/path/to/proposal.yaml
```

Equivalent internal command:

```bash
.venv/bin/python -m project.research.agent_io.issue_proposal   --proposal /abs/path/to/proposal.yaml   --registry_root project/configs/registries   --run_id <planned_run_id>   --plan_only 0
```

### 6. Evaluate the run on three layers

Every meaningful run needs:

1. mechanical conclusion
2. statistical conclusion
3. thesis lifecycle conclusion

Do not collapse these into a single yes/no answer.

---

## Thesis bootstrap workflow

Use this lane when either of these is true:

- the thesis store is empty or sparse
- you already have bounded candidate claims and need thesis packaging artifacts rather than another discovery run

### Bootstrap sequence

```bash
python -m project.scripts.build_seed_bootstrap_artifacts
python -m project.scripts.build_seed_testing_artifacts
python -m project.scripts.build_seed_empirical_artifacts
python -m project.scripts.build_founding_thesis_evidence
python -m project.scripts.build_seed_packaging_artifacts
python -m project.scripts.build_structural_confirmation_artifacts
python -m project.scripts.build_thesis_overlap_artifacts
./project/scripts/regenerate_artifacts.sh
```

### What each step does

1. **seed bootstrap**
   - creates the bounded founding thesis queue
   - writes `promotion_seed_inventory.*`
2. **seed testing**
   - scores the queue on governance, contract fit, and packaging readiness
   - writes `thesis_testing_scorecards.*`
3. **seed empirical**
   - maps real evidence bundles onto the founding queue
   - writes `thesis_empirical_scorecards.*`
4. **founding thesis evidence**
   - generates canonical evidence bundles under `data/reports/promotions/<thesis_id>/evidence_bundles.jsonl`
5. **seed packaging**
   - writes canonical packaged theses under `data/live/theses/`
   - emits seed thesis cards and catalog
6. **structural confirmation**
   - optionally creates conservative bridge theses from supported component evidence
7. **thesis overlap**
   - builds the overlap graph used by allocator and live-review surfaces

### Thesis lifecycle ladder

The operator should treat thesis classes as strict stages:

- `candidate`
- `tested`
- `seed_promoted`
- `paper_promoted`
- `production_promoted`

`seed_promoted` is enough for monitor-only retrieval and overlap generation.
It is not enough for production deployment.

---

## Exact operating sequence

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
.venv/bin/python -m project.research.agent_io.issue_proposal   --proposal /abs/path/to/proposal.yaml   --registry_root project/configs/registries   --plan_only 1
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
.venv/bin/python -m project.research.agent_io.issue_proposal   --proposal /abs/path/to/proposal.yaml   --registry_root project/configs/registries   --run_id <planned_run_id>   --plan_only 0
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

Then decide whether the output contributes to:

- another bounded experiment
- the founding thesis queue
- repair work
- no further action

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
