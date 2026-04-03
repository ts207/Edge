# Testing and maintenance

This document explains how to keep the repo and its documentation coherent.

## Core principle

This repo is guarded by tests that enforce both behavior and architectural shape. Documentation has to stay aligned with those contracts.

## Main verification surfaces

### Canonical validation shortcut

```bash
make validate
```

This is the easiest repo-level gate for day-to-day work.

### Researcher verification

```bash
python -m project.scripts.run_researcher_verification --mode contracts
```

For a completed run:

```bash
python -m project.scripts.run_researcher_verification --mode experiment --run-id <run_id>
```

The detailed contract is documented in [VERIFICATION.md](VERIFICATION.md).

### Minimum green gate

```bash
make minimum-green-gate
```

This exercises a deeper repo-health block that includes compile checks, architecture tests, generated-doc drift checks, selected regressions, and golden workflows.

## Generated-doc maintenance

Generated docs should be rebuilt when the underlying contract or inventory changes.

Important regeneration surfaces include:

```bash
python -m project.scripts.build_system_map
python -m project.scripts.generate_operator_surface_inventory
python -m project.scripts.build_event_contract_artifacts
python -m project.scripts.build_seed_bootstrap_artifacts
# optional explicit thesis context:
# python -m project.scripts.build_seed_bootstrap_artifacts --thesis_run_id <run_id>
python -m project.scripts.build_seed_empirical_artifacts
python -m project.scripts.build_seed_packaging_artifacts
python -m project.scripts.build_thesis_overlap_artifacts --run_id <run_id>
./project/scripts/regenerate_artifacts.sh
```

Use the full regeneration script when multiple inventory surfaces may have drifted together.

## What docs are test-coupled

A few docs are effectively part of the contract surface because tests assert their content or existence.

Examples:

- `README.md`
- `docs/00_START_HERE.md`
- `docs/02_REPOSITORY_MAP.md`
- `docs/operator_command_inventory.md`
- `docs/ARCHITECTURE_SURFACE_INVENTORY.md`
- `docs/ARCHITECTURE_MAINTENANCE_CHECKLIST.md`
- `docs/RESEARCH_CALIBRATION_BASELINE.md`

When editing these, run targeted tests or full validation.

## Maintenance loops by change type

### You changed a proposal or operator surface

Run:

```bash
make validate
python -m project.scripts.generate_operator_surface_inventory
```

Then check:

- `README.md`
- `docs/00_START_HERE.md`
- `docs/03_OPERATOR_WORKFLOW.md`
- `docs/04_COMMANDS_AND_ENTRY_POINTS.md`

### You changed event, ontology, or registry contracts

Run:

```bash
make validate
python -m project.scripts.build_event_contract_artifacts
python -m project.scripts.build_system_map
```

Then check:

- `docs/generated/event_contract_reference.md`
- `docs/02_REPOSITORY_MAP.md`
- `docs/05_ARTIFACTS_AND_INTERPRETATION.md`

### You changed thesis packaging or overlap logic

Run:

```bash
python -m project.research.export_promoted_theses --run_id <run_id>
make package
python -m project.scripts.build_thesis_overlap_artifacts
```

Then check:

- `data/live/theses/index.json`
- `data/live/theses/<run_id>/promoted_theses.json`
- `docs/generated/seed_thesis_catalog.md`
- `docs/generated/seed_thesis_packaging_summary.md`
- `docs/generated/thesis_overlap_graph.md`
- `docs/09_THESIS_BOOTSTRAP_AND_PROMOTION.md`
- `docs/11_LIVE_THESIS_STORE_AND_OVERLAP.md`

### You changed architectural boundaries

Run:

```bash
make validate
python -m project.scripts.build_system_map
```

Then check:

- `docs/ARCHITECTURE_SURFACE_INVENTORY.md`
- `docs/ARCHITECTURE_MAINTENANCE_CHECKLIST.md`
- `docs/generated/system_map.md`

## Documentation maintenance rule

When behavior changes, update the doc that owns the concept instead of adding a new one-off note.

Ownership map:

- repo mental model -> `README.md`, `docs/00_START_HERE.md`, `docs/01_PROJECT_MODEL.md`
- repo structure -> `docs/02_REPOSITORY_MAP.md`
- operator lifecycle -> `docs/03_OPERATOR_WORKFLOW.md`
- command selection -> `docs/04_COMMANDS_AND_ENTRY_POINTS.md`
- artifacts and reports -> `docs/05_ARTIFACTS_AND_INTERPRETATION.md`
- quality and promotion -> `docs/06_QUALITY_GATES_AND_PROMOTION.md`
- packaging lane -> `docs/09_THESIS_BOOTSTRAP_AND_PROMOTION.md`
- runtime thesis consumption -> `docs/11_LIVE_THESIS_STORE_AND_OVERLAP.md`

## Anti-patterns

- updating generated docs manually instead of regenerating them
- creating new planning markdown instead of updating canonical docs
- teaching wrappers instead of canonical surfaces
- changing command behavior without updating the operator docs and README
