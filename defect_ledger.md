# Platform Defect Ledger - Phase 0 Baseline

This document tracks all known platform defects, architecture breaches, and drift identified during the Phase 0 stabilization baseline.

| ID | Status | Category | Defect Description | Root Cause | Owner | Acceptance Criteria |
|----|--------|----------|--------------------|------------|-------|----------------------|
| D-001 | Closed | Artifact Drift | `spec_qa_linter.py` reports 24 missing artifacts across multiple concepts. | Un-synced spec definitions or missing data generation. | ts | `spec_qa_linter.py` reports 0 missing artifacts. |
| D-002 | Closed | Artifact Drift | `system_map.md` and `system_map.json` drift from current implementation. | System map not updated after recent changes. | ts | `make minimum-green-gate` passes system-map check. |
| D-003 | Closed | Code Quality | `project/research/promotion/core.py` exceeds 1000 lines (1709 lines). | High density of promotion logic and helper functions. | ts | Module refactored below 1000 lines. |
| D-004 | Closed | Code Quality | `project/research/helpers/shrinkage.py` exceeds 1000 lines (1258 lines). | Complex shrinkage estimation logic. | ts | Module refactored below 1000 lines. |
| D-005 | Open | Reliability | `safe_int` and `safe_float` produce high volume of warnings during smoke run. | Pipeline processing `None` values or missing columns in small datasets. | TBD | Smoke run completes with zero `safe_coercion` warnings. |
| D-006 | Closed | Ontology | State registry has 2 un-materialized states: `MS_BASIS_STATE`, `MS_LIQUIDATION_STATE`. | Registry entry exists but implementation is missing. | ts | `ontology_consistency_audit.py` reports 0 un-materialized states. |

## Reproducible Baseline Status

- **Compilation:** GREEN (`python -m compileall` passed)
- **Architecture Integrity:** GREEN (`pytest tests/architecture` passed)
- **Spec Validation CLI:** GREEN (`spec_qa_linter.py` passed)
- **Detector Coverage Audit:** GREEN (Passed)
- **Ontology Consistency Audit:** GREEN (Passed)
- **System-Map Check:** GREEN (No drift detected)
- **Targeted Fast Regression Slice:** GREEN (Snapshot generated)
- **Research Smoke Run:** GREEN (Completed)
- **Full Test Suite:** GREEN (`pytest` passed)
