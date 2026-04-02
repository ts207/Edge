#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 2 ]; then
  echo "usage: $0 BASELINE_RUN_ID CANDIDATE_RUN_ID" >&2
  exit 2
fi

baseline_run_id="$1"
candidate_run_id="$2"

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$script_dir/_edge_common.sh"

repo_root="$(edge_repo_root)"
ensure_edge_env "$repo_root"
cd "$repo_root"

"$repo_root/.venv/bin/python" "$repo_root/project/scripts/compare_research_runs.py" \
  --baseline_run_id "$baseline_run_id" \
  --candidate_run_id "$candidate_run_id"
