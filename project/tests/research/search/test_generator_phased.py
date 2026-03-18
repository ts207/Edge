import pytest
from project.research.search.generator import generate_hypotheses

def test_generate_hypotheses_phase1():
    # Phase 1: Core discovery
    h1 = generate_hypotheses("phase1")
    assert len(h1) > 0
    # Check if some expected event is there
    event_ids = [h.trigger.event_id for h in h1 if h.trigger.event_id]
    assert "VOL_SPIKE" in event_ids

def test_generate_hypotheses_full():
    # Full mode
    h_full = generate_hypotheses("full")
    h_phase1 = generate_hypotheses("phase1")
    # Full should have more hypotheses than phase 1
    assert len(h_full) > len(h_phase1)

def test_generate_hypotheses_wildcards():
    h = generate_hypotheses("phase1")
    # Wildcard context expansion should now yield conditioned hypotheses only.
    assert len(h) > 0
    assert all(h_spec.context is not None for h_spec in h)


def test_context_combinations_scalar_string():
    """Scalar context values must not be iterated as characters."""
    from project.research.search.generator import _context_combinations
    result = _context_combinations({"vol_regime": "low"})
    assert result == [{"vol_regime": "low"}]


def test_context_combinations_mixed_scalar_and_list():
    """Mix of list and scalar context values."""
    from project.research.search.generator import _context_combinations
    result = _context_combinations({"vol_regime": ["low", "high"], "carry_state": "funding_pos"})
    assert len(result) == 2
    assert {"vol_regime": "low", "carry_state": "funding_pos"} in result
    assert {"vol_regime": "high", "carry_state": "funding_pos"} in result


def test_base_hypotheses_use_template_id_base():
    """Pass 1 base hypotheses use template_id='base'; pass 2 filter hypotheses use their filter name."""
    h = generate_hypotheses("smoke_volspike")
    assert len(h) > 0
    # Base hypotheses (no feature_condition) must all have template_id="base"
    base_hypotheses = [spec for spec in h if spec.feature_condition is None]
    assert all(spec.template_id == "base" for spec in base_hypotheses), (
        f"Base hypotheses with non-base template_ids: "
        f"{[spec.template_id for spec in base_hypotheses if spec.template_id != 'base']}"
    )
    # Filter hypotheses must NOT use "base" as their template_id
    filter_hypotheses = [spec for spec in h if spec.feature_condition is not None]
    assert all(spec.template_id != "base" for spec in filter_hypotheses), (
        "Filter hypotheses should carry their filter template name, not 'base'"
    )


def test_no_template_duplication():
    """For smoke_volspike: exactly 1 base hypothesis per (event, direction, horizon, lag, ctx)."""
    h = generate_hypotheses("smoke_volspike")
    # Base hypotheses: 1 event × 2 directions × 1 horizon × 1 lag × 1 ctx = 2
    base_hypotheses = [spec for spec in h if spec.feature_condition is None]
    assert len(base_hypotheses) == 2, (
        f"Expected 2 base hypotheses (no 4× inflation), got {len(base_hypotheses)}"
    )
