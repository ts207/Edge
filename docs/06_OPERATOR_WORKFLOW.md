# Edge — Operator & Research Workflow Guide

## Roles

| Role | Starting Point |
|---|---|
| Researcher / Autonomous Agent | This guide + `CLAUDE.md` |
| Developer / Engineer | `docs/developer/ONBOARDING.md` |
| Deployment Operator | `deploy/` templates |

---

## Research Loop

The canonical workflow is a bounded, replayable loop:

```
observe → retrieve memory → define objective → propose → plan → execute → evaluate → reflect → adapt
```

Optimize for: **reproducibility → post-cost robustness → contract cleanliness → narrow attribution → decision quality -alpha discovery**

---

## Step 1: Inspect State Before Any Run

Always check prior memory and available knobs before starting:

```bash    ?example knobs, use cases
# What knobs are tunable?
python3 -m project.research.knowledge.query knobs

# What has been found in prior runs for this program?
python3 -m project.research.knowledge.query memory --program_id btc_campaign

# What is known statically about a specific event?
python3 -m project.research.knowledge.query static --event BASIS_DISLOC
```

---

## Step 2: Write a Proposal

A proposal is a compact YAML document specifying a bounded hypothesis test.

**Minimum required fields:**

```yaml
program_id: btc_campaign
objective: "Test VOL_SHOCK mean_reversion in high vol regime for BTC"
symbols: [BTCUSDT]
timeframe: 5m
start: "2024-01-01"
end: "2024-06-30"
trigger_space:
  events: [VOL_SHOCK]
templates: [mean_reversion]
contexts:
  vol_regime: [high]
horizons_bars: [12, 36, 72]
directions: [long, short]
entry_lags: [0, 1, 2]
```

**Rules:**  

- One event family or narrow trigger set per run
- One template family per run
- One primary context family per run
- Only set knobs that are explicitly proposal-settable

---

## Step 3: Translate Proposal to Run Config

```bash
python3 -m project.research.agent_io.proposal_to_experiment \
  --proposal /path/to/proposal.yaml \
  --registry_root project/configs/registries \
  --config_path /tmp/experiment.yaml \
  --overrides_path /tmp/run_all_overrides.json
```

---

## Step 4: Plan Before Executing

**Always plan first on material runs.** Planning validates scope without writing artifacts.

```bash  ?why 3 different but same options, explain them and recommend
# Via issue_proposal (with memory bookkeeping)
python3 -m project.research.agent_io.issue_proposal \
  --proposal /path/to/proposal.yaml \
  --registry_root project/configs/registries \
  --plan_only 1

# Via execute_proposal
python3 -m project.research.agent_io.execute_proposal \
  --proposal /path/to/proposal.yaml \
  --run_id btc_vol_shock_001 \
  --registry_root project/configs/registries \
  --out_dir data/artifacts/experiments/btc_campaign/proposals/btc_vol_shock_001 \
  --plan_only 1

# Via CLI directly
edge-run-all \
  --run_id demo \
  --symbols BTCUSDT \
  --start 2024-01-01 \
  --end 2024-03-31 \
  --plan_only 1
```

---

## Step 5: Execute

Remove `--plan_only` or set it to `0` to execute:

```bash
edge-run-all \
  --run_id btc_vol_shock_001 \
  --symbols BTCUSDT \
  --start 2024-01-01 \
  --end 2024-06-30
```

### Targeted Discovery (single event)

```bash
make discover-target SYMBOLS=BTCUSDT EVENT=VOL_SHOCK    
```

### Full Discovery (all events)

```bash
make discover-edges     
```

```

### Promotion Pass

```bash
edge-promote --run_id btc_vol_shock_001  

```

### Blueprint Compilation

```bash
compile-strategy-blueprints --run_id btc_vol_shock_001
```

---

## Step 6: Evaluate Output

A run must be evaluated on **three layers**:

### Layer 1 — Mechanical Integrity

- Did the run complete without stage failures?
- Do stage manifests reconcile with the top-level manifest?
- Are artifact counts and hashes consistent?
- Are there any contract violations?

**Never trust a run based on exit code alone.** Read the manifests. ?more explicit instructions

### Layer 2 — Statistical Quality

Check at minimum:

- `split_counts` (train / validation / test event counts)
- `q_value` (must be ≤ 0.05 for Gate V1)
- `after_cost_expectancy_bps` (must be > 0.1 bps)
- `stressed_after_cost_expectancy_bps` (at 1.5× cost multiplier)
- `sign_stability` (consistent directional signal across splits)
- `regime_ess` (effective sample size per regime)

```bash
# View benchmark review
PYTHONPATH=. python3 project/scripts/show_benchmark_review.py ?what benchmark, benchmark of what, use cases
```

### Layer 3 — Deployment Relevance

- Does the event occur at sufficient frequency in live markets?
- Is the strategy executable given market microstructure?
- Does the blueprint pass the promotion confirmatory gates?
- Is there regime stability across ≥2 distinct regimes?

---

## Step 7: Record Next Action

Every meaningful run must leave behind a recorded next action:

| Action | Meaning |
|---|---|
| `exploit` | Gates passed; pursue live testing or promotion |
| `explore` | Results are suggestive; refine and re-run |
| `repair` | Mechanical or data issue found; fix before proceeding |
| `hold` | Insufficient data or ambiguous; wait for more evidence |
| `stop` | No evidence of edge; do not continue this line |

---

## Make Targets (Common Shortcuts)

```bash
# Research
make discover-blueprints    # Full pipeline: Ingest → Discovery → Blueprints
make discover-edges         # Phase 2 discovery for all events
make discover-target SYMBOLS=BTCUSDT EVENT=VOL_SHOCK  # Targeted single event
make baseline               # Full discovery + profitable strategy packaging
make golden-workflow        # Canonical end-to-end smoke
make golden-certification   # Golden workflow + runtime certification manifest

# Testing
make test           # Full test suite (407 files)
make test-fast      # Excludes @pytest.mark.slow
make minimum-green-gate  # Required baseline: compile + architecture + spec + drift checks + golden

# Style
make lint           # Ruff lint (changed files)
make format         # Ruff format in-place
make format-check   # Ruff format check (no writes)
make style          # lint + format-check

# Maintenance
make benchmark-maintenance        # Full benchmark governance cycle
make benchmark-maintenance-smoke  # Dry-run
make governance     # Audit specs and sync schemas

# Cleanup
make clean-all-data  # Wipe data/lake and reports
```

---

## Synthetic Validation Workflow

Synthetic data is used for **calibration and infrastructure validation only** — not as evidence of live profitability.

**Appropriate uses:**

- Detector truth recovery after code changes
- Infrastructure validation (pipeline mechanics)
- Negative-control testing
- Regime stress testing
- Search and promotion calibration

**Maintained commands:**

```bash
# Generate synthetic dataset suite
python3 -m project.scripts.generate_synthetic_crypto_regimes \
  --suite_config project/configs/synthetic_dataset_suite.yaml \
  --run_id synthetic_suite

# Run golden synthetic discovery
python3 -m project.scripts.run_golden_synthetic_discovery

# Fast certification (CI/pre-merge)
python3 -m project.scripts.run_fast_synthetic_certification

# Validate detector truth
python3 -m project.scripts.validate_synthetic_detector_truth \
  --run_id golden_synthetic_discovery
```

**Synthetic rules:**

- Freeze the synthetic profile before evaluating outcomes
- Keep the manifest and truth map with the run
- Rerun truth validation after any detector or generator edits
- Compare across ≥1 additional profile before strengthening belief

---

## Benchmark Governance Cycle

Benchmarks are the certified performance baselines. They must be maintained when detectors, features, or gates change.

```bash
# Full production cycle
make benchmark-maintenance

# Dry-run only
make benchmark-maintenance-smoke

# Inspect promotion readiness
PYTHONPATH=. python3 project/scripts/show_promotion_readiness.py \
  --review data/reports/benchmarks/latest/benchmark_review.json \
  --cert data/reports/benchmarks/latest/benchmark_certification.json
```

---

## Maintenance Scripts (Operator)

Run these after any structural change to synchronize the event registry and regenerate machine-owned artifacts.

### 1. Synchronize Event Registry
If you have added, deleted, or modified individual event YAML files in `spec/events/`, you **must** rebuild the unified registry first:

```bash
# Authoritative sync of spec/events/event_registry_unified.yaml
PYTHONPATH=. python3 project/scripts/build_unified_event_registry.py
```

### 2. Regenerate All Artifacts
Use the all-in-one script to regenerate the System Map, Detector Coverage, and Ontology Audit:

```bash
# Recommended for full artifact updates
bash project/scripts/regenerate_artifacts.sh
```

### 3. Individual Maintenance Commands
You can also run specific audits or metrics manually:

```bash
# Regenerate architecture metrics
PYTHONPATH=. python3 project/scripts/build_architecture_metrics.py --check

# Lint all YAML specs for governance compliance
PYTHONPATH=. python3 project/scripts/spec_qa_linter.py
```

### 4. Minimum Green Gate
To run the full suite of stabilization and governance checks (including tests and regressions):

```bash
make minimum-green-gate
```

---

## Live Engine Operations

```bash
# Inspect session metadata
edge-live-engine \
  --config project/configs/golden_certification.yaml \
  --print_session_metadata

# Launch with state snapshot
edge-live-engine \
  --config project/configs/golden_certification.yaml \
  --snapshot_path artifacts/live_state.json
```

**Health monitoring:** The `LiveDataManager` exposes `health_monitor_keys()` returning `(symbol, channel)` pairs for all active streams. Each stream must be monitored for staleness.

**Kill switch:** Configured in `spec/grammar/kill_switch_config.yaml`. Triggers hard shutdown of execution on configurable conditions.

---

## What to Avoid

- Broad search over unrelated triggers in one run
- Re-runs that differ only in wording (not in hypothesis)
- Treating detector materialization as strategy proof
- Treating synthetic wins as live-market evidence
- Trusting command exit status without artifact reconciliation
- Presenting synthetic profitability as live-market evidence
- Comparing runs across different cost configs without normalizing
