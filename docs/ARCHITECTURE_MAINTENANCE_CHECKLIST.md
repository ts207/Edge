# Architecture Maintenance Checklist

Use this checklist when a refactor touches contracts, generated docs, orchestration, or service/package ownership.

## Contracts and Generated Docs

- If you change [`project/contracts/pipeline_registry.py`](/home/tstuv/workspace/trading/EDGEE/project/contracts/pipeline_registry.py) or [`project/contracts/system_map.py`](/home/tstuv/workspace/trading/EDGEE/project/contracts/system_map.py), regenerate the system map artifacts in [`docs/generated/`](/home/tstuv/workspace/trading/EDGEE/docs/generated).
- Run the contract and generated-artifact tests after any registry or serialization change.
- Do not leave generated docs as stale snapshots; the architecture tests should reflect the current contract shape.

## Research Services and Wrappers

- Keep research pipeline wrappers entrypoint-only. Reusable helper logic belongs in `project.research.services.*`, `project.research.promotion.*`, or `project.specs.*`.
- If a test needs a helper, prefer importing the canonical service/spec module instead of a pipeline wrapper.
- If you add a new helper to discovery or promotion, decide whether it is service-owned or private before exporting it.

## Strategy Surfaces

- Prefer `project.strategy.dsl` and `project.strategy.templates` for new public or cross-domain imports.
- If you touch `project.strategy.__init__`, avoid eager imports that can reintroduce circular-import chains.
- Treat `project.strategy_dsl` and `project.strategy_templates` as removed packages; if they reappear, that is a regression.

## Orchestration

- Keep [`project/pipelines/run_all.py`](/home/tstuv/workspace/trading/EDGEE/project/pipelines/run_all.py) as a coordinator over focused helpers.
- Add or keep characterization tests before moving planning, bootstrap, or terminalization logic.
- If `run_all` grows materially, measure whether the logic belongs in `run_all_support`, `run_all_bootstrap`, or `run_all_finalize` instead.

## Metrics and Guardrails

- Recompute architecture metrics after a migration wave and refresh [`docs/generated/architecture_metrics.json`](/home/tstuv/workspace/trading/EDGEE/docs/generated/architecture_metrics.json).
- Update [`docs/ARCHITECTURE_SURFACE_INVENTORY.md`](/home/tstuv/workspace/trading/EDGEE/docs/ARCHITECTURE_SURFACE_INVENTORY.md) when transitional importer counts or dispositions change.
- Keep [`project/tests/test_architectural_integrity.py`](/home/tstuv/workspace/trading/EDGEE/project/tests/test_architectural_integrity.py) aligned with the current canonical package model.

## Research Calibration

- Keep the default drift thresholds in [`project/research/services/run_comparison_service.py`](/home/tstuv/workspace/trading/EDGEE/project/research/services/run_comparison_service.py) aligned with the CLI defaults in [`project/pipelines/pipeline_planning.py`](/home/tstuv/workspace/trading/EDGEE/project/pipelines/pipeline_planning.py).
- Keep the default sample-quality policies in [`project/research/services/candidate_discovery_service.py`](/home/tstuv/workspace/trading/EDGEE/project/research/services/candidate_discovery_service.py) aligned with the current research profiles.
- If you retune research defaults, update [`docs/RESEARCH_CALIBRATION_BASELINE.md`](/home/tstuv/workspace/trading/EDGEE/docs/RESEARCH_CALIBRATION_BASELINE.md) and the pinned tests in `tests/research/services/` and `tests/pipelines/`.
