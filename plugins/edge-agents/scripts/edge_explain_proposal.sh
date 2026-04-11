#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 1 ] || [ "$#" -gt 3 ]; then
  echo "usage: $0 PROPOSAL_PATH [REGISTRY_ROOT] [OUT_DIR]" >&2
  exit 2
fi

proposal_path="$1"
registry_root="${2:-project/configs/registries}"
out_dir="${3:-}"

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$script_dir/_edge_common.sh"

repo_root="$(edge_repo_root)"
ensure_edge_env "$repo_root"
cd "$repo_root"

cmd=(
  "$repo_root/.venv/bin/python" -m project.operator.proposal_tools explain
  --proposal "$proposal_path"
  --registry_root "$registry_root"
)

if [ -n "$out_dir" ]; then
  cmd+=(--out_dir "$out_dir")
fi

"${cmd[@]}"
