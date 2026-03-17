# Specification: Harden Detector Inventory and Synthetic Research Loop

## Overview
This track focuses on stabilizing the event-driven research pipeline by hardening the detector inventory against a high-fidelity synthetic truth map. The goal is to ensure that all core detectors pass the noise gates and that synthetic data generation accurately represents complex market regimes like deleveraging rebounds.

## Functional Requirements
- **Synthetic Data Enhancement:** Finalize the return, volume, and wick profiles for all synthetic regimes, specifically focusing on `post_deleveraging_rebound` and `breakout_failure`.
- **Detector Hardening:** Tune parameters (e.g., quantiles, minimum distances) for noisy detectors (`DELEVERAGING_WAVE`, `TREND_ACCELERATION`, `FALSE_BREAKOUT`) to pass the 75% noise gate.
- **Inert Detector Repair:** Investigate and fix detectors that are currently failing to hit seeded synthetic windows (`BREAKOUT_TRIGGER`, `POST_DELEVERAGING_REBOUND`).
- **Pipeline Infrastructure:** Ensure global configuration flags (e.g., `--config`) are correctly propagated and filtered across all pipeline stages.

## Non-Functional Requirements
- **Reproducibility:** All synthetic research runs must be deterministic and produce identical results given the same seed.
- **Auditability:** Every pipeline stage must generate a valid manifest and execution log.
- **Performance:** Hardening logic should not introduce significant latency to the event analysis stage.

## Acceptance Criteria
- All 14 core event types must hit at least 75% of their expected synthetic windows.
- At least 80% of core detectors must pass the 75% noise gate requirement.
- The `POST_DELEVERAGING_REBOUND` detector must successfully hit all seeded segments in a 2-month synthetic run.
- The full "Golden Synthetic Discovery" workflow must complete successfully with 0 errors using the project's real `pipeline.yaml` config.

## Out of Scope
- Implementation of new detector families not currently in the inventory.
- Real-market data ingestion or cleaning (focus is strictly synthetic).
- Live trading engine integration.
