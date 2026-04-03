#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "Regenerating repository artifacts..."

echo "[registry] Rebuilding unified event registry..."
PYTHONPATH="$REPO_ROOT" python3 "$REPO_ROOT/project/scripts/build_unified_event_registry.py"

echo "[templates] Regenerating template registry sidecars..."
PYTHONPATH="$REPO_ROOT" python3 "$REPO_ROOT/project/scripts/build_template_registry_sidecars.py"

echo "[states] Regenerating state registry sidecars..."
PYTHONPATH="$REPO_ROOT" python3 "$REPO_ROOT/project/scripts/build_state_registry_sidecars.py"

echo "[regimes] Regenerating regime registry sidecars..."
PYTHONPATH="$REPO_ROOT" python3 "$REPO_ROOT/project/scripts/build_regime_registry_sidecars.py"

echo "[domain] Rebuilding compiled domain graph..."
PYTHONPATH="$REPO_ROOT" python3 "$REPO_ROOT/project/scripts/build_domain_graph.py"

echo "[runtime] Regenerating runtime event registry..."
PYTHONPATH="$REPO_ROOT" python3 "$REPO_ROOT/project/scripts/build_runtime_event_registry.py"

echo "[sidecars] Regenerating compatibility sidecars..."
PYTHONPATH="$REPO_ROOT" python3 "$REPO_ROOT/project/scripts/build_canonical_registry_sidecars.py"

echo "[0/13] Regenerating Event Governance Artifacts..."
PYTHONPATH="$REPO_ROOT" python3 "$REPO_ROOT/project/scripts/build_event_contract_artifacts.py"
PYTHONPATH="$REPO_ROOT" python3 "$REPO_ROOT/project/scripts/event_ontology_audit.py"
PYTHONPATH="$REPO_ROOT" python3 "$REPO_ROOT/project/scripts/build_event_ontology_artifacts.py"
PYTHONPATH="$REPO_ROOT" python3 "$REPO_ROOT/project/scripts/build_event_deep_analysis_suite.py"

echo "[1/13] Regenerating Thesis Bootstrap Artifacts..."
PYTHONPATH="$REPO_ROOT" python3 "$REPO_ROOT/project/scripts/build_seed_bootstrap_artifacts.py"

echo "[2/13] Building Founding Thesis Evidence Bundles..."
PYTHONPATH="$REPO_ROOT" python3 "$REPO_ROOT/project/scripts/build_founding_thesis_evidence.py"

echo "[3/13] Regenerating Thesis Testing Artifacts..."
PYTHONPATH="$REPO_ROOT" python3 "$REPO_ROOT/project/scripts/build_seed_testing_artifacts.py"

echo "[4/13] Regenerating Structural Confirmation Bridge Artifacts..."
PYTHONPATH="$REPO_ROOT" python3 "$REPO_ROOT/project/scripts/build_structural_confirmation_artifacts.py"

echo "[5/13] Regenerating Empirical Thesis Artifacts..."
PYTHONPATH="$REPO_ROOT" python3 "$REPO_ROOT/project/scripts/build_seed_empirical_artifacts.py"

echo "[6/13] Regenerating Seed Thesis Packaging Artifacts..."
PYTHONPATH="$REPO_ROOT" python3 "$REPO_ROOT/project/scripts/build_seed_packaging_artifacts.py"

echo "[7/13] Regenerating Thesis Overlap Artifacts..."
PYTHONPATH="$REPO_ROOT" python3 "$REPO_ROOT/project/scripts/build_thesis_overlap_artifacts.py"

echo "[8/13] Regenerating paired-event studies for packaged confirmation theses..."
PYTHONPATH="$REPO_ROOT" python3 "$REPO_ROOT/project/scripts/build_paired_event_study.py" \
  --candidate-id THESIS_VOL_SHOCK_LIQUIDITY_CONFIRM
PYTHONPATH="$REPO_ROOT" python3 "$REPO_ROOT/project/scripts/build_paired_event_study.py" \
  --candidate-id THESIS_LIQUIDITY_VACUUM_CASCADE_CONFIRM

echo "[9/13] Regenerating integrated Block H overlap + shadow-live artifacts..."
PYTHONPATH="$REPO_ROOT" python3 "$REPO_ROOT/project/scripts/run_block_h.py"

echo "[10/13] Regenerating System Map..."
PYTHONPATH="$REPO_ROOT" python3 "$REPO_ROOT/project/scripts/build_system_map.py"

echo "[11/13] Regenerating Detector Coverage Report..."
PYTHONPATH="$REPO_ROOT" python3 "$REPO_ROOT/project/scripts/detector_coverage_audit.py" \
    --md-out "$REPO_ROOT/docs/generated/detector_coverage.md" \
    --json-out "$REPO_ROOT/docs/generated/detector_coverage.json"

echo "[12/13] Regenerating Ontology Audit..."
PYTHONPATH="$REPO_ROOT" python3 "$REPO_ROOT/project/scripts/ontology_consistency_audit.py" \
    --output "$REPO_ROOT/docs/generated/ontology_audit.json"

echo "[13/13] Verifying latest thesis store loads cleanly..."
PYTHONPATH="$REPO_ROOT" python3 - <<'PY'
from project.live.thesis_store import ThesisStore
store = ThesisStore.latest()
print(f"Loaded {len(store.all())} theses from latest run_id={store.run_id}")
PY

echo "Artifact regeneration complete."
echo "Please review changes and commit them."
