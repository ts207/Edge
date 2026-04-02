#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import yaml

from project import PROJECT_ROOT
from project.domain.compiled_registry import get_domain_registry
from project.events.contract_registry import load_active_event_contracts
from project.spec_registry import load_yaml_path


REPO_ROOT = PROJECT_ROOT.parent
EVENTS_ROOT = REPO_ROOT / "spec" / "events"
_SKIP_FILES = {
    "canonical_event_registry.yaml",
    "compatibility.yaml",
    "precedence.yaml",
    "event_contract_overrides.yaml",
    "event_ontology_mapping.yaml",
    "event_registry_unified.yaml",
    "DESIGN.yaml",
}


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _clean_list(values: Any) -> list[Any]:
    if isinstance(values, list):
        return list(values)
    if isinstance(values, tuple):
        return list(values)
    return []


def _compatibility_index() -> tuple[dict[str, list[dict[str, Any]]], dict[str, list[dict[str, Any]]]]:
    payload = load_yaml_path(EVENTS_ROOT / "compatibility.yaml")
    suppress_by_active: dict[str, list[dict[str, Any]]] = {}
    suppressed_by_target: dict[str, list[dict[str, Any]]] = {}
    for rule in payload.get("suppression_rules", []) if isinstance(payload, dict) else []:
        if not isinstance(rule, dict):
            continue
        active = _clean_text(rule.get("when_active")).upper()
        if not active:
            continue
        suppress = [
            _clean_text(event_type).upper()
            for event_type in rule.get("suppress", [])
            if _clean_text(event_type)
        ]
        if not suppress:
            continue
        reason = _clean_text(rule.get("reason"))
        penalty_factor = float(rule.get("penalty_factor", 0.0) or 0.0)
        block = bool(rule.get("block", False))
        for target in suppress:
            suppress_by_active.setdefault(active, []).append(
                {
                    "event_type": target,
                    "penalty_factor": penalty_factor,
                    "block": block,
                    "reason": reason,
                }
            )
            suppressed_by_target.setdefault(target, []).append(
                {
                    "event_type": active,
                    "penalty_factor": penalty_factor,
                    "block": block,
                    "reason": reason,
                }
            )
    return suppress_by_active, suppressed_by_target


def _precedence_index() -> dict[str, int]:
    payload = load_yaml_path(EVENTS_ROOT / "precedence.yaml")
    out: dict[str, int] = {}
    for row in payload.get("event_overrides", []) if isinstance(payload, dict) else []:
        if not isinstance(row, dict):
            continue
        event_type = _clean_text(row.get("event_type")).upper()
        if not event_type:
            continue
        out[event_type] = int(row.get("override_priority", 0) or 0)
    return out


def _bool(value: Any) -> bool:
    return bool(value)


def _set_if_value(target: dict[str, Any], key: str, value: Any) -> None:
    if value in (None, "", [], {}):
        return
    target[key] = value


def _migrate_event_spec(
    path: Path,
    *,
    registry,
    contracts: dict[str, dict[str, Any]],
    suppress_by_active: dict[str, list[dict[str, Any]]],
    suppressed_by_target: dict[str, list[dict[str, Any]]],
    precedence_by_event: dict[str, int],
) -> bool:
    payload = load_yaml_path(path)
    if not isinstance(payload, dict) or "event_type" not in payload or not payload.get("active", True):
        return False

    event_type = _clean_text(payload.get("event_type")).upper()
    spec = registry.event_definitions.get(event_type)
    contract = contracts.get(event_type, {})
    if spec is None:
        return False

    identity = _mapping(payload.get("identity"))
    governance = _mapping(payload.get("governance"))
    runtime = _mapping(payload.get("runtime"))
    semantics = _mapping(payload.get("semantics"))
    interaction = _mapping(payload.get("interaction"))
    routing = _mapping(payload.get("routing"))

    identity.update(
        {
            "canonical_regime": spec.canonical_regime,
            "legacy_family": spec.legacy_family,
            "subtype": spec.subtype,
            "phase": spec.phase,
            "evidence_mode": spec.evidence_mode,
            "layer": spec.layer,
            "disposition": spec.disposition,
            "asset_scope": spec.asset_scope,
            "venue_scope": spec.venue_scope,
        }
    )

    governance.update(
        {
            "event_kind": spec.event_kind,
            "default_executable": spec.default_executable,
            "research_only": spec.research_only,
            "strategy_only": spec.strategy_only,
            "context_tag": spec.is_context_tag,
            "is_composite": spec.is_composite,
            "maturity": _clean_text(spec.maturity or payload.get("maturity")),
            "tier": _clean_text(contract.get("tier") or spec.tier),
            "operational_role": _clean_text(contract.get("operational_role") or spec.operational_role),
            "deployment_disposition": _clean_text(
                contract.get("deployment_disposition") or spec.deployment_disposition
            ),
            "runtime_category": _clean_text(contract.get("runtime_category") or spec.runtime_category),
        }
    )

    runtime.update(
        {
            "detector": _clean_text(spec.detector_name),
            "enabled": spec.enabled,
            "signal_column": _clean_text(spec.signal_column),
            "events_file": _clean_text(spec.events_file),
            "reports_dir": _clean_text(spec.reports_dir),
            "instrument_classes": _clean_list(spec.instrument_classes),
            "requires_features": _clean_list(spec.requires_features),
            "sequence_eligible": spec.sequence_eligible,
            "runtime_tags": _clean_list(spec.runtime_tags),
        }
    )

    _set_if_value(semantics, "summary", _clean_text(payload.get("description")))
    _set_if_value(semantics, "cluster_id", _clean_text(spec.cluster_id or payload.get("cluster_id")))
    _set_if_value(
        semantics,
        "collapse_target",
        _clean_text(spec.collapse_target or payload.get("collapse_target")),
    )
    _set_if_value(
        semantics,
        "overlap_group",
        _clean_text(spec.overlap_group or payload.get("overlap_group")),
    )
    _set_if_value(
        semantics,
        "notes",
        _clean_text(spec.notes or payload.get("notes") or payload.get("description")),
    )
    precedence_rank = int(spec.precedence_rank or precedence_by_event.get(event_type, 0) or 0)
    semantics["precedence_rank"] = precedence_rank

    interaction["suppresses"] = suppress_by_active.get(event_type, [])
    interaction["suppressed_by"] = suppressed_by_target.get(event_type, [])

    _set_if_value(
        routing,
        "routing_profile_ref",
        _clean_text(spec.routing_profile_ref or payload.get("routing_profile_ref")),
    )

    payload["identity"] = identity
    payload["governance"] = governance
    payload["runtime"] = runtime
    payload["semantics"] = semantics
    payload["interaction"] = interaction
    payload["routing"] = routing

    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return True


def main() -> int:
    registry = get_domain_registry()
    contracts = load_active_event_contracts()
    suppress_by_active, suppressed_by_target = _compatibility_index()
    precedence_by_event = _precedence_index()

    updated = 0
    for path in sorted(EVENTS_ROOT.glob("*.yaml")):
        if path.name.startswith("_") or path.name in _SKIP_FILES:
            continue
        if _migrate_event_spec(
            path,
            registry=registry,
            contracts=contracts,
            suppress_by_active=suppress_by_active,
            suppressed_by_target=suppressed_by_target,
            precedence_by_event=precedence_by_event,
        ):
            updated += 1
    print(f"Migrated {updated} event specs to the sectioned canonical schema")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
