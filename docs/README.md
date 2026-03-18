# Agent Research Docs

This doc set is the operating manual for repository-native research work.

The intended loop is:

`observe -> retrieve memory -> propose -> run -> evaluate -> reflect -> adapt`

Read `../CLAUDE.md` first when the controlling agent is Claude Code. It defines the current query, proposal,
and execution entrypoints plus the default conservative operating policy.

## Core Reading Path

Read these in order when starting new research work:

1. [Autonomous Research Loop](./AUTONOMOUS_RESEARCH_LOOP.md)
2. [Interaction Protocol](./INTERACTION_PROTOCOL.md)
3. [Experiment Protocol](./EXPERIMENT_PROTOCOL.md)
4. [Artifacts And Contracts](./ARTIFACTS_AND_CONTRACTS.md)
5. [Operations And Guardrails](./OPERATIONS_AND_GUARDRAILS.md)
6. [Memory And Reflection](./MEMORY_AND_REFLECTION.md)
7. [Synthetic Datasets](./SYNTHETIC_DATASETS.md)
8. [Event Families, Templates, Contexts, And Regimes](./FAMILIES_TEMPLATES_AND_REGIMES.md)
9. [Research Workflow Example](./RESEARCH_WORKFLOW_EXAMPLE.md)

## Read By Question

Use these shortcuts when the task is already scoped.

- "What should I do next in a run?" -> [Autonomous Research Loop](./AUTONOMOUS_RESEARCH_LOOP.md)
- "How should I talk to the operator or summarize results?" -> [Interaction Protocol](./INTERACTION_PROTOCOL.md)
- "How should I design or batch an experiment?" -> [Experiment Protocol](./EXPERIMENT_PROTOCOL.md)
- "Which artifacts matter and what can I trust?" -> [Artifacts And Contracts](./ARTIFACTS_AND_CONTRACTS.md)
- "What should stop or gate a run?" -> [Operations And Guardrails](./OPERATIONS_AND_GUARDRAILS.md)
- "What should be remembered or reflected?" -> [Memory And Reflection](./MEMORY_AND_REFLECTION.md)
- "How should synthetic data be used?" -> [Synthetic Datasets](./SYNTHETIC_DATASETS.md)
- "How do families, templates, contexts, and regimes fit together?" -> [Event Families, Templates, Contexts, And Regimes](./FAMILIES_TEMPLATES_AND_REGIMES.md)
- "What does one good research run actually look like end to end?" -> [Research Workflow Example](./RESEARCH_WORKFLOW_EXAMPLE.md)

## Calibration And Maintenance

Use these when the work touches policy defaults, package surfaces, or detector quality history:

- [Research Calibration Baseline](./RESEARCH_CALIBRATION_BASELINE.md)
- [Future Milestones](./FUTURE_MILESTONES.md)
- [Architecture Surface Inventory](./ARCHITECTURE_SURFACE_INVENTORY.md)
- [Architecture Maintenance Checklist](./ARCHITECTURE_MAINTENANCE_CHECKLIST.md)
- [Detector Defect Ledger](./defect_ledger.md)

Relevant layer READMEs also live with the code:

- `project/pipelines/README.md`
- `project/research/README.md`
- `project/contracts/README.md`
- `project/engine/README.md`
- `project/runtime/README.md`

## Generated Diagnostics

The files under `docs/generated/` are machine-owned diagnostics, not authored policy.

Check them after infrastructure edits:

1. `docs/generated/detector_coverage.*` after detector inventory or registry changes
2. `docs/generated/system_map.*` after stage-family, service-boundary, or contract-surface changes

Regenerate them with:

```bash
scripts/regenerate_artifacts.sh
```
