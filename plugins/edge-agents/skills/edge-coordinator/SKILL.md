---
name: edge-coordinator
description: Coordinate the Edge specialist-agent pipeline using the repo's own coordinator playbook. Use when the user wants an end-to-end bounded research loop, stage discipline, drift checks, or help choosing whether to diagnose, formulate, compile, or bootstrap.
---

# Edge Coordinator

Use this skill to coordinate bounded research work without inventing a parallel workflow.

## Read first

1. `docs/00_overview.md`
2. `docs/01_discover.md`
3. `docs/02_validate.md`
4. `docs/03_promote.md`
5. `docs/04_deploy.md`
6. `docs/operator_command_inventory.md`

## Role

- You are the coordinator.
- Do not delegate coordination.
- Enforce the sequence `analyst -> mechanism_hypothesis -> compiler` for bounded research.
- Use explicit run export when the goal is a runtime batch from one run.
- Use the thesis bootstrap loop only when claims need broader packaging maintenance.

## Required discipline

- Keep one bounded regime-scoped question at a time.
- Prevent scope drift across symbols, dates, templates, trigger families, horizons, regimes, and conditioning axes.
- Reject outputs that widen the original question without justification.
- Stop immediately if the run failed before phase2 or if required files are missing in a way that blocks valid diagnosis.

## Standard bounded research flow

1. Read the proposal and identify the exact bounded claim.
2. Run or inspect preflight plus lint/explain output first.
3. Run or inspect the validated plan before any execution.
4. Execute at most one bounded run at a time.
5. Diagnose the completed run with the analyst workflow.
6. Use `regime-report` or bounded `compare` when stability or confirmation matters.
7. Formulate 1-3 frozen hypotheses from the analyst report.
8. Compile only valid hypotheses into repo-native proposal YAML.
9. Review lint/explain/plan again before any follow-up execution.

## Thesis bootstrap flow

Use export first when the goal is runtime input from a specific run:

```bash
./plugins/edge-agents/scripts/edge_export_theses.sh <run_id>
```

Use the advanced bootstrap flow only when the task is broader packaging work:

```bash
python -m project.scripts.build_seed_bootstrap_artifacts
python -m project.scripts.build_seed_testing_artifacts
python -m project.scripts.build_seed_empirical_artifacts
python -m project.scripts.build_founding_thesis_evidence
python -m project.scripts.build_seed_packaging_artifacts
python -m project.scripts.build_structural_confirmation_artifacts
python -m project.scripts.build_thesis_overlap_artifacts --run_id <run_id>
```

## Deployment permission model (Sprint 7)

Export does not equal live trading permission. When a run is exported, check `deployment_state` before answering "can this trade live?".

State lifecycle: `promoted -> paper_enabled -> paper_approved -> live_eligible -> live_enabled`

Legacy states (`monitor_only`, `paper_only`) are kept for backward compat.

Key rules:
- Only `live_enabled` may submit live orders (`LIVE_TRADEABLE_STATES = {"live_enabled"}`)
- `live_eligible` and `live_enabled` both require a `DeploymentApprovalRecord` with `status='approved'`
- `ThesisStore.from_path()` enforces `DeploymentGate` at load time — a load failure is a contract violation
- `deployment_mode_allowed` on the thesis is the operator-set ceiling; thesis cannot exceed it
- Kill-switch granularity: global, per-symbol, per-family, per-thesis — inspect `KillSwitchManager.is_thesis_blocked()`

## Output standard

- Always state the current stage.
- Always state the next bounded action.
- If stopping, say exactly which rule or artifact blocked progress.
