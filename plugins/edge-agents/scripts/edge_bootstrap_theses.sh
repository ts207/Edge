#!/usr/bin/env bash
set -euo pipefail

step="${1:-all}"

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$script_dir/_edge_common.sh"

repo_root="$(edge_repo_root)"
ensure_edge_env "$repo_root"
cd "$repo_root"

run_step() {
  case "$1" in
    seed-bootstrap)
      "$repo_root/.venv/bin/python" -m project.scripts.build_seed_bootstrap_artifacts
      ;;
    seed-testing)
      "$repo_root/.venv/bin/python" -m project.scripts.build_seed_testing_artifacts
      ;;
    seed-empirical)
      "$repo_root/.venv/bin/python" -m project.scripts.build_seed_empirical_artifacts
      ;;
    founding-evidence)
      "$repo_root/.venv/bin/python" -m project.scripts.build_founding_thesis_evidence
      ;;
    seed-packaging)
      "$repo_root/.venv/bin/python" -m project.scripts.build_seed_packaging_artifacts
      ;;
    structural-confirmation)
      "$repo_root/.venv/bin/python" -m project.scripts.build_structural_confirmation_artifacts
      ;;
    thesis-overlap)
      "$repo_root/.venv/bin/python" -m project.scripts.build_thesis_overlap_artifacts
      ;;
    all)
      run_step seed-bootstrap
      run_step seed-testing
      run_step seed-empirical
      run_step founding-evidence
      run_step seed-packaging
      run_step structural-confirmation
      run_step thesis-overlap
      ;;
    *)
      echo "usage: $0 [all|seed-bootstrap|seed-testing|seed-empirical|founding-evidence|seed-packaging|structural-confirmation|thesis-overlap]" >&2
      exit 2
      ;;
  esac
}

run_step "$step"
