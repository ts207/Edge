# Benchmark Governance Runbook

This runbook defines the maintained operator workflow for benchmark reruns, certification, and promotion gating.

## Canonical Cycle Cadence

The maintenance cycle must be executed:
1.  **Monthly**: On the first day of the month after new live data is ingested.
2.  **Event/Feature Updates**: Whenever core event detectors or feature schemas are modified.
3.  **New Research Program**: Before a new research program is initiated.

## Command Sequence

### Step 1: Execute Maintenance Cycle

Run the unified maintenance command to rebuild the benchmark matrix and certify the new results:

```bash
# Via script
PYTHONPATH=. python3 project/scripts/run_benchmark_maintenance_cycle.py

# Or via Makefile (recommended for production)
make benchmark-maintenance
```

This command will automatically:
- Re-run all maintained benchmark slices.
- Certify results against absolute thresholds and the prior baseline.
- Generate a `promotion_readiness.json` report.
- Update the `latest` pointer in `data/reports/benchmarks/`.

### Step 2: Review Certification

Check the terminal summary for the **CERTIFICATION** status:

```bash
PYTHONPATH=. python3 project/scripts/show_benchmark_review.py --path data/reports/benchmarks/latest/benchmark_review.json
```

- **If PASS**: Proceed to confirmatory checks.
- **If FAIL**: Follow the [Benchmark Triage Guide](./BENCHMARK_TRIAGE.md). Do NOT promote any candidates from failed families.

### Step 3: Check Promotion Readiness

Inspect the combined readiness report to identify blockers and rerun priorities:

```bash
PYTHONPATH=. python3 project/scripts/show_promotion_readiness.py \
  --review data/reports/benchmarks/latest/benchmark_review.json \
  --cert data/reports/benchmarks/latest/benchmark_certification.json
```

### Step 4: Promotion Decisions

Promotion is automatically gated by benchmark health.
- **Certified Families**: Candidates can be promoted if they pass all standard statistical and economic gates.
- **Degraded Families**: Promotion is blocked. The operator must first resolve the benchmark issues (detector drift, data gaps, etc.).

## Drift Analysis

The certification report includes a **Historical Drift** table comparing row counts across the last 5 baselines.
- **Small Deviations**: Normal variance in sampling or data cleaning.
- **Large Deviations (>20%)**: Indicates a systemic change in event frequency or data quality. Investigate if code changes or data sources have diverged.
- **Steady Decline**: Potential "data decay" or detector desensitization.

## Artifact Retention Policy

The system maintains a history of certified baselines under `data/reports/benchmarks/history/`.
- **Retention Limit**: The system automatically preserves the **last 5 certified passing** benchmark baselines. 
- **Pruning**: Uncertified runs and dry-runs are automatically purged when they become older than the oldest retained certified baseline.
- **Canonical Artifacts**: The authoritative artifacts for any run are:
  - `benchmark_review.json`: Defines the slice row counts and status.
  - `benchmark_certification.json`: Defines the PASS/FAIL outcome against priors.
  - `promotion_readiness.json`: The final gating state for the promotion service.

## Failure Escalation Policy

When a family's benchmark status shifts, follow this escalation path:

- **Certified -> Degraded** (e.g., `informative` -> `coverage_limited`)
  - **Impact**: Promotion is blocked for this family.
  - **Action**: File a defect in `defect_ledger.md`. Fix must be prioritized in the next research sprint.
  
- **Degraded -> Failed** (e.g., `coverage_limited` -> `foundation_only` with blocked readiness)
  - **Impact**: Severe platform regression.
  - **Action**: Immediate halt on all research for this family. Revert recent code changes or escalate to architectural review.

- **Informative -> Empty** (e.g., `hard_evaluated_rows` drops to 0)
  - **Impact**: Detector broken or search space missing events.
  - **Action**: Urgent fix required. Debug the `phase2` search engine output for that specific benchmark run.

## Confirmatory Rerun Contract

For high-trust families, ensure the confirmatory rerun follows the contract in `spec/benchmarks/confirmatory_rerun_contract_*.yaml`.
- Requires `decision_lag_bars: 1`.
- Requires `calibration_mode: train_fit`.
