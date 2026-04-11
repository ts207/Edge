---
name: edge-maintainer
description: Route repo changes through the correct validation, generated-doc regeneration, plugin sync, and maintenance commands. Use when the task is developer upkeep, doc drift, plugin upkeep, app-surface maintenance, or figuring out the smallest correct verification loop.
---

# Edge Maintainer

Use this skill for developer maintenance and repo-upkeep work in `/home/irene/Edge`.

## Read first

1. `docs/README.md`
2. `docs/operator_command_inventory.md`
3. `docs/92_assurance_and_benchmarks.md`
4. `Makefile`

## Role

- Route the current change through the smallest correct maintenance loop.
- Prefer canonical repo entrypoints over ad hoc script sequences.
- Regenerate generated docs instead of editing them by hand.
- Keep plugin maintenance thin and repo-aligned.
- Treat `project/tests/` as the only pytest root; `tmp/`, `.tmp/`, `live/persist/`, `artifacts/`, and `logs/` are local-only scratch.

## Primary routing table

### Proposal or operator-surface change

Use:

```bash
make check-hygiene
./plugins/edge-agents/scripts/edge_verify_contracts.sh
./plugins/edge-agents/scripts/edge_validate_repo.sh minimum-green
```

Then inspect:

- `README.md`
- `docs/README.md`
- `docs/00_overview.md`
- `docs/operator_command_inventory.md`

### Event, ontology, or registry change

Use:

```bash
make check-hygiene
./plugins/edge-agents/scripts/edge_verify_contracts.sh
PYTHONPATH=. ./.venv/bin/python -m project.scripts.build_event_contract_artifacts
PYTHONPATH=. ./.venv/bin/python -m project.scripts.build_system_map
```

Then inspect:

- `docs/generated/event_contract_completeness.md`
- `docs/generated/event_tiers.md`
- `docs/02_REPOSITORY_MAP.md`
- `docs/90_architecture.md`

### Runtime-thesis export or overlap change

Use:

```bash
make check-hygiene
./plugins/edge-agents/scripts/edge_verify_contracts.sh
./plugins/edge-agents/scripts/edge_export_theses.sh <run_id>
PYTHONPATH=. ./.venv/bin/python -m project.scripts.build_thesis_overlap_artifacts --run_id <run_id>
```

Then inspect:

- `data/live/theses/<run_id>/promoted_theses.json`
- `data/live/theses/index.json`
- `docs/generated/thesis_overlap_graph.md`
- `docs/03_promote.md`
- `docs/04_deploy.md`

### Architectural boundary change

Use:

```bash
make check-hygiene
./plugins/edge-agents/scripts/edge_verify_contracts.sh
PYTHONPATH=. ./.venv/bin/python -m project.scripts.build_system_map
```

Then inspect:

- `docs/90_architecture.md`
- `docs/02_REPOSITORY_MAP.md`
- `docs/generated/system_map.md`

### Live runtime change (deployment gate, kill switch, audit log, approval contract)

Use:

```bash
make validate
```

Then inspect:

- `project/live/deployment.py` — `DeploymentGate` contract
- `project/live/contracts/deployment_approval.py` — `DeploymentApprovalRecord` schema
- `project/live/audit_log.py` — audit event types and JSONL writer
- `project/live/kill_switch.py` — per-thesis/symbol/family disable/resume controls
- `project/live/contracts/promoted_thesis.py` — `DeploymentState` lifecycle and `LIVE_TRADEABLE_STATES`
- `data/live/audit.jsonl` — append-only live action log (if runtime has run)

Key invariants:
- `ThesisStore.from_path()` enforces `DeploymentGate` at load — violations raise `RuntimeError`
- `live_enabled` requires: `DeploymentApprovalRecord` with `status='approved'`, `approved_by`, `approved_at`, `risk_profile_id`, and configured `cap_profile`
- Kill-switch scope priority: global > symbol > family > thesis

### Plugin change

Use:

```bash
./plugins/edge-agents/scripts/edge_sync_plugin.sh check
./plugins/edge-agents/scripts/edge_sync_plugin.sh sync
```

### Repo-level validation or governance work

Use:

```bash
make check-hygiene
./plugins/edge-agents/scripts/edge_validate_repo.sh contracts
./plugins/edge-agents/scripts/edge_validate_repo.sh minimum-green
./plugins/edge-agents/scripts/edge_governance.sh
```

## ChatGPT app surface

When the task touches `project/apps/chatgpt/`, use:

```bash
./plugins/edge-agents/scripts/edge_chatgpt_app.sh backlog
./plugins/edge-agents/scripts/edge_chatgpt_app.sh blueprint
./plugins/edge-agents/scripts/edge_chatgpt_app.sh widget
./plugins/edge-agents/scripts/edge_chatgpt_app.sh serve --host 127.0.0.1 --port 8000 --path /mcp
```

Treat this as an interface layer around canonical operator surfaces, not a separate runtime.

## Hard rules

- Do not teach wrappers as if they own repo policy.
- Do not manually edit `docs/generated/*` when a generator exists; use `project/scripts/regenerate_artifacts.sh`.
- Do not stop at `make validate` if the change type implies additional regeneration.
- If plugin source changes, remember that the installed plugin cache may still be stale until synced.
