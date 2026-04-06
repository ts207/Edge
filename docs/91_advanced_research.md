# Advanced Research

This document covers internal research tools and methodologies that are not part of the standard four-stage workflow. These features are generally considered **EXPERIMENTAL** and are not part of the canonical operator discovery path.

## Experimental Features
- **Hierarchical Search**: Multi-stage (A-D) refinement to prune search space efficiently.
- **Ledger Scoring (v3)**: Merit-based multiplicity correction using historical evidence burden.
- **Diversified Shortlist**: Greedy selection to maximize signal diversity in top candidates.
- **Trigger Discovery**: Lane for mining new proposal-generating market anchors.

## Search Generation
Edge includes tools for automated hypothesis generation using a grammar-based approach.
* **Ontology**: Definition of valid market events and states.
* **Generator**: Engine that samples from the ontology to produce structured hypotheses.

## Synthetic Truth
Tools for generating synthetic price data with known ground-truth edges. These are used to calibrate validation gates and ensure they can correctly distinguish signal from noise.

## Advanced Diagnostics
* **Multiplicity Control**: Tools for handling False Discovery Rate (FDR) across large search spaces.
* **Clustered Bootstrap**: Methodology for assessing dependency across overlapping alpha windows.

---

## Statistical Integrity: Known Fixes and Current Behaviour

This section records confirmed statistical issues that have been diagnosed and corrected. It exists so future researchers know what changed, when, and why.

### P-value Direction (Fixed)

**File**: `project/research/gating.py`, `project/research/gating_primitives.py`

All directional hypothesis tests use a one-sided right-tail p-value via `one_sided_p_from_t(t_stat, df)`. A previous alias `two_sided_p_from_t` has been redirected to `one_sided_p_from_t` with a `DeprecationWarning` and an ERROR-level log. Any code calling `two_sided_p_from_t` will behave correctly but will produce a visible log error.

**Historical contamination**: Candidates generated before this fix may have passed gating on strongly negative t-statistics (the two-sided test gave them a low p-value). There is no automated re-evaluation pass over the artifact history. Promoted theses generated under the old regime should be treated as potentially contaminated until individually re-evaluated.

### Split-Label Contamination in Gate t-Statistic (Fixed)

**File**: `project/research/gating.py` — `calculate_expectancy_stats`

The gate t-statistic and p-value are now computed on **train + validation observations only**. The test split is a pure holdout and must not participate in gate decisions. Events labelled `split_label = "test"` are excluded from the NW computation; they contribute only to the separately reported `mean_test_return` output field.

If no split labels are present (the common case), all events are treated as `"train"` and the behaviour is unchanged.

### Newey-West Degrees of Freedom for Weighted Estimation (Fixed)

**File**: `project/research/gating.py` — `calculate_expectancy_stats`

When time-decay weights are applied, the t-distribution degrees of freedom are now `n_gate - 1` (the observation count in the gate window), not `ESS - 1`. The weighted NW standard error already adjusts for weight concentration; using ESS as df was a double-penalty that made weighted and unweighted hypothesis p-values incoherent.

### LOSO Stability for Single-Symbol Hypotheses (Fixed)

**File**: `project/research/helpers/estimation_kernels.py` — `_compute_loso_stability`

Leave-one-symbol-out stability cannot be computed for groups containing only one symbol. These groups are now marked `stable = False` (previously they silently received `stable = True`). Single-symbol hypotheses require cross-symbol evidence before they can be promoted to deployable status. Shadow promotion remains available.

### Remaining Known Limitations

| Issue | Location | Status |
|-------|----------|--------|
| DSR `n_trials` scoped to family, not full campaign | `promotion_gate_evaluators.py:393` | Open — `num_tests_event_family` undercounts by ~10× for typical campaigns |
| Historical p-value contamination (pre-fix candidates) | Artifact history | Open — no automated re-evaluation pass |

#### Resolved Issues (April 2026)

| Issue | Resolution |
|-------|------------|
| ~~`side_policy='both'` counted as 1 test in BH denominator~~ | **Fixed**: Now correctly weighted as 2 tests in `apply_canonical_cross_campaign_multiplicity()` |
| ~~Cross-campaign multiplicity correction absent~~ | **Fixed**: `effective_q_value = max(q_value, q_value_scope, q_value_program)` is canonical decision field; scope-level FDR applied |
| ~~Discovery search burden not propagated to promotion~~ | **Fixed**: `search_burden_summary.json` loaded and merged in `promotion_service.py`; all outputs carry search-burden fields |
| ~~Artifact audit provenance undefined~~ | **Fixed**: `stat_regime`, `audit_status`, `artifact_audit_version` stamped on all promotion-derived artifacts; historical scanner available |

## Gate Parameters Reference

Current discovery-track thresholds (see `spec/gates.yaml` for full spec):

| Gate | Parameter | Value |
|------|-----------|-------|
| Phase 2 standard | `min_t_stat` | 2.0 |
| Phase 2 standard | `regime_ess_min_regimes` | 3 |
| Phase 2 standard | `conditioned_bucket_hard_floor` | 75 |
| Phase 2 standard | `max_q_value` | 0.05 |
| Phase 2 discovery profile | `max_q_value` | 0.15 |
| Phase 2 synthetic profile | `min_t_stat` | 1.0 |
| Bridge | `search_bridge_min_t_stat` | 2.0 |
| Deployable promotion | `min_regimes_supported` | 3 |
| Permutation bootstrap (standard) | `robust_bootstrap_iters` | 2000 |
| Permutation bootstrap (synthetic) | `robust_bootstrap_iters` | 500 |
