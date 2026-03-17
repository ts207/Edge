# Detector Stabilization Plan

Goal: Improve detector precision (reduce noise) and recall (reduce silence) using the patterns identified in High-Fidelity detectors.

## Phase 1: Utility Extraction and Standardization
- [ ] Task: Extract Adaptive Quantile logic (1.1)
    - [ ] Identify reusable components in `BasisDislocationDetector`
    - [ ] Move logic to `project/events/thresholding.py` or a dedicated Mixin
- [ ] Task: Standardize `ThresholdDetector` (1.2)
    - [ ] Support adaptive buffers by default in the base class

## Phase 2: Refactoring Noisy Detectors (Precision)
- [ ] Task: Refactor `FUNDING_FLIP` (2.1)
    - [ ] Add minimum magnitude requirement (e.g., > 50th percentile of absolute funding)
- [ ] Task: Refactor `MOMENTUM_DIVERGENCE_TRIGGER` (2.2)
    - [ ] Require minimum trend extension before allowing divergence to trigger
- [ ] Task: Refactor `TREND_ACCELERATION` (2.3)
    - [ ] Increase acceleration quantile threshold or add a volatility filter

## Phase 3: Simplifying Silent Detectors (Recall)
- [ ] Task: Refactor `TREND_EXHAUSTION_TRIGGER` (3.1)
    - [ ] Move to hierarchical approach: Signal (Trend Peak) + Guard (Reversal)
    - [ ] Allow a small alignment window (e.g., 3-5 bars) instead of single-bar intersection
- [ ] Task: Refactor `FND_DISLOC` (3.2)
    - [ ] Implement lead-lag window for basis/funding alignment
- [ ] Task: Resolve `LIQUIDITY_STRESS_DIRECT` (3.3)
    - [ ] Add L2 column checks; fallback gracefully to PROXY mode if data is missing

## Phase 4: Enhancing Synthetic Verification
- [ ] Task: Update Synthetic Generator (4.1)
    - [ ] Add basic order book depth proxies to `generate_synthetic_crypto_regimes.py`
- [ ] Task: Refine Truth Validator (4.2)
    - [ ] Ensure tolerance windows are correctly applied in `validate_synthetic_detector_truth.py`

## Phase 5: Final Validation and Baselining
- [ ] Task: Execute Golden Synthetic Discovery (5.1)
    - [ ] Run `make golden-synthetic-discovery`
- [ ] Task: Verify Results (5.2)
    - [ ] Confirm `passed: true` in `reliability/golden_synthetic_discovery_summary.json`
- [ ] Task: Update Ledger (5.3)
    - [ ] Synchronize `defect_ledger.md` with new detector performance baselines
