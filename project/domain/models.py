from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Mapping


@dataclass(frozen=True)
class EventDefinition:
    event_type: str
    canonical_family: str
    canonical_regime: str
    legacy_family: str
    event_kind: str
    reports_dir: str
    events_file: str
    signal_column: str
    subtype: str = ""
    phase: str = ""
    evidence_mode: str = ""
    asset_scope: str = ""
    venue_scope: str = ""
    is_composite: bool = False
    is_context_tag: bool = False
    is_strategy_construct: bool = False
    research_only: bool = False
    strategy_only: bool = False
    deconflict_priority: int = 0
    disposition: str = ""
    layer: str = ""
    notes: str = ""
    tier: str = ""
    operational_role: str = ""
    deployment_disposition: str = ""
    runtime_category: str = "active_runtime_event"
    maturity: str = ""
    default_executable: bool = True
    enabled: bool = True
    detector_name: str = ""
    instrument_classes: tuple[str, ...] = ()
    requires_features: tuple[str, ...] = ()
    runtime_tags: tuple[str, ...] = ()
    sequence_eligible: bool = True
    cluster_id: str = ""
    collapse_target: str = ""
    overlap_group: str = ""
    precedence_rank: int = 0
    routing_profile_ref: str = ""
    suppresses: tuple[Any, ...] = ()
    suppressed_by: tuple[Any, ...] = ()
    maturity_scores: Dict[str, Any] = field(default_factory=dict)
    parameters: Dict[str, Any] = field(default_factory=dict)
    raw: Dict[str, Any] = field(default_factory=dict)
    spec_path: str = ""
    source_kind: str = "unified_registry"


@dataclass(frozen=True)
class StateDefinition:
    state_id: str
    family: str
    source_event_type: str
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TemplateOperatorDefinition:
    template_id: str
    compatible_families: tuple[str, ...]
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DomainRegistry:
    unified_payload: Dict[str, Any]
    event_definitions: Dict[str, EventDefinition]
    state_definitions: Dict[str, StateDefinition]
    template_operator_definitions: Dict[str, TemplateOperatorDefinition]
    gates_spec: Dict[str, Any]
    unified_registry_path: str
    template_registry_payload: Dict[str, Any] = field(default_factory=dict)
    family_registry_payload: Dict[str, Any] = field(default_factory=dict)
    context_state_map: Dict[tuple[str, str], str] = field(default_factory=dict)
    searchable_event_families: tuple[str, ...] = ()
    searchable_state_families: tuple[str, ...] = ()
    state_aliases: tuple[str, ...] = ()
    stress_scenarios: tuple[Dict[str, Any], ...] = ()
    kill_switch_candidate_features: tuple[str, ...] = ()
    sequence_definitions: tuple[Dict[str, Any], ...] = ()
    interaction_definitions: tuple[Dict[str, Any], ...] = ()

    def has_event(self, event_type: str) -> bool:
        normalized = str(event_type).strip().upper()
        return normalized in self.event_definitions

    def get_event(self, event_type: str) -> EventDefinition | None:
        normalized = str(event_type).strip().upper()
        return self.event_definitions.get(normalized)

    def has_state(self, state_id: str) -> bool:
        return str(state_id).strip().upper() in self.state_definitions

    def get_state(self, state_id: str) -> StateDefinition | None:
        return self.state_definitions.get(str(state_id).strip().upper())

    def get_operator(self, template_id: str) -> TemplateOperatorDefinition | None:
        return self.template_operator_definitions.get(str(template_id).strip())

    def operator_rows(self) -> Dict[str, Dict[str, Any]]:
        return {name: dict(spec.raw) for name, spec in self.template_operator_definitions.items()}

    def family_templates(self, family_name: str) -> tuple[str, ...]:
        template_families = self.template_registry_payload.get("families", {})
        if isinstance(template_families, Mapping):
            family_row = template_families.get(str(family_name).strip().upper(), {})
            if isinstance(family_row, Mapping):
                templates = family_row.get("templates", family_row.get("allowed_templates", []))
                if isinstance(templates, (list, tuple)):
                    seen: set[str] = set()
                    out: list[str] = []
                    for item in templates:
                        token = str(item).strip()
                        if token and token not in seen:
                            out.append(token)
                            seen.add(token)
                    if out:
                        return tuple(out)
        row = self.family_defaults(family_name)
        templates = row.get("templates", [])
        if not isinstance(templates, (list, tuple)):
            return ()
        seen: set[str] = set()
        out: list[str] = []
        for item in templates:
            token = str(item).strip()
            if token and token not in seen:
                out.append(token)
                seen.add(token)
        return tuple(out)

    def family_defaults(self, family: str) -> Dict[str, Any]:
        families = self.unified_payload.get("families", {})
        if not isinstance(families, Mapping):
            return {}
        row = families.get(str(family).strip().upper(), {})
        return dict(row) if isinstance(row, Mapping) else {}

    def defaults(self) -> Dict[str, Any]:
        payload = self.unified_payload.get("defaults", {})
        return dict(payload) if isinstance(payload, Mapping) else {}

    def template_registry(self) -> Dict[str, Any]:
        return dict(self.template_registry_payload)

    def template_defaults(self) -> Dict[str, Any]:
        payload = self.template_registry_payload.get("defaults", {})
        return dict(payload) if isinstance(payload, Mapping) else {}

    def family_registry(self) -> Dict[str, Any]:
        return dict(self.family_registry_payload)

    def event_family_rows(self) -> Dict[str, Any]:
        payload = self.family_registry_payload.get("event_families", {})
        return dict(payload) if isinstance(payload, Mapping) else {}

    def state_family_rows(self) -> Dict[str, Any]:
        payload = self.family_registry_payload.get("state_families", {})
        return dict(payload) if isinstance(payload, Mapping) else {}

    def event_row(self, event_type: str) -> Dict[str, Any]:
        event = self.get_event(event_type)
        return dict(event.raw) if event is not None else {}

    def event_spec_path(self, event_type: str) -> str:
        event = self.get_event(event_type)
        return str(event.spec_path) if event is not None else ""

    def get_event_ids_for_family(self, family_name: str) -> tuple[str, ...]:
        family = str(family_name).strip().upper()
        return tuple(
            sorted(
                event_type
                for event_type, spec in self.event_definitions.items()
                if spec.canonical_family == family
                or spec.canonical_regime == family
                or spec.legacy_family == family
            )
        )

    def get_event_ids_for_regime(
        self,
        regime_name: str,
        *,
        executable_only: bool = False,
    ) -> tuple[str, ...]:
        regime = str(regime_name).strip().upper()
        return tuple(
            sorted(
                event_type
                for event_type, spec in self.event_definitions.items()
                if spec.canonical_regime == regime
                and (
                    not executable_only
                    or (
                        not spec.is_composite
                        and not spec.is_context_tag
                        and not spec.is_strategy_construct
                    )
                )
            )
        )

    def canonical_regime_rows(self) -> Dict[str, tuple[str, ...]]:
        regimes = {
            spec.canonical_regime
            for spec in self.event_definitions.values()
            if spec.canonical_regime
        }
        return {
            regime: self.get_event_ids_for_regime(regime)
            for regime in sorted(regimes)
        }

    def default_executable_event_ids(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                event_type
                for event_type, spec in self.event_definitions.items()
                if spec.default_executable
                and spec.runtime_category == "active_runtime_event"
                and not spec.is_composite
                and not spec.is_context_tag
                and not spec.is_strategy_construct
            )
        )

    def get_event_ids_for_tier(self, tier: str) -> tuple[str, ...]:
        normalized = str(tier).strip().upper()
        return tuple(sorted(event_type for event_type, spec in self.event_definitions.items() if str(spec.tier).upper() == normalized))

    def get_event_ids_for_role(self, role: str) -> tuple[str, ...]:
        normalized = str(role).strip().lower()
        return tuple(sorted(event_type for event_type, spec in self.event_definitions.items() if str(spec.operational_role).strip().lower() == normalized))

    def get_state_ids_for_family(self, family_name: str) -> tuple[str, ...]:
        family = str(family_name).strip().upper()
        return tuple(
            sorted(
                state_id
                for state_id, spec in self.state_definitions.items()
                if spec.family == family
            )
        )

    def resolve_context_state(self, family: str, label: str) -> str | None:
        return self.context_state_map.get((str(family).strip(), str(label).strip()))

    def context_labels_for_family(self, family: str) -> tuple[str, ...]:
        normalized = str(family).strip()
        return tuple(
            sorted(label for fam, label in self.context_state_map.keys() if fam == normalized)
        )

    @property
    def state_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self.state_definitions.keys()))

    @property
    def event_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self.event_definitions.keys()))

    @property
    def valid_state_ids(self) -> tuple[str, ...]:
        return tuple(sorted({*self.state_definitions.keys(), *self.state_aliases}))

    def default_templates(self) -> tuple[str, ...]:
        defaults = self.template_defaults()
        templates = defaults.get("templates", [])
        if not isinstance(templates, (list, tuple)):
            return ()
        out: list[str] = []
        seen: set[str] = set()
        for item in templates:
            token = str(item).strip()
            if token and token not in seen:
                out.append(token)
                seen.add(token)
        return tuple(out)

    def family_filter_templates(self, family_name: str) -> tuple[Dict[str, Any], ...]:
        filter_block = self.template_registry_payload.get("filter_templates", {})
        if not isinstance(filter_block, Mapping):
            return ()
        allowed = set(self.family_templates(family_name))
        out: list[Dict[str, Any]] = []
        for name, cond in filter_block.items():
            if name in allowed and isinstance(cond, Mapping):
                out.append(
                    {
                        "name": str(name),
                        "feature": cond["feature"],
                        "operator": cond["operator"],
                        "threshold": float(cond["threshold"]),
                    }
                )
        return tuple(out)

    def family_execution_templates(self, family_name: str) -> tuple[str, ...]:
        allowed = self.family_templates(family_name)
        if not allowed:
            allowed = self.default_templates()
        if not allowed:
            return ()
        filter_names = {row["name"] for row in self.family_filter_templates(family_name)}
        return tuple(name for name in allowed if name not in filter_names)

    def default_entry_lags(self) -> tuple[int, ...]:
        defaults = self.template_defaults()
        grids = defaults.get("template_param_grid_defaults", {})
        if not isinstance(grids, Mapping):
            return (1, 2)
        common = grids.get("common", {})
        if not isinstance(common, Mapping):
            return (1, 2)
        values = common.get("entry_lag_bars", [1, 2])
        if not isinstance(values, (list, tuple)):
            return (1, 2)
        out: list[int] = []
        for value in values:
            try:
                out.append(int(value))
            except (TypeError, ValueError):
                continue
        return tuple(out or [1, 2])

    def stress_scenario_rows(self) -> list[Dict[str, Any]]:
        return [dict(row) for row in self.stress_scenarios]

    def kill_switch_candidates(self) -> list[str]:
        return list(self.kill_switch_candidate_features)

    def sequence_rows(self) -> list[Dict[str, Any]]:
        return [dict(row) for row in self.sequence_definitions]

    def interaction_rows(self) -> list[Dict[str, Any]]:
        return [dict(row) for row in self.interaction_definitions]
