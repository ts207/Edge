# Edge Agents

Repo-local Codex plugin for the `Edge` repository.

This plugin is aligned to the repository's existing `agents/` workflow rather
than to a separate parallel process.

Included surfaces:

- `skills/edge-repo/` for repo orientation and guardrails
- `skills/edge-coordinator/` for the coordinator playbook
- `skills/edge-analyst/` for completed-run diagnosis
- `skills/edge-mechanism-hypothesis/` for bounded follow-up hypotheses
- `skills/edge-compiler/` for proposal compilation
- `skills/edge-thesis-bootstrap/` for the packaging lane
- `scripts/` for common operator and verification wrappers
- `hooks.json` as a local hook config placeholder

Scripts:

- `scripts/edge_query_knowledge.sh`
- `scripts/edge_preflight_proposal.sh`
- `scripts/edge_plan_proposal.sh`
- `scripts/edge_run_proposal.sh`
- `scripts/edge_verify_contracts.sh`
- `scripts/edge_verify_run.sh`
- `scripts/edge_compare_runs.sh`
- `scripts/edge_show_run_artifacts.sh`
- `scripts/edge_bootstrap_theses.sh`

Active hooks:

- post-write guardrail hook
  - warns on forbidden contract surfaces
  - suggests preflight and plan after proposal edits
  - suggests contract verification after contract-sensitive repo edits
- post-bash run watcher
  - detects fresh run manifests and suggests artifact inspection plus run verification
