from __future__ import annotations

import json
from pathlib import Path

from project.scripts.build_event_contract_artifacts import build_artifacts
from project.scripts.build_event_ontology_artifacts import build_outputs
from project.scripts.event_ontology_audit import main as audit_main
from project.scripts.event_ontology_audit import render_markdown, run_audit


def test_event_governance_artifacts_build_cleanly_in_temp_dir(
    tmp_path: Path
) -> None:
    out_root = tmp_path / "docs" / "generated"

    contract_outputs = build_artifacts(base_dir=str(out_root))["outputs"]
    for path, content in contract_outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        assert Path(path).read_text(encoding="utf-8") == content

    ontology_outputs = build_outputs(str(out_root))
    for path, content in ontology_outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        assert Path(path).read_text(encoding="utf-8") == content

    assert (
        audit_main(
            [
                "--json-out",
                str(out_root / "event_ontology_audit.json"),
                "--md-out",
                str(out_root / "event_ontology_audit.md"),
            ]
        )
        == 0
    )
    audit_report = run_audit()
    assert (out_root / "event_ontology_audit.json").read_text(encoding="utf-8") == (
        json.dumps(audit_report, indent=2, sort_keys=True) + "\n"
    )
    assert (out_root / "event_ontology_audit.md").read_text(encoding="utf-8") == render_markdown(audit_report)
