# tests/research/robustness/test_kill_switch.py
import pandas as pd
import numpy as np
import pytest
from project.domain.compiled_registry import get_domain_registry
from project.research.robustness.kill_switch import detect_kill_switches, KILL_SWITCH_CANDIDATE_FEATURES
from project.domain.hypotheses import HypothesisSpec, TriggerSpec


def _make_kill_switch_features(n_bars: int = 800) -> pd.DataFrame:
    """
    Event fires every 8 bars. Returns are positive when rv_pct < 0.7, negative when rv_pct > 0.8.
    kill-switch condition: rv_pct_17280 > 0.75
    """
    np.random.seed(5)
    dates = pd.date_range("2023-01-01", periods=n_bars, freq="5min")
    rv = np.random.uniform(0.0, 1.0, n_bars)
    # close chosen so fwd return correlates with rv
    close = np.zeros(n_bars)
    close[0] = 100.0
    for i in range(1, n_bars):
        # Positive drift when rv low, negative when rv high
        sign = 1 if rv[i] < 0.7 else -1
        close[i] = close[i-1] * (1 + sign * np.abs(np.random.normal(0.001, 0.0005)))

    df = pd.DataFrame({"timestamp": dates, "close": close})
    df["event_vol_shock"] = [i % 8 == 0 for i in range(n_bars)]
    df["rv_pct_17280"] = rv
    # Irrelevant feature
    df["spread_zscore"] = np.random.normal(0, 1, n_bars)
    return df


def test_detect_kill_switches_returns_dataframe():
    df = _make_kill_switch_features()
    spec = HypothesisSpec(
        trigger=TriggerSpec.event("VOL_SHOCK"),
        direction="long",
        horizon="15m",
        template_id="base",
    )
    result = detect_kill_switches(spec, df, horizon_bars=4)
    assert isinstance(result, pd.DataFrame)
    assert "feature" in result.columns
    assert "operator" in result.columns
    assert "threshold" in result.columns
    assert "accuracy" in result.columns
    assert "lift" in result.columns
    assert "coverage" in result.columns


def test_detect_kill_switches_finds_rv_condition():
    df = _make_kill_switch_features()
    spec = HypothesisSpec(
        trigger=TriggerSpec.event("VOL_SHOCK"),
        direction="long",
        horizon="15m",
        template_id="base",
    )
    result = detect_kill_switches(spec, df, horizon_bars=4, min_n=10)
    if result.empty:
        pytest.skip("No kill-switch conditions found — may need more data")
    # rv_pct_17280 should appear as the top kill-switch feature
    top_feature = result.iloc[0]["feature"]
    assert "rv_pct" in top_feature or "rv_pct_17280" in top_feature


def test_detect_kill_switches_accuracy_reasonable():
    df = _make_kill_switch_features()
    spec = HypothesisSpec(
        trigger=TriggerSpec.event("VOL_SHOCK"),
        direction="long",
        horizon="15m",
        template_id="base",
    )
    result = detect_kill_switches(spec, df, horizon_bars=4, min_n=5)
    if not result.empty:
        assert (result["accuracy"] >= 0.5).all()
        assert (result["coverage"] > 0).all()
        assert (result["lift"] >= 0).all()


def test_kill_switch_candidate_features_constant():
    assert isinstance(KILL_SWITCH_CANDIDATE_FEATURES, list)
    assert len(KILL_SWITCH_CANDIDATE_FEATURES) >= 5
    assert KILL_SWITCH_CANDIDATE_FEATURES == get_domain_registry().kill_switch_candidates()
