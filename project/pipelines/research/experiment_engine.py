from __future__ import annotations

import logging
import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

_LOG = logging.getLogger(__name__)

@dataclass(frozen=True)
class InstrumentScope:
    instrument_classes: List[str]
    symbols: List[str]
    timeframe: str
    start: str
    end: str

@dataclass(frozen=True)
class TriggerSpace:
    allowed_trigger_types: List[str]
    events: Dict[str, List[str]] = field(default_factory=dict)
    sequences: Dict[str, Any] = field(default_factory=dict)
    states: Dict[str, List[str]] = field(default_factory=dict)
    transitions: Dict[str, List[Dict[str, str]]] = field(default_factory=dict)
    feature_predicates: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    interactions: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)

@dataclass(frozen=True)
class TemplateSelection:
    include: List[str]

@dataclass(frozen=True)
class EvaluationConfig:
    horizons_bars: List[int]
    directions: List[str]
    entry_lags: List[int]

@dataclass(frozen=True)
class ContextSelection:
    include: Dict[str, List[str]]

@dataclass(frozen=True)
class SearchControl:
    max_hypotheses_total: int
    max_hypotheses_per_template: int
    max_hypotheses_per_event_family: int
    random_seed: int = 42

@dataclass(frozen=True)
class PromotionConfig:
    enabled: bool
    track: str = "standard"
    multiplicity_scope: str = "program_id"

@dataclass(frozen=True)
class AgentExperimentRequest:
    program_id: str
    run_mode: str
    description: str
    instrument_scope: InstrumentScope
    trigger_space: TriggerSpace
    templates: TemplateSelection
    evaluation: EvaluationConfig
    contexts: ContextSelection
    search_control: SearchControl
    promotion: PromotionConfig
    artifacts: Dict[str, bool] = field(default_factory=dict)

from project.domain.hypotheses import HypothesisSpec, TriggerSpec

@dataclass(frozen=True)
class ValidatedExperimentPlan:
    program_id: str
    hypotheses: List[HypothesisSpec]
    required_detectors: List[str]
    required_features: List[str]
    required_states: List[str]
    estimated_hypothesis_count: int

class RegistryBundle:
    def __init__(self, registry_root: Path):
        self.events = self._load_yaml(registry_root / "events.yaml")
        self.states = self._load_yaml(registry_root / "states.yaml")
        self.features = self._load_yaml(registry_root / "features.yaml")
        self.templates = self._load_yaml(registry_root / "templates.yaml")
        self.contexts = self._load_yaml(registry_root / "contexts.yaml")
        self.limits = self._load_yaml(registry_root / "search_limits.yaml")
        self.detectors = self._load_yaml(registry_root / "detectors.yaml")

    def _load_yaml(self, path: Path) -> Dict[str, Any]:
        if not path.exists():
            _LOG.warning(f"Registry file not found: {path}")
            return {}
        return yaml.safe_load(path.read_text())

def load_agent_experiment_config(path: Path) -> AgentExperimentRequest:
    raw = yaml.safe_load(path.read_text())
    return AgentExperimentRequest(
        program_id=raw["program_id"],
        run_mode=raw["run_mode"],
        description=raw.get("description", ""),
        instrument_scope=InstrumentScope(**raw["instrument_scope"]),
        trigger_space=TriggerSpace(**raw["trigger_space"]),
        templates=TemplateSelection(**raw["templates"]),
        evaluation=EvaluationConfig(**raw["evaluation"]),
        contexts=ContextSelection(**raw["contexts"]),
        search_control=SearchControl(**raw["search_control"]),
        promotion=PromotionConfig(**raw["promotion"]),
        artifacts=raw.get("artifacts", {})
    )

def validate_agent_request(
    request: AgentExperimentRequest,
    registries: RegistryBundle,
) -> None:
    # 1. Platform-level Validations (Invariants)
    _validate_templates(request, registries)
    _validate_instrument_compatibility(request, registries)
    _validate_contexts(request, registries)
    _validate_search_limits(request, registries)

    # 2. Campaign-level Safeguards & State
    _validate_campaign_status(request, registries)
    
    # 3. Proposal Quality Checks (Agent Steering)
    _validate_proposal_quality(request, registries)

    # 4. Trigger-specific validations
    for t_type in request.trigger_space.allowed_trigger_types:
        t_type_upper = t_type.upper()
        if t_type_upper == "EVENT":
            _validate_event_trigger(request, registries)
        elif t_type_upper == "STATE":
            _validate_state_trigger(request, registries)
        elif t_type_upper == "TRANSITION":
            _validate_transition_trigger(request, registries)
        elif t_type_upper == "SEQUENCE":
            _validate_sequence_trigger(request, registries)
        elif t_type_upper == "FEATURE_PREDICATE":
            _validate_feature_predicate_trigger(request, registries)
        elif t_type_upper == "INTERACTION":
            _validate_interaction_trigger(request, registries)
        else:
            raise ValueError(f"Unsupported trigger type in experiment config: {t_type}")

def _validate_campaign_status(request: AgentExperimentRequest, registries: RegistryBundle) -> None:
    from project.core.config import get_data_root
    data_root = get_data_root()
    campaign_dir = data_root / "artifacts" / "experiments" / request.program_id
    ledger_path = campaign_dir / "tested_ledger.parquet"
    state_path = campaign_dir / "campaign_state.json"
    
    # Load state
    current_state = "active"
    if state_path.exists():
        current_state = json.loads(state_path.read_text()).get("state", "active")
        
    if current_state != "active":
        raise ValueError(f"Campaign '{request.program_id}' is in state '{current_state}' and cannot accept new proposals.")

    if ledger_path.exists():
        import pandas as pd
        df = pd.read_parquet(ledger_path)
        
        # Cumulative Budget
        limit_total = registries.limits.get("limits", {}).get("max_hypotheses_total_per_campaign", 5000)
        if len(df) > limit_total:
             # Auto-transition state
             state_path.write_text(json.dumps({"state": "budget_exhausted"}))
             raise ValueError(f"Campaign '{request.program_id}' has exceeded the cumulative limit of {limit_total} hypotheses.")
             
        # Check for failure rates in last 2 runs
        runs = df["run_id"].unique()
        if len(runs) >= 2:
            last_runs = runs[-2:]
            recent = df[df["run_id"].isin(last_runs)]
            
            empty_rate = len(recent[recent["eval_status"] == "empty_sample"]) / len(recent)
            if empty_rate > 0.9:
                state_path.write_text(json.dumps({"state": "halted_empty_sample"}))
                raise ValueError(f"Campaign '{request.program_id}' halted due to excessive empty sample rate.")
            
            unsupported_rate = len(recent[recent["eval_status"] == "unsupported_trigger_evaluator"]) / len(recent)
            if unsupported_rate > 0.5:
                state_path.write_text(json.dumps({"state": "halted_unsupported"}))
                raise ValueError(f"Campaign '{request.program_id}' halted due to excessive unsupported trigger share.")

def _validate_proposal_quality(request: AgentExperimentRequest, registries: RegistryBundle) -> None:
    # Penalize redundancy and low-diversity
    from project.core.config import get_data_root
    data_root = get_data_root()
    ledger_path = data_root / "artifacts" / "experiments" / request.program_id / "tested_ledger.parquet"
    
    if not ledger_path.exists():
        return # First run always accepted
        
    import pandas as pd
    df = pd.read_parquet(ledger_path)
    
    # 1. Retesting exhausted regions
    def get_eid(payload):
        try: return json.loads(payload).get("event_id")
        except: return None
    df["eid"] = df["trigger_payload"].apply(get_eid)
    
    fail_counts = df[df["eval_status"].isin(["empty_sample", "insufficient_sample"])].groupby("eid").size()
    exhausted = set(fail_counts[fail_counts >= 3].index)
    
    requested_events = set(request.trigger_space.events.get("include", []))
    exhausted_overlap = requested_events.intersection(exhausted)
    if len(exhausted_overlap) > len(requested_events) * 0.5:
        raise ValueError(f"Proposal quality rejection: >50% of requested events are already exhausted: {exhausted_overlap}")

    # 2. Material difference from previous run
    runs = df["run_id"].unique()
    if len(runs) > 0:
        last_run = df[df["run_id"] == runs[-1]]
        last_events = set(last_run["eid"].unique())
        if requested_events == last_events:
             _LOG.warning("Proposal quality warning: Requested events are identical to the previous run.")

def _validate_templates(request: AgentExperimentRequest, registries: RegistryBundle) -> None:
    allowed_templates = registries.templates.get("templates", {})
    allowed_trigger_types = set(request.trigger_space.allowed_trigger_types)
    
    for tpl in request.templates.include:
        if tpl not in allowed_templates:
            raise ValueError(f"Template '{tpl}' is not in the authoritative registry.")
        tpl_meta = allowed_templates[tpl]
        if not tpl_meta.get("enabled", True):
            raise ValueError(f"Template '{tpl}' is disabled in the registry.")
        
        # Check trigger type compatibility
        tpl_supported = set(tpl_meta.get("supports_trigger_types", []))
        for t_type in allowed_trigger_types:
            if t_type.upper() not in [s.upper() for s in tpl_supported]:
                raise ValueError(f"Template '{tpl}' does not support trigger type '{t_type}'.")

def _validate_instrument_compatibility(request: AgentExperimentRequest, registries: RegistryBundle) -> None:
    requested_ics = request.instrument_scope.instrument_classes
    
    # Check events
    allowed_events = registries.events.get("events", {})
    for event_id in request.trigger_space.events.get("include", []):
        if event_id not in allowed_events:
            continue # Let _validate_event_trigger handle it
        event_meta = allowed_events.get(event_id, {})
        event_ics = event_meta.get("instrument_classes", [])
        for ic in requested_ics:
            if ic not in event_ics:
                raise ValueError(f"Event '{event_id}' is not allowed for instrument class '{ic}'.")

    # Check states
    allowed_states = registries.states.get("states", {})
    for state_id in request.trigger_space.states.get("include", []):
        if state_id not in allowed_states:
            continue # Let _validate_state_trigger handle it
        state_meta = allowed_states.get(state_id, {})
        state_ics = state_meta.get("instrument_classes", [])
        for ic in requested_ics:
            if ic not in state_ics:
                raise ValueError(f"State '{state_id}' is not allowed for instrument class '{ic}'.")

def _validate_contexts(request: AgentExperimentRequest, registries: RegistryBundle) -> None:
    allowed_contexts = registries.contexts.get("context_dimensions", {})
    for dim, values in request.contexts.include.items():
        if dim not in allowed_contexts:
            raise ValueError(f"Context dimension '{dim}' is not in the authoritative registry.")
        for val in values:
            if val not in allowed_contexts[dim].get("allowed_values", []):
                raise ValueError(f"Value '{val}' is not allowed for context dimension '{dim}'.")

def _validate_search_limits(request: AgentExperimentRequest, registries: RegistryBundle) -> None:
    limits = registries.limits.get("limits", {})
    
    if len(request.trigger_space.events.get("include", [])) > limits.get("max_events_per_run", 100):
        raise ValueError("Exceeded max_events_per_run limit.")
    if len(request.templates.include) > limits.get("max_templates_per_run", 100):
        raise ValueError("Exceeded max_templates_per_run limit.")
    if len(request.evaluation.horizons_bars) > limits.get("max_horizons_per_run", 10):
        raise ValueError("Exceeded max_horizons_per_run limit.")
    if len(request.evaluation.directions) > limits.get("max_directions_per_run", 2):
        raise ValueError("Exceeded max_directions_per_run limit.")

def _validate_event_trigger(request: AgentExperimentRequest, registries: RegistryBundle) -> None:
    allowed_events = registries.events.get("events", {})
    requested = request.trigger_space.events.get("include", [])
    if not requested:
         raise ValueError("Trigger type EVENT enabled but no events included.")
    for event_id in requested:
        if event_id not in allowed_events:
            raise ValueError(f"Event ID '{event_id}' is not in the authoritative registry.")
        if not allowed_events[event_id].get("enabled", True):
            raise ValueError(f"Event ID '{event_id}' is disabled.")

def _validate_state_trigger(request: AgentExperimentRequest, registries: RegistryBundle) -> None:
    allowed_states = registries.states.get("states", {})
    requested = request.trigger_space.states.get("include", [])
    if not requested:
        raise ValueError("Trigger type STATE enabled but no states included.")
    for state_id in requested:
        if state_id not in allowed_states:
            raise ValueError(f"State ID '{state_id}' is not in the authoritative registry.")
        if not allowed_states[state_id].get("enabled", True):
            raise ValueError(f"State ID '{state_id}' is disabled.")

def _validate_transition_trigger(request: AgentExperimentRequest, registries: RegistryBundle) -> None:
    allowed_states = registries.states.get("states", {})
    requested = request.trigger_space.transitions.get("include", [])
    if not requested:
        raise ValueError("Trigger type TRANSITION enabled but no transitions included.")
    for trans in requested:
        from_s = trans.get("from_state")
        to_s = trans.get("to_state")
        if not from_s or not to_s:
            raise ValueError("Transition must specify from_state and to_state.")
        if from_s not in allowed_states:
            raise ValueError(f"Transition from_state '{from_s}' unknown.")
        if to_s not in allowed_states:
            raise ValueError(f"Transition to_state '{to_s}' unknown.")

def _validate_sequence_trigger(request: AgentExperimentRequest, registries: RegistryBundle) -> None:
    allowed_events = registries.events.get("events", {})
    seq_config = request.trigger_space.sequences
    requested = seq_config.get("include", [])
    if not requested:
        raise ValueError("Trigger type SEQUENCE enabled but no sequences included.")
    
    max_len = registries.limits.get("limits", {}).get("max_sequence_length", 5)
    
    for seq in requested:
        if not isinstance(seq, list):
             raise ValueError("Sequence inclusion must be a list of event IDs.")
        if len(seq) > max_len:
            raise ValueError(f"Sequence length {len(seq)} exceeds limit {max_len}.")
        for event_id in seq:
            if event_id not in allowed_events:
                raise ValueError(f"Sequence contains unknown event ID '{event_id}'.")
            if not allowed_events[event_id].get("sequence_eligible", True):
                raise ValueError(f"Event '{event_id}' is not sequence-eligible.")

def _validate_feature_predicate_trigger(request: AgentExperimentRequest, registries: RegistryBundle) -> None:
    allowed_features = registries.features.get("features", {})
    requested = request.trigger_space.feature_predicates.get("include", [])
    if not requested:
        raise ValueError("Trigger type FEATURE_PREDICATE enabled but no predicates included.")
    
    for pred in requested:
        feat_id = pred.get("feature")
        op = pred.get("operator")
        if not feat_id or not op:
            raise ValueError("Feature predicate must specify feature and operator.")
        if feat_id not in allowed_features:
            raise ValueError(f"Feature '{feat_id}' is not in the authoritative registry.")
        
        feat_meta = allowed_features[feat_id]
        if op not in feat_meta.get("allowed_operators", []):
            raise ValueError(f"Operator '{op}' not allowed for feature '{feat_id}'.")

def _validate_interaction_trigger(request: AgentExperimentRequest, registries: RegistryBundle) -> None:
    allowed_events = registries.events.get("events", {})
    allowed_states = registries.states.get("states", {})
    requested = request.trigger_space.interactions.get("include", [])
    if not requested:
        raise ValueError("Trigger type INTERACTION enabled but no interactions included.")
    
    for inter in requested:
        left = inter.get("left")
        right = inter.get("right")
        op = inter.get("op")
        if not left or not right or not op:
            raise ValueError("Interaction must specify left, right, and op.")
        
        if op.upper() not in ["AND", "CONFIRM", "EXCLUDE"]:
             raise ValueError(f"Unsupported interaction operator '{op}'.")
        
        # Binary interaction validation: depth = 1 check (operands must be events or states)
        for operand in [left, right]:
            if operand not in allowed_events and operand not in allowed_states:
                raise ValueError(f"Interaction operand '{operand}' must be a known EVENT or STATE.")

def expand_hypotheses(
    request: AgentExperimentRequest,
    registries: RegistryBundle,
) -> List[HypothesisSpec]:
    hypotheses = []
    
    # Resolve context slices (Cartesian product of selected values)
    import itertools
    context_keys = sorted(request.contexts.include.keys())
    context_values = [request.contexts.include[k] for k in context_keys]
    context_slices = [dict(zip(context_keys, v)) for v in itertools.product(*context_values)]
    if not context_slices:
        context_slices = [None]

    for t_type in request.trigger_space.allowed_trigger_types:
        t_type_upper = t_type.upper()
        if t_type_upper == "EVENT":
            hypotheses.extend(_expand_event_triggers(request, context_slices))
        elif t_type_upper == "STATE":
            hypotheses.extend(_expand_state_triggers(request, context_slices))
        elif t_type_upper == "TRANSITION":
            hypotheses.extend(_expand_transition_triggers(request, context_slices))
        elif t_type_upper == "SEQUENCE":
            hypotheses.extend(_expand_sequence_triggers(request, context_slices))
        elif t_type_upper == "FEATURE_PREDICATE":
            hypotheses.extend(_expand_feature_predicate_triggers(request, context_slices))
        elif t_type_upper == "INTERACTION":
            hypotheses.extend(_expand_interaction_triggers(request, context_slices))

    # Apply search budget
    max_total = request.search_control.max_hypotheses_total
    if len(hypotheses) > max_total:
        _LOG.warning(f"Truncating hypotheses expansion from {len(hypotheses)} to {max_total}")
        # TODO: Better selection strategy (e.g. balanced across templates)
        hypotheses = hypotheses[:max_total]
        
    return hypotheses

def _expand_event_triggers(request: AgentExperimentRequest, context_slices: List[Optional[Dict[str, str]]]) -> List[HypothesisSpec]:
    hyps = []
    requested_events = request.trigger_space.events.get("include", [])
    for event_id in requested_events:
        for tpl in request.templates.include:
            for horizon in request.evaluation.horizons_bars:
                for direction in request.evaluation.directions:
                    for lag in request.evaluation.entry_lags:
                        for ctx in context_slices:
                            trigger = TriggerSpec.event(event_id)
                            hyps.append(HypothesisSpec(
                                trigger=trigger,
                                direction=direction,
                                horizon=f"{horizon}b",
                                template_id=tpl,
                                entry_lag=lag,
                                context=ctx
                            ))
    return hyps

def _expand_state_triggers(request: AgentExperimentRequest, context_slices: List[Optional[Dict[str, str]]]) -> List[HypothesisSpec]:
    hyps = []
    requested_states = request.trigger_space.states.get("include", [])
    for state_id in requested_states:
        for tpl in request.templates.include:
            for horizon in request.evaluation.horizons_bars:
                for direction in request.evaluation.directions:
                    for lag in request.evaluation.entry_lags:
                        for ctx in context_slices:
                            trigger = TriggerSpec.state(state_id)
                            hyps.append(HypothesisSpec(
                                trigger=trigger,
                                direction=direction,
                                horizon=f"{horizon}b",
                                template_id=tpl,
                                entry_lag=lag,
                                context=ctx
                            ))
    return hyps

def _expand_transition_triggers(request: AgentExperimentRequest, context_slices: List[Optional[Dict[str, str]]]) -> List[HypothesisSpec]:
    hyps = []
    requested_transitions = request.trigger_space.transitions.get("include", [])
    for trans in requested_transitions:
        from_s = trans["from_state"]
        to_s = trans["to_state"]
        for tpl in request.templates.include:
            for horizon in request.evaluation.horizons_bars:
                for direction in request.evaluation.directions:
                    for lag in request.evaluation.entry_lags:
                        for ctx in context_slices:
                            trigger = TriggerSpec.transition(from_s, to_s)
                            hyps.append(HypothesisSpec(
                                trigger=trigger,
                                direction=direction,
                                horizon=f"{horizon}b",
                                template_id=tpl,
                                entry_lag=lag,
                                context=ctx
                            ))
    return hyps

def _expand_sequence_triggers(request: AgentExperimentRequest, context_slices: List[Optional[Dict[str, str]]]) -> List[HypothesisSpec]:
    hyps = []
    seq_config = request.trigger_space.sequences
    requested_sequences = seq_config.get("include", [])
    max_gaps = seq_config.get("max_gaps_bars", [1])
    
    for seq_events in requested_sequences:
        for gap in max_gaps:
            # Generate deterministic sequence ID
            import hashlib
            payload = "|".join(seq_events) + f"|gap={gap}"
            seq_id = "SEQ_" + hashlib.sha256(payload.encode()).hexdigest()[:12].upper()
            
            # Domain TriggerSpec.sequence takes List[int] for max_gap if length matches
            gaps_list = [gap] * (len(seq_events) - 1)
            
            for tpl in request.templates.include:
                for horizon in request.evaluation.horizons_bars:
                    for direction in request.evaluation.directions:
                        for lag in request.evaluation.entry_lags:
                            for ctx in context_slices:
                                trigger = TriggerSpec.sequence(seq_id, seq_events, gaps_list)
                                hyps.append(HypothesisSpec(
                                    trigger=trigger,
                                    direction=direction,
                                    horizon=f"{horizon}b",
                                    template_id=tpl,
                                    entry_lag=lag,
                                    context=ctx
                                ))
    return hyps

def _expand_feature_predicate_triggers(request: AgentExperimentRequest, context_slices: List[Optional[Dict[str, str]]]) -> List[HypothesisSpec]:
    hyps = []
    requested_preds = request.trigger_space.feature_predicates.get("include", [])
    for pred in requested_preds:
        feat = pred["feature"]
        op = pred["operator"]
        threshold = pred["threshold"]
        for tpl in request.templates.include:
            for horizon in request.evaluation.horizons_bars:
                for direction in request.evaluation.directions:
                    for lag in request.evaluation.entry_lags:
                        for ctx in context_slices:
                            trigger = TriggerSpec.feature_predicate(feat, op, threshold)
                            hyps.append(HypothesisSpec(
                                trigger=trigger,
                                direction=direction,
                                horizon=f"{horizon}b",
                                template_id=tpl,
                                entry_lag=lag,
                                context=ctx
                            ))
    return hyps

def _expand_interaction_triggers(request: AgentExperimentRequest, context_slices: List[Optional[Dict[str, str]]]) -> List[HypothesisSpec]:
    hyps = []
    requested_inters = request.trigger_space.interactions.get("include", [])
    for inter in requested_inters:
        left = inter["left"]
        right = inter["right"]
        op = inter["op"]
        lag = inter.get("lag", 6)
        
        # Generate deterministic interaction ID
        import hashlib
        payload = f"{left}|{op}|{right}|lag={lag}"
        int_id = "INT_" + hashlib.sha256(payload.encode()).hexdigest()[:12].upper()

        for tpl in request.templates.include:
            for horizon in request.evaluation.horizons_bars:
                for direction in request.evaluation.directions:
                    for lag_e in request.evaluation.entry_lags:
                        for ctx in context_slices:
                            trigger = TriggerSpec.interaction(int_id, left, right, op, lag)
                            hyps.append(HypothesisSpec(
                                trigger=trigger,
                                direction=direction,
                                horizon=f"{horizon}b",
                                template_id=tpl,
                                entry_lag=lag_e,
                                context=ctx
                            ))
    return hyps

def resolve_required_detectors(
    hypotheses: List[HypothesisSpec],
    registries: RegistryBundle,
) -> List[str]:
    detector_map = registries.detectors.get("detector_ownership", {})
    required = set()
    for h in hypotheses:
        t = h.trigger
        if t.trigger_type == "event":
            det = detector_map.get(t.event_id)
            if det:
                required.add(det)
        elif t.trigger_type == "sequence":
            required.add("EventSequenceDetector")
            if t.events:
                for eid in t.events:
                    det = detector_map.get(eid)
                    if det:
                        required.add(det)
        elif t.trigger_type == "interaction":
            required.add("EventInteractionDetector")
            for operand in [t.left, t.right]:
                det = detector_map.get(operand)
                if det:
                    required.add(det)
            
    return sorted(list(required))

def resolve_required_features(
    hypotheses: List[HypothesisSpec],
    registries: RegistryBundle,
) -> List[str]:
    required = set()
    event_meta = registries.events.get("events", {})
    
    for h in hypotheses:
        t = h.trigger
        # 1. Direct feature predicates
        if t.trigger_type == "feature_predicate":
            if t.feature:
                required.add(t.feature)
        
        # 2. Event dependencies
        if t.trigger_type == "event":
            meta = event_meta.get(t.event_id, {})
            for f in meta.get("requires_features", []):
                required.add(f)
        
        # 3. Sequence constituent dependencies
        if t.trigger_type == "sequence" and t.events:
            for eid in t.events:
                meta = event_meta.get(eid, {})
                for f in meta.get("requires_features", []):
                    required.add(f)
                    
        # 4. Interaction operand dependencies
        if t.trigger_type == "interaction":
            for operand in [t.left, t.right]:
                meta = event_meta.get(operand, {})
                for f in meta.get("requires_features", []):
                    required.add(f)

    return sorted(list(required))

def resolve_required_states(
    hypotheses: List[HypothesisSpec],
    registries: RegistryBundle,
) -> List[str]:
    required = set()
    for h in hypotheses:
        t = h.trigger
        if t.trigger_type == "state":
            if t.state_id:
                required.add(t.state_id)
        elif t.trigger_type == "transition":
            if t.from_state:
                required.add(t.from_state)
            if t.to_state:
                required.add(t.to_state)
        elif t.trigger_type == "interaction":
            state_registry = registries.states.get("states", {})
            for operand in [t.left, t.right]:
                if operand in state_registry:
                    required.add(operand)
                    
    return sorted(list(required))

def export_experiment_artifacts(
    plan: ValidatedExperimentPlan,
    config_path: Path,
    registry_root: Path,
    out_dir: Path,
) -> None:
    import shutil
    import hashlib
    import json
    import pandas as pd
    
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. request.yaml
    shutil.copy(config_path, out_dir / "request.yaml")
    
    # 2. hashes
    req_bytes = (out_dir / "request.yaml").read_bytes()
    (out_dir / "request_hash.txt").write_text(hashlib.sha256(req_bytes).hexdigest())
    
    reg_hash = hashlib.sha256()
    for y in sorted(registry_root.glob("*.yaml")):
        reg_hash.update(y.name.encode("utf-8"))
        reg_hash.update(y.read_bytes())
    (out_dir / "registry_hash.txt").write_text(reg_hash.hexdigest())
    
    # 3. Validated plan & execution requirements
    plan_dict = {
        "program_id": plan.program_id,
        "estimated_hypothesis_count": plan.estimated_hypothesis_count,
        "required_detectors": plan.required_detectors,
        "required_features": plan.required_features,
        "required_states": plan.required_states,
    }
    (out_dir / "validated_plan.json").write_text(json.dumps(plan_dict, indent=2))
    
    req_dict = {
        "detectors": plan.required_detectors,
        "features": plan.required_features,
        "state_engines": plan.required_states,
    }
    (out_dir / "execution_requirements.json").write_text(json.dumps(req_dict, indent=2))
    
    # 4. Expanded hypotheses
    rows = []
    for h in plan.hypotheses:
        row = h.to_dict()
        row["hypothesis_id"] = h.hypothesis_id()
        row["trigger_type"] = h.trigger.trigger_type
        row["context_slice"] = json.dumps(h.context) if h.context else None
        row["trigger_payload"] = json.dumps(h.trigger.to_dict())
        
        # Clean up nested dicts to keep parquet flat
        if "trigger" in row: del row["trigger"]
        if "feature_condition" in row: del row["feature_condition"]
        if "context" in row: del row["context"]
        
        rows.append(row)
        
    df = pd.DataFrame(rows)
    # Ensure all required schema columns even if empty
    for col in ["hypothesis_id", "trigger_type", "trigger_payload", "template_id", "horizon", "direction", "entry_lag", "context_slice"]:
        if col not in df.columns:
            df[col] = None
            
    from project.io.utils import write_parquet
    write_parquet(df, out_dir / "expanded_hypotheses.parquet")

def build_experiment_plan(config_path: Path, registry_root: Path, out_dir: Optional[Path] = None) -> ValidatedExperimentPlan:
    registries = RegistryBundle(registry_root)
    request = load_agent_experiment_config(config_path)
    validate_agent_request(request, registries)
    hypotheses = expand_hypotheses(request, registries)
    
    detectors = resolve_required_detectors(hypotheses, registries)
    features = resolve_required_features(hypotheses, registries)
    states = resolve_required_states(hypotheses, registries)
    
    plan = ValidatedExperimentPlan(
        program_id=request.program_id,
        hypotheses=hypotheses,
        required_detectors=detectors,
        required_features=features,
        required_states=states,
        estimated_hypothesis_count=len(hypotheses)
    )
    
    if out_dir:
        export_experiment_artifacts(plan, config_path, registry_root, out_dir)
        
    return plan
