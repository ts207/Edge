from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Sequence

from project.spec_registry import load_yaml_path, resolve_relative_spec_path
from project import PROJECT_ROOT
from project.core.coercion import as_bool


@dataclass(frozen=True)
class EventRegistrySpec:
    event_type: str
    reports_dir: str
    events_file: str
    signal_column: str
    merge_gap_bars: int = 1
    cooldown_bars: int = 0
    anchor_rule: str = "max_intensity"
    min_occurrences: int = 0
    is_descriptive: bool = False
    is_trade_trigger: bool = True
    requires_confirmation: bool = False
    allowed_templates: Sequence[str] = ("all",)
    disallowed_states: Sequence[str] = ()


def _load_event_specs() -> Dict[str, EventRegistrySpec]:
    spec_dir = resolve_relative_spec_path("spec/events", repo_root=PROJECT_ROOT.parent)
    if not spec_dir.exists():
        return {}

    required = {"event_type", "reports_dir", "events_file", "signal_column"}
    specs = {}
    for yaml_file in sorted(spec_dir.glob("*.yaml")):
        if yaml_file.name.startswith("_"):
            continue
        data = load_yaml_path(yaml_file)
        if not isinstance(data, dict) or not data:
            continue
        if bool(data.get("deprecated", False)) or not bool(data.get("active", True)):
            continue
        if data.get("kind") in {
            "canonical_event_registry",
            "event_config_defaults",
            "event_family_defaults",
            "event_unified_registry",
        }:
            continue
        if "event_type" not in data:
            continue
        missing = required - set(data.keys())
        if missing:
            raise ValueError(f"Malformed spec {yaml_file.name} — missing registry fields")
        parameters = data.get("parameters", {})
        if not isinstance(parameters, dict):
            parameters = {}

        def _canon_param(name: str, default: int | str | Sequence[str] | bool):
            if name in data:
                return data.get(name, default)
            if name in parameters:
                return parameters.get(name, default)
            return default

        spec = EventRegistrySpec(
            event_type=data["event_type"],
            reports_dir=data["reports_dir"],
            events_file=data["events_file"],
            signal_column=data["signal_column"],
            merge_gap_bars=int(_canon_param("merge_gap_bars", 1)),
            cooldown_bars=int(_canon_param("cooldown_bars", 0)),
            anchor_rule=str(_canon_param("anchor_rule", "max_intensity")),
            min_occurrences=int(_canon_param("min_occurrences", 0)),
            is_descriptive=as_bool(_canon_param("is_descriptive", False)),
            is_trade_trigger=as_bool(_canon_param("is_trade_trigger", True)),
            requires_confirmation=as_bool(_canon_param("requires_confirmation", False)),
            allowed_templates=list(_canon_param("allowed_templates", ["all"])),
            disallowed_states=list(_canon_param("disallowed_states", [])),
        )
        specs[spec.event_type] = spec
    return specs


def assert_event_specs_available() -> None:
    specs = _load_event_specs()
    if not specs:
        raise FileNotFoundError(
            "No active event registry specifications found under spec/events; "
            "ensure the analyzer specs are present before running phase1/registry."
        )


EVENT_REGISTRY_SPECS: Dict[str, EventRegistrySpec] = _load_event_specs()

SIGNAL_TO_EVENT_TYPE: Dict[str, str] = {
    spec.signal_column: event_type for event_type, spec in EVENT_REGISTRY_SPECS.items()
}
REGISTRY_BACKED_SIGNALS = set(SIGNAL_TO_EVENT_TYPE.keys())

REGISTRY_EVENT_COLUMNS = [
    "run_id", "event_type", "signal_column", "timestamp", "event_ts_raw", "event_ts_snapped",
    "signal_bar_open_time", "first_tradable_bar_open_time", "active_start_time", "active_end_time",
    "effective_entry_bar_open_time", "phenom_enter_ts", "eval_bar_ts", "detected_ts", "signal_ts",
    "enter_ts", "exit_ts", "symbol", "event_id", "direction", "sign", "severity_bucket",
    "vol_regime", "carry_state", "ms_trend_state", "ms_spread_state", "split_label",
    "features_at_event", "is_observational", "is_signal_eligible", "is_tradable_now",
    "is_tradable_next_bar",
]

AGGREGATE_EVENT_TYPE_UNIONS: Dict[str, Sequence[str]] = {}


def expected_event_types_for_spec(event_type: str) -> Sequence[str]:
    from project.events.event_aliases import resolve_event_alias
    normalized = str(event_type).strip().upper()
    if not normalized:
        return ()
    canonical = resolve_event_alias(normalized)
    if canonical != normalized:
        return (normalized, canonical)
    return AGGREGATE_EVENT_TYPE_UNIONS.get(normalized, (normalized,))


VALID_DIRECTIONS = frozenset({"long", "short", "neutral", "non_directional"})
_DIRECTION_DEFAULT = "non_directional"
