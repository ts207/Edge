from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from project import PROJECT_ROOT


def _load_concept_specs(spec_dir: Path) -> list[tuple[Path, dict[str, Any]]]:
    loaded: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(Path(spec_dir).glob("*.yaml")):
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if payload.get("concept_id"):
            loaded.append((path, payload))
    return loaded


def build_bootstrap_literature_artifacts(
    *,
    spec_dir: Path,
    atlas_path: Path,
    fragments_path: Path,
) -> dict[str, Any]:
    claims: list[dict[str, Any]] = []
    fragments: list[dict[str, Any]] = []

    for path, payload in _load_concept_specs(spec_dir):
        concept_id = str(payload.get("concept_id", "")).strip()
        name = str(payload.get("name", concept_id)).strip()
        definition = str(payload.get("definition", "")).strip()
        metrics = [str(item.get("id", "")).strip() for item in payload.get("metrics", []) if item]
        tests = [str(item.get("id", "")).strip() for item in payload.get("tests", []) if item]
        columns = [
            str(column).strip()
            for req in payload.get("data_requirements", [])
            for column in req.get("columns", []) or []
            if str(column).strip()
        ]
        horizon = next(
            (
                str(req.get("granularity", "")).strip()
                for req in payload.get("data_requirements", [])
                if str(req.get("granularity", "")).strip()
            ),
            "N/A",
        )
        label = next(
            (
                str(test.get("criteria", "")).strip()
                for test in payload.get("tests", [])
                if str(test.get("criteria", "")).strip()
            ),
            "",
        )
        operational_features = list(dict.fromkeys([*metrics, *columns]))
        locator = f"spec/concepts/{path.name}#definition"
        summary_parts = [f"{name}: {definition}"]
        if metrics:
            summary_parts.append(f"Metrics: {', '.join(metrics)}.")
        if tests:
            summary_parts.append(f"Tests: {', '.join(tests)}.")
        text = " ".join(part for part in summary_parts if part).strip()
        fragment_id = f"{concept_id.lower()}_bootstrap_fragment"

        fragments.append(
            {
                "fragment_id": fragment_id,
                "source_id": concept_id,
                "concept_id": concept_id,
                "text": text,
                "locator": locator,
                "strength": "medium",
            }
        )
        claims.append(
            {
                "claim_id": f"{concept_id}_BOOTSTRAP",
                "concept_id": concept_id,
                "claim_type": "mechanistic" if metrics else "heuristic",
                "statement": text,
                "status": "bootstrap_internal",
                "operationalization": {
                    "features": operational_features,
                    "label": label,
                },
                "scope": {
                    "assets": [],
                    "horizon": horizon,
                    "stage": "bootstrap_internal",
                },
                "evidence": [
                    {
                        "locator": locator,
                        "source_id": fragment_id,
                    }
                ],
            }
        )

    atlas_payload = {
        "version": 1,
        "generation_mode": "bootstrap_internal",
        "claims": claims,
    }
    atlas_path.write_text(json.dumps(atlas_payload, indent=2), encoding="utf-8")
    fragments_path.write_text(
        "\n".join(json.dumps(fragment, sort_keys=True) for fragment in fragments) + "\n",
        encoding="utf-8",
    )
    return {
        "atlas_path": atlas_path,
        "fragments_path": fragments_path,
        "claim_count": len(claims),
        "fragment_count": len(fragments),
    }


def main() -> int:
    result = build_bootstrap_literature_artifacts(
        spec_dir=PROJECT_ROOT.parent / "spec" / "concepts",
        atlas_path=PROJECT_ROOT.parent / "knowledge_atlas.json",
        fragments_path=PROJECT_ROOT.parent / "fragments.jsonl",
    )
    print(
        f"Wrote bootstrap literature artifacts: "
        f"{result['claim_count']} claims, {result['fragment_count']} fragments."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
