from __future__ import annotations

import functools
from typing import Any, Dict, Iterable, Mapping

from project.spec_registry import load_yaml_relative

ONTOLOGY_MAPPING_PATH = "spec/events/event_ontology_mapping.yaml"


def _as_mapping(value: object) -> Dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


@functools.lru_cache(maxsize=1)
def load_event_ontology_mapping() -> Dict[str, Any]:
    payload = load_yaml_relative(ONTOLOGY_MAPPING_PATH)
    return payload if isinstance(payload, dict) else {}


def allowed_ontology_layers() -> tuple[str, ...]:
    payload = load_event_ontology_mapping()
    rows = payload.get("allowed_values", {}) if isinstance(payload, dict) else {}
    values = rows.get("layer", []) if isinstance(rows, Mapping) else []
    return tuple(str(value).strip() for value in values if str(value).strip())


def allowed_dispositions() -> tuple[str, ...]:
    payload = load_event_ontology_mapping()
    rows = payload.get("allowed_values", {}) if isinstance(payload, dict) else {}
    values = rows.get("disposition", []) if isinstance(rows, Mapping) else []
    return tuple(str(value).strip() for value in values if str(value).strip())


def allowed_evidence_modes() -> tuple[str, ...]:
    payload = load_event_ontology_mapping()
    rows = payload.get("allowed_values", {}) if isinstance(payload, dict) else {}
    values = rows.get("evidence_mode", []) if isinstance(rows, Mapping) else []
    return tuple(str(value).strip() for value in values if str(value).strip())


@functools.lru_cache(maxsize=1)
def ontology_rows_by_event() -> Dict[str, Dict[str, Any]]:
    payload = load_event_ontology_mapping()
    events = payload.get("events", {}) if isinstance(payload, dict) else {}
    out: Dict[str, Dict[str, Any]] = {}
    if not isinstance(events, Mapping):
        return out
    for event_type, row in events.items():
        token = str(event_type).strip().upper()
        if token and isinstance(row, Mapping):
            out[token] = dict(row)
    return out


def ontology_row(event_type: str) -> Dict[str, Any]:
    return dict(ontology_rows_by_event().get(str(event_type).strip().upper(), {}))


def canonical_regime_fanout(
    rows: Mapping[str, Mapping[str, Any]] | None = None,
    *,
    executable_only: bool = False,
) -> Dict[str, tuple[str, ...]]:
    selected = rows if rows is not None else ontology_rows_by_event()
    groups: Dict[str, list[str]] = {}
    for event_type, row in selected.items():
        if not isinstance(row, Mapping):
            continue
        if executable_only and not is_default_executable(row):
            continue
        regime = str(row.get("canonical_regime", "")).strip().upper()
        if not regime:
            continue
        groups.setdefault(regime, []).append(str(event_type).strip().upper())
    return {regime: tuple(sorted(event_types)) for regime, event_types in sorted(groups.items())}


def rows_for_layer(layer: str) -> Dict[str, Dict[str, Any]]:
    normalized = str(layer).strip()
    return {
        event_type: dict(row)
        for event_type, row in ontology_rows_by_event().items()
        if str(row.get("layer", "")).strip() == normalized
    }


def is_default_executable(row: Mapping[str, Any]) -> bool:
    return not any(
        bool(row.get(flag, False))
        for flag in ("is_composite", "is_context_tag", "is_strategy_construct")
    )


def infer_bool_flags(row: Mapping[str, Any]) -> Dict[str, bool]:
    layer = str(row.get("layer", "")).strip()
    return {
        "is_composite": layer == "composite",
        "is_context_tag": layer == "context_tag",
        "is_strategy_construct": layer == "strategy_construct",
    }


def normalized_ontology_row(event_type: str, row: Mapping[str, Any]) -> Dict[str, Any]:
    token = str(event_type).strip().upper()
    data = dict(row)
    flags = infer_bool_flags(data)
    normalized = {
        "event_type": token,
        "canonical_regime": str(data.get("canonical_regime", "")).strip().upper(),
        "subtype": str(data.get("subtype", "")).strip(),
        "phase": str(data.get("phase", "")).strip(),
        "evidence_mode": str(data.get("evidence_mode", "")).strip(),
        "layer": str(data.get("layer", "")).strip(),
        "disposition": str(data.get("disposition", "")).strip(),
        "asset_scope": str(data.get("asset_scope", "")).strip(),
        "venue_scope": str(data.get("venue_scope", "")).strip(),
        "deconflict_priority": int(data.get("deconflict_priority", 0) or 0),
        "research_only": bool(data.get("research_only", False)),
        "strategy_only": bool(data.get("strategy_only", False)),
        "notes": str(data.get("notes", "")).strip(),
    }
    normalized.update(flags)
    return normalized


def normalized_ontology_rows() -> Dict[str, Dict[str, Any]]:
    return {
        event_type: normalized_ontology_row(event_type, row)
        for event_type, row in ontology_rows_by_event().items()
    }


def validate_mapping_rows(rows: Mapping[str, Mapping[str, Any]] | None = None) -> list[str]:
    selected = rows if rows is not None else ontology_rows_by_event()
    allowed_layers = set(allowed_ontology_layers())
    allowed_disposition_values = set(allowed_dispositions())
    allowed_evidence_values = set(allowed_evidence_modes())
    issues: list[str] = []
    for event_type, raw in selected.items():
        row = normalized_ontology_row(event_type, raw)
        if not row["canonical_regime"]:
            issues.append(f"{event_type}: missing canonical_regime")
        if not row["subtype"]:
            issues.append(f"{event_type}: missing subtype")
        if not row["phase"]:
            issues.append(f"{event_type}: missing phase")
        if row["layer"] not in allowed_layers:
            issues.append(f"{event_type}: invalid layer={row['layer']}")
        if row["disposition"] not in allowed_disposition_values:
            issues.append(f"{event_type}: invalid disposition={row['disposition']}")
        if row["evidence_mode"] not in allowed_evidence_values:
            issues.append(f"{event_type}: invalid evidence_mode={row['evidence_mode']}")
        layer_flags = [
            row["is_composite"],
            row["is_context_tag"],
            row["is_strategy_construct"],
        ]
        if sum(1 for flag in layer_flags if flag) > 1:
            issues.append(f"{event_type}: multiple ontology layer flags enabled")
        if row["strategy_only"] and not row["is_strategy_construct"]:
            issues.append(f"{event_type}: strategy_only requires strategy_construct layer")
    return issues


def clear_caches() -> None:
    load_event_ontology_mapping.cache_clear()
    ontology_rows_by_event.cache_clear()

