# Testing and maintenance

This document explains how to keep the repo and the docs aligned with the actual contracts.

## Default verification surface

Use:

```bash
make validate
```

That is the shortest repo-level gate for normal maintenance.

## Researcher verification

Contract block:

```bash
python -m project.scripts.run_researcher_verification --mode contracts
```

Experiment block:

```bash
python -m project.scripts.run_researcher_verification --mode experiment --run-id <run_id>
```

Use the experiment block after a completed run or after a fix that was triggered by one specific run.

## Minimum green gate

Use:

```bash
make minimum-green-gate
```

This is deeper than day-to-day validation and is appropriate when you changed architecture, command surfaces, or broader repo contracts.

## What changes require which checks

### You changed proposal loading, operator flow, or front-door docs

Run:

```bash
make validate
python -m project.scripts.generate_operator_surface_inventory
```

Then inspect:

- `README.md`
- `docs/00_START_HERE.md`
- `docs/03_OPERATOR_WORKFLOW.md`
- `docs/04_COMMANDS_AND_ENTRY_POINTS.md`
- `docs/operator_command_inventory.md`

### You changed thesis export or runtime-facing thesis handling

Run:

```bash
make validate
python -m project.research.export_promoted_theses --run_id <run_id>
python -m project.scripts.build_thesis_overlap_artifacts --run_id <run_id>
```

Then inspect:

- `data/live/theses/<run_id>/promoted_theses.json`
- `data/live/theses/index.json`
- `docs/generated/thesis_overlap_graph.md`
- `docs/11_LIVE_THESIS_STORE_AND_OVERLAP.md`

### You changed advanced bootstrap/package surfaces

Run:

```bash
make validate
make package
./project/scripts/regenerate_artifacts.sh
```

Then inspect:

- `docs/09_THESIS_BOOTSTRAP_AND_PROMOTION.md`
- bootstrap-maintenance generated docs under `docs/generated/`

### You changed architecture boundaries or doc ownership

Run:

```bash
make validate
python -m project.scripts.build_system_map
```

Then inspect:

- `docs/ARCHITECTURE_SURFACE_INVENTORY.md`
- `docs/ARCHITECTURE_MAINTENANCE_CHECKLIST.md`
- `docs/generated/system_map.md`

## Generated-doc maintenance

Generated docs should be regenerated, not hand-edited.

Important generators:

```bash
python -m project.scripts.build_system_map
python -m project.scripts.generate_operator_surface_inventory
python -m project.scripts.build_event_contract_artifacts
python -m project.scripts.build_seed_bootstrap_artifacts
python -m project.scripts.build_seed_empirical_artifacts
python -m project.scripts.build_seed_packaging_artifacts
python -m project.scripts.build_thesis_overlap_artifacts --run_id <run_id>
./project/scripts/regenerate_artifacts.sh
```

## Canonical doc ownership

- repo orientation: `README.md`, `docs/00_START_HERE.md`
- stable model: `docs/01_PROJECT_MODEL.md`
- operator loop: `docs/03_OPERATOR_WORKFLOW.md`
- command selection: `docs/04_COMMANDS_AND_ENTRY_POINTS.md`
- artifact interpretation: `docs/05_ARTIFACTS_AND_INTERPRETATION.md`
- quality and permission: `docs/06_QUALITY_GATES_AND_PROMOTION.md`
- advanced bootstrap lane: `docs/09_THESIS_BOOTSTRAP_AND_PROMOTION.md`
- runtime thesis model: `docs/11_LIVE_THESIS_STORE_AND_OVERLAP.md`

When behavior changes, update the owner doc instead of adding a one-off note elsewhere.

## Anti-patterns

- editing generated docs by hand
- changing command behavior without updating the owning canonical doc
- teaching low-level wrappers before the operator surface
- leaving legacy or bootstrap surfaces undocumented as advanced/internal after a behavior change
