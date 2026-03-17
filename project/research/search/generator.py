"""
Hypothesis generator.

Refactored to support phased search specs, family-based expansion,
sequences, and interactions.
"""
from __future__ import annotations

import logging
from itertools import product
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import yaml

from project.domain.compiled_registry import get_domain_registry
from project.research.search.feasibility import FeasibilityResult, check_hypothesis_feasibility
from project.domain.hypotheses import HypothesisSpec, TriggerSpec, TriggerType
from project.research.search.stage_models import CandidateHypothesis, FeasibilityCheckedHypothesis
from project.research.search.validation import validate_hypothesis_spec
from project.spec_validation.loaders import load_search_spec
from project.spec_validation.search import expand_triggers, resolve_entry_lags, resolve_filter_templates

log = logging.getLogger(__name__)


def _candidate_row(spec: HypothesisSpec, *, search_spec_name: str) -> Dict[str, Any]:
    return CandidateHypothesis(spec=spec, search_spec_name=search_spec_name).to_record()

def _context_combinations(contexts: Dict[str, Any]) -> List[Optional[Dict[str, str]]]:
    """
    Expand contexts dict into a list of conditioning dicts.
    Supports '*' wildcard for expanding all labels in a family.
    """
    if not contexts:
        return [None]

    registry = get_domain_registry()

    keys = list(contexts.keys())
    active_keys = []
    values = []
    for k in keys:
        v = contexts[k]
        if v == "*":
            labels = registry.context_labels_for_family(k)
            if labels:
                active_keys.append(k)
                values.append(list(labels))
            else:
                log.warning("Family %r not found in compiled domain registry context labels. Skipping wildcard expansion for this family.", k)
                # Ensure we don't invent "unknown" labels. Just skip this family from combinations.
                continue
        else:
            active_keys.append(k)
            values.append(v if isinstance(v, list) else [v])
            
    if not values:
        return [None]

    combos: List[Optional[Dict[str, str]]] = []
    for combo in product(*values):
        combos.append(dict(zip(active_keys, combo)))
    return combos


def _build_hypotheses(
    trigger_type: str,
    ids_or_configs: List[Any],
    horizons: List[str],
    directions: List[str],
    entry_lags: List[int],
    contexts: List[Optional[Dict[str, str]]],
    templates: List[str],
) -> Iterable[HypothesisSpec]:
    for item in ids_or_configs:
        if trigger_type == TriggerType.EVENT:
            trigger = TriggerSpec.event(item)
        elif trigger_type == TriggerType.STATE:
            trigger = TriggerSpec.state(item)
        elif trigger_type == TriggerType.TRANSITION:
            trigger = TriggerSpec.transition(from_state=item["from"], to_state=item["to"])
        elif trigger_type == TriggerType.FEATURE_PREDICATE:
            trigger = TriggerSpec.feature_predicate(
                feature=item["feature"],
                operator=item["operator"],
                threshold=item["threshold"]
            )
        elif trigger_type == TriggerType.SEQUENCE:
            trigger = TriggerSpec.sequence(
                sequence_id=item["name"],
                events=item["events"],
                max_gap=item.get("max_gap", [6] * (len(item["events"]) - 1))
            )
        elif trigger_type == TriggerType.INTERACTION:
            trigger = TriggerSpec.interaction(
                interaction_id=item["name"],
                left=item["left"],
                right=item["right"],
                op=item["op"],
                lag=item.get("lag", 6)
            )
        else:
            log.warning("Unsupported trigger_type in _build_hypotheses: %s", trigger_type)
            continue

        for horizon, direction, lag, ctx, template in product(
            horizons, directions, entry_lags, contexts, templates
        ):
            yield HypothesisSpec(
                trigger=trigger,
                direction=direction,
                horizon=horizon,
                template_id=template,
                context=ctx,
                entry_lag=lag,
            )


def load_sequence_registry() -> List[Dict[str, Any]]:
    return get_domain_registry().sequence_rows()

def load_interaction_registry() -> List[Dict[str, Any]]:
    return get_domain_registry().interaction_rows()


def generate_hypotheses_with_audit(
    search_spec_name: str = "full",
    *,
    max_hypotheses: Optional[int] = None,
    skip_invalid: bool = True,
    search_space_path: Optional[Path | str] = None,
    features=None,
) -> Tuple[List[HypothesisSpec], Dict[str, Any]]:
    """
    Generate all hypothesis candidates from a phased search spec.
    """
    if search_space_path:
        from project.spec_registry import load_yaml_path
        doc = load_yaml_path(Path(search_space_path))
    else:
        doc = load_search_spec(search_spec_name)
    
    # Expand triggers from families and explicit lists
    expanded = expand_triggers(doc)
    events = expanded.get("events", [])
    states = expanded.get("states", [])
    transitions = expanded.get("transitions", [])
    feature_predicates = expanded.get("feature_predicates", [])
    event_family_map: Dict[str, str] = expanded.get("event_family_map", {})
    
    # Resolve wildcards
    horizons = [str(h) for h in doc.get("horizons", ["15m"])]
    directions = [str(d) for d in doc.get("directions", ["long", "short"])]
    entry_lags = resolve_entry_lags(doc)
    templates_raw = doc.get("templates", ["base"])
    if isinstance(templates_raw, str):
        templates = ["base"] if templates_raw == "*" else [templates_raw]
    else:
        templates = list(templates_raw)

    raw_contexts = doc.get("contexts", {})
    contexts = _context_combinations(raw_contexts)

    # Budgets and Quotas
    quotas = doc.get("quotas", {})
    template_budgets = doc.get("template_budgets", {})
    
    type_counts: Dict[str, int] = {}
    template_counts: Dict[str, int] = {}

    hypotheses: List[HypothesisSpec] = []
    seen_ids: set = set()
    skipped_invalid = 0
    skipped_dup = 0
    skipped_quota = 0
    skipped_budget = 0
    skipped_cap = 0
    rejection_reason_counts: Dict[str, int] = {}
    generated_rows: List[Dict[str, Any]] = []
    rejected_rows: List[Dict[str, Any]] = []
    feasible_rows: List[Dict[str, Any]] = []

    def _add(spec: HypothesisSpec) -> None:
        nonlocal skipped_invalid, skipped_dup, skipped_quota, skipped_budget, skipped_cap
        generated_rows.append(_candidate_row(spec, search_spec_name=search_spec_name))

        def _record_rejection(reason: str, details: Optional[Dict[str, Any]] = None) -> None:
            rejection_reason_counts[reason] = rejection_reason_counts.get(reason, 0) + 1
            candidate = CandidateHypothesis(spec=spec, search_spec_name=search_spec_name)
            rejected_rows.append(
                FeasibilityCheckedHypothesis(
                    candidate=candidate,
                    feasibility=FeasibilityResult(
                        valid=False,
                        reasons=(reason,),
                        details=dict(details or {}),
                    ),
                ).to_record()
            )

        # 1. Global cap
        if max_hypotheses is not None and len(hypotheses) >= max_hypotheses:
            skipped_cap += 1
            _record_rejection("max_hypotheses_cap")
            return

        # 2. Type Quota
        ttype = spec.trigger.trigger_type
        if ttype in quotas and type_counts.get(ttype, 0) >= quotas[ttype]:
            skipped_quota += 1
            _record_rejection("type_quota")
            return

        # 2b. Template Budget
        tid = spec.template_id
        if tid in template_budgets and template_counts.get(tid, 0) >= template_budgets[tid]:
            skipped_budget += 1
            _record_rejection("template_budget")
            return

        # 3. Validation
        errors = validate_hypothesis_spec(spec)
        if errors:
            if skip_invalid:
                skipped_invalid += 1
                log.debug("Rejecting invalid spec %s: %s", spec.label(), errors)
                _record_rejection("validation_error", {"errors": list(errors)})
                return
            raise ValueError(f"Invalid HypothesisSpec {spec.label()!r}: {errors}")

        feasibility = check_hypothesis_feasibility(spec, features=features)
        if not feasibility.valid:
            if skip_invalid:
                skipped_invalid += 1
                log.debug("Rejecting infeasible spec %s: %s", spec.label(), feasibility.reasons)
                _record_rejection(
                    feasibility.primary_reason or "infeasible",
                    {"reasons": list(feasibility.reasons), **dict(feasibility.details)},
                )
                return
            raise ValueError(
                f"Infeasible HypothesisSpec {spec.label()!r}: {list(feasibility.reasons)}"
            )

        # 4. Deduplication
        hid = spec.hypothesis_id()
        if hid in seen_ids:
            skipped_dup += 1
            _record_rejection("duplicate_hypothesis_id")
            return

        # Success - add
        seen_ids.add(hid)
        hypotheses.append(spec)
        feasible_rows.append(
            FeasibilityCheckedHypothesis(
                candidate=CandidateHypothesis(spec=spec, search_spec_name=search_spec_name),
                feasibility=FeasibilityResult(valid=True),
            ).to_record()
        )
        type_counts[ttype] = type_counts.get(ttype, 0) + 1
        template_counts[tid] = template_counts.get(tid, 0) + 1

    # Build event-led
    for spec in _build_hypotheses(
        TriggerType.EVENT, events, horizons, directions, entry_lags, contexts, templates
    ):
        _add(spec)

    # Build state-led
    for spec in _build_hypotheses(
        TriggerType.STATE, states, horizons, directions, entry_lags, contexts, templates
    ):
        _add(spec)

    # Build transitions
    for spec in _build_hypotheses(
        TriggerType.TRANSITION, transitions, horizons, directions, entry_lags, contexts, templates
    ):
        _add(spec)

    # Build feature predicates
    for spec in _build_hypotheses(
        TriggerType.FEATURE_PREDICATE, feature_predicates, horizons, directions, entry_lags, contexts, templates
    ):
        _add(spec)

    # Build sequences if requested
    if doc.get("include_sequences", False) or search_spec_name == "full":
        sequences = load_sequence_registry()
        for spec in _build_hypotheses(
            TriggerType.SEQUENCE, sequences, horizons, directions, entry_lags, contexts, templates
        ):
            _add(spec)

    # Build interactions if requested
    if doc.get("include_interactions", False) or search_spec_name == "full":
        interactions = load_interaction_registry()
        for spec in _build_hypotheses(
            TriggerType.INTERACTION, interactions, horizons, directions, entry_lags, contexts, templates
        ):
            _add(spec)

    # Pass 2 — filter template hypotheses for events
    # For each event with a known family, generate one hypothesis per filter template
    # applicable to that family, with feature_condition set from the template definition.
    for event_id in events:
        family = event_family_map.get(event_id)
        if not family:
            continue
        filter_templates = resolve_filter_templates(family)
        if not filter_templates:
            continue
        trigger = TriggerSpec.event(event_id)
        for ft in filter_templates:
            fc = TriggerSpec.feature_predicate(
                feature=ft["feature"],
                operator=ft["operator"],
                threshold=ft["threshold"],
            )
            for horizon, direction, lag, ctx in product(
                horizons, directions, entry_lags, contexts
            ):
                _add(HypothesisSpec(
                    trigger=trigger,
                    direction=direction,
                    horizon=horizon,
                    template_id=ft["name"],
                    context=ctx,
                    entry_lag=lag,
                    feature_condition=fc,
                ))

    if skipped_invalid:
        log.warning("Skipped %d invalid HypothesisSpec objects during generation", skipped_invalid)
    if rejection_reason_counts:
        log.warning("Generation rejections by reason: %s", rejection_reason_counts)
    
    log.info(
        "Generated %d hypotheses from search spec '%s' (events=%d states=%d transitions=%d features=%d). "
        "Audit: skipped_cap=%d, skipped_quota=%d, skipped_budget=%d, skipped_dup=%d, skipped_invalid=%d",
        len(hypotheses),
        search_spec_name,
        len(events),
        len(states),
        len(transitions),
        len(feature_predicates),
        skipped_cap,
        skipped_quota,
        skipped_budget,
        skipped_dup,
        skipped_invalid,
    )

    audit = {
        "search_spec_name": search_spec_name,
        "generated_rows": generated_rows,
        "rejected_rows": rejected_rows,
        "feasible_rows": feasible_rows,
        "counts": {
            "generated": int(len(generated_rows)),
            "rejected": int(len(rejected_rows)),
            "feasible": int(len(feasible_rows)),
            "skipped_cap": int(skipped_cap),
            "skipped_quota": int(skipped_quota),
            "skipped_budget": int(skipped_budget),
            "skipped_dup": int(skipped_dup),
            "skipped_invalid": int(skipped_invalid),
        },
        "rejection_reason_counts": dict(rejection_reason_counts),
    }
    return hypotheses, audit


def generate_hypotheses(
    search_spec_name: str = "full",
    *,
    max_hypotheses: Optional[int] = None,
    skip_invalid: bool = True,
    search_space_path: Optional[Path | str] = None,
) -> List[HypothesisSpec]:
    hypotheses, _ = generate_hypotheses_with_audit(
        search_spec_name,
        max_hypotheses=max_hypotheses,
        skip_invalid=skip_invalid,
        search_space_path=search_space_path,
    )
    return hypotheses
