> [!IMPORTANT]
> **HISTORICAL ARCHIVE**: This document is preserved for architectural context and represents a completed research milestone. See `docs/TECHNICAL_DEBT_AUDIT.md` for the current system state.

# Confirmatory Expansion and Baseline Retention Implementation Plan

> **For Gemini:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Expand confirmatory contracts to all maintained families and implement comparison against historical benchmark baselines.

**Architecture:** 
1. **Contract Expansion**: Create individual confirmatory contracts for `STATISTICAL_DISLOCATION`, `TREND_STRUCTURE`, `LIQUIDITY_DISLOCATION`, `POSITIONING_EXTREMES`, and `EXECUTION_FRICTION` to ensure temporal consistency across all primary families.
2. **Governance Evolution**: Enhance the governance service to handle multiple historical baselines, enabling multi-point drift detection.
3. **Operator Surface Upgrade**: Update terminal tools to allow comparing the current run against a specific historical baseline or the last N baselines.

**Tech Stack:** Python, YAML, JSON, Pandas.

---

### Task 1: Create Confirmatory Contracts for Remaining Families

**Files:**
- Create: `spec/benchmarks/confirmatory_rerun_contract_stat_disloc.yaml`
- Create: `spec/benchmarks/confirmatory_rerun_contract_trend.yaml`
- Create: `spec/benchmarks/confirmatory_rerun_contract_liquidity.yaml`
- Create: `spec/benchmarks/confirmatory_rerun_contract_positioning.yaml`
- Create: `spec/benchmarks/confirmatory_rerun_contract_execution.yaml`

**Step 1: Write the failing test**
Create a test that verifies the existence of all family contracts.
```python
def test_all_family_contracts_exist():
    families = ["stat_disloc", "trend", "liquidity", "positioning", "execution"]
    for f in families:
        path = Path(f"spec/benchmarks/confirmatory_rerun_contract_{f}.yaml")
        assert path.exists(), f"Contract for {f} is missing"
```

**Step 2: Run test to verify it fails**
Run: `pytest tests/research/services/test_contracts_exist.py`
Expected: FAIL

**Step 3: Write minimal implementation**
Create the 5 YAML files following the `VOL_SHOCK` template but tailored to each family's primitives (e.g., `basis_zscore` for `STAT_DISLOC`, `depth_usd` for `LIQUIDITY`).

**Step 4: Run test to verify it passes**
Run: `pytest tests/research/services/test_contracts_exist.py`
Expected: PASS

**Step 5: Commit**
```bash
git add spec/benchmarks/confirmatory_rerun_contract_*.yaml
git commit -m "feat: add confirmatory contracts for all maintained families"
```

### Task 2: Implement Multi-Baseline Comparison in Governance Service

**Files:**
- Modify: `project/research/services/benchmark_governance_service.py`
- Test: `tests/research/services/test_multi_baseline_comparison.py`

**Step 1: Write the failing test**
Test that `certify_benchmark_review` can accept a list of `prior_reviews` and detect drift across them.

**Step 2: Run test to verify it fails**
Run: `pytest tests/research/services/test_multi_baseline_comparison.py`
Expected: FAIL

**Step 3: Write minimal implementation**
- Update `certify_benchmark_review` to handle `List[Dict[str, Any]]` for `prior_reviews`.
- Add "Historical Drift" section to the certification report if multiple priors are present.

**Step 4: Run test to verify it passes**
Run: `pytest tests/research/services/test_multi_baseline_comparison.py`
Expected: PASS

**Step 5: Commit**
```bash
git add project/research/services/benchmark_governance_service.py
git commit -m "feat: support multi-baseline comparison in governance service"
```

### Task 3: Update Maintenance Cycle to Feed Historical Priors

**Files:**
- Modify: `project/scripts/run_benchmark_maintenance_cycle.py`

**Step 1: Write the failing test**
Update the dry-run test to verify that the maintenance cycle correctly identifies and loads up to 5 historical baselines from `data/reports/benchmarks/history/`.

**Step 2: Run test to verify it fails**
Run: `PYTHONPATH=. python3 project/scripts/run_benchmark_maintenance_cycle.py --execute 0`
(Verify logs show only one prior being loaded)

**Step 3: Write minimal implementation**
- Modify `run_benchmark_maintenance_cycle.py` to scan the `history/` directory.
- Pass the list of historical reviews to the matrix runner/certifier.

**Step 4: Run test to verify it passes**
Run: `PYTHONPATH=. python3 project/scripts/run_benchmark_maintenance_cycle.py --execute 0`
(Verify logs show multiple priors being loaded)

**Step 5: Commit**
```bash
git add project/scripts/run_benchmark_maintenance_cycle.py
git commit -m "feat: maintenance cycle now feeds historical priors to certification"
```

### Task 4: Enhance show_benchmark_review.py for History Comparison

**Files:**
- Modify: `project/scripts/show_benchmark_review.py`

**Step 1: Write the failing test**
Add a smoke test for `show_benchmark_review.py --compare-history 3`.

**Step 2: Run test to verify it fails**
Run: `PYTHONPATH=. python3 project/scripts/show_benchmark_review.py --compare-history 3`
Expected: unrecognized arguments error.

**Step 3: Write minimal implementation**
- Add `--compare-history` argument.
- Implement a simple table rendering that shows row counts for the current run vs. the last N historical runs side-by-side.

**Step 4: Run test to verify it passes**
Run: `PYTHONPATH=. python3 project/scripts/show_benchmark_review.py --compare-history 3`
Expected: PASS (Terminal table shown)

**Step 5: Commit**
```bash
git add project/scripts/show_benchmark_review.py
git commit -m "feat: terminal tool now supports historical comparison"
```
