# Architecture Maintenance Checklist

Use this checklist when a refactor touches contracts, generated docs, orchestration, or service/package ownership.

## Contracts and Generated Docs

- If you change `project/contracts/pipeline_registry.py` or `project/contracts/system_map.py`, regenerate the system map artifacts in `docs/generated/`.
- Run the contract and generated-artifact tests after any registry or serialization change.
- Do not leave generated docs as stale snapshots; the architecture tests should reflect the current contract shape.

Recommended commands:

```bash
python3 -m project.scripts.build_system_map --check
python3 -m project.scripts.detector_coverage_audit \
  --md-out docs/generated/detector_coverage.md \
  --json-out docs/generated/detector_coverage.json \
  --check
```

## Research Services and Wrappers

- Keep research pipeline wrappers entrypoint-only. Reusable helper logic belongs in `project.research.services.*`, `project.research.promotion.*`, or `project.specs.*`.
- If a test needs a helper, prefer importing the canonical service/spec module instead of a pipeline wrapper.
- If you add a new helper to discovery or promotion, decide whether it is service-owned or private before exporting it.
- If `candidate_discovery_service.py`, `promotion_decisions.py`, or `promotion_reporting.py` starts growing again, split focused helpers into support modules instead of loosening the file-size threshold.

## Strategy Surfaces

- Prefer `project.strategy.dsl` and `project.strategy.templates` for new public or cross-domain imports.
- If you touch `project.strategy.__init__`, avoid eager imports that can reintroduce circular-import chains.
- Treat `project.strategy_dsl` and `project.strategy_templates` as removed packages; if they reappear, that is a regression.

## Compatibility Facades

- `project.apps.*`, `project.execution.*`, and `project.infra.*` are compatibility facades, not primary implementation homes.
- Keep wrapper modules pure re-exports with the `COMPAT WRAPPER` marker and no local `def` or `class` logic.
- If a facade needs new behavior, add it to the canonical source module and re-export it rather than implementing it inside the wrapper.

## Package Roots

- Prefer explicit package-root surfaces where they exist: `project.artifacts`, `project.compilers`, `project.eval`, `project.experiments`, `project.live`, `project.portfolio`, and `project.spec_validation`.
- Keep package-root `__init__.py` files intentionally small. They should re-export stable symbols, not own heavy logic.
- For lazy pipeline package roots such as `project.pipelines.clean`, `project.pipelines.features`, and `project.pipelines.ingest`, keep `__getattr__`-based dispatch minimal and deterministic.

## Orchestration

- Keep `project/pipelines/run_all.py` as a coordinator over focused helpers.
- Add or keep characterization tests before moving planning, bootstrap, or terminalization logic.
- If `run_all` grows materially, measure whether the logic belongs in `run_all_support`, `run_all_bootstrap`, or `run_all_finalize` instead.
- Keep `project/pipelines/execution_engine.py` coordinator-oriented as well. Shared helper logic belongs in `project/pipelines/execution_engine_support.py`.

## Metrics and Guardrails

- Recompute architecture metrics after a migration wave and refresh `docs/generated/architecture_metrics.json`.
- Update `docs/ARCHITECTURE_SURFACE_INVENTORY.md` when transitional importer counts or dispositions change.
- Keep `project/tests/test_architectural_integrity.py` aligned with the current canonical package model.

## Research Calibration

- Keep the default drift thresholds in `project/research/services/run_comparison_service.py` aligned with the CLI defaults in `project/pipelines/pipeline_planning.py`.
- Keep the default sample-quality policies in `project/research/services/candidate_discovery_service.py` aligned with the current research profiles.
- If you retune research defaults, update `docs/RESEARCH_CALIBRATION_BASELINE.md` and the pinned tests in `tests/research/services/` and `tests/pipelines/`.
