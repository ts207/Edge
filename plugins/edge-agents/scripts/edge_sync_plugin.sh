#!/usr/bin/env bash
set -euo pipefail

mode="${1:-sync}"
target_dir="${2:-}"

usage() {
  echo "usage: $0 [targets|sync|check] [target_dir]" >&2
  exit 2
}

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$script_dir/_edge_common.sh"

repo_root="$(edge_repo_root)"
source_dir="$repo_root/plugins/edge-agents"

if [ ! -d "$source_dir" ]; then
  echo "missing plugin source: $source_dir" >&2
  exit 1
fi

default_target="${CODEX_HOME:-$HOME/.codex}/plugins/cache/edge-local/edge-agents/local"

discover_targets() {
  local -a raw_targets=()
  local cache_root
  local path

  if [ -n "$target_dir" ]; then
    raw_targets+=("$target_dir")
  else
    raw_targets+=("$default_target")
    cache_root="${CODEX_HOME:-$HOME/.codex}/plugins/cache"
    if [ -d "$cache_root" ]; then
      while IFS= read -r path; do
        raw_targets+=("$path")
      done < <(find "$cache_root" -type d -path '*/edge-agents/local' 2>/dev/null | sort)
    fi
  fi

  awk '!seen[$0]++' < <(printf '%s\n' "${raw_targets[@]}")
}

check_target() {
  local current_target="$1"
  if [ ! -d "$current_target" ]; then
    echo "missing plugin target: $current_target" >&2
    return 1
  fi
  if diff -qr --exclude='*.Zone.Identifier' "$source_dir" "$current_target"; then
    echo "plugin source and installed target match: $current_target"
    return 0
  fi
  return 1
}

sync_target() {
  local current_target="$1"
  local parent_dir
  local tmp_dir

  parent_dir="$(dirname "$current_target")"
  mkdir -p "$parent_dir"
  tmp_dir="$(mktemp -d "$parent_dir/.edge-agents-sync.XXXXXX")"
  cp -R "$source_dir"/. "$tmp_dir"/
  find "$tmp_dir" -name '*.Zone.Identifier' -delete
  rm -rf "$current_target"
  mv "$tmp_dir" "$current_target"
  echo "synced plugin source to: $current_target"
}

case "$mode" in
  targets)
    discover_targets
    ;;
  check|sync)
    mapfile -t targets < <(discover_targets)
    if [ "${#targets[@]}" -eq 0 ]; then
      echo "no plugin targets found" >&2
      exit 1
    fi
    status=0
    for current_target in "${targets[@]}"; do
      if [ "$mode" = "check" ]; then
        if ! check_target "$current_target"; then
          status=1
        fi
      else
        sync_target "$current_target"
      fi
    done
    exit "$status"
    ;;
  *)
    usage
    ;;
esac
