import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).parents[2]
# print(f"DEBUG: REPO_ROOT is {REPO_ROOT.absolute()}")
# print(f"DEBUG: SPEC_DIR is {SPEC_DIR.absolute()}")
SPEC_DIR = REPO_ROOT / "spec"
ONTOLOGY_DIR = SPEC_DIR / "ontology"
GRAMMAR_DIR = SPEC_DIR / "grammar"
SEARCH_DIR = SPEC_DIR / "search"


def load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_ontology_events() -> Dict[str, Dict[str, Any]]:
    events = {}
    event_dirs = [SPEC_DIR / "events", ONTOLOGY_DIR / "events"]
    for event_dir in event_dirs:
        if not event_dir.exists():
            continue
        for p in event_dir.glob("*.yaml"):
            spec = load_yaml(p)
            if not isinstance(spec, dict):
                continue
            kind = str(spec.get("kind", "")).strip().lower() if isinstance(spec, dict) else ""
            if kind in {
                "event_unified_registry",
                "canonical_event_registry",
                "event_config_defaults",
                "event_family_defaults",
            }:
                continue
            if not any(str(spec.get(key, "")).strip() for key in ("event_type", "canonical_family")):
                continue
            if not any(str(spec.get(key, "")).strip() for key in ("family", "canonical_family")):
                continue
            event_id = str(spec.get("event_type", p.stem)).strip() or p.stem
            events[event_id] = spec
    return events


def load_ontology_states() -> Dict[str, Dict[str, Any]]:
    states = {}
    state_dirs = [SPEC_DIR / "states", ONTOLOGY_DIR / "states"]
    for state_dir in state_dirs:
        if not state_dir.exists():
            continue
        for p in state_dir.glob("*.yaml"):
            spec = load_yaml(p)
            if not isinstance(spec, dict):
                continue
            kind = str(spec.get("kind", "")).strip().lower() if isinstance(spec, dict) else ""
            if kind in {
                "state_registry",
                "state_family_registry",
                "state_family_defaults",
            }:
                continue
            if not any(str(spec.get(key, "")).strip() for key in ("state_id", "family")):
                continue
            state_id = str(spec.get("state_id", p.stem)).strip() or p.stem
            states[state_id] = spec
    return states


def load_family_registry() -> Dict[str, Any]:
    return load_yaml(GRAMMAR_DIR / "family_registry.yaml")


def load_template_registry() -> Dict[str, Any]:
    return load_yaml(ONTOLOGY_DIR / "templates" / "template_registry.yaml")


def load_search_spec(name: str) -> Dict[str, Any]:
    # e.g. name="phase1" -> spec/search/search_phase1.yaml
    path = SEARCH_DIR / f"search_{name}.yaml"
    if not path.exists():
        # fallback for direct paths
        path = Path(name)
    return load_yaml(path)
