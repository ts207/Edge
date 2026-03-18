from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

from project.scripts import ontology_consistency_audit as audit

def test_ontology_consistency_audit_fail_closed_passes_for_repo_contract():
    repo_root = str(Path(__file__).resolve().parents[2])
    args = [
        "ontology_consistency_audit.py",
        "--repo-root",
        repo_root,
        "--format",
        "json",
        "--fail-on-missing",
    ]
    with patch.object(sys, "argv", args):
        rc = audit.main()
    assert rc == 0
    report = audit.run_audit(Path(__file__).resolve().parents[2])
    counts = report["counts"]
    assert counts["state_registry_materialized_total"] + counts["state_registry_not_materialized_total"] == counts["state_registry_total"]

def test_ontology_consistency_audit_reports_chain_mismatch_failure(tmp_path):
    fake_chain = [("UNKNOWN_EVENT", "missing_script.py", [])]
    with patch.object(audit, "PHASE2_EVENT_CHAIN", fake_chain):
        report = audit.run_audit(Path(__file__).resolve().parents[2])

    failures = report.get("failures", [])
    assert any("chain_entries_with_missing_specs" in item for item in failures)
    assert any("missing_phase2_chain_entries" in item for item in failures)

    output = tmp_path / "audit.json"
    output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    assert output.exists()
