from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from project import PROJECT_ROOT
from project.domain.models import (
    DomainRegistry,
    EventDefinition,
    StateDefinition,
    TemplateOperatorDefinition,
)
from project.spec_registry import (
    load_gates_spec,
    load_state_registry,
    load_unified_event_registry,
    load_yaml_relative,
    load_yaml_path,
    resolve_relative_spec_path,
)


_SPECIAL_EVENT_SPEC_KINDS = {
    "canonical_event_registry",
    "event_config_defaults",
    "event_family_defaults",
    "event_unified_registry",
}


def _event_spec_dir() -> Path:
    return resolve_relative_spec_path("spec/events", repo_root=PROJECT_ROOT.parent)


def _merge_event_rows(unified: Dict[str, Any]) -> Dict[str, EventDefinition]:
    defaults = unified.get("defaults", {})
    families = unified.get("families", {})
    unified_events = unified.get("events", {})
    out: Dict[str, EventDefinition] = {}

    event_types = set()
    if isinstance(unified_events, dict):
        event_types.update(str(k).strip().upper() for k in unified_events.keys())

    for event_type in sorted(event_types):
        unified_row = unified_events.get(event_type, {}) if isinstance(unified_events, dict) else {}
        row: Dict[str, Any] = {}
        if isinstance(defaults, dict):
            row.update(defaults)
        family_name = str(unified_row.get("canonical_family", "")).strip().upper()
        
        if (
            family_name
            and isinstance(families, dict)
            and isinstance(families.get(family_name), dict)
        ):
            row.update(families[family_name])
        
        if isinstance(unified_row, dict):
            row.update(unified_row)
            
        parameters = {}
        default_params = defaults.get("parameters", {}) if isinstance(defaults, dict) else {}
        family_params = {}
        if (
            family_name
            and isinstance(families, dict)
            and isinstance(families.get(family_name), dict)
        ):
            family_params = families[family_name].get("parameters", {})
            
        if isinstance(default_params, dict):
            parameters.update(default_params)
        if isinstance(family_params, dict):
            parameters.update(family_params)
        if isinstance(row.get("parameters"), dict):
            parameters.update(row["parameters"])
            
        row["parameters"] = parameters
        spec_path = str((_event_spec_dir() / f"{event_type}.yaml").resolve())
        
        out[event_type] = EventDefinition(
            event_type=event_type,
            canonical_family=family_name or str(row.get("canonical_family", "")).strip().upper(),
            reports_dir=str(row.get("reports_dir", event_type.lower())),
            events_file=str(row.get("events_file", f"{event_type.lower()}_events.parquet")),
            signal_column=str(row.get("signal_column", f"{event_type.lower()}_event")),
            parameters=dict(parameters),
            raw=dict(row),
            spec_path=spec_path,
            source_kind="unified_registry",
        )
    return out


def _load_states() -> Dict[str, StateDefinition]:
    out: Dict[str, StateDefinition] = {}

    # Merge the newer registry with the legacy spec registry. The newer file
    # carries runtime engine metadata, while the legacy spec still contains the
    # broader ontology-backed state universe used by search specs.
    newer_path = PROJECT_ROOT / "configs" / "registries" / "states.yaml"
    if newer_path.exists():
        payload = load_yaml_path(newer_path)
        states_dict = payload.get("states", {})
        if isinstance(states_dict, dict):
            for state_id, row in states_dict.items():
                if not isinstance(row, dict):
                    continue
                sid = str(state_id).strip().upper()
                out[sid] = StateDefinition(
                    state_id=sid,
                    family=str(row.get("family", "")).strip().upper(),
                    source_event_type=str(row.get("source_event_type", "")).strip().upper(),
                    raw=dict(row),
                )
    # Legacy spec path remains the canonical source for searchable ontology
    # states that may not yet be materialized in the runtime registry.
    payload = load_state_registry()
    rows = payload.get("states", []) if isinstance(payload, dict) else []
    for row in rows:
        if not isinstance(row, dict):
            continue
        state_id = str(row.get("state_id", "")).strip().upper()
        if not state_id:
            continue
        if state_id in out:
            existing = out[state_id]
            merged_raw = dict(row)
            merged_raw.update(existing.raw)
            out[state_id] = StateDefinition(
                state_id=state_id,
                family=existing.family or str(row.get("family", "")).strip().upper(),
                source_event_type=existing.source_event_type
                or str(row.get("source_event_type", "")).strip().upper(),
                raw=merged_raw,
            )
            continue
        out[state_id] = StateDefinition(
            state_id=state_id,
            family=str(row.get("family", "")).strip().upper(),
            source_event_type=str(row.get("source_event_type", "")).strip().upper(),
            raw=dict(row),
        )
    return out


def _load_context_state_map() -> Dict[tuple[str, str], str]:
    payload = load_yaml_relative("spec/grammar/state_registry.yaml")
    raw_map = payload.get("context_state_map", {}) if isinstance(payload, dict) else {}
    out: Dict[tuple[str, str], str] = {}
    if not isinstance(raw_map, dict):
        return out
    for family, labels in raw_map.items():
        if not isinstance(labels, dict):
            continue
        for label, state_id in labels.items():
            fam = str(family).strip()
            lab = str(label).strip()
            sid = str(state_id).strip().upper()
            if fam and lab and sid:
                out[(fam, lab)] = sid
    return out


def _load_state_aliases() -> tuple[str, ...]:
    payload = load_yaml_relative("spec/grammar/state_registry.yaml")
    out: set[str] = set()
    if not isinstance(payload, dict):
        return ()
    regimes = payload.get("regimes", {})
    if isinstance(regimes, dict):
        for labels in regimes.values():
            if isinstance(labels, list):
                out.update(str(label).strip().upper() for label in labels if str(label).strip())
    state_map = payload.get("context_state_map", {})
    if isinstance(state_map, dict):
        for labels in state_map.values():
            if isinstance(labels, dict):
                out.update(
                    str(state_id).strip().upper()
                    for state_id in labels.values()
                    if str(state_id).strip()
                )
    return tuple(sorted(out))


def _load_searchable_families() -> tuple[tuple[str, ...], tuple[str, ...]]:
    payload = load_yaml_relative("spec/grammar/family_registry.yaml")
    event_families = payload.get("event_families", {}) if isinstance(payload, dict) else {}
    state_families = payload.get("state_families", {}) if isinstance(payload, dict) else {}
    searchable_events = tuple(
        sorted(
            str(name).strip().upper()
            for name, cfg in event_families.items()
            if isinstance(cfg, dict) and bool(cfg.get("searchable", False))
        )
    )
    searchable_states = tuple(
        sorted(
            str(name).strip().upper()
            for name, cfg in state_families.items()
            if isinstance(cfg, dict) and bool(cfg.get("searchable", False))
        )
    )
    return searchable_events, searchable_states


def _load_stress_scenarios() -> tuple[Dict[str, Any], ...]:
    payload = load_yaml_relative("spec/grammar/stress_scenarios.yaml")
    rows = payload.get("scenarios", []) if isinstance(payload, dict) else []
    if not isinstance(rows, list):
        return ()
    out: list[Dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name", "")).strip()
        feature = str(row.get("feature", "")).strip()
        operator = str(row.get("operator", "")).strip()
        if not (name and feature and operator):
            continue
        out.append(dict(row))
    return tuple(out)


def _load_kill_switch_candidate_features() -> tuple[str, ...]:
    payload = load_yaml_relative("spec/grammar/kill_switch_config.yaml")
    rows = payload.get("candidates", []) if isinstance(payload, dict) else []
    if not isinstance(rows, list):
        return ()
    return tuple(str(value).strip() for value in rows if str(value).strip())


def _load_sequence_definitions() -> tuple[Dict[str, Any], ...]:
    payload = load_yaml_relative("spec/grammar/sequence_registry.yaml")
    rows = payload.get("sequences", []) if isinstance(payload, dict) else []
    if not isinstance(rows, list):
        return ()
    out: list[Dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name", "")).strip()
        events = row.get("events", [])
        if not (name and isinstance(events, list) and events):
            continue
        out.append(dict(row))
    return tuple(out)


def _load_interaction_definitions() -> tuple[Dict[str, Any], ...]:
    payload = load_yaml_relative("spec/grammar/interaction_registry.yaml")
    rows = payload.get("motifs", []) if isinstance(payload, dict) else []
    if not isinstance(rows, list):
        return ()
    out: list[Dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name", "")).strip()
        left = str(row.get("left", "")).strip()
        right = str(row.get("right", "")).strip()
        op = str(row.get("op", "")).strip()
        if not (name and left and right and op):
            continue
        out.append(dict(row))
    return tuple(out)


def _load_operators(unified: Dict[str, Any]) -> Dict[str, TemplateOperatorDefinition]:
    lexicon = load_yaml_relative("spec/hypotheses/template_verb_lexicon.yaml")
    operators = lexicon.get("operators", {})
    out: Dict[str, TemplateOperatorDefinition] = {}
    if not isinstance(operators, dict):
        return out
    for template_id, row in operators.items():
        if not isinstance(row, dict):
            continue
        out[str(template_id).strip()] = TemplateOperatorDefinition(
            template_id=str(template_id).strip(),
            compatible_families=tuple(
                str(x).strip().upper() for x in row.get("compatible_families", []) or []
            ),
            raw=dict(row),
        )
    return out


def compile_domain_registry() -> DomainRegistry:
    unified = load_unified_event_registry()
    if not unified:
        raise FileNotFoundError("Unified event registry is missing or empty")
    template_registry_payload = load_yaml_relative("spec/ontology/templates/template_registry.yaml")
    family_registry_payload = load_yaml_relative("spec/grammar/family_registry.yaml")
    event_definitions = _merge_event_rows(unified)
    state_definitions = _load_states()
    template_operator_definitions = _load_operators(unified)
    context_state_map = _load_context_state_map()
    state_aliases = _load_state_aliases()
    searchable_event_families, searchable_state_families = _load_searchable_families()
    stress_scenarios = _load_stress_scenarios()
    kill_switch_candidate_features = _load_kill_switch_candidate_features()
    sequence_definitions = _load_sequence_definitions()
    interaction_definitions = _load_interaction_definitions()
    return DomainRegistry(
        unified_payload=dict(unified),
        event_definitions=event_definitions,
        state_definitions=state_definitions,
        template_operator_definitions=template_operator_definitions,
        gates_spec=dict(load_gates_spec()),
        unified_registry_path=str(
            resolve_relative_spec_path(
                "spec/events/event_registry_unified.yaml", repo_root=PROJECT_ROOT.parent
            )
        ),
        template_registry_payload=dict(template_registry_payload)
        if isinstance(template_registry_payload, dict)
        else {},
        family_registry_payload=dict(family_registry_payload)
        if isinstance(family_registry_payload, dict)
        else {},
        context_state_map=context_state_map,
        searchable_event_families=searchable_event_families,
        searchable_state_families=searchable_state_families,
        state_aliases=state_aliases,
        stress_scenarios=stress_scenarios,
        kill_switch_candidate_features=kill_switch_candidate_features,
        sequence_definitions=sequence_definitions,
        interaction_definitions=interaction_definitions,
    )
