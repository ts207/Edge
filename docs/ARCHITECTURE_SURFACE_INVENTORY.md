# Architecture Surface Inventory

This note records the current package-surface decision for the research platform and freezes the transitional import boundary so it can only shrink.

## Canonical Surfaces

- `project.pipelines.run_all`
  Canonical orchestration entrypoint.
- `project.research.services.candidate_discovery_service`
  Canonical discovery service surface.
- `project.research.services.promotion_service`
  Canonical promotion service surface.
- `project.research.services.reporting_service`
  Canonical reporting surface.
- `project.pipelines.research.phase2_candidate_discovery`
  Pipeline entrypoint only. Helper and policy code should live in research service/spec modules instead of this wrapper.
- `project.pipelines.research.promote_candidates`
  Pipeline entrypoint only. Promotion policy and reusable helpers should live in research service/promotion modules instead of this wrapper.
- `project.strategy.dsl`
  Canonical public Strategy DSL import surface.
- `project.strategy.templates`
  Canonical public strategy-template import surface.
- `project.strategy.runtime`
  Canonical public runtime-facing strategy surface.

## Explicit Package-Root Surfaces

These package roots now exist as deliberate import surfaces rather than implicit namespace folders:

- `project.artifacts`
  Artifact path and payload helpers for run- and report-scoped outputs.
- `project.compilers`
  Executable strategy-spec and blueprint transformation surface.
- `project.eval`
  Multiplicity and split-building helpers.
- `project.experiments`
  Experiment config loading and registry helpers.
- `project.live`
  Live runner, kill-switch, and runtime health helpers.
- `project.portfolio`
  Allocation, sizing, and risk-budget helpers.
- `project.spec_validation`
  Ontology, grammar, loader, and search-spec validation helpers.

## Explicit Subpackage Roots

These are package roots for active subdomains. They should stay thin and should not absorb business logic:

- `project.pipelines.clean`
- `project.pipelines.features`
- `project.pipelines.ingest`
- `project.pipelines.smoke`
- `project.research.clustering`
- `project.research.reports`
- `project.research.utils`

For `project.pipelines.clean`, `project.pipelines.features`, and `project.pipelines.ingest`, the package roots are lazy import shims over concrete stage entrypoints. Keep them light.

## Compatibility Facades

These surfaces are still allowed, but only as pure re-export compatibility wrappers:

- `project.apps.*`
- `project.execution.*`
- `project.infra.*`

Compatibility wrappers must:

- include the `COMPAT WRAPPER` marker
- import from canonical `project.*` modules
- avoid local `def` or `class` logic

## Transitional Surfaces

- None currently approved.

## Removed Surfaces

- `project.research.compat`
  Removed after migrating pipeline wrappers, tests, smoke helpers, and debug scripts to canonical research modules.
- `project.strategy_dsl`
  Removed after migrating all remaining callers and inlining the canonical implementation into `project.strategy.dsl`.
- `project.strategy_templates`
  Removed after inlining the canonical implementation into `project.strategy.templates`.

## Internal Legacy-Carrying Surfaces

- `project.strategy.runtime`
  This is still heavily used by runtime internals and tests. Treat it as an internal implementation package for now rather than a preferred public import surface.
  Current importer count: 16 files.
  Target disposition: keep stable internally while converging public callers on `project.strategy.runtime`.
  
  **Strategy Namespace Boundary Policy:**
  - `project.strategy`: The **canonical** namespace. All new models, DSL definitions, and template logic must be added here.
  - `project.strategy.runtime`: The **legacy** implementation tree. It currently hosts concrete runtime logic (e.g., `dsl_runtime`). 
  - **Consolidation Path**: Move concrete runtime implementation from `project.strategy.runtime` to `project.strategy.runtime` (or a private peer like `project.strategy._runtime`) once the public surface is fully decoupled. Do not add new business logic to `project.strategy.runtime`.

## Current Policy

- New public or cross-domain code should prefer:
  - explicit package-root surfaces where they exist
  - `project.strategy.dsl`
  - `project.strategy.templates`
  - `project.strategy.runtime`
  - research service modules instead of removed compatibility packages
- Large policy or orchestration modules should split into focused support modules before relaxing architecture thresholds.
  Examples now in use:
  - `project/pipelines/execution_engine_support.py`
  - `project/research/services/candidate_discovery_diagnostics.py`
  - `project/research/services/candidate_discovery_scoring.py`
  - `project/research/promotion/promotion_decision_support.py`
  - `project/research/promotion/promotion_result_support.py`
  - `project/research/promotion/promotion_reporting_support.py`
- Transitional imports are allowed only from the currently documented importer set enforced in architecture tests.
- When migrating call sites, update tests and scripts before deleting compatibility modules.

## Immediate Follow-On

1. Keep research pipeline wrappers entrypoint-only and route helper logic through canonical research service/spec modules.
2. Keep compatibility facades pure re-export wrappers rather than letting them turn into parallel implementations.
3. Keep deleted compatibility packages from reappearing.
4. Recompute generated metrics after any future package-surface cleanup.
5. Recompute this inventory after each migration wave.
