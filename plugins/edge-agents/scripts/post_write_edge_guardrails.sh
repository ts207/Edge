#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$script_dir/_edge_common.sh"

repo_root="$(edge_repo_root)"
cd "$repo_root"

mapfile -t changed_files < <(
  {
    git diff --name-only HEAD
    git ls-files --others --exclude-standard
  } | sort -u
)

if [ "${#changed_files[@]}" -eq 0 ]; then
  exit 0
fi

proposal_files=()
forbidden_hits=()
contract_hits=()
operator_hits=()
event_registry_hits=()
packaging_hits=()
live_runtime_hits=()
architecture_hits=()
chatgpt_hits=()
plugin_hits=()
generated_doc_hits=()
doc_coupled_hits=()

for path in "${changed_files[@]}"; do
  case "$path" in
    spec/proposals/*.yaml)
      proposal_files+=("$path")
      ;;
  esac

  case "$path" in
    spec/events/event_registry_unified.yaml|\
    spec/events/regime_routing.yaml|\
    project/contracts/pipeline_registry.py|\
    project/contracts/schemas.py|\
    project/engine/schema.py|\
    project/research/experiment_engine_schema.py|\
    project/strategy/dsl/schema.py|\
    project/strategy/models/executable_strategy_spec.py)
      forbidden_hits+=("$path")
      ;;
  esac

  case "$path" in
    project/*|spec/*|pyproject.toml|pytest.ini|Makefile|requirements-dev.txt)
      contract_hits+=("$path")
      ;;
  esac

  case "$path" in
    project/tests/*)
      contract_hits+=("$path")
      ;;
  esac

  case "$path" in
    Makefile|README.md|docs/README.md|docs/00_overview.md|docs/01_discover.md|docs/02_validate.md|docs/03_promote.md|docs/04_deploy.md|docs/93_trigger_discovery.md|docs/94_discovery_benchmarks.md|docs/operator_command_inventory.md|project/cli.py|project/operator/*|project/research/agent_io/*)
      operator_hits+=("$path")
      ;;
  esac

  case "$path" in
    project/events/*|project/spec_registry/*|project/spec_validation/*|project/configs/registries/*|spec/events/*|spec/ontology/*|spec/states/*|spec/templates/*)
      event_registry_hits+=("$path")
      ;;
  esac

  case "$path" in
    project/portfolio/thesis_overlap.py|project/live/*|project/live/contracts/*|docs/03_promote.md|docs/04_deploy.md|data/live/theses/*)
      packaging_hits+=("$path")
      ;;
  esac

  case "$path" in
    project/live/deployment.py|project/live/audit_log.py|project/live/kill_switch.py|project/live/risk.py|project/live/state.py|project/live/thesis_store.py|project/live/runner.py|project/live/contracts/*)
      live_runtime_hits+=("$path")
      ;;
  esac

  case "$path" in
    project/pipelines/*|project/domain/*|docs/ARCHITECTURE_*|docs/generated/system_map.*)
      architecture_hits+=("$path")
      ;;
  esac

  case "$path" in
    project/apps/chatgpt/*)
      chatgpt_hits+=("$path")
      ;;
  esac

  case "$path" in
    plugins/edge-agents/*|.agents/plugins/marketplace.json)
      plugin_hits+=("$path")
      ;;
  esac

  case "$path" in
    docs/generated/*)
      generated_doc_hits+=("$path")
      ;;
  esac

  case "$path" in
    README.md|docs/README.md|docs/00_overview.md|docs/02_REPOSITORY_MAP.md|docs/90_architecture.md|docs/92_assurance_and_benchmarks.md|docs/operator_command_inventory.md|docs/ARCHITECTURE_SURFACE_INVENTORY.md)
      doc_coupled_hits+=("$path")
      ;;
  esac
done

if [ "${#forbidden_hits[@]}" -gt 0 ]; then
  echo "[edge-hook] Forbidden contract surface touched:"
  printf '  - %s\n' "${forbidden_hits[@]}"
  echo "[edge-hook] Stop and get explicit human approval before continuing."
fi

if [ "${#proposal_files[@]}" -gt 0 ]; then
  echo "[edge-hook] Proposal edit detected:"
  printf '  - %s\n' "${proposal_files[@]}"
  first_proposal="${proposal_files[0]}"
  echo "[edge-hook] Next commands:"
  echo "  ./plugins/edge-agents/scripts/edge_preflight_proposal.sh $first_proposal"
  echo "  ./plugins/edge-agents/scripts/edge_lint_proposal.sh $first_proposal"
  echo "  ./plugins/edge-agents/scripts/edge_explain_proposal.sh $first_proposal"
  echo "  ./plugins/edge-agents/scripts/edge_plan_proposal.sh $first_proposal <run_id>"
fi

if [ "${#contract_hits[@]}" -gt 0 ]; then
  echo "[edge-hook] Contract-sensitive repo change detected."
  echo "[edge-hook] Run:"
  echo "  ./plugins/edge-agents/scripts/edge_verify_contracts.sh"
fi

if [ "${#operator_hits[@]}" -gt 0 ]; then
  echo "[edge-hook] Operator-surface change detected."
  echo "[edge-hook] Maintenance loop:"
  echo "  ./plugins/edge-agents/scripts/edge_validate_repo.sh contracts"
  echo "  ./plugins/edge-agents/scripts/edge_validate_repo.sh minimum-green"
  echo "[edge-hook] Review docs:"
  echo "  README.md"
  echo "  docs/README.md"
  echo "  docs/00_overview.md"
  echo "  docs/operator_command_inventory.md"
fi

if [ "${#event_registry_hits[@]}" -gt 0 ]; then
  echo "[edge-hook] Event / ontology / registry surface change detected."
  echo "[edge-hook] Maintenance loop:"
  echo "  ./plugins/edge-agents/scripts/edge_verify_contracts.sh"
  echo "  PYTHONPATH=. ./.venv/bin/python -m project.scripts.build_event_contract_artifacts"
  echo "  PYTHONPATH=. ./.venv/bin/python -m project.scripts.build_system_map"
  echo "[edge-hook] Review docs:"
  echo "  docs/generated/event_contract_completeness.md"
  echo "  docs/generated/event_tiers.md"
  echo "  docs/02_REPOSITORY_MAP.md"
  echo "  docs/90_architecture.md"
fi

if [ "${#packaging_hits[@]}" -gt 0 ]; then
  echo "[edge-hook] Runtime-thesis / packaging / overlap surface change detected."
  echo "[edge-hook] Maintenance loop:"
  echo "  ./plugins/edge-agents/scripts/edge_verify_contracts.sh"
  echo "  ./plugins/edge-agents/scripts/edge_export_theses.sh <run_id>"
  echo "  PYTHONPATH=. ./.venv/bin/python -m project.scripts.build_thesis_overlap_artifacts --run_id <run_id>"
  echo "[edge-hook] Review docs and artifacts:"
  echo "  data/live/theses/<run_id>/promoted_theses.json"
  echo "  data/live/theses/index.json"
  echo "  docs/generated/thesis_overlap_graph.md"
  echo "  docs/03_promote.md"
  echo "  docs/04_deploy.md"
fi

if [ "${#live_runtime_hits[@]}" -gt 0 ]; then
  echo "[edge-hook] Live runtime contract surface changed:"
  printf '  - %s\n' "${live_runtime_hits[@]}"
  echo "[edge-hook] Key invariants to verify:"
  echo "  - DeploymentGate: ThesisStore.from_path() enforces approval contract at load time"
  echo "  - live_enabled requires: DeploymentApprovalRecord with status='approved', approved_by, approved_at, risk_profile_id, configured cap_profile"
  echo "  - LIVE_TRADEABLE_STATES = {live_enabled} — only this state submits live orders"
  echo "  - Kill-switch scope priority: global > symbol > family > thesis"
  echo "[edge-hook] Run:"
  echo "  make validate"
  echo "[edge-hook] Review:"
  echo "  project/live/contracts/promoted_thesis.py"
  echo "  project/live/deployment.py"
  echo "  project/live/contracts/deployment_approval.py"
  echo "  project/live/audit_log.py"
fi

if [ "${#architecture_hits[@]}" -gt 0 ]; then
  echo "[edge-hook] Architecture-surface change detected."
  echo "[edge-hook] Maintenance loop:"
  echo "  ./plugins/edge-agents/scripts/edge_verify_contracts.sh"
  echo "  PYTHONPATH=. ./.venv/bin/python -m project.scripts.build_system_map"
  echo "[edge-hook] Review docs:"
  echo "  docs/90_architecture.md"
  echo "  docs/02_REPOSITORY_MAP.md"
  echo "  docs/generated/system_map.md"
fi

if [ "${#chatgpt_hits[@]}" -gt 0 ]; then
  echo "[edge-hook] ChatGPT app surface change detected."
  echo "[edge-hook] Useful commands:"
  echo "  edge-chatgpt-app backlog"
  echo "  edge-chatgpt-app blueprint"
  echo "  edge-chatgpt-app widget"
  echo "  edge-chatgpt-app serve --host 127.0.0.1 --port 8000 --path /mcp"
fi

if [ "${#generated_doc_hits[@]}" -gt 0 ]; then
  echo "[edge-hook] Generated-doc files changed."
  echo "[edge-hook] Prefer regeneration over manual edits for the approved tracked docs/generated set:"
  echo "  ./project/scripts/regenerate_artifacts.sh"
fi

if [ "${#doc_coupled_hits[@]}" -gt 0 ]; then
  echo "[edge-hook] Test-coupled docs changed."
  echo "[edge-hook] Run targeted tests or full validation:"
  echo "  make validate"
fi

if [ "${#plugin_hits[@]}" -gt 0 ]; then
  echo "[edge-hook] Plugin surface change detected."
  echo "[edge-hook] Sync and check the installed plugin copy:"
  echo "  ./plugins/edge-agents/scripts/edge_sync_plugin.sh targets"
  echo "  ./plugins/edge-agents/scripts/edge_sync_plugin.sh check"
  echo "  ./plugins/edge-agents/scripts/edge_sync_plugin.sh sync"
fi
