# Operator Workflow

## Objective

Use this repository to run bounded, replayable research loops with a clean artifact trail.

Default posture:

- start narrow
- inspect prior memory first
- plan before material execution
- separate mechanical, statistical, and deployment conclusions
- record the next action

## Canonical Loop

1. inspect prior knowledge
2. define the bounded objective
3. write or select a proposal
4. translate proposal into repo-native config
5. inspect the validated plan
6. execute only when the plan is acceptable
7. evaluate artifacts in the correct order
8. decide `explore`, `repair`, `hold`, `stop`, or `exploit`

## Step 1: Inspect Knowledge and Knobs

```bash
.venv/bin/python -m project.research.knowledge.query knobs
.venv/bin/python -m project.research.knowledge.query memory --program_id btc_campaign
.venv/bin/python -m project.research.knowledge.query static --event BASIS_DISLOC
```

Use this step to avoid rerunning near-duplicates and to narrow proposal scope.

## Step 2: Write a Compact Proposal

Proposal inputs should be hypothesis-shaped, not essay-shaped.

Minimum proposal structure:

- `program_id`
- `objective`
- `symbols`
- `timeframe`
- `start`
- `end`
- `trigger_space`
- `templates`
- `contexts` when relevant
- `horizons_bars`
- `directions`
- `entry_lags`

Keep the search space bounded. Avoid broad unrelated trigger sets in one run.

## Step 3: Translate and Validate

```bash
.venv/bin/python -m project.research.agent_io.proposal_to_experiment \
  --proposal /abs/path/to/proposal.yaml \
  --registry_root project/configs/registries \
  --config_path /tmp/experiment.yaml \
  --overrides_path /tmp/run_all_overrides.json
```

Outputs:

- experiment config
- `run_all` overrides
- validated plan summary with required detectors/features/states

Stop here if the validated plan is already too broad.

## Step 4: Plan Before Execution

```bash
.venv/bin/python -m project.research.agent_io.execute_proposal \
  --proposal /abs/path/to/proposal.yaml \
  --run_id btc_basis_slice_001 \
  --registry_root project/configs/registries \
  --out_dir data/artifacts/experiments/btc_campaign/proposals/btc_basis_slice_001 \
  --plan_only 1
```

Or, if you want proposal bookkeeping under memory:

```bash
.venv/bin/python -m project.research.agent_io.issue_proposal \
  --proposal /abs/path/to/proposal.yaml \
  --registry_root project/configs/registries \
  --plan_only 1
```

Review:

- estimated hypothesis count
- required detectors
- required features
- required states
- resulting `run_all` command

## Step 5: Execute Narrowly

Examples:

```bash
make discover-target SYMBOLS=BTCUSDT EVENT=VOL_SHOCK
make discover-edges
edge-run-all --run_id demo --symbols BTCUSDT --start 2024-01-01 --end 2024-03-31 --plan_only 1
```

Use `run_all` directly when you need full control over flags such as:

- `--events`
- `--templates`
- `--contexts`
- `--entry_lags`
- `--candidate_promotion_profile`
- `--run_strategy_builder`
- `--runtime_invariants_mode`
- research comparison tolerances

## Step 6: Read Artifacts in the Correct Order

Read in this order:

1. top-level run manifest
2. stage manifests
3. stage logs
4. report artifacts
5. generated diagnostics

If these disagree, the disagreement is the finding.

## Step 7: Evaluate on Three Layers

Every meaningful run should be evaluated on:

1. mechanical integrity
2. statistical quality
3. deployment relevance

Minimum checks:

- artifact completeness
- warning surface
- split counts / sample adequacy
- q-values
- after-cost expectancy
- stressed cost survival
- promotion eligibility

## Synthetic Policy

Use synthetic workflows for:

- detector truth recovery
- infrastructure validation
- negative controls
- regime stress
- search/promotion calibration

Do not present synthetic profitability as live evidence.

Maintained commands:

```bash
python3 -m project.scripts.generate_synthetic_crypto_regimes \
  --suite_config project/configs/synthetic_dataset_suite.yaml \
  --run_id synthetic_suite
python3 -m project.scripts.run_golden_synthetic_discovery
python3 -m project.scripts.run_fast_synthetic_certification
python3 -m project.scripts.validate_synthetic_detector_truth --run_id golden_synthetic_discovery
```

## Benchmarks and Governance

For benchmark governance:

```bash
make benchmark-maintenance-smoke
make benchmark-maintenance
```

For structural maintenance:

```bash
make minimum-green-gate
```

## Stop Conditions

Stop and re-scope when:

- the validated plan is too broad
- the run differs from a prior run only cosmetically
- artifacts disagree
- synthetic-only support is being mistaken for deployable evidence
- drift or runtime invariants fail

## Expected Outputs of a Good Run

A good run leaves:

- a bounded question
- manifested evidence
- an interpretable result
- a next action
