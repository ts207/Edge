# Edge Documentation Index

This documentation set describes the current repository as it exists today.

The hand-authored docs explain intent, structure, and workflow. The generated docs in `docs/generated/` are the live inventory and audit surfaces. When hand-authored narrative and generated inventory disagree, trust the generated artifacts and then inspect code.

## Document Map

| File | Scope | Use It For |
| --- | --- | --- |
| `00_INDEX.md` | navigation | finding the right doc quickly |
| `01_PROJECT_OVERVIEW.md` | system purpose and operating model | understanding what Edge is for |
| `02_ARCHITECTURE.md` | runtime and package architecture | tracing control flow and ownership |
| `03_COMPONENT_REFERENCE.md` | package-level responsibilities | orienting within `project/` |
| `04_SPEC_AND_ONTOLOGY.md` | YAML spec layer and ontology/routing | understanding event and template legality |
| `05_DEPENDENCIES_AND_STACK.md` | Python stack, storage, tooling, CI | setup and maintenance |
| `06_OPERATOR_WORKFLOW.md` | proposal-driven research loop | running bounded experiments |
| `07_DATA_FLOW_AND_CONTRACTS.md` | artifacts, manifests, stage contracts | debugging pipeline correctness |
| `08_ENTRY_POINTS_AND_CLI.md` | console scripts, `make`, scripts | knowing what to run |
| `09_RESEARCH_CONCEPTS_AND_HYPOTHESES.md` | research primitives and evaluation | designing good runs |
| `10_TESTING_AND_QUALITY.md` | local and CI quality gates | knowing what "green" means |
| `ARCHITECTURE_SURFACE_INVENTORY.md` | architecture surface summary | fast orientation |
| `ARCHITECTURE_MAINTENANCE_CHECKLIST.md` | maintenance checklist | regeneration and drift workflows |
| `RESEARCH_CALIBRATION_BASELINE.md` | regression baseline notes | comparing research drift tolerances |

## Generated Docs

`docs/generated/` is the live source of truth for current inventory and audit outputs.

Use:

- `system_map.{md,json}` for generated system inventory
- `detector_coverage.{md,json}` for detector inventory and warnings
- `ontology_audit.json` for ontology consistency drift
- `event_ontology_mapping.{md,json}` for canonical mapping
- `canonical_to_raw_event_map.{md,json}` for executable crosswalks
- `event_ontology_audit.{md,json}` for event ontology health
- `regime_routing_audit.{md,json}` for canonical regime routing validity
- `architecture_metrics.json` for generated metrics

Do not hand-edit those files.

## Quick Navigation

If you need to:

- run a bounded research experiment
  - read `06_OPERATOR_WORKFLOW.md`
- understand the current command surface
  - read `08_ENTRY_POINTS_AND_CLI.md`
- understand stage ordering and contracts
  - read `07_DATA_FLOW_AND_CONTRACTS.md`
- understand how specs, ontology, and routing fit together
  - read `04_SPEC_AND_ONTOLOGY.md`
- understand package responsibilities
  - read `03_COMPONENT_REFERENCE.md`
- understand what CI and local "green" mean
  - read `10_TESTING_AND_QUALITY.md`

## Hard Invariants

These rules are stable across the repository:

1. Artifacts beat impressions.
2. Exit codes are not enough.
3. `plan_only` comes before material execution.
4. Synthetic evidence is calibration evidence, not live profitability evidence.
5. Promotion is a gate, not a reward.
6. Narrow attribution is preferred over broad simultaneous search.
7. Generated docs are inventory outputs, not narrative documentation.
8. Stage and artifact contracts live in code, not prose.
9. Replay and determinism checks are first-class quality surfaces.
10. A good run leaves a clear next action.

## Repo Summary

Core repository layers:

- `project/`
  - Python implementation
- `spec/`
  - domain specs and policy
- `project/configs/`
  - workflow and runtime configs
- `docs/`
  - hand-authored docs
- `docs/generated/`
  - generated inventories and audits
- `data/` and `artifacts/`
  - runtime outputs

The canonical pipeline entry point is `project/pipelines/run_all.py`.
