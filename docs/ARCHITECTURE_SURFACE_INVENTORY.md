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

- `project.strategies`
  This is still heavily used by runtime internals and tests. Treat it as an internal implementation package for now rather than a preferred public import surface.
  Current importer count: 17 files.
  Target disposition: keep stable internally while converging public callers on `project.strategy.runtime`.

## Current Policy

- New public or cross-domain code should prefer:
  - `project.strategy.dsl`
  - `project.strategy.templates`
  - `project.strategy.runtime`
  - research service modules instead of removed compatibility packages
- Transitional imports are allowed only from the currently documented importer set enforced in architecture tests.
- When migrating call sites, update tests and scripts before deleting compatibility modules.

## Immediate Follow-On

1. Keep research pipeline wrappers entrypoint-only and route helper logic through canonical research service/spec modules.
2. Keep deleted compatibility packages from reappearing.
3. Recompute generated metrics after any future package-surface cleanup.
4. Recompute this inventory after each migration wave.
