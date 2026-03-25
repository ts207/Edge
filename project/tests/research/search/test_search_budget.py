"""
E5-T1: Search-budget controls and family quotas.

The hypothesis generator must support:
  - Global max_hypotheses cap (already exists but verify it works as intended).
  - Family-level quotas (event, state, transition, feature).
  - Template-level budgets.
"""

from __future__ import annotations

import yaml
import pytest
from pathlib import Path
from project.research.search.generator import generate_hypotheses


def _write_spec(tmp_path: Path, doc: dict) -> Path:
    p = tmp_path / "search_space.yaml"
    p.write_text(yaml.dump(doc), encoding="utf-8")
    return p


@pytest.fixture
def base_spec_doc():
    return {
        "triggers": {
            "events": ["VOL_SHOCK", "BASIS_DISLOC", "LIQUIDITY_VACUUM"],
            "states": ["AFTERSHOCK_STATE", "EXHAUSTION_STATE"],
            "transitions": [{"from": "AFTERSHOCK_STATE", "to": "EXHAUSTION_STATE"}],
            "feature_predicates": [
                {"feature": "f1", "operator": ">", "threshold": 2.0},
                {"feature": "f2", "operator": "<", "threshold": -1.0},
            ],
        },
        "templates": ["mean_reversion", "continuation"],
        "horizons": ["5m"],
        "directions": ["long"],
        "entry_lags": [1],
    }


def test_global_max_hypotheses(tmp_path, base_spec_doc):
    """max_hypotheses must cap the total number of generated hypotheses."""
    spec_path = _write_spec(tmp_path, base_spec_doc)

    all_hyp = generate_hypotheses(spec_path)
    # The generator now adds valid event-specific template expansions in addition
    # to the base event/state/transition/feature combinations.
    assert len(all_hyp) > 16

    capped_hyp = generate_hypotheses(spec_path, max_hypotheses=5)
    assert len(capped_hyp) == 5


def test_family_quotas(tmp_path, base_spec_doc):
    """
    The search space spec can define quotas per trigger family.
    If 'quotas' is present in the spec, the generator must respect them.
    """
    doc = base_spec_doc.copy()
    doc["quotas"] = {
        "event": 2,
        "state": 1,
        "transition": 0,
        "feature_predicate": 10,  # more than available
    }
    spec_path = _write_spec(tmp_path, doc)

    hypotheses = generate_hypotheses(spec_path)

    # Quotas are applied to the number of TRIGGERS (or unique triggers * templates combos?)
    # Usually quotas apply to the final count of hypotheses per family.

    events = [h for h in hypotheses if h.trigger.trigger_type == "event"]
    states = [h for h in hypotheses if h.trigger.trigger_type == "state"]
    transitions = [h for h in hypotheses if h.trigger.trigger_type == "transition"]
    features = [h for h in hypotheses if h.trigger.trigger_type == "feature_predicate"]

    assert len(events) == 2
    assert len(states) == 1
    assert len(transitions) == 0
    assert len(features) == 4  # available was 4, quota was 10


def test_template_budgets(tmp_path, base_spec_doc):
    """
    The search space spec can define budgets per template.
    """
    uncapped_spec_path = _write_spec(tmp_path, base_spec_doc)
    uncapped = generate_hypotheses(uncapped_spec_path)
    uncapped_by_template = {
        template_id: len([h for h in uncapped if h.template_id == template_id])
        for template_id in {h.template_id for h in uncapped}
    }

    doc = base_spec_doc.copy()
    doc["template_budgets"] = {"mean_reversion": 3, "continuation": 100}
    spec_path = _write_spec(tmp_path, doc)

    hypotheses = generate_hypotheses(spec_path)

    t1_hyp = [h for h in hypotheses if h.template_id == "mean_reversion"]
    t2_hyp = [h for h in hypotheses if h.template_id == "continuation"]

    assert len(t1_hyp) == 3
    # Continuation should remain uncapped; current totals reflect valid generated
    # hypotheses after validation, not a fixed pre-expansion template count.
    assert len(t2_hyp) == uncapped_by_template["continuation"]
