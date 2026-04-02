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
    project/*|spec/*|tests/*|pyproject.toml|pytest.ini|Makefile|requirements-dev.txt)
      contract_hits+=("$path")
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
  echo "  ./plugins/edge-agents/scripts/edge_plan_proposal.sh $first_proposal <run_id>"
fi

if [ "${#contract_hits[@]}" -gt 0 ]; then
  echo "[edge-hook] Contract-sensitive repo change detected."
  echo "[edge-hook] Run:"
  echo "  ./plugins/edge-agents/scripts/edge_verify_contracts.sh"
fi
