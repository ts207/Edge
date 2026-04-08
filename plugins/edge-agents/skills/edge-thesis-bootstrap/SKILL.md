---
name: edge-thesis-bootstrap
description: Run the Edge thesis bootstrap lane using the documented packaging sequence. Use when the task is converting tested claims into canonical thesis artifacts, scorecards, packaged theses, and overlap outputs rather than running another discovery experiment.
---

# Edge Thesis Bootstrap

Use this skill for the packaging lane, not for raw discovery.

## Read first

1. `docs/03_promote.md`
2. `docs/04_deploy.md`
3. `docs/operator_command_inventory.md`
4. `docs/92_assurance_and_benchmarks.md`
5. `docs/README.md`

## Preferred front door

- Use explicit run export when the goal is a runtime thesis batch from one run.
- Use `make package` or the plugin package wrapper only for the advanced packaging lane.
- Use the underlying script sequence only when repairing or inspecting a specific packaging block.

Canonical run-export bridge:

```bash
./plugins/edge-agents/scripts/edge_export_theses.sh <run_id>
```

## Canonical sequence

```bash
./plugins/edge-agents/scripts/edge_package_theses.sh [thesis_run_id]
python -m project.scripts.build_seed_bootstrap_artifacts
python -m project.scripts.build_seed_testing_artifacts
python -m project.scripts.build_seed_empirical_artifacts
python -m project.scripts.build_founding_thesis_evidence
python -m project.scripts.build_seed_packaging_artifacts
python -m project.scripts.build_structural_confirmation_artifacts
python -m project.scripts.build_thesis_overlap_artifacts --run_id <run_id>
./project/scripts/regenerate_artifacts.sh
```

## Required review surfaces

- `docs/generated/promotion_seed_inventory.*`
- `docs/generated/thesis_testing_scorecards.*`
- `docs/generated/thesis_empirical_scorecards.*`
- `docs/generated/founding_thesis_evidence_summary.*`
- `docs/generated/seed_thesis_packaging_summary.*`
- `docs/generated/thesis_overlap_graph.*`
- `data/live/theses/index.json`

## Deployment state lifecycle (Sprint 7)

```
promoted -> paper_enabled -> paper_approved -> live_eligible -> live_enabled
```

Legacy states `monitor_only` and `paper_only` are preserved for backward compat.

- `LIVE_TRADEABLE_STATES = {"live_enabled"}` — only this state may submit live orders
- `LIVE_APPROVAL_REQUIRED_STATES = {"live_eligible", "live_enabled"}` — both require a `DeploymentApprovalRecord`
- `deployment_mode_allowed` is the operator-set ceiling on the thesis
- `ThesisStore.from_path()` enforces `DeploymentGate` automatically at load time

## Hard rules

- Do not describe `seed_promoted` as production-ready.
- Regenerate overlap artifacts after packaging changes.
- Treat bootstrap artifacts as authoritative over hand-written notes.
- `live_eligible` and `live_enabled` both require a `DeploymentApprovalRecord` with `status='approved'` before `ThesisStore` will load them.
- Do not manually set `deployment_state=live_enabled` without a valid approval record and configured `cap_profile`.
