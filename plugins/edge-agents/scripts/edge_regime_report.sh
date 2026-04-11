#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
  echo "usage: $0 RUN_ID [DATA_ROOT]" >&2
  exit 2
fi

run_id="$1"
data_root="${2:-}"

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$script_dir/_edge_common.sh"

repo_root="$(edge_repo_root)"
ensure_edge_env "$repo_root"
cd "$repo_root"

cmd=(
  "$repo_root/.venv/bin/edge" validate report
  --run_id "$run_id"
)

if [ -n "$data_root" ]; then
  cmd+=(--data_root "$data_root")
fi

"${cmd[@]}"
