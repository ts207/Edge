"""Tests for project.research.search.validation."""

from __future__ import annotations

import pytest
from project.domain.hypotheses import HypothesisSpec, TriggerSpec
from project.research.search.validation import validate_hypothesis_spec, assert_valid


def _valid_spec(**overrides) -> HypothesisSpec:
    defaults = dict(
        trigger=TriggerSpec.event("VOL_SPIKE"),
        direction="long",
        horizon="15m",
        template_id="continuation",
        entry_lag=1,
    )
    defaults.update(overrides)
    return HypothesisSpec(**defaults)


def test_valid_spec_produces_no_errors():
    assert validate_hypothesis_spec(_valid_spec()) == []


def test_invalid_direction():
    errors = validate_hypothesis_spec(_valid_spec(direction="up"))
    assert any("direction" in e.lower() for e in errors)


def test_invalid_horizon():
    errors = validate_hypothesis_spec(_valid_spec(horizon="2m"))
    assert any("horizon" in e.lower() for e in errors)


def test_empty_template_id():
    errors = validate_hypothesis_spec(_valid_spec(template_id=""))
    assert any("template_id" in e.lower() for e in errors)


def test_negative_entry_lag():
    errors = validate_hypothesis_spec(_valid_spec(entry_lag=-1))
    assert any("entry_lag" in e.lower() for e in errors)


def test_feature_predicate_invalid_operator():
    spec = _valid_spec(
        trigger=TriggerSpec.feature_predicate(feature="spread_pct", operator="!=", threshold=0.5)
    )
    errors = validate_hypothesis_spec(spec)
    assert any("operator" in e.lower() for e in errors)


def test_feature_predicate_valid_operator():
    spec = _valid_spec(
        trigger=TriggerSpec.feature_predicate(feature="spread_pct", operator=">=", threshold=0.5)
    )
    assert validate_hypothesis_spec(spec) == []


def test_feature_condition_must_be_feature_predicate():
    spec = _valid_spec(feature_condition=TriggerSpec.event("VOL_SPIKE"))
    errors = validate_hypothesis_spec(spec)
    assert any("feature_condition" in e.lower() for e in errors)


def test_feature_condition_valid():
    spec = _valid_spec(
        feature_condition=TriggerSpec.feature_predicate(
            feature="rv_percentile_24h", operator=">=", threshold=0.8
        )
    )
    assert validate_hypothesis_spec(spec) == []


def test_assert_valid_raises_on_invalid():
    with pytest.raises(ValueError, match="Invalid"):
        assert_valid(_valid_spec(direction="sideways"))


def test_assert_valid_passes_on_valid():
    assert_valid(_valid_spec())  # Should not raise


def test_incompatible_template_family_is_reported():
    errors = validate_hypothesis_spec(_valid_spec(template_id="false_breakout_reversal"))
    assert any("incompatible_template_family" in e for e in errors)


def test_all_valid_horizons():
    for h in ("1m", "5m", "15m", "30m", "60m", "1h", "4h", "1d"):
        assert validate_hypothesis_spec(_valid_spec(horizon=h)) == []


def test_all_valid_directions():
    for d in ("long", "short", "both"):
        assert validate_hypothesis_spec(_valid_spec(direction=d)) == []
