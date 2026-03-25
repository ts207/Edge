import pytest
import project.research.hypothesis_registry
from project.research.hypothesis_registry import Hypothesis
from project.domain.hypotheses import HypothesisSpec, TriggerType


def _make_hypothesis(**overrides):
    defaults = dict(
        event_family="volatility",
        event_type="VOL_SPIKE",
        symbol_scope="BTC",
        side="long",
        horizon="15m",
        condition_template="mean_reversion",
        state_filter="HIGH_VOL_REGIME",
        parameterization_id="p0",
        family_id="fam0",
        cluster_id="cl0",
    )
    return Hypothesis(**{**defaults, **overrides})


def test_to_spec_returns_hypothesis_spec():
    h = _make_hypothesis()
    spec = h.to_spec()
    assert isinstance(spec, HypothesisSpec)


def test_to_spec_trigger_is_event():
    h = _make_hypothesis(event_type="VOL_SPIKE")
    spec = h.to_spec()
    assert spec.trigger.trigger_type == TriggerType.EVENT
    assert spec.trigger.event_id == "VOL_SPIKE"


def test_to_spec_direction_maps_side():
    h = _make_hypothesis(side="short")
    spec = h.to_spec()
    assert spec.direction == "short"


def test_to_spec_horizon_preserved():
    h = _make_hypothesis(horizon="60m")
    spec = h.to_spec()
    assert spec.horizon == "60m"


def test_to_spec_template_preserved():
    h = _make_hypothesis(condition_template="mean_reversion")
    spec = h.to_spec()
    assert spec.template_id == "mean_reversion"


def test_to_spec_state_filter_in_context():
    h = _make_hypothesis(state_filter="HIGH_VOL_REGIME")
    spec = h.to_spec()
    assert spec.context is not None
    assert spec.context.get("state_filter") == "HIGH_VOL_REGIME"


def test_to_spec_null_state_filter_no_context():
    h = _make_hypothesis(state_filter="")
    spec = h.to_spec()
    assert spec.context is None


def test_hypothesis_id_delegates_to_spec():
    h = _make_hypothesis()
    assert h.hypothesis_id() == h.to_spec().hypothesis_id()


def test_hypothesis_id_deterministic():
    h1 = _make_hypothesis()
    h2 = _make_hypothesis()
    assert h1.hypothesis_id() == h2.hypothesis_id()


def test_hypothesis_id_differs_for_different_events():
    h1 = _make_hypothesis(event_type="VOL_SPIKE")
    h2 = _make_hypothesis(event_type="FUNDING_FLIP")
    assert h1.hypothesis_id() != h2.hypothesis_id()
