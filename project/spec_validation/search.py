from typing import Any, Dict, List, Optional

from project.domain.compiled_registry import get_domain_registry
from project.spec_validation.ontology import (
    get_event_ids_for_family,
    get_state_ids_for_family,
    get_searchable_event_families,
    get_searchable_state_families,
    get_event_family,
)


def expand_triggers(search_cfg: Dict[str, Any]) -> Dict[str, Any]:
    triggers = search_cfg.get("triggers", {})

    # 1. Expand events — also build event_id → family map
    event_ids: set = set()
    event_family_map: Dict[str, str] = {}
    # From families
    raw_event_fams = triggers.get("event_families", [])
    if raw_event_fams == "*":
        raw_event_fams = get_searchable_event_families()
    for fam in raw_event_fams:
        for eid in get_event_ids_for_family(fam):
            event_ids.add(eid)
            event_family_map[eid] = fam
    # From explicit list
    for eid in triggers.get("events", []):
        event_ids.add(eid)
        if eid not in event_family_map:
            fam = get_event_family(eid)
            if fam:
                event_family_map[eid] = fam

    # 2. Expand states
    state_ids: set = set()
    # From families
    raw_state_fams = triggers.get("state_families", [])
    if raw_state_fams == "*":
        raw_state_fams = get_searchable_state_families()
    for fam in raw_state_fams:
        state_ids.update(get_state_ids_for_family(fam))
    # From explicit list
    state_ids.update(triggers.get("states", []))

    # 3. Transitions
    transition_ids = triggers.get("transitions", [])

    # 4. Feature predicates
    feature_predicates = triggers.get("feature_predicates", [])

    return {
        "events": sorted(list(event_ids)),
        "states": sorted(list(state_ids)),
        "transitions": transition_ids,
        "feature_predicates": feature_predicates,
        "event_family_map": event_family_map,
    }


def resolve_templates(search_cfg: Dict[str, Any]) -> List[str]:
    # Check both 'templates' and 'template_ids' if needed,
    # but generator currently uses 'templates'
    templates = search_cfg.get("templates", [])
    if templates == "*":
        return list(get_domain_registry().default_templates())
    return templates


def resolve_execution_templates(family: str) -> List[str]:
    """
    Return execution template names for a family — allowed_templates minus filter_templates.
    Falls back to the registry defaults if the family has no config.
    """
    return list(get_domain_registry().family_execution_templates(family))


def resolve_filter_templates(family: str) -> List[Dict[str, Any]]:
    """
    Return filter template definitions applicable to a family.
    A filter template is one whose name appears in the family's allowed_templates
    AND has an entry in the registry's filter_templates block.
    Returns list of dicts: {name, feature, operator, threshold}.
    """
    return list(get_domain_registry().family_filter_templates(family))


def resolve_entry_lags(search_cfg: Dict[str, Any]) -> List[int]:
    # Support both 'entry_lag' and legacy 'entry_lags'
    lags = search_cfg.get("entry_lag", search_cfg.get("entry_lags", []))
    if lags == "*":
        return list(get_domain_registry().default_entry_lags())

    if not lags:
        return [1]  # Default to 1 bar lag

    return [lags] if isinstance(lags, int) else lags
