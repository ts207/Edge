# Edge — Testing, Quality Gates & CI

## Test Suite Overview

The active test suite is organized under `project/tests/`. The suite is structured into distinct test categories, each testing a different layer of the system.

```bash
make test       # Full suite under project/tests
make test-fast  # Excludes @pytest.mark.slow
pytest -q       # Direct pytest invocation
```

---

## Test Categories

### Architecture Tests (`project/tests/architecture/`)

The highest-priority tests — checked in **every CI run**. These enforce:

- No forbidden cross-package imports
- No circular dependencies
- Package surface boundaries are respected
- Canonical import patterns are followed
- Legacy compatibility wrapper surfaces are absent

These tests catch structural regressions before any functional code is examined.

```bash
pytest project/tests/architecture
```

### Contract Tests (`project/tests/contracts/`)

Validate that stage artifact schemas and manifest structures are correct:

| Test File | What It Validates |
|---|---|
| `test_strategy_trace_schema.py` | Strategy execution trace format |
| `test_portfolio_ledger_schema.py` | Portfolio ledger artifact schema |
| `test_candidate_artifact_schema.py` | Discovery candidate artifact schema |
| `test_promotion_artifacts_schema.py` | Promotion output artifact schema |
| `test_manifest_integrity.py` | Run manifest completeness and consistency |
| `test_cross_artifact_reconciliation.py` | Cross-artifact hash reconciliation |

### Regression Tests (`project/tests/regressions/`)

Named regressions for previously-found bugs:

| Test File | Guards Against |
|---|---|
| `test_runner_position_contract.py` | Position contract violation |
| `test_next_open_entry_accounting.py` | Entry bar accounting error |
| `test_event_analyzer_full_market_requirement.py` | Event analyzer missing full market data |
| `test_timeframe_contracts.py` | Timeframe token mismatch |
| `test_storage_fallback_respected.py` | Storage fallback not honoured |
| `test_bundle_policy_consistency.py` | Bundle policy inconsistency |

### Event Tests (`project/tests/events/`)

Unit tests for each event detector family. Validates:

- Detector fires on synthetic data with known signals
- Detector does not fire on negative controls
- Parameter boundaries are respected
- Cooldown logic works correctly

### Feature Tests (`project/tests/features/`)

Validates feature computation:

- Point-in-time correctness (no look-ahead)
- Correct formula application
- Null handling and edge cases

### Research Tests (`project/tests/research/`)

| Directory | Tests |
|---|---|
| `project/tests/research/agent_io/` | Proposal validation, translation, execution |
| `project/tests/research/event_quality/` | Event quality metrics |
| `project/tests/research/knowledge/` | Memory and knowledge retrieval |
| `project/tests/research/promotion/` | Promotion gate logic |
| `project/tests/research/services/` | Discovery and promotion service unit tests |
| `project/tests/research/validation/` | Expectancy trap detection |

### Strategy Tests (`project/tests/strategy/`, `project/tests/strategy_dsl/`, `project/tests/strategy_templates/`)

- Blueprint schema validation
- DSL condition evaluation
- Template instantiation
- Policy enforcement

### Pipeline Tests (`project/tests/pipelines/`)

Per-stage pipeline integration tests.

### Live Engine Tests (`project/tests/live/`)

WebSocket client behavior, reconnect logic, health monitoring.

### Replay Tests (`project/tests/replays/`)

- OMS replay validation
- Causal lane tick verification
- Determinism checks

### Point-in-Time Tests (`project/tests/pit/`)

Strict PIT correctness: no features should observe data beyond `t0`.

### Spec Tests (`project/tests/specs/`, `project/tests/spec_registry/`, `project/tests/spec_validation/`)

- YAML spec loading
- Registry consistency
- Schema conformance

### Audit Tests (`project/tests/audit/`)

- Ontology consistency
- Detector coverage completeness

### Smoke Tests (`project/tests/smoke/`)

End-to-end minimal run smoke tests.

### Artifact Tests (`project/tests/artifacts/`)

Baseline artifact integrity (golden snapshots).

### Synthetic Truth Tests (`project/tests/synthetic_truth/`)

Validates the system against ground-truth synthetic datasets:

| Test File | What It Validates |
|---|---|
| `test_truth_infrastructure.py` | Synthetic generation engine |
| `test_signal_scoring.py` | Normalized score aggregation |
| `test_signal_quality.py` | Firing frequency and clustering |
| `test_event_chain.py` | Temporal sequence detection |
| `test_conflicts.py` | Mutually exclusive event enforcement |

---

## CI Gate Tiers

### Tier 1 — Structural Fast Gate (every push/PR to main)

Steps in order:

1. **Compile Check** — `python -m compileall -q project project/tests`
2. **Architecture Tests** — `pytest project/tests/architecture`
3. **Spec Validation** — `python -m project.spec_validation.cli`
4. **Artifact Drift Checks:**
   - Ontology consistency audit (with `--check` flag — fails on drift)
   - Detector coverage audit (with `--check` flag)
   - System map (with `--check` flag)
5. **Fast Regression Tests** — 12 selected contract + regression tests
6. **Pyright Static Type Check** — `pyright project`

### Tier 2 (Scheduled/Manual)

Broader test coverage beyond Tier 1. Includes extended functional tests.

### Tier 3 (Manual/Release)

Full test suite including `@pytest.mark.slow` tests, golden workflow, and certification manifest.

### Minimum Green Gate

The minimum required passing state for platform stabilization:

```bash
make minimum-green-gate
```

Runs:

1. `python -m compileall -q project project/tests`
2. `pytest project/tests/architecture`
3. `python project/scripts/spec_qa_linter.py`
4. Detector coverage audit (--check)
5. Ontology consistency audit (--check)
6. System map (--check)
7. Architecture metrics (--check)
8. Golden regression
9. Golden workflow

All listed steps must pass for `minimum-green-gate` to succeed.

---

## Quality Gate Hierarchy

The pipeline enforces quality gates at three levels:

### Gate E1 — Event Detection Quality

Applied in Phase 1 analysis. Rejects events that:

- Fire too rarely (`< 1.0` per 10k bars)
- Fire too frequently (`> 500` per 10k bars)
- Have a low join rate to hypothesis frames (`< 0.99`)
- Are temporally clustered (`max_clustering_5b > 0.20`)

### Gate V1 — Statistical Quality (Phase 2)

Applied in discovery. Requires:

| Metric | Threshold |
|---|---|
| q-value (FDR) | ≤ 0.05 |
| After-cost expectancy | ≥ 0.1 bps |
| Conservative cost (1.5× stress) | > 0 bps |
| Sign stability | Required |
| Sample size | ≥ 50 events |
| Regime ESS | ≥ 1 per regime |
| Quality floor (strict) | ≥ 0.66 |

### P3 — Promotion Confirmatory Gate

Applied in the promotion stage. Two tiers:

**Deployable** (strict): q ≤ 0.05, OOS ESS ≥ 50, ≥ 2 regimes, cost stress 2×
**Shadow** (lenient): q ≤ 0.10, OOS ESS ≥ 20, ≥ 1 regime, cost stress 1.5×

---

## Pandera Schema Validation

The platform uses **Pandera** (v0.19.3) throughout for DataFrame schema enforcement. Every stage output that is consumed by another stage is validated against a `pandera.DataFrameSchema` before being written to disk.

Key validated schemas:

- OHLCV input schema (timestamp, open, high, low, close, volume)
- Feature frame schema (typed columns per feature family)
- Event episode schema (event_type, timestamp, symbol, signal columns)
- Candidate artifact schema (hypothesis ID, metrics, q-value, expectancy)
- Promotion artifact schema (promotion tier, gate results)

---

## Drift Detection

Three machine-owned artifacts are checked for drift on every CI run:

| Artifact | Regenerated By | Drift Detected When |
|---|---|---|
| `docs/generated/system_map.json` | `build_system_map.py` | Stage contracts change, new entrypoints added |
| `docs/generated/detector_coverage.json` | `detector_coverage_audit.py` | New events added without detectors, or vice versa |
| `docs/generated/ontology_audit.json` | `ontology_consistency_audit.py` | Template mappings change, family assignments change |

If any of these show drift in CI (i.e., the regenerated file differs from what's committed), **the build fails**. This forces developers to explicitly commit updated machine-owned artifacts when making structural changes.

---

## Determinism Enforcement

The `run_determinism_replay_checks` stage validates that re-running the pipeline with the same inputs, config, and code commit produces bit-identical outputs. This is enforced by:

1. `data_fingerprint` — hash of input data at run start
2. `config_digest` — hash of effective config
3. `git_commit` — code commit hash
4. `claim_map_hash` — hash of the artifact claim map

Any divergence between two runs with the same (fingerprint, digest, commit) is a first-class bug.
