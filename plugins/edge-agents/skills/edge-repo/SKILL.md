---
name: edge-repo
description: Use for general work inside the Edge repository when the user has not already narrowed the task to a specialist role. Orients Codex on the repo model, forbidden surfaces, operator commands, and minimum verification before branching into analyst/compiler/mechanism work.
---

# Edge Repo

Use this as the default project skill for `/home/irene/Edge`.

## Read first

1. `CLAUDE.md`
2. `docs/AGENT_CONTRACT.md`
3. `docs/03_OPERATOR_WORKFLOW.md`
4. `docs/04_COMMANDS_AND_ENTRY_POINTS.md`
5. `docs/VERIFICATION.md`

## Core model

- Edge is a governed event-driven crypto research platform.
- Normal progress happens in one of three connected loops:
  - bounded experiment lane: `proposal -> explain -> preflight -> plan -> run -> review -> export`
  - runtime/export loop: `promoted run -> explicit export -> explicit runtime selection`
  - advanced bootstrap lane: `seed inventory -> testing -> empirical evidence -> package -> overlap graph`
- The operating unit is a bounded hypothesis, not a broad discovery brief.
- Sprint 7 live runtime layer: `ThesisStore -> DeploymentGate -> KillSwitchManager -> RiskEnforcer -> OMS`
  - Only `live_enabled` theses may trade; requires a `DeploymentApprovalRecord` with `status='approved'`
  - Deployment lifecycle: `promoted -> paper_enabled -> paper_approved -> live_eligible -> live_enabled`
  - `deployment_state` is the first field to inspect for runtime permission

## Hard guardrails

- Do not edit these surfaces without explicit human approval:
  - `spec/events/event_registry_unified.yaml`
  - `spec/events/regime_routing.yaml`
  - `project/contracts/pipeline_registry.py`
  - `project/contracts/schemas.py`
  - `project/engine/schema.py`
  - `project/research/experiment_engine_schema.py`
  - `project/strategy/dsl/schema.py`
  - `project/strategy/models/executable_strategy_spec.py`
- Do not widen symbols, regimes, templates, detectors, horizons, or date ranges without saying so explicitly.
- Do not treat discovery output as production readiness.
- Do not rescue weak claims by relaxing thresholds or cost assumptions.

## Default command surface

```bash
make discover PROPOSAL=/abs/path/to/proposal.yaml DISCOVER_ACTION=preflight
make discover PROPOSAL=/abs/path/to/proposal.yaml DISCOVER_ACTION=plan
make discover PROPOSAL=/abs/path/to/proposal.yaml DISCOVER_ACTION=run
make review RUN_ID=<run_id> REVIEW_ACTION=diagnose|regime-report
make review REVIEW_ACTION=compare RUN_IDS=<baseline_run,followup_run>
make export RUN_ID=<run_id>
make validate
edge operator lint --proposal /abs/path/to/proposal.yaml
edge operator explain --proposal /abs/path/to/proposal.yaml
edge operator preflight --proposal /abs/path/to/proposal.yaml
edge operator plan --proposal /abs/path/to/proposal.yaml
edge operator run --proposal /abs/path/to/proposal.yaml
edge operator diagnose --run_id <run_id>
edge operator regime-report --run_id <run_id>
edge operator compare --run_ids <baseline_run,followup_run>
./plugins/edge-agents/scripts/edge_export_theses.sh <run_id>
./plugins/edge-agents/scripts/edge_package_theses.sh [thesis_run_id]
.venv/bin/python -m project.scripts.run_researcher_verification --mode contracts
```

## Routing

- If the task is repo maintenance, generated-doc drift, validation routing, or plugin upkeep, use `edge-maintainer`.
- If the task is developing or inspecting `project/apps/chatgpt/`, use `edge-chatgpt-app-developer`.
- If the task is end-to-end research flow control, use `edge-coordinator`.
- If the task is diagnosing a completed run, use `edge-analyst`.
- If the task is turning an analyst report into next hypotheses, use `edge-mechanism-hypothesis`.
- If the task is compiling a frozen hypothesis into proposal YAML and commands, use `edge-compiler`.

## Verification default

- After code, plugin, hook, or config changes, run the contract block from `docs/VERIFICATION.md`.
- After bounded experiment work, run the experiment verification block.
- Keep verification targeted to the surface changed unless the repo contract requires more.
