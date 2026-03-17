# Agent Research Docs

This documentation set is for an autonomous research agent operating inside this repository.

The intended loop is:

`observe -> propose -> run -> evaluate -> reflect -> store memory -> adapt next run`

## Start Here

Read in this order:

1. [Claude Code Guide](../CLAUDE.md)
2. [Autonomous Research Loop](./AUTONOMOUS_RESEARCH_LOOP.md)
3. [Interaction Protocol](./INTERACTION_PROTOCOL.md)
4. [Experiment Protocol](./EXPERIMENT_PROTOCOL.md)
5. [Memory And Reflection](./MEMORY_AND_REFLECTION.md)
6. [Synthetic Datasets](./SYNTHETIC_DATASETS.md)
7. [Artifacts And Contracts](./ARTIFACTS_AND_CONTRACTS.md)
8. [Operations And Guardrails](./OPERATIONS_AND_GUARDRAILS.md)

If the controlling agent is Claude Code, start with `../CLAUDE.md` first. It points at the current proposal, query, and execution entrypoints and the default safe operating policy.

## Architecture And Maintenance Docs

Use these when the work touches package surfaces, contract ownership, or drift policy:

- [Architecture Surface Inventory](./ARCHITECTURE_SURFACE_INVENTORY.md)
- [Research Calibration Baseline](./RESEARCH_CALIBRATION_BASELINE.md)
- [Architecture Maintenance Checklist](./ARCHITECTURE_MAINTENANCE_CHECKLIST.md)

Relevant layer READMEs also live alongside the code:

- `project/pipelines/README.md`
- `project/research/README.md`
- `project/contracts/README.md`
- `project/engine/README.md`
- `project/runtime/README.md`

## Generated Diagnostics

The files under `docs/generated/` are machine-owned diagnostics, not policy documents.

Current generated artifacts worth checking after infrastructure edits:

1. `docs/generated/detector_coverage.*` after detector registry or ownership changes
2. `docs/generated/system_map.*` after stage, service, or contract-surface changes

Regenerate them with:

```bash
scripts/regenerate_artifacts.sh
```

Agent-driven synthetic research should read `SYNTHETIC_DATASETS.md` before running discovery on generated data.
