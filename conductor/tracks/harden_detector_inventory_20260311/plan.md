# Implementation Plan: Harden Detector Inventory and Synthetic Research Loop

## Phase 1: Synthetic Data & Infrastructure Stabilization [checkpoint: 6137a50]
- [x] Task: Finalize Synthetic Relief Profiles [044f0f6]
    - [x] Write tests to verify synthetic data properties (e.g., return signs, volume decay) for rebound segments.
    - [x] Refine `generate_synthetic_crypto_regimes.py` profiles for `post_deleveraging_rebound`.
- [x] Task: Harden Pipeline Flag Filtering [3995e42]
    - [x] Write tests for `execution_engine.py` flag filtering logic.
    - [x] Ensure core flags like `--run_id` are preserved while filtering global configs.
- [x] Task: Support 2021-style synthetic volatility [8b0f54b]
    - [x] Implement `2021_bull` profile with lower base prices and higher noise.
    - [x] Add SOLUSDT base parameters to the generator.
- [x] Task: Support long-duration synthetic runs with repeating cycles [6344a43]
    - [x] Modify `build_regime_schedule` to repeat cycle every 60 days.
- [x] Task: Conductor - User Manual Verification 'Phase 1: Synthetic Data & Infrastructure Stabilization' (Protocol in workflow.md)

## Phase 2: Detector Tuning & Precision Hardening
- [x] Task: Harden `DELEVERAGING_WAVE` and `TREND` Families [c8a645e]
    - [x] Write tests verifying detector sensitivity to threshold adjustments.
    - [x] Update `oi.py` and `trend.py` with tighter quantile requirements.
- [x] Task: Repair and Tune `FALSE_BREAKOUT` [05ae55f]
    - [x] Write tests for `min_breakout_distance` logic in `trend.py`.
    - [x] Implement robust distance-based filtering to reduce noise.
- [ ] Task: Conductor - User Manual Verification 'Phase 2: Detector Tuning & Precision Hardening' (Protocol in workflow.md)

## Phase 3: Validation & Golden Run Certification
- [x] Task: Repair `POST_DELEVERAGING_REBOUND` Detector
    - [x] Write tests for the forced_flow cooldown logic.
    - [x] Fix the detector logic to align with synthetic relief profiles.
- [x] Task: Execute Golden Synthetic Discovery Workflow
    - [x] Run full 2-month discovery with `golden_synthetic_discovery.yaml`.
    - [x] Verify summary artifacts and noise gate pass rates.
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Validation & Golden Run Certification' (Protocol in workflow.md)
