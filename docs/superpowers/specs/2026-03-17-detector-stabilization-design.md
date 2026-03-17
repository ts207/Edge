# Detector Stabilization Design

**Date:** 2026-03-17
**Status:** Approved
**Scope:** All detectors
**Driver:** Platform health + research signal quality

---

## Goals

1. Classify every detector as stable, noisy, silent, or broken using measurable precision/recall metrics
2. Fix all detectors classified as noisy, silent, or broken
3. Establish a permanent per-detector regression surface in the test suite
4. Pass golden synthetic discovery after all fixes land

## Success Criterion

A detector is **stabilized** when:
- Precision ≥ 0.50 and recall ≥ 0.30 across all applicable synthetic profiles
- Passes golden synthetic truth validation
- Has a passing per-detector regression test in the test suite

The overall effort is **complete** when:
- All detectors are classified — none left as noisy, silent, or broken without a documented reason
- `tests/events/test_detector_precision_recall.py` is green
- Golden synthetic discovery passes (`passed: true`)
- `defect_ledger.md` is updated with detector baselines (see schema below)

---

## Metric Definitions

| Metric | Definition |
|--------|-----------|
| Precision | Events landing inside truth windows / total events fired |
| Recall | Truth windows that received ≥ 1 event / total truth windows |
| Event rate | Events per 1000 bars (flags pathological over/under-firing) |

**Classification thresholds (initial, conservative):**

| Class | Condition | Resolution |
|-------|-----------|------------|
| `stable` | Precision ≥ 0.50 AND recall ≥ 0.30 | No action required |
| `noisy` | Precision < 0.50 AND recall ≥ 0.30 | Tighten filter logic |
| `silent` | Precision ≥ 0.50 AND recall < 0.30 | Loosen filter logic |
| `broken` | Precision < 0.50 AND recall < 0.30 | Both precision and recall need work |
| `uncovered` | No truth windows for this event type in the profile | Excluded from assertions; event rate still measured |

---

## Architecture

### Shared Measurement Module

**File:** `project/scripts/detector_audit_module.py`

Placed in `project/scripts/` (not `project/events/`) to avoid circular import risk — some family modules import from `project.research` at module level.

Core logic:
- Accept a detector instance, a DataFrame, and truth windows
- Run `detector.detect(df, symbol=symbol)` directly (no pipeline machinery)
- Compute precision, recall, and event rate against truth windows with configurable per-event-type tolerance
- Return a structured metrics dict

```python
def measure_detector(
    detector: BaseEventDetector,
    df: pd.DataFrame,
    symbol: str,
    truth_windows: list[dict],
    tolerance_minutes: Union[int, Dict[str, int]] = 30,
) -> DetectorMetrics:
    ...
```

When `tolerance_minutes` is a dict, the value for `detector.event_type` is used; unrecognized event types fall back to the scalar default.

Imported by both the audit script and the regression tests. This ensures identical measurement logic across both surfaces.

### Audit Script

**File:** `project/scripts/audit_detector_precision_recall.py`

- Discovers all detectors via catalog dynamically (no hardcoded list)
- Resolves profiles to run_ids and data paths via `data/synthetic/<run_id>/synthetic_generation_manifest.json`

**Label → run_id mapping:**

| Label | run_id | Generated profile |
|-------|--------|-------------------|
| `2021_bull` | `synthetic_2021_bull` | `2021_bull` |
| `default` | `synthetic_2025_full_year` | `default` (not a distinct profile name) |
| `stress_crash` | `synthetic_2025_stress_crash` | `stress_crash` |
| `golden` | `golden_synthetic_discovery` | `default` |

Note: `synthetic_2025_full_year` was generated with the `default` volatility profile. Do not pass `2025_full_year` as a `--volatility_profile` argument to the generator — it is a run_id label only.

The audit script reads `synthetic_generation_manifest.json` for each run_id to obtain per-symbol parquet paths and the associated `synthetic_regime_segments.json` for truth windows.

- Outputs JSON report to `data/artifacts/detector_audit/<timestamp>/`
- Prints human-readable classification table to stdout
- CLI args: `--run_id` (optional filter), `--event_type` (optional filter), `--out_dir`

### Regression Tests

**File:** `tests/events/test_detector_precision_recall.py`

- Parameterized: one test case per detector × run_id combination
- Thresholds loaded from `tests/events/fixtures/detector_thresholds.json`
- Test is skipped (not failed) when the fixture file does not exist or a detector entry is absent — allowing incremental population during the fix phase
- `uncovered` detectors excluded from precision/recall assertions but measured for event rate
- Runs as part of normal `pytest` suite

### Fixture File

**File:** `tests/events/fixtures/detector_thresholds.json`

Seeded after the audit (step 4b below), populated with post-audit measured values:

```json
{
  "FUNDING_FLIP": {
    "synthetic_2021_bull": {
      "min_precision": 0.50,
      "min_recall": 0.30
    }
  }
}
```

Thresholds are set to actual post-fix measured values with a small buffer (subtract 0.05 from measured value, floor at the spec minimums). This makes the tests detect regressions without being brittle.

---

## Truth Validator Updates

**File:** `project/scripts/validate_synthetic_detector_truth.py`

Make tolerance window configurable per event type.

**Interface change:** `tolerance_minutes` parameter changes from `int` to `Union[int, Dict[str, int]]`.

```python
# Before
def validate_detector_truth(*, tolerance_minutes: int = 30, ...) -> Dict:

# After
def validate_detector_truth(*, tolerance_minutes: Union[int, Dict[str, int]] = 30, ...) -> Dict:
```

When a dict is supplied, each event type uses its own tolerance; types not in the dict fall back to 30 minutes. Existing callers passing an integer are unaffected. No other behavioral changes.

---

## Infrastructure Already Complete (No Work Required)

The following items from the original stabilization plan are already implemented:

| Item | Status | Evidence |
|------|--------|---------|
| `thresholding.py` utility module | Done | `project/events/thresholding.py` (219 lines) |
| Adaptive threshold in `ThresholdDetector` | Done | `threshold_quantile` parameter in `threshold.py` |
| `depth_usd` / `spread_bps` in synthetic data | Done | Present in all cleaned perp parquets |
| `FUNDING_FLIP` magnitude filter | Done | Rolling `funding_q_mag` at 50th percentile gating every flip |
| `FND_DISLOC` 3-bar alignment window | Done | `alignment_window = int(params.get('alignment_window', 3))` |

---

## Known Detectors Requiring Investigation

The following detectors were pre-classified before the audit based on prior campaign analysis. The audit may revise these classifications.

| Detector | Pre-audit Class | Pre-audit Hypothesis |
|----------|----------------|---------------------|
| `MOMENTUM_DIVERGENCE_TRIGGER` | noisy | May need stricter trend extension requirement |
| `TREND_ACCELERATION` | noisy | May need higher quantile threshold or vol filter |
| `TREND_EXHAUSTION_TRIGGER` | silent | May need wider alignment window (3-5 bars) |
| `LIQUIDITY_STRESS_DIRECT` | silent | May need improved column fallback handling |
| `FUNDING_FLIP` | unknown | Fix already present; audit will confirm actual class |
| `FND_DISLOC` | unknown | Fix already present; audit will confirm actual class |

All remaining detectors across all catalog families will be classified by the audit. The exact count is determined at runtime by `load_all_detectors()` — do not assert a specific module count.

---

## Execution Order

1. Build `project/scripts/detector_audit_module.py`
2. Build `project/scripts/audit_detector_precision_recall.py`
3. Create `tests/events/test_detector_precision_recall.py` with skip-when-no-fixture behavior
4. Run audit across all detectors and profiles — produce classification report
   - **4b:** Seed `tests/events/fixtures/detector_thresholds.json` with pre-fix measured values (for reference; tests use post-fix values)
5. Fix detectors in priority order: `broken` first, then `noisy`, then `silent`
   - After each fix: re-run `pytest tests/events/` to catch contract regressions
6. Update fixture thresholds with post-fix measured values; confirm regression tests pass
7. Update `project/scripts/validate_synthetic_detector_truth.py` with per-event-type tolerance support
8. Run golden synthetic discovery — confirm `passed: true`
9. Run full test suite — confirm green
10. Update `defect_ledger.md`

---

## `defect_ledger.md` Update Schema

Add one row per detector that was classified as noisy, silent, or broken (not for stable or uncovered detectors). `stable` and `uncovered` detectors require no ledger entry.

| Column | Content |
|--------|---------|
| ID | New sequential defect ID (e.g., D-007) |
| Status | Closed |
| Category | Detector Calibration |
| Defect Description | Detector class pre-fix (noisy/silent/broken) |
| Root Cause | Brief statement of what caused the misclassification |
| Owner | ts |
| Acceptance Criteria | Post-fix precision and recall values on the audit profiles |

---

## Constraints

- Only change the minimum necessary per detector fix (quantile values, filter conditions, window sizes)
- No class hierarchy restructuring unless the audit reveals a structural root cause
- No changes that affect detectors not being worked on in a given fix step
- Re-run `pytest tests/events/` after each detector fix
- Truth validator changes are additive only — no behavioral change to existing callers
