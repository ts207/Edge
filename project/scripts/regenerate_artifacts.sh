#!/usr/bin/env bash
set -euo pipefail

# Scripts directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "Regenerating repository artifacts..."

# 1. System Map
echo "[1/3] Regenerating System Map..."
PYTHONPATH="$REPO_ROOT" python3 "$REPO_ROOT/project/scripts/build_system_map.py"

# 2. Detector Coverage Report
echo "[2/3] Regenerating Detector Coverage Report..."
PYTHONPATH="$REPO_ROOT" python3 "$REPO_ROOT/project/scripts/detector_coverage_audit.py" \
    --md-out "$REPO_ROOT/docs/generated/detector_coverage.md" \
    --json-out "$REPO_ROOT/docs/generated/detector_coverage.json"

# 3. Ontology Consistency Audit
echo "[3/3] Regenerating Ontology Audit..."
PYTHONPATH="$REPO_ROOT" python3 "$REPO_ROOT/project/scripts/ontology_consistency_audit.py" \
    --output "$REPO_ROOT/docs/generated/ontology_audit.json"

echo "Artifact regeneration complete."
echo "Please review changes and commit them."
