---
name: edge-coordinator
description: Coordinate the Edge specialist-agent pipeline using the repo's own coordinator playbook. Use when the user wants an end-to-end bounded research loop, stage discipline, drift checks, or help choosing whether to diagnose, formulate, compile, or bootstrap.
---

# Edge Coordinator

This skill follows `agents/coordinator_playbook.md`.

## Read first

1. `agents/coordinator_playbook.md`
2. `docs/AGENT_CONTRACT.md`
3. `docs/03_OPERATOR_WORKFLOW.md`

## Role

- You are the coordinator.
- Do not delegate coordination.
- Enforce the sequence `analyst -> mechanism_hypothesis -> compiler` for bounded research.
- Use the thesis bootstrap loop only when claims need canonical packaging.

## Required discipline

- Keep one bounded regime-scoped question at a time.
- Prevent scope drift across symbols, dates, templates, trigger families, horizons, regimes, and conditioning axes.
- Reject outputs that widen the original question without justification.
- Stop immediately if the run failed before phase2 or if required files are missing in a way that blocks valid diagnosis.

## Standard bounded research flow

1. Read the proposal and identify the exact bounded claim.
2. Run or inspect preflight and plan output first.
3. Diagnose the completed run with the analyst workflow.
4. Formulate 1-3 frozen hypotheses from the analyst report.
5. Compile only valid hypotheses into repo-native proposal YAML.
6. Review the plan before execution.
7. Execute at most one bounded run at a time.

## Thesis bootstrap flow

Use only when the task is packaging tested claims:

```bash
python -m project.scripts.build_seed_bootstrap_artifacts
python -m project.scripts.build_seed_testing_artifacts
python -m project.scripts.build_seed_empirical_artifacts
python -m project.scripts.build_founding_thesis_evidence
python -m project.scripts.build_seed_packaging_artifacts
python -m project.scripts.build_structural_confirmation_artifacts
python -m project.scripts.build_thesis_overlap_artifacts
```

## Output standard

- Always state the current stage.
- Always state the next bounded action.
- If stopping, say exactly which rule or artifact blocked progress.
