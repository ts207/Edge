# Research Platform Update Plan

## Goal

Reduce architecture debt in the research platform without destabilizing the canonical discovery and promotion flow.

Success means:

- contract-generated documentation is trustworthy
- canonical import paths are explicit and enforced
- orchestration is easier to reason about
- compatibility shims are materially reduced
- architecture checks catch drift before it lands

## Principles

- Preserve behavior first, simplify second.
- Refactor behind characterization tests.
- Prefer one canonical surface per domain.
- Keep pipelines as orchestration, not policy.
- Remove shims only after consumers are migrated.

## Phase 1: Restore Contract and Documentation Trust

Estimated effort: 1-2 days

### Tasks

- Fix malformed artifact tuple declarations in [`project/contracts/pipeline_registry.py`](/home/tstuv/workspace/trading/EDGEE/project/contracts/pipeline_registry.py).
- Regenerate and verify [`docs/generated/system_map.md`](/home/tstuv/workspace/trading/EDGEE/docs/generated/system_map.md).
- Add tests that validate rendered contract payloads, not only source registry definitions.
- Add a regression test for the `canonicalize_event_episodes*` artifact contract shape.

### File Targets

- [`project/contracts/pipeline_registry.py`](/home/tstuv/workspace/trading/EDGEE/project/contracts/pipeline_registry.py)
- [`project/contracts/system_map.py`](/home/tstuv/workspace/trading/EDGEE/project/contracts/system_map.py)
- [`docs/generated/system_map.md`](/home/tstuv/workspace/trading/EDGEE/docs/generated/system_map.md)
- [`tests/contracts/`](/home/tstuv/workspace/trading/EDGEE/tests/contracts)
- [`tests/pipelines/`](/home/tstuv/workspace/trading/EDGEE/tests/pipelines)

### Acceptance Criteria

- No artifact contract renders as character-by-character output.
- Generated system map matches the underlying registry contract shapes.
- CI fails if generated contract payloads drift or serialize invalid field types.

## Phase 2: Inventory and Classify Compatibility Debt

Estimated effort: 2-3 days

### Tasks

- Inventory all imports and call sites involving `project.research.compat`.
- Inventory overlapping strategy surfaces across `project.strategy`, `project.strategy_dsl`, `project.strategies`, and `project.strategy_templates`.
- Classify each surface as `canonical`, `transitional`, or `remove`.
- Publish a short architecture decision note with the approved long-term package model.

### File Targets

- [`project/research/compat/`](/home/tstuv/workspace/trading/EDGEE/project/research/compat)
- [`project/strategy/`](/home/tstuv/workspace/trading/EDGEE/project/strategy)
- [`project/strategy_dsl/`](/home/tstuv/workspace/trading/EDGEE/project/strategy_dsl)
- [`project/strategies/`](/home/tstuv/workspace/trading/EDGEE/project/strategies)
- [`project/strategy_templates/`](/home/tstuv/workspace/trading/EDGEE/project/strategy_templates)
- [`project/tests/test_architectural_integrity.py`](/home/tstuv/workspace/trading/EDGEE/project/tests/test_architectural_integrity.py)
- [`docs/`](/home/tstuv/workspace/trading/EDGEE/docs)

### Acceptance Criteria

- Every compatibility surface has an owner and disposition.
- A single canonical import path is documented for each strategy/research concern.
- No new code is allowed to introduce fresh transitional imports.

## Phase 3: Migrate Non-Production Consumers First

Estimated effort: 3-5 days

### Tasks

- Update tests to use canonical imports instead of transitional wrappers where possible.
- Update scripts and reliability helpers to depend on service or canonical package surfaces.
- Narrow compat modules to only the call sites still required by runtime code.
- Add architecture assertions that block new test/script imports from deprecated surfaces.

### File Targets

- [`tests/`](/home/tstuv/workspace/trading/EDGEE/tests)
- [`project/scripts/`](/home/tstuv/workspace/trading/EDGEE/project/scripts)
- [`project/reliability/`](/home/tstuv/workspace/trading/EDGEE/project/reliability)
- [`project/research/compat/`](/home/tstuv/workspace/trading/EDGEE/project/research/compat)
- [`project/tests/test_architectural_integrity.py`](/home/tstuv/workspace/trading/EDGEE/project/tests/test_architectural_integrity.py)

### Acceptance Criteria

- Test and script imports from compatibility modules are reduced to the minimum necessary set.
- Architecture tests explicitly reject newly introduced deprecated imports.
- Smoke and contract tests still pass with the migrated call sites.

## Phase 4: Decompose Orchestration

Estimated effort: 4-6 days

### Tasks

- Split [`project/pipelines/run_all.py`](/home/tstuv/workspace/trading/EDGEE/project/pipelines/run_all.py) into focused modules for:
  startup guards,
  preflight and contract validation,
  manifest/provenance assembly,
  execution coordination,
  terminalization and failure reporting.
- Keep `run_all.py` as the thin canonical CLI coordinator.
- Add characterization tests around current planning and failure behavior before moving logic.
- Ensure no policy logic migrates into orchestration during the refactor.

### File Targets

- [`project/pipelines/run_all.py`](/home/tstuv/workspace/trading/EDGEE/project/pipelines/run_all.py)
- [`project/pipelines/pipeline_planning.py`](/home/tstuv/workspace/trading/EDGEE/project/pipelines/pipeline_planning.py)
- [`project/pipelines/pipeline_execution.py`](/home/tstuv/workspace/trading/EDGEE/project/pipelines/pipeline_execution.py)
- [`project/pipelines/pipeline_provenance.py`](/home/tstuv/workspace/trading/EDGEE/project/pipelines/pipeline_provenance.py)
- [`tests/pipelines/`](/home/tstuv/workspace/trading/EDGEE/tests/pipelines)

### Acceptance Criteria

- `run_all.py` becomes materially smaller and easier to scan.
- Planning, resume, and failure paths remain behaviorally unchanged.
- Existing orchestration tests pass without broad fixture rewrites.

## Phase 5: Harden Service Boundaries

Estimated effort: 3-4 days

### Tasks

- Move any lingering discovery policy decisions behind the discovery service.
- Move any lingering promotion policy or schema stabilization decisions behind the promotion service.
- Reduce direct pipeline-wrapper helper access from callers.
- Ensure service outputs remain typed and report-friendly.

### File Targets

- [`project/research/services/candidate_discovery_service.py`](/home/tstuv/workspace/trading/EDGEE/project/research/services/candidate_discovery_service.py)
- [`project/research/services/promotion_service.py`](/home/tstuv/workspace/trading/EDGEE/project/research/services/promotion_service.py)
- [`project/research/services/reporting_service.py`](/home/tstuv/workspace/trading/EDGEE/project/research/services/reporting_service.py)
- [`project/pipelines/research/`](/home/tstuv/workspace/trading/EDGEE/project/pipelines/research)
- [`tests/pipelines/research/`](/home/tstuv/workspace/trading/EDGEE/tests/pipelines/research)

### Acceptance Criteria

- Pipelines orchestrate services rather than re-implement service logic.
- Discovery and promotion policy logic are each owned in one place.
- Public helper access through wrappers continues to decline.

## Phase 6: Retire Shims and Duplicate Package Surfaces

Estimated effort: 4-7 days

### Tasks

- Remove unused compatibility re-export modules after migration is complete.
- Collapse duplicate strategy-facing package layers where the canonical direction is clear.
- Strengthen removal tests so deleted surfaces do not reappear.
- Refresh public docs to mention only current canonical paths.

### File Targets

- [`project/research/compat/`](/home/tstuv/workspace/trading/EDGEE/project/research/compat)
- [`project/strategy/`](/home/tstuv/workspace/trading/EDGEE/project/strategy)
- [`project/strategy_dsl/`](/home/tstuv/workspace/trading/EDGEE/project/strategy_dsl)
- [`project/strategy_templates/`](/home/tstuv/workspace/trading/EDGEE/project/strategy_templates)
- [`tests/test_legacy_wrapper_packages_removed.py`](/home/tstuv/workspace/trading/EDGEE/tests/test_legacy_wrapper_packages_removed.py)
- [`README.md`](/home/tstuv/workspace/trading/EDGEE/README.md)
- [`docs/README.md`](/home/tstuv/workspace/trading/EDGEE/docs/README.md)

### Acceptance Criteria

- Unused shims are deleted.
- Canonical package surfaces are obvious from imports and docs.
- Removal tests and architecture checks prevent regression.

## Phase 7: Measure and Lock In the New Shape

Estimated effort: 1-2 days

### Tasks

- Recompute architecture metrics after the cleanup.
- Compare before and after counts for compat imports, duplicate surfaces, and oversized modules.
- Add a brief maintenance checklist for future refactors touching contracts, generated docs, and service ownership.

### File Targets

- [`docs/generated/`](/home/tstuv/workspace/trading/EDGEE/docs/generated)
- [`docs/`](/home/tstuv/workspace/trading/EDGEE/docs)
- [`project/tests/test_architectural_integrity.py`](/home/tstuv/workspace/trading/EDGEE/project/tests/test_architectural_integrity.py)

### Acceptance Criteria

- The repo has a clear before/after architecture summary.
- Maintenance guidance exists for future contributors.
- The simplified structure is enforced by tests, not just intent.

## Recommended Execution Order

1. Phase 1
2. Phase 2
3. Phase 3
4. Phase 4
5. Phase 5
6. Phase 6
7. Phase 7

## Ownership

- Platform owner: contracts, orchestration, manifests, generated docs
- Research owner: discovery, promotion, reporting, compat retirement in research
- Architecture owner: dependency rules, CI enforcement, migration tracking

## Risks

- Refactoring orchestration before characterization tests may change behavior silently.
- Shim removal before test and script migration will create noisy breakage.
- Canonical package decisions made too late will cause churn and duplicated migration work.

## Immediate Next Step

Start with Phase 1 and land the contract/doc fix plus generated-artifact regression coverage before any broader structural refactor.
