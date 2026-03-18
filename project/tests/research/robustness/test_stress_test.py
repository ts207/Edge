# tests/research/robustness/test_stress_test.py
import pandas as pd
import numpy as np
import pytest
from project.domain.compiled_registry import get_domain_registry
from project.research.robustness.stress_test import evaluate_stress_scenarios, STRESS_SCENARIOS
from project.domain.hypotheses import HypothesisSpec, TriggerSpec


def _make_stress_features(n_bars: int = 500) -> pd.DataFrame:
    np.random.seed(42)
    dates = pd.date_range("2023-01-01", periods=n_bars, freq="5min")
    close = 100.0 + np.cumsum(np.random.normal(0.03, 0.1, n_bars))
    df = pd.DataFrame({"timestamp": dates, "close": close})
    df["event_vol_shock"] = [i % 8 == 0 for i in range(n_bars)]
    # High vol only in first 200 bars (stress period)
    df["rv_pct_17280"] = [0.95] * 200 + [0.3] * 300
    # Normal spread everywhere
    df["spread_zscore"] = np.random.normal(0, 0.5, n_bars)
    return df


def test_evaluate_stress_scenarios_returns_dataframe():
    df = _make_stress_features()
    spec = HypothesisSpec(
        trigger=TriggerSpec.event("VOL_SHOCK"),
        direction="long",
        horizon="15m",
        template_id="base",
    )
    result = evaluate_stress_scenarios(spec, df, horizon_bars=3)
    assert isinstance(result, pd.DataFrame)
    assert "scenario" in result.columns
    assert "n" in result.columns
    assert "t_stat" in result.columns
    assert "mean_return_bps" in result.columns
    assert "valid" in result.columns


def test_stress_scenarios_constant_exists():
    assert isinstance(STRESS_SCENARIOS, list)
    assert len(STRESS_SCENARIOS) >= 3
    assert STRESS_SCENARIOS == get_domain_registry().stress_scenario_rows()
    for scenario in STRESS_SCENARIOS:
        assert "name" in scenario
        assert "feature" in scenario
        assert "operator" in scenario
        assert "threshold" in scenario


def test_high_vol_scenario_detected():
    df = _make_stress_features()
    spec = HypothesisSpec(
        trigger=TriggerSpec.event("VOL_SHOCK"),
        direction="long",
        horizon="15m",
        template_id="base",
    )
    result = evaluate_stress_scenarios(spec, df, horizon_bars=3, min_n=3)
    high_vol = result[result["scenario"] == "HIGH_VOL_SHOCK"]
    assert len(high_vol) == 1
    # Events in stress bars should have n > 0
    assert int(high_vol["n"].iloc[0]) > 0


def test_missing_feature_column_marks_invalid():
    df = pd.DataFrame({
        "timestamp": pd.date_range("2023-01-01", periods=50, freq="5min"),
        "close": 100.0,
        "event_vol_shock": [i % 5 == 0 for i in range(50)],
        # Intentionally omit all stress feature columns
    })
    spec = HypothesisSpec(
        trigger=TriggerSpec.event("VOL_SHOCK"),
        direction="long",
        horizon="15m",
        template_id="base",
    )
    result = evaluate_stress_scenarios(spec, df, horizon_bars=3)
    # All scenarios should be invalid (feature column missing)
    if not result.empty:
        assert result["valid"].sum() == 0
