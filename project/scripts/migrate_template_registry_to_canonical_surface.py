#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import yaml

from project import PROJECT_ROOT


def _load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def main() -> int:
    repo_root = PROJECT_ROOT.parent
    canonical_path = repo_root / "spec" / "templates" / "registry.yaml"
    ontology_path = repo_root / "spec" / "ontology" / "templates" / "template_registry.yaml"
    runtime_path = PROJECT_ROOT / "configs" / "registries" / "templates.yaml"
    lexicon_path = repo_root / "spec" / "hypotheses" / "template_verb_lexicon.yaml"

    canonical = _load_yaml(canonical_path)
    ontology = _load_yaml(ontology_path)
    runtime = _load_yaml(runtime_path)
    lexicon = _load_yaml(lexicon_path)

    runtime_templates = runtime.get("templates", {}) if isinstance(runtime.get("templates"), dict) else {}
    lexicon_operators = lexicon.get("operators", {}) if isinstance(lexicon.get("operators"), dict) else {}
    filter_templates = ontology.get("filter_templates", {}) if isinstance(ontology.get("filter_templates"), dict) else {}

    if filter_templates:
        canonical["filter_templates"] = dict(filter_templates)

    all_names = sorted(
        {
            *(str(name).strip() for name in runtime_templates.keys()),
            *(str(name).strip() for name in lexicon_operators.keys()),
            *(str(name).strip() for name in filter_templates.keys()),
        }
    )
    operators: Dict[str, Dict[str, Any]] = {}
    for name in all_names:
        if not name:
            continue
        payload: Dict[str, Any] = {}
        runtime_row = runtime_templates.get(name, {})
        if isinstance(runtime_row, dict):
            payload.update(runtime_row)
        lexicon_row = lexicon_operators.get(name, {})
        if isinstance(lexicon_row, dict):
            payload.update(lexicon_row)
        filter_row = filter_templates.get(name, {})
        if isinstance(filter_row, dict) and filter_row:
            payload["template_kind"] = "filter_template"
            payload["feature"] = filter_row.get("feature")
            payload["operator"] = filter_row.get("operator")
            payload["threshold"] = filter_row.get("threshold")
        else:
            payload["template_kind"] = "execution_template"
        operators[name] = payload

    canonical["operators"] = operators
    canonical_path.write_text(yaml.safe_dump(canonical, sort_keys=False), encoding="utf-8")
    print(f"Wrote {canonical_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
