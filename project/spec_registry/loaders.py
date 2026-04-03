from __future__ import annotations

import copy
import functools
import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping

import yaml

from project import PROJECT_ROOT
from project.spec_registry.policy import _DEFAULT_BLUEPRINT_POLICY

REPO_ROOT = PROJECT_ROOT.parent
SPEC_ROOT = REPO_ROOT / "spec"

ONTOLOGY_SPEC_RELATIVE_PATHS: Dict[str, str] = {
    "taxonomy": "spec/multiplicity/taxonomy.yaml",
    "canonical_event_registry": "spec/events/canonical_event_registry.yaml",
    "state_registry": "spec/states/state_registry.yaml",
    "thesis_registry": "spec/theses/thesis_registry.yaml",
    "template_verb_lexicon": "spec/hypotheses/template_verb_lexicon.yaml",
    "domain_graph": "spec/domain/domain_graph.yaml",
}

RUNTIME_SPEC_RELATIVE_PATHS: Dict[str, str] = {
    "lanes": "spec/runtime/lanes.yaml",
    "firewall": "spec/runtime/firewall.yaml",
    "hashing": "spec/runtime/hashing.yaml",
}


def repo_root() -> Path:
    return REPO_ROOT


def spec_root() -> Path:
    return SPEC_ROOT


def _read_yaml(path: Path, required: bool = True) -> Dict[str, Any]:
    if not path.exists():
        if required:
            raise FileNotFoundError(f"Spec file missing: {path}")
        return {}
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"Failed to parse YAML spec {path}: {exc}") from exc
    if not isinstance(payload, dict) and payload is not None:
         # Some YAML files might be empty or just a list, but our loaders expect dicts
         if required:
             raise ValueError(f"Spec file {path} must be a dictionary, got {type(payload)}")
    return payload if isinstance(payload, dict) else {}


def _deep_merge(base: Mapping[str, Any], override: Mapping[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = copy.deepcopy(dict(base))
    for key, value in dict(override).items():
        if isinstance(value, Mapping) and isinstance(out.get(key), Mapping):
            out[str(key)] = _deep_merge(dict(out[key]), dict(value))
        else:
            out[str(key)] = copy.deepcopy(value)
    return out


def resolve_relative_spec_path(relative_path: str | Path, repo_root: Path | None = None) -> Path:
    rel = Path(relative_path)
    base = Path(repo_root).resolve() if repo_root is not None else REPO_ROOT
    return (base / rel).resolve()


@functools.lru_cache(maxsize=None)
def load_yaml_relative(relative_path: str) -> Dict[str, Any]:
    return _read_yaml(resolve_relative_spec_path(relative_path))


def load_yaml_path(path: str | Path) -> Dict[str, Any]:
    return _read_yaml(Path(path))


@functools.lru_cache(maxsize=1)
def load_gates_spec() -> Dict[str, Any]:
    return load_yaml_relative("spec/gates.yaml")


@functools.lru_cache(maxsize=1)
def load_family_specs() -> Dict[str, Any]:
    return load_yaml_relative("spec/multiplicity/families.yaml")


def load_family_spec(family_id: str) -> Dict[str, Any]:
    payload = load_family_specs()
    families = payload.get("families", {}) if isinstance(payload, dict) else {}
    if not isinstance(families, dict):
        return {}
    row = families.get(family_id, {})
    return dict(row) if isinstance(row, dict) else {}


@functools.lru_cache(maxsize=1)
def load_unified_event_registry() -> Dict[str, Any]:
    return load_yaml_relative("spec/events/event_registry_unified.yaml")


@functools.lru_cache(maxsize=1)
def load_event_ontology_mapping() -> Dict[str, Any]:
    return load_yaml_relative("spec/events/event_ontology_mapping.yaml")


@functools.lru_cache(maxsize=1)
def load_template_registry() -> Dict[str, Any]:
    unified = load_unified_event_registry()
    if unified:
        return unified
    return load_yaml_relative("spec/templates/event_template_registry.yaml")


@functools.lru_cache(maxsize=1)
def load_state_registry() -> Dict[str, Any]:
    return load_yaml_relative("spec/states/state_registry.yaml")


@functools.lru_cache(maxsize=1)
def load_thesis_registry() -> Dict[str, Any]:
    return load_yaml_relative("spec/theses/thesis_registry.yaml")


@functools.lru_cache(maxsize=1)
def load_event_contract_overrides() -> Dict[str, Any]:
    return load_yaml_relative("spec/events/event_contract_overrides.yaml")


@functools.lru_cache(maxsize=None)
def load_runtime_spec(name: str) -> Dict[str, Any]:
    normalized = str(name).strip().lower()
    if not normalized:
        return {}
    return load_yaml_relative(f"spec/runtime/{normalized}.yaml")


@functools.lru_cache(maxsize=1)
def load_blueprint_policy_spec(policy_path: str | None = None) -> Dict[str, Any]:
    if policy_path:
        raw = load_yaml_path(Path(policy_path).resolve())
    else:
        raw = load_yaml_relative("spec/blueprint_policies.yaml")
    return _deep_merge(_DEFAULT_BLUEPRINT_POLICY, raw)


def _safe_objective(payload: object) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    raw = payload.get("objective", payload)
    if not isinstance(raw, dict):
        return {}
    out = dict(raw)
    if not isinstance(out.get("score_weights"), dict):
        out["score_weights"] = {}
    if not isinstance(out.get("hard_gates"), dict):
        out["hard_gates"] = {}
    if not isinstance(out.get("constraints"), dict):
        out["constraints"] = {}
    return out


def _safe_profiles(payload: object) -> Dict[str, Dict[str, Any]]:
    if not isinstance(payload, dict):
        return {}
    raw_profiles = payload.get("profiles", payload)
    if not isinstance(raw_profiles, dict):
        return {}
    out: Dict[str, Dict[str, Any]] = {}
    for name, cfg in raw_profiles.items():
        key = str(name).strip()
        if key and isinstance(cfg, dict):
            out[key] = dict(cfg)
    return out


def load_objective_spec(
    *,
    objective_name: str = "retail_profitability",
    explicit_path: str | Path | None = None,
    required: bool = False,
) -> Dict[str, Any]:
    resolved_name = str(objective_name).strip() or "retail_profitability"
    candidates: list[Path] = []
    if explicit_path:
        candidates.append(Path(explicit_path))
    env_path = str(os.getenv("BACKTEST_OBJECTIVE_SPEC_PATH", "")).strip()
    if env_path:
        candidates.append(Path(env_path))
    candidates.append(SPEC_ROOT / "objectives" / f"{resolved_name}.yaml")
    for path in candidates:
        if path.exists():
            loaded = _safe_objective(_read_yaml(path))
            if loaded:
                loaded.setdefault("id", resolved_name)
            return loaded
    if required:
        raise FileNotFoundError(
            "Unable to locate objective spec. Checked: " + ", ".join(str(p) for p in candidates)
        )
    return {}


def load_retail_profiles_spec(
    *, explicit_path: str | Path | None = None, required: bool = False
) -> Dict[str, Dict[str, Any]]:
    candidates: list[Path] = []
    if explicit_path:
        candidates.append(Path(explicit_path))
    env_path = str(os.getenv("BACKTEST_RETAIL_PROFILES_PATH", "")).strip()
    if env_path:
        candidates.append(Path(env_path))
    candidates.append(PROJECT_ROOT / "configs" / "retail_profiles.yaml")
    for path in candidates:
        if path.exists():
            profiles = _safe_profiles(_read_yaml(path))
            if profiles:
                return profiles
    if required:
        raise FileNotFoundError(
            "Unable to locate retail profile spec. Checked: "
            + ", ".join(str(p) for p in candidates)
        )
    return {}


def load_retail_profile(
    *,
    profile_name: str = "capital_constrained",
    explicit_path: str | Path | None = None,
    required: bool = False,
) -> Dict[str, Any]:
    resolved_name = str(profile_name).strip() or "capital_constrained"
    profiles = load_retail_profiles_spec(explicit_path=explicit_path, required=required)
    if not profiles:
        return {}
    row = profiles.get(resolved_name)
    if isinstance(row, dict):
        out = dict(row)
        out.setdefault("id", resolved_name)
        return out
    if required:
        available = ", ".join(sorted(profiles.keys())) or "<none>"
        raise KeyError(f"Retail profile '{resolved_name}' not found. Available: {available}")
    return {}


@functools.lru_cache(maxsize=None)
def load_hypothesis_spec(name: str) -> Dict[str, Any]:
    normalized = str(name).strip()
    if not normalized:
        return {}
    return load_yaml_relative(f"spec/hypotheses/{normalized}.yaml")


@functools.lru_cache(maxsize=None)
def load_concept_spec(concept_id: str) -> Dict[str, Any]:
    normalized = str(concept_id).strip()
    if not normalized:
        return {}
    return load_yaml_relative(f"spec/concepts/{normalized}.yaml")


@functools.lru_cache(maxsize=None)
def load_global_defaults() -> Dict[str, Any]:
    return load_yaml_relative("spec/global_defaults.yaml")


@functools.lru_cache(maxsize=None)
def load_event_spec(event_type: str) -> Dict[str, Any]:
    normalized = str(event_type).strip()
    if not normalized:
        return {}
    return load_yaml_relative(f"spec/events/{normalized}.yaml")


def ontology_spec_paths(repo_root: Path | None = None) -> Dict[str, Path]:
    return {
        key: resolve_relative_spec_path(rel, repo_root=repo_root)
        for key, rel in ONTOLOGY_SPEC_RELATIVE_PATHS.items()
    }


def runtime_spec_paths(repo_root: Path | None = None) -> Dict[str, Path]:
    return {
        key: resolve_relative_spec_path(rel, repo_root=repo_root)
        for key, rel in RUNTIME_SPEC_RELATIVE_PATHS.items()
    }


def feature_schema_registry_path(version: str | None = None) -> Path:
    token = str(version or os.getenv("BACKTEST_FEATURE_SCHEMA_VERSION", "v2")).strip().lower()
    if token != "v2":
        token = "v2"
    return (PROJECT_ROOT / "schemas" / f"feature_schema_{token}.json").resolve()


def load_feature_schema_registry(version: str | None = None) -> Dict[str, Any]:
    path = feature_schema_registry_path(version)
    if not path.exists():
        raise ValueError(f"Feature schema registry missing: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Feature schema registry is invalid JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"Feature schema registry must be a JSON object: {path}")
    return payload


def iter_spec_yaml_files(repo_root: Path | None = None) -> list[Path]:
    base = (
        spec_root()
        if repo_root is None
        else resolve_relative_spec_path("spec", repo_root=repo_root)
    )
    files = [p for p in base.rglob("*.yaml") if p.is_file()]
    return sorted(files)


def canonical_yaml_hash(path: Path) -> str:
    payload = load_yaml_path(path)
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str
    )


def compute_spec_digest(relative_paths: Iterable[str | Path]) -> str:
    entries: list[dict[str, Any]] = []
    for rel in relative_paths:
        path = resolve_relative_spec_path(rel)
        if not path.exists():
            entries.append({"path": str(rel), "exists": False})
            continue
        entries.append(
            {
                "path": str(rel),
                "exists": True,
                "content": path.read_text(encoding="utf-8"),
            }
        )
    return json.dumps(entries, sort_keys=True)


def clear_caches() -> None:
    load_yaml_relative.cache_clear()
    load_gates_spec.cache_clear()
    load_family_specs.cache_clear()
    load_unified_event_registry.cache_clear()
    load_event_ontology_mapping.cache_clear()
    load_template_registry.cache_clear()
    load_state_registry.cache_clear()
    load_thesis_registry.cache_clear()
    load_event_contract_overrides.cache_clear()
    load_runtime_spec.cache_clear()
    load_blueprint_policy_spec.cache_clear()
    load_hypothesis_spec.cache_clear()
    load_concept_spec.cache_clear()
    load_global_defaults.cache_clear()
    load_event_spec.cache_clear()
