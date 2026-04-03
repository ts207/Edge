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


def _load_proposal_payload(path_or_payload: str | Path | Dict[str, Any]) -> Dict[str, Any]:
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
    return raw


def _as_mapping(values: Any, *, field_name: str) -> Dict[str, Any]:
    if values in (None, "", False):
        return {}
    if not isinstance(values, dict):
        raise ValueError(f"{field_name} must be an object")
    return dict(values)


def _as_single_str(values: Any, *, field_name: str) -> str:
    if isinstance(values, (list, tuple, set, dict)):
        raise ValueError(f"{field_name} must be a single string")
    return str(values or "").strip()


def _as_single_int(
    values: Any,
    *,
    field_name: str,
    minimum: int | None = None,
) -> int:
    if values is None or isinstance(values, bool) or isinstance(values, (list, tuple, set, dict)):
        raise ValueError(f"{field_name} must be a single integer")
    try:
        normalized = int(values)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a single integer") from exc
    if minimum is not None and normalized < minimum:
        raise ValueError(f"{field_name} must be >= {minimum}")
    return normalized


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


@dataclass(frozen=True)
class TriggerSpec:
    type: str
    event_id: str = ""
    state_id: str = ""
    from_state: str = ""
    to_state: str = ""
    feature: str = ""
    operator: str = ""
    threshold: Any = None
    events: List[str] = field(default_factory=list)
    max_gap_bars: int | None = None
    left: str = ""
    right: str = ""
    op: str = ""
    lag: int | None = None
    left_direction: str = ""
    right_direction: str = ""

    def to_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"type": self.type}
        if self.event_id:
            payload["event_id"] = self.event_id
        if self.state_id:
            payload["state_id"] = self.state_id
        if self.from_state:
            payload["from_state"] = self.from_state
        if self.to_state:
            payload["to_state"] = self.to_state
        if self.feature:
            payload["feature"] = self.feature
        if self.operator:
            payload["operator"] = self.operator
        if self.threshold is not None:
            payload["threshold"] = self.threshold
        if self.events:
            payload["events"] = list(self.events)
        if self.max_gap_bars is not None:
            payload["max_gap_bars"] = int(self.max_gap_bars)
        if self.left:
            payload["left"] = self.left
        if self.right:
            payload["right"] = self.right
        if self.op:
            payload["op"] = self.op
        if self.lag is not None:
            payload["lag"] = int(self.lag)
        if self.left_direction:
            payload["left_direction"] = self.left_direction
        if self.right_direction:
            payload["right_direction"] = self.right_direction
        return payload


@dataclass(frozen=True)
class SingleHypothesisSpec:
    trigger: TriggerSpec
    template: str
    direction: str
    horizon_bars: int
    entry_lag_bars: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trigger": self.trigger.to_dict(),
            "template": self.template,
            "direction": self.direction,
            "horizon_bars": int(self.horizon_bars),
            "entry_lag_bars": int(self.entry_lag_bars),
        }


@dataclass(frozen=True)
class SingleHypothesisProposal:
    program_id: str
    start: str
    end: str
    symbols: List[str]
    hypothesis: SingleHypothesisSpec
    description: str = ""
    run_mode: str = "research"
    objective_name: str = "retail_profitability"
    promotion_profile: str = "research"
    timeframe: str = "5m"
    instrument_classes: List[str] = field(default_factory=lambda: ["crypto"])
    contexts: Dict[str, List[str]] = field(default_factory=dict)
    avoid_region_keys: List[str] = field(default_factory=list)
    search_control: Dict[str, Any] = field(default_factory=dict)
    artifacts: Dict[str, Any] = field(default_factory=dict)
    knobs: Dict[str, Any] = field(default_factory=dict)
    discovery_profile: str = "standard"
    phase2_gate_profile: str = "auto"
    search_spec: str = "spec/search_space.yaml"
    config_overlays: List[str] = field(default_factory=list)
    bounded: BoundedProposalSpec | None = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "program_id": self.program_id,
            "description": self.description,
            "start": self.start,
            "end": self.end,
            "symbols": list(self.symbols),
            "timeframe": self.timeframe,
            "instrument_classes": list(self.instrument_classes),
            "hypothesis": self.hypothesis.to_dict(),
            "run_mode": self.run_mode,
            "objective_name": self.objective_name,
            "promotion_profile": self.promotion_profile,
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


def _normalize_trigger_spec(raw: Any) -> TriggerSpec:
    if not isinstance(raw, dict):
        raise ValueError("hypothesis.trigger must be an object")
    trigger_type = _as_single_str(
        raw.get("type", raw.get("trigger_type")),
        field_name="hypothesis.trigger.type",
    ).lower()
    if trigger_type not in {
        "event",
        "state",
        "transition",
        "feature_predicate",
        "sequence",
        "interaction",
    }:
        raise ValueError(f"Unsupported hypothesis.trigger.type: {trigger_type or raw.get('type')}")

    if trigger_type == "event":
        return TriggerSpec(
            type=trigger_type,
            event_id=_as_single_str(raw.get("event_id"), field_name="hypothesis.trigger.event_id"),
        )
    if trigger_type == "state":
        return TriggerSpec(
            type=trigger_type,
            state_id=_as_single_str(raw.get("state_id"), field_name="hypothesis.trigger.state_id"),
        )
    if trigger_type == "transition":
        return TriggerSpec(
            type=trigger_type,
            from_state=_as_single_str(
                raw.get("from_state"), field_name="hypothesis.trigger.from_state"
            ),
            to_state=_as_single_str(raw.get("to_state"), field_name="hypothesis.trigger.to_state"),
        )
    if trigger_type == "feature_predicate":
        return TriggerSpec(
            type=trigger_type,
            feature=_as_single_str(raw.get("feature"), field_name="hypothesis.trigger.feature"),
            operator=_as_single_str(
                raw.get("operator"), field_name="hypothesis.trigger.operator"
            ),
            threshold=raw.get("threshold"),
        )
    if trigger_type == "sequence":
        raw_gap = raw.get("max_gap_bars", raw.get("max_gap"))
        return TriggerSpec(
            type=trigger_type,
            events=_as_str_list(raw.get("events"), field_name="hypothesis.trigger.events"),
            max_gap_bars=(
                None
                if raw_gap in (None, "")
                else _as_single_int(
                    raw_gap,
                    field_name="hypothesis.trigger.max_gap_bars",
                    minimum=0,
                )
            ),
        )
    return TriggerSpec(
        type=trigger_type,
        left=_as_single_str(raw.get("left"), field_name="hypothesis.trigger.left"),
        right=_as_single_str(raw.get("right"), field_name="hypothesis.trigger.right"),
        op=_as_single_str(raw.get("op"), field_name="hypothesis.trigger.op"),
        lag=(
            None
            if raw.get("lag") in (None, "")
            else _as_single_int(raw.get("lag"), field_name="hypothesis.trigger.lag", minimum=0)
        ),
        left_direction=_as_single_str(
            raw.get("left_direction"), field_name="hypothesis.trigger.left_direction"
        ),
        right_direction=_as_single_str(
            raw.get("right_direction"), field_name="hypothesis.trigger.right_direction"
        ),
    )


def _load_single_hypothesis_proposal(
    path_or_payload: str | Path | Dict[str, Any],
) -> SingleHypothesisProposal:
    raw = _load_proposal_payload(path_or_payload)
    hypothesis = _as_mapping(raw.get("hypothesis"), field_name="hypothesis")
    objective_name = str(
        raw.get("objective_name", raw.get("objective", "retail_profitability"))
        or "retail_profitability"
    ).strip()
    promotion_profile = _normalize_promotion_profile(
        raw.get("promotion_profile", raw.get("promotion_mode", "research"))
    )
    knobs = _as_mapping(raw.get("knobs", {}), field_name="knobs")
    allowed_knobs = _proposal_settable_knobs()
    invalid_knobs = sorted(str(key) for key in knobs if str(key) not in allowed_knobs)
    if invalid_knobs:
        raise ValueError("Proposal contains non-settable knobs: " + ", ".join(invalid_knobs))

    proposal = SingleHypothesisProposal(
        program_id=str(raw.get("program_id", "")).strip(),
        description=str(raw.get("description", "") or "").strip(),
        start=str(raw.get("start", "")).strip(),
        end=str(raw.get("end", "")).strip(),
        symbols=_as_str_list(raw.get("symbols"), field_name="symbols"),
        timeframe=str(raw.get("timeframe", "5m") or "5m").strip(),
        instrument_classes=_as_str_list(
            raw.get("instrument_classes", ["crypto"]),
            field_name="instrument_classes",
        ),
        hypothesis=SingleHypothesisSpec(
            trigger=_normalize_trigger_spec(hypothesis.get("trigger")),
            template=_as_single_str(
                hypothesis.get("template"), field_name="hypothesis.template"
            ),
            direction=_as_single_str(
                hypothesis.get("direction"), field_name="hypothesis.direction"
            ),
            horizon_bars=_as_single_int(
                hypothesis.get("horizon_bars"),
                field_name="hypothesis.horizon_bars",
                minimum=1,
            ),
            entry_lag_bars=_as_single_int(
                hypothesis.get("entry_lag_bars"),
                field_name="hypothesis.entry_lag_bars",
                minimum=1,
            ),
        ),
        run_mode=str(raw.get("run_mode", "research") or "research").strip(),
        objective_name=objective_name,
        promotion_profile=promotion_profile,
        contexts=_normalize_contexts(raw.get("contexts", {})),
        avoid_region_keys=_as_str_list(
            raw.get("avoid_region_keys", []),
            field_name="avoid_region_keys",
        ),
        search_control=_as_mapping(raw.get("search_control", {}), field_name="search_control"),
        artifacts=_as_mapping(raw.get("artifacts", {}), field_name="artifacts"),
        knobs={str(key): value for key, value in knobs.items()},
        discovery_profile=_normalize_discovery_profile(raw.get("discovery_profile", "standard")),
        phase2_gate_profile=_normalize_phase2_gate_profile(raw.get("phase2_gate_profile", "auto")),
        search_spec=str(
            raw.get("search_spec", "spec/search_space.yaml") or "spec/search_space.yaml"
        ).strip(),
        config_overlays=_normalize_config_overlays(raw.get("config_overlays", [])),
        bounded=_normalize_bounded_spec(raw.get("bounded")),
    )
    validate_single_hypothesis_proposal(proposal)
    return proposal


def load_agent_proposal(path_or_payload: str | Path | Dict[str, Any]) -> AgentProposal:
    raw = _load_proposal_payload(path_or_payload)
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


def validate_single_hypothesis_proposal(proposal: SingleHypothesisProposal) -> None:
    if not proposal.program_id:
        raise ValueError("program_id is required")
    if not proposal.start or not proposal.end:
        raise ValueError("start and end are required")
    if len(proposal.symbols) != 1:
        raise ValueError("single-hypothesis proposals must contain exactly 1 symbol")
    if not proposal.instrument_classes:
        raise ValueError("instrument_classes must contain at least one class")
    if not proposal.hypothesis.template:
        raise ValueError("hypothesis.template is required")
    if not proposal.hypothesis.direction:
        raise ValueError("hypothesis.direction is required")
    if proposal.hypothesis.horizon_bars < 1:
        raise ValueError("hypothesis.horizon_bars must be >= 1")
    if proposal.hypothesis.entry_lag_bars < 1:
        raise ValueError("hypothesis.entry_lag_bars must be >= 1")
    if not proposal.search_spec:
        raise ValueError("search_spec must be provided")
    if proposal.bounded is not None:
        if not proposal.bounded.baseline_run_id:
            raise ValueError("bounded.baseline_run_id is required")
        if not proposal.bounded.allowed_change_field:
            raise ValueError("bounded.allowed_change_field is required")

    trigger = proposal.hypothesis.trigger
    if trigger.type == "event" and not trigger.event_id:
        raise ValueError("event triggers require hypothesis.trigger.event_id")
    if trigger.type == "state" and not trigger.state_id:
        raise ValueError("state triggers require hypothesis.trigger.state_id")
    if trigger.type == "transition" and (not trigger.from_state or not trigger.to_state):
        raise ValueError(
            "transition triggers require hypothesis.trigger.from_state and hypothesis.trigger.to_state"
        )
    if trigger.type == "feature_predicate":
        if not trigger.feature or not trigger.operator or trigger.threshold is None:
            raise ValueError(
                "feature_predicate triggers require hypothesis.trigger.feature, "
                "hypothesis.trigger.operator, and hypothesis.trigger.threshold"
            )
    if trigger.type == "sequence":
        if len(trigger.events) < 2:
            raise ValueError("sequence triggers require hypothesis.trigger.events with at least 2 events")
    if trigger.type == "interaction" and (not trigger.left or not trigger.right or not trigger.op):
        raise ValueError(
            "interaction triggers require hypothesis.trigger.left, hypothesis.trigger.right, and hypothesis.trigger.op"
        )


def _compile_trigger_spec_to_trigger_space(trigger: TriggerSpec) -> Dict[str, Any]:
    if trigger.type == "event":
        return _normalize_trigger_space(
            {
                "allowed_trigger_types": ["EVENT"],
                "events": {"include": [trigger.event_id]},
            }
        )
    if trigger.type == "state":
        return _normalize_trigger_space(
            {
                "allowed_trigger_types": ["STATE"],
                "states": {"include": [trigger.state_id]},
            }
        )
    if trigger.type == "transition":
        return _normalize_trigger_space(
            {
                "allowed_trigger_types": ["TRANSITION"],
                "transitions": {
                    "include": [
                        {"from_state": trigger.from_state, "to_state": trigger.to_state}
                    ]
                },
            }
        )
    if trigger.type == "feature_predicate":
        return _normalize_trigger_space(
            {
                "allowed_trigger_types": ["FEATURE_PREDICATE"],
                "feature_predicates": {
                    "include": [
                        {
                            "feature": trigger.feature,
                            "operator": trigger.operator,
                            "threshold": trigger.threshold,
                        }
                    ]
                },
            }
        )
    if trigger.type == "sequence":
        sequences: Dict[str, Any] = {"include": [list(trigger.events)]}
        if trigger.max_gap_bars is not None:
            sequences["max_gaps_bars"] = [int(trigger.max_gap_bars)]
        return _normalize_trigger_space(
            {
                "allowed_trigger_types": ["SEQUENCE"],
                "sequences": sequences,
            }
        )
    if trigger.type == "interaction":
        interaction: Dict[str, Any] = {
            "left": trigger.left,
            "right": trigger.right,
            "op": trigger.op.upper(),
        }
        if trigger.lag is not None:
            interaction["lag"] = int(trigger.lag)
        if trigger.left_direction:
            interaction["left_direction"] = trigger.left_direction
        if trigger.right_direction:
            interaction["right_direction"] = trigger.right_direction
        return _normalize_trigger_space(
            {
                "allowed_trigger_types": ["INTERACTION"],
                "interactions": {"include": [interaction]},
            }
        )
    raise ValueError(f"Unsupported trigger type for compilation: {trigger.type}")


def compile_single_hypothesis_to_agent_proposal(
    proposal: SingleHypothesisProposal,
) -> AgentProposal:
    compiled = AgentProposal(
        program_id=proposal.program_id,
        start=proposal.start,
        end=proposal.end,
        symbols=list(proposal.symbols),
        trigger_space=_compile_trigger_spec_to_trigger_space(proposal.hypothesis.trigger),
        templates=[proposal.hypothesis.template],
        description=proposal.description,
        run_mode=proposal.run_mode,
        objective_name=proposal.objective_name,
        promotion_profile=proposal.promotion_profile,
        timeframe=proposal.timeframe,
        instrument_classes=list(proposal.instrument_classes),
        horizons_bars=[int(proposal.hypothesis.horizon_bars)],
        directions=[proposal.hypothesis.direction],
        entry_lags=[int(proposal.hypothesis.entry_lag_bars)],
        contexts=dict(proposal.contexts),
        avoid_region_keys=list(proposal.avoid_region_keys),
        search_control=dict(proposal.search_control),
        artifacts=dict(proposal.artifacts),
        knobs=dict(proposal.knobs),
        discovery_profile=proposal.discovery_profile,
        phase2_gate_profile=proposal.phase2_gate_profile,
        search_spec=proposal.search_spec,
        config_overlays=list(proposal.config_overlays),
        bounded=proposal.bounded,
    )
    _validate_proposal(compiled)
    return compiled


def load_operator_proposal(path_or_payload: str | Path | Dict[str, Any]) -> AgentProposal:
    raw = _load_proposal_payload(path_or_payload)
    if isinstance(raw.get("hypothesis"), dict):
        return compile_single_hypothesis_to_agent_proposal(
            _load_single_hypothesis_proposal(raw)
        )
    return load_agent_proposal(raw)


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
    """Return legacy proxy-tier compatibility events from compiled registry metadata."""
    from project.events.canonical_registry_sidecars import proxy_event_types

    return proxy_event_types()


def validate_proposal_with_warnings(
    path_or_payload: "str | Path | Dict[str, Any]",
) -> list[str]:
    """Validate proposal and return a list of non-fatal advisory warnings.

    Raises ValueError on hard failures (same as load_operator_proposal).
    Returns warnings (not errors) for proxy-tier events.
    """
    proposal = load_operator_proposal(path_or_payload)
    warnings: list[str] = []
    proxy_events = _load_proxy_event_types()
    included_events: set[str] = set()
    for raw_event in proposal.trigger_space.get("events", {}).get("include", []):
        if isinstance(raw_event, dict):
            event_id = str(
                raw_event.get("event_id", raw_event.get("id", raw_event.get("event", ""))) or ""
            ).strip()
        else:
            event_id = str(raw_event).strip()
        if event_id:
            included_events.add(event_id)
    for event_type in sorted(included_events & proxy_events):
        warnings.append(
            f"[PROXY_TIER] {event_type} resolves to a proxy detector "
            "(evidence_tier=proxy). Results reflect indirect signal quality."
        )
    return warnings
