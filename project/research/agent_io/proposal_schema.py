from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

import yaml

from project.research.context_labels import canonicalize_contexts
from project.research.knowledge.knobs import build_agent_knob_rows


def _as_str_list(values: Any, *, field_name: str) -> List[str]:
    if values is None:
        return []
    if isinstance(values, str):
        cleaned = values.strip()
        return [cleaned] if cleaned else []
    if not isinstance(values, (list, tuple, set)):
        raise ValueError(f"{field_name} must be a string or list of strings")
    out = [str(value).strip() for value in values if str(value).strip()]
    return out


def _as_int_list(values: Any, *, field_name: str) -> List[int]:
    if values is None:
        return []
    if isinstance(values, (int, float)) and not isinstance(values, bool):
        return [int(values)]
    if not isinstance(values, (list, tuple, set)):
        raise ValueError(f"{field_name} must be an integer or list of integers")
    out: List[int] = []
    for value in values:
        out.append(int(value))
    return out


def _normalize_contexts(values: Any) -> Dict[str, List[str]]:
    if values is None:
        return {}
    if not isinstance(values, dict):
        raise ValueError("contexts must be a mapping of dimension -> allowed values")
    raw_out: Dict[str, List[str]] = {}
    for key, raw in sorted(values.items()):
        name = str(key).strip()
        if not name:
            continue
        raw_out[name] = _as_str_list(raw, field_name=f"contexts.{name}")
    return canonicalize_contexts(raw_out)


def _normalize_trigger_space(values: Any) -> Dict[str, Any]:
    if not isinstance(values, dict):
        raise ValueError("trigger_space must be an object")
    payload = dict(values)
    allowed = _as_str_list(
        payload.get("allowed_trigger_types"), field_name="trigger_space.allowed_trigger_types"
    )
    if not allowed:
        raise ValueError("trigger_space.allowed_trigger_types must be provided")
    payload["allowed_trigger_types"] = [value.upper() for value in allowed]
    for key in (
        "events",
        "canonical_regimes",
        "subtypes",
        "phases",
        "evidence_modes",
        "tiers",
        "operational_roles",
        "deployment_dispositions",
        "states",
        "sequences",
        "transitions",
        "feature_predicates",
        "interactions",
    ):
        payload.setdefault(
            key,
            {}
            if key
            in {"events", "states", "sequences", "transitions", "feature_predicates", "interactions"}
            else [],
        )
    for key in ("canonical_regimes", "subtypes", "phases", "evidence_modes", "tiers", "operational_roles", "deployment_dispositions"):
        payload[key] = _as_str_list(payload.get(key), field_name=f"trigger_space.{key}")
    return payload


def _normalize_promotion_profile(raw: Any) -> str:
    value = str(raw or "research").strip().lower()
    if value in {"off", "disabled", "none"}:
        return "disabled"
    if value in {"research", "deploy"}:
        return value
    raise ValueError(f"Unsupported promotion profile: {raw}")




def _normalize_discovery_profile(raw: Any) -> str:
    value = str(raw or "standard").strip().lower()
    if value not in {"standard", "synthetic"}:
        raise ValueError(f"Unsupported discovery profile: {raw}")
    return value


def _normalize_phase2_gate_profile(raw: Any) -> str:
    value = str(raw or "auto").strip().lower()
    if value not in {"auto", "discovery", "promotion", "synthetic"}:
        raise ValueError(f"Unsupported phase2 gate profile: {raw}")
    return value


def _normalize_config_overlays(values: Any) -> List[str]:
    return _as_str_list(values, field_name="config_overlays")


@dataclass(frozen=True)
class BoundedProposalSpec:
    baseline_run_id: str
    experiment_type: str = "confirmation"
    allowed_change_field: str = ""
    change_reason: str = ""
    compare_to_baseline: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "baseline_run_id": self.baseline_run_id,
            "experiment_type": self.experiment_type,
            "allowed_change_field": self.allowed_change_field,
            "change_reason": self.change_reason,
            "compare_to_baseline": bool(self.compare_to_baseline),
        }


def _normalize_bounded_spec(raw: Any) -> BoundedProposalSpec | None:
    if raw in (None, False, "", {}):
        return None
    if not isinstance(raw, dict):
        raise ValueError("bounded must be an object when provided")
    baseline_run_id = str(raw.get("baseline_run_id", "") or "").strip()
    experiment_type = str(raw.get("experiment_type", "confirmation") or "confirmation").strip().lower()
    allowed_change_field = str(raw.get("allowed_change_field", "") or "").strip()
    change_reason = str(raw.get("change_reason", "") or "").strip()
    compare_to_baseline = bool(raw.get("compare_to_baseline", True))
    if experiment_type not in {"confirmation", "horizon_test", "regime_test", "template_fit_test", "negative_control"}:
        raise ValueError(f"Unsupported bounded.experiment_type: {experiment_type}")
    return BoundedProposalSpec(
        baseline_run_id=baseline_run_id,
        experiment_type=experiment_type,
        allowed_change_field=allowed_change_field,
        change_reason=change_reason,
        compare_to_baseline=compare_to_baseline,
    )

def _proposal_settable_knobs() -> set[str]:
    return {
        str(row.get("name", "")).strip()
        for row in build_agent_knob_rows()
        if str(row.get("mutability", "")).strip() == "proposal_settable"
    }


@dataclass(frozen=True)
class AgentProposal:
    program_id: str
    start: str
    end: str
    symbols: List[str]
    trigger_space: Dict[str, Any]
    templates: List[str]
    description: str = ""
    run_mode: str = "research"
    objective_name: str = "retail_profitability"
    promotion_profile: str = "research"
    timeframe: str = "5m"
    instrument_classes: List[str] = field(default_factory=lambda: ["crypto"])
    horizons_bars: List[int] = field(default_factory=lambda: [12, 24])
    directions: List[str] = field(default_factory=lambda: ["long", "short"])
    entry_lags: List[int] = field(default_factory=lambda: [1])
    contexts: Dict[str, List[str]] = field(default_factory=dict)
    avoid_region_keys: List[str] = field(default_factory=list)
    search_control: Dict[str, int] = field(default_factory=dict)
    artifacts: Dict[str, bool] = field(default_factory=dict)
    knobs: Dict[str, Any] = field(default_factory=dict)
    discovery_profile: str = "standard"
    phase2_gate_profile: str = "auto"
    search_spec: str = "spec/search_space.yaml"
    config_overlays: List[str] = field(default_factory=list)
    bounded: BoundedProposalSpec | None = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "program_id": self.program_id,
            "start": self.start,
            "end": self.end,
            "symbols": list(self.symbols),
            "trigger_space": dict(self.trigger_space),
            "templates": list(self.templates),
            "description": self.description,
            "run_mode": self.run_mode,
            "objective_name": self.objective_name,
            "promotion_profile": self.promotion_profile,
            "timeframe": self.timeframe,
            "instrument_classes": list(self.instrument_classes),
            "horizons_bars": list(self.horizons_bars),
            "directions": list(self.directions),
            "entry_lags": list(self.entry_lags),
            "contexts": dict(self.contexts),
            "avoid_region_keys": list(self.avoid_region_keys),
            "search_control": dict(self.search_control),
            "artifacts": dict(self.artifacts),
            "knobs": dict(self.knobs),
            "discovery_profile": self.discovery_profile,
            "phase2_gate_profile": self.phase2_gate_profile,
            "search_spec": self.search_spec,
            "config_overlays": list(self.config_overlays),
            "bounded": self.bounded.to_dict() if self.bounded is not None else None,
        }


def load_agent_proposal(path_or_payload: str | Path | Dict[str, Any]) -> AgentProposal:
    if isinstance(path_or_payload, dict):
        raw = dict(path_or_payload)
    else:
        path = Path(path_or_payload)
        text = path.read_text(encoding="utf-8")
        if path.suffix.lower() == ".json":
            raw = json.loads(text)
        else:
            raw = yaml.safe_load(text)
    if not isinstance(raw, dict):
        raise ValueError("Proposal must be a JSON/YAML object")

    objective_name = str(
        raw.get("objective_name", raw.get("objective", "retail_profitability"))
        or "retail_profitability"
    ).strip()
    promotion_profile = _normalize_promotion_profile(
        raw.get("promotion_profile", raw.get("promotion_mode", "research"))
    )
    knobs = raw.get("knobs", {}) or {}
    if not isinstance(knobs, dict):
        raise ValueError("knobs must be a mapping of knob_name -> value")
    allowed_knobs = _proposal_settable_knobs()
    invalid_knobs = sorted(str(key) for key in knobs if str(key) not in allowed_knobs)
    if invalid_knobs:
        raise ValueError("Proposal contains non-settable knobs: " + ", ".join(invalid_knobs))

    proposal = AgentProposal(
        program_id=str(raw.get("program_id", "")).strip(),
        start=str(raw.get("start", "")).strip(),
        end=str(raw.get("end", "")).strip(),
        symbols=_as_str_list(raw.get("symbols"), field_name="symbols"),
        trigger_space=_normalize_trigger_space(raw.get("trigger_space")),
        templates=_as_str_list(raw.get("templates"), field_name="templates"),
        description=str(raw.get("description", "") or "").strip(),
        run_mode=str(raw.get("run_mode", "research") or "research").strip(),
        objective_name=objective_name,
        promotion_profile=promotion_profile,
        timeframe=str(raw.get("timeframe", "5m") or "5m").strip(),
        instrument_classes=_as_str_list(
            raw.get("instrument_classes", ["crypto"]),
            field_name="instrument_classes",
        ),
        horizons_bars=_as_int_list(raw.get("horizons_bars", [12, 24]), field_name="horizons_bars"),
        directions=_as_str_list(raw.get("directions", ["long", "short"]), field_name="directions"),
        entry_lags=_as_int_list(raw.get("entry_lags", [1]), field_name="entry_lags"),
        contexts=_normalize_contexts(raw.get("contexts", {})),
        avoid_region_keys=_as_str_list(
            raw.get("avoid_region_keys", []),
            field_name="avoid_region_keys",
        ),
        search_control=dict(raw.get("search_control", {}) or {}),
        artifacts=dict(raw.get("artifacts", {}) or {}),
        knobs={str(key): value for key, value in knobs.items()},
        discovery_profile=_normalize_discovery_profile(raw.get("discovery_profile", "standard")),
        phase2_gate_profile=_normalize_phase2_gate_profile(raw.get("phase2_gate_profile", "auto")),
        search_spec=str(raw.get("search_spec", "spec/search_space.yaml") or "spec/search_space.yaml").strip(),
        config_overlays=_normalize_config_overlays(raw.get("config_overlays", [])),
        bounded=_normalize_bounded_spec(raw.get("bounded")),
    )
    _validate_proposal(proposal)
    return proposal


def _validate_proposal(proposal: AgentProposal) -> None:
    if not proposal.program_id:
        raise ValueError("program_id is required")
    if not proposal.start or not proposal.end:
        raise ValueError("start and end are required")
    if not proposal.symbols:
        raise ValueError("symbols must contain at least one symbol")
    if not proposal.templates:
        raise ValueError("templates must contain at least one template")
    if not proposal.horizons_bars:
        raise ValueError("horizons_bars must contain at least one horizon")
    if not proposal.directions:
        raise ValueError("directions must contain at least one direction")
    if not proposal.entry_lags:
        raise ValueError("entry_lags must contain at least one lag")
    if not proposal.search_spec:
        raise ValueError("search_spec must be provided")
    if proposal.bounded is not None:
        if not proposal.bounded.baseline_run_id:
            raise ValueError("bounded.baseline_run_id is required")
        if not proposal.bounded.allowed_change_field:
            raise ValueError("bounded.allowed_change_field is required")
    invalid_entry_lags = [int(lag) for lag in proposal.entry_lags if int(lag) < 1]
    if invalid_entry_lags:
        raise ValueError("entry_lags must be >= 1 to prevent same-bar entry leakage")
    allowed = set(proposal.trigger_space.get("allowed_trigger_types", []))
    if "EVENT" in allowed:
        has_events = bool(proposal.trigger_space.get("events", {}).get("include"))
        has_regimes = bool(proposal.trigger_space.get("canonical_regimes", []))
        if not has_events and not has_regimes:
            raise ValueError(
                "EVENT trigger proposals must include trigger_space.events.include or trigger_space.canonical_regimes"
            )
    if "STATE" in allowed and not proposal.trigger_space.get("states", {}).get("include"):
        raise ValueError("STATE trigger proposals must include trigger_space.states.include")


def _load_proxy_event_types() -> set[str]:
    """Return event types with evidence_tier=proxy from canonical_event_registry.yaml."""
    from project.spec_registry import load_yaml_relative

    registry = load_yaml_relative("spec/events/canonical_event_registry.yaml")
    meta = registry.get("event_metadata", {})
    return {
        event_type
        for event_type, attrs in meta.items()
        if isinstance(attrs, dict) and attrs.get("evidence_tier") == "proxy"
    }


def validate_proposal_with_warnings(
    path_or_payload: "str | Path | Dict[str, Any]",
) -> list[str]:
    """Validate proposal and return a list of non-fatal advisory warnings.

    Raises ValueError on hard failures (same as load_agent_proposal).
    Returns warnings (not errors) for proxy-tier events.
    """
    proposal = load_agent_proposal(path_or_payload)
    warnings: list[str] = []
    proxy_events = _load_proxy_event_types()
    included_events = set(proposal.trigger_space.get("events", {}).get("include", []))
    for event_type in sorted(included_events & proxy_events):
        warnings.append(
            f"[PROXY_TIER] {event_type} resolves to a proxy detector "
            "(evidence_tier=proxy). Results reflect indirect signal quality."
        )
    return warnings
