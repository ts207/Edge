# tests/research/robustness/test_robustness_scorer.py
import pandas as pd
import numpy as np
import pytest
from project.research.robustness.robustness_scorer import compute_robustness_score


def _make_regime_results(
    regimes: list[str],
    mean_returns: list[float],
    t_stats: list[float],
    ns: list[int],
    overall_direction: float = 1.0,
) -> pd.DataFrame:
    """Build a per-regime results DataFrame for testing the scorer."""
    valid = [abs(t) > 0.5 and n >= 10 for t, n in zip(t_stats, ns)]
    return pd.DataFrame({
        "regime": regimes,
        "n": ns,
        "mean_return_bps": mean_returns,
        "t_stat": t_stats,
        "hit_rate": [0.55 if mr > 0 else 0.45 for mr in mean_returns],
        "valid": valid,
    })


def test_perfect_robustness():
    """Hypothesis positive in all regimes → score near 1.0."""
    df = _make_regime_results(
        regimes=["high_vol.funding_pos.trend.tight", "low_vol.funding_neg.chop.wide"],
        mean_returns=[20.0, 15.0],
        t_stats=[3.5, 2.1],
        ns=[100, 80],
    )
    score = compute_robustness_score(df, overall_direction=1.0)
    assert score >= 0.8


def test_all_regimes_wrong_direction():
    """Hypothesis negative in all regimes → score near 0."""
    # Note: Scorer should penalize regimes that go against overall direction
    df = _make_regime_results(
        regimes=["high_vol.funding_pos.trend.tight", "low_vol.funding_neg.chop.wide"],
        mean_returns=[-20.0, -15.0],
        t_stats=[-3.5, -2.1],
        ns=[100, 80],
    )
    score = compute_robustness_score(df, overall_direction=1.0)
    assert score < 0.3


def test_mixed_regime_score():
    """Half regimes positive, half negative → intermediate score."""
    df = _make_regime_results(
        regimes=["r1", "r2", "r3", "r4"],
        mean_returns=[20.0, 15.0, -10.0, -8.0],
        t_stats=[2.5, 2.0, -1.8, -1.5],
        ns=[80, 70, 60, 55],
    )
    score = compute_robustness_score(df, overall_direction=1.0)
    assert 0.3 < score < 0.8


def test_no_valid_regimes_returns_zero():
    """No valid regime results → score = 0."""
    df = pd.DataFrame({
        "regime": ["r1"], "n": [3],
        "mean_return_bps": [10.0], "t_stat": [1.0],
        "hit_rate": [0.6], "valid": [False],
    })
    score = compute_robustness_score(df, overall_direction=1.0)
    assert score == 0.0


def test_score_bounded():
    """Score must be in [0, 1]."""
    df = _make_regime_results(
        regimes=["r1", "r2"],
        mean_returns=[50.0, 40.0],
        t_stats=[5.0, 4.0],
        ns=[200, 150],
    )
    score = compute_robustness_score(df, overall_direction=1.0)
    assert 0.0 <= score <= 1.0
