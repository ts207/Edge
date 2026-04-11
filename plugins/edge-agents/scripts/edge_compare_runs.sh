#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 2 ] || [ "$#" -gt 3 ]; then
  echo "usage: $0 BASELINE_RUN_ID CANDIDATE_RUN_ID [DATA_ROOT]" >&2
  exit 2
fi

baseline_run_id="$1"
candidate_run_id="$2"
data_root="${3:-}"

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$script_dir/_edge_common.sh"

repo_root="$(edge_repo_root)"
ensure_edge_env "$repo_root"
cd "$repo_root"

cmd=(
  "$repo_root/.venv/bin/edge" catalog compare
  --run_id_a "$baseline_run_id"
  --run_id_b "$candidate_run_id"
  --stage validate
)

if [ -n "$data_root" ]; then
  cmd+=(--data_root "$data_root")
fi

"${cmd[@]}"
