# Assurance & Benchmarks

This document describes the benchmarking methodology and regression testing used to ensure system integrity.

## Benchmark Methodology
Every code change is tested against a set of *Baseline Snapshots*.
* **Baseline Snapshots**: Known successful research runs that must remain consistent across versions.
* **Performance Regression**: Metrics for ensuring discovery and validation performance does not rot over time.

## Certification
Promotion often requires a *Certification* step, which is an automated or semi-automated verification of a candidate's out-of-sample behavior.

## Regression Suites
* **Adversarial Tests**: Tests that attempt to break validation gates using known noise patterns.
* **Contract Integrity**: Tests that ensure artifact schemas remain compatible across stages.

---

## Change Log: Statistical and Execution Integrity Fixes

### April 2026 — Deep System Audit

A comprehensive audit of the research pipeline, execution model, and live engine identified and corrected the following issues. All code changes are tracked in git; this section records the *intent* of each change for future researchers.

#### Statistics

| ID | File | Change | Impact |
|----|------|--------|--------|
| B1 | `research/gating.py` | Gate t-stat now computed on train+val only; test split excluded | Holdout independence restored |
| B2 | `research/helpers/estimation_kernels.py` | LOSO single-symbol groups now marked `stable=False` | BTC-only hypotheses no longer pass stability gate silently |
| B6 | `research/gating.py`, `research/gating_primitives.py` | `two_sided_p_from_t` emits ERROR-level log in addition to DeprecationWarning | Deprecated calls visible in production log aggregators |
| B8 | `research/gating.py` | NW degrees of freedom: `n_eff - 1` → `n_gate - 1` | Weighted and unweighted p-values now use the same df convention |
| — | `research/validate_expectancy_traps.py` | Surviving local two-sided `_p_from_t` replaced with `one_sided_p_from_t` | Eliminates last instance of two-sided computation in validation path |
| — | `spec/gates.yaml` | `min_t_stat` 1.5→2.0, regime ESS 2→3, conditioned bucket floor 30→75, synthetic t-stat 0.25→1.0, bridge t-stat 1.5→2.0, deployable `min_regimes_supported` 2→3 | Tightened discovery and promotion gates |
| — | `research/validate_expectancy_traps.py` | Bootstrap iterations: standard 400→2000, promotion 800→2000, synthetic 100→500 | SE on empirical p-value at α=0.05 drops from ±1.4% to ±0.5% |
| — | `research/helpers/estimation_kernels.py` | `_apply_hierarchical_shrinkage` gains `elapsed_days` + `lambda_decay_halflife_days` parameters; decay now time-based | Cross-session lambda continuity no longer degrades from session-count accumulation |
| — | `project/tests/core/test_stats.py` | BH test expectations corrected: `adj_smaller[2]` expectation changed from `0.013` to `0.01333` (exact rational value); monotonicity test added | Statistical test correctness; monotonic conservatism verified |
| — | `research/multiplicity.py` | `side_policy='both'` now correctly weighted as 2 tests in BH denominator | Two-sided hypotheses no longer undercounted in multiplicity correction |
| — | `research/promotion/promotion_gate_evaluators.py` | DSR `n_trials` precedence: `num_tests_effective` → `num_tests_campaign` → `num_tests_family` → fallback to 1 with WARNING | Selection bias penalty now uses most granular available multiplicity count |

#### Live Execution

| ID | File | Change | Impact |
|----|------|--------|--------|
| — | `live/kill_switch.py` | `PSI_ERROR_THRESHOLD` 0.50→0.25; `PSI_WARN_THRESHOLD` 0.25→0.10; TIER1 features expanded from 3 to 6 | Kill switch triggers on minor-to-major shift boundary; more features monitored |
| — | `live/drift.py` | Adaptive PSI binning (≥30 obs/bin); outer edges extended to ±∞; KS statistic added | PSI estimates stable at small research sample sizes; tail drift detectable |
| — | `live/scoring.py` | `MIN_SETUP_MATCH = 0.20` hard gate added | Prevents trades when no qualifying event has fired |
| — | `live/decay.py` | `default_decay_rules()` added; `LiveEngineRunner` uses it when none supplied | Per-thesis degradation monitoring always active |
| — | `engine/risk_allocator.py` | `AllocationPolicy.mode` default: `"heuristic"` → `"deterministic_optimizer"` | Allocation decisions reproducible by default |
| — | `engine/risk_allocator.py` | `stressed_regime_values` expanded to cover uppercase and alternate naming conventions | Stress correlation limit activates regardless of registry label convention |
| B5 | `engine/pnl.py` | `FUNDING_HOURS_BYBIT_4H` constant added; `compute_pnl_ledger` and `compute_pnl_components` accept `funding_hours` parameter | Bybit 4-hour contracts can now use correct funding schedule |
| — | `live/thesis_reconciliation.py` | New module: thesis-batch reconciliation on live startup | Detects added/removed/superseded/downgraded theses; enforces fail-safe rules before live trading |
| — | `live/runner.py` | Added `_reconcile_thesis_batch()` called at startup when `reconcile_at_startup=True` | Runtime state drift blocked; removed/downgraded theses with open positions trigger kill-switch |
| — | `core/regime_classifier.py` | New unified `classify_regime()` function with `RESEARCH_EXACT` and `RUNTIME_APPROX` modes | Live and research use shared logic; approximation path is explicit and documented |

#### Open Issues (not yet fixed)

| ID | Description | Location | Status |
|----|-------------|----------|--------|
| B3 | DSR `n_trials` scoped to mechanism family (~10–20), not full campaign (~hundreds) | `promotion/promotion_gate_evaluators.py:393` | **Partially fixed**: Precedence chain implemented (`effective` → `campaign` → `family`); family-level not yet automatic |
| B4 | ~~`side_policy='both'` counted as 1 test in BH denominator~~ | `research/multiplicity.py` | **Fixed** (April 2026): Now correctly weighted as 2 |
| A1 | Research batch feature computation and live REST polling are independent implementations | `build_features.py` vs `runner.py` | **Still open**: No shared feature builder yet |
| A2 | ~~Live regime classifier uses single-bar bps threshold; research used rolling percentile state machine~~ | `live/runner.py:_classify_canonical_regime` | **Partially fixed**: Unified `classify_regime()` exists; live uses `runtime_approx` with explicit metadata when research features unavailable |
| A4 | ~~BH FDR applied within mechanism groups only; no cross-campaign correction~~ | `research/multiplicity.py` | **Fixed** (April 2026): `apply_canonical_cross_campaign_multiplicity()` wired into promotion; `effective_q_value` is canonical decision field |
| A5 | ~~No documented thesis-state reconciliation procedure when a new export is written between engine restarts~~ | `live/thesis_store.py`, `live/thesis_state.py` | **Fixed** (April 2026): `thesis_reconciliation.py` added; startup reconciliation enforced |

---

## Sprint 4+: Workstream A — Canonical Multiplicity (Complete)

### Scope-Level FDR Correction

Cross-campaign / campaign-lineage multiplicity is now canonical:

| Component | Implementation | Location |
|-----------|---------------|----------|
| Scope multiplicity contract | `MultiplicityScope` dataclass with scope mode, version, key | `research/contracts/multiplicity_scope.py` |
| Historical universe merge | `merge_historical_candidates()` loads scope-relevant historical candidates | `research/multiplicity.py:403` |
| Effective q-value | `effective_q_value = max(q_value, q_value_scope, q_value_program)` | `research/multiplicity.py:389` |
| Promotion gating | Uses `effective_q_value` when `use_effective_q_value=True` (default) | `research/promotion/promotion_decisions.py:142` |
| Degraded handling | `multiplicity_scope_degraded=True` + `multiplicity_scope_reason` when history missing | `research/multiplicity.py:430` |
| Audit stamp | `audit_status="degraded"` when multiplicity degraded | `research/services/promotion_service.py:335` |

### Required Fields in Promotion Outputs

Every promotion artifact now includes:

- `q_value_scope` — FDR-corrected q-value at scope level
- `effective_q_value` — Max of (q_value, q_value_scope, q_value_program)
- `num_tests_scope` — Number of tests in the scope
- `multiplicity_scope_mode` — "run" | "campaign" | "program" | "campaign_lineage"
- `multiplicity_scope_key` — Unique identifier for the scope
- `multiplicity_scope_version` — Contract version (e.g., "phase1_v1")
- `multiplicity_scope_degraded` — True if historical data was unavailable
- `multiplicity_scope_reason` — "ok" | "missing_history" | other reason

### Phase 1 Invariant

**No promoted candidate may lack `effective_q_value`.**

---

## Sprint 4+: Workstream B — Search Burden Accounting (Complete)

### Canonical Search Burden Contract

Every discovery and promotion artifact must explain the search universe it emerged from:

| Field | Description |
|-------|-------------|
| `search_proposals_attempted` | Number of search proposals attempted |
| `search_candidates_generated` | Total candidates generated |
| `search_candidates_scored` | Candidates that passed scoring |
| `search_candidates_eligible` | Candidates eligible for promotion |
| `search_parameterizations_attempted` | Parameter combinations explored |
| `search_mutations_attempted` | Mutation attempts |
| `search_directions_tested` | Direction tests |
| `search_confirmations_attempted` | Confirmation attempts |
| `search_trigger_variants_attempted` | Trigger variant attempts |
| `search_family_count` | Unique families explored |
| `search_lineage_count` | Unique lineages explored |
| `search_scope_version` | Contract version (e.g., "phase1_v1") |
| `search_burden_estimated` | True if counts are estimated vs exact |

### Propagation Flow

1. **Discovery**: `phase2_search_engine.py` emits `search_burden_summary.json`
2. **Promotion**: `promotion_service.py` loads summary (or defaults to `estimated=True`)
3. **Merge**: `merge_search_burden_columns()` merges into `candidates_df`
4. **Artifacts**: Fields propagate through `build_promotion_statistical_audit()`, evidence bundles, and exports

### Contract Module

`project/research/contracts/search_burden.py`:
- `SEARCH_BURDEN_FIELDS` — canonical field list
- `default_search_burden_dict(estimated=True)` — defaults for missing burden
- `merge_search_burden_columns(df, defaults)` — idempotent column merge
- `write_search_burden_summary()` / `load_search_burden_summary()`

---

## Sprint 4+: Workstream C — Artifact Audit Provenance (Complete)

### Statistical Regime Contract

All promotion-derived artifacts carry explicit audit provenance:

| Field | Values | Description |
|-------|--------|-------------|
| `stat_regime` | `pre_audit_stat_regime` \| `post_audit_stat_regime` \| `unknown_stat_regime` | Statistical provenance of the artifact |
| `audit_status` | `current` \| `degraded` \| `manual_review_required` \| `legacy` \| `unknown` | Confidence/completeness of provenance |
| `artifact_audit_version` | `phase1_v1` | Contract version |

### Inference Rules

The `infer_stat_regime_from_artifact_metadata()` function classifies artifacts:

1. **Explicit stamp**: If `stat_regime` already present and valid → preserve it
2. **Recognized version**: If `artifact_audit_version` is recognized → `post_audit_stat_regime`
3. **Phase 1 fields + provenance**: If Phase 1 multiplicity fields present with recognized policy/bundle → `post_audit_stat_regime` (high confidence)
4. **After boundary**: If artifact timestamp ≥ 2025-01-01 and has Phase 1 fields → `post_audit_stat_regime` (medium confidence)
5. **Pre-boundary**: If artifact predates audit boundary → `pre_audit_stat_regime` + `legacy`
6. **Insufficient provenance**: → `unknown_stat_regime` + `manual_review_required`

### Current Output Stamping

All newly written promotion artifacts are stamped:
- `stat_regime = "post_audit_stat_regime"`
- `audit_status = "current"` (or `"degraded"` if multiplicity/search burden degraded)
- `artifact_audit_version = "phase1_v1"`

### Historical Artifact Scanner

`project/research/audit_historical_artifacts.py`:
- `scan_historical_artifacts()` — Scans promotion artifacts for audit inventory
- `write_audit_inventory()` — Emits parquet/json/md inventory
- `rewrite_audit_stamp_sidecars()` — Writes non-destructive `*.audit_stamp.json` sidecars

### CLI

```bash
edge catalog audit-artifacts --data_root /path/to/data
edge catalog audit-artifacts --run_id specific_run
edge catalog audit-artifacts --rewrite_stamps 1
```

---

## Definition of Done

Workstream A, B, C implementation is complete when:

- [x] Multiplicity scope fields present in all promotion artifacts
- [x] `effective_q_value` governs promotion decisions
- [x] Degraded multiplicity explicitly stamped
- [x] Search burden fields propagate from discovery to promotion
- [x] Evidence bundles contain nested `search_burden` block
- [x] All new artifacts carry `stat_regime`, `audit_status`, `artifact_audit_version`
- [x] Historical artifact scanner produces inventory
- [x] `--rewrite_stamps` writes sidecars non-destructively
- [x] Tests cover propagation, inference, and stamping
