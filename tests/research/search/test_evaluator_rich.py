import pytest
import pandas as pd
import numpy as np
from project.research.search.evaluator import evaluate_hypothesis_batch
from project.domain.hypotheses import HypothesisSpec, TriggerSpec

def test_evaluate_rich_metrics():
    # Setup dummy data
    np.random.seed(42)
    dates = pd.date_range("2023-01-01", periods=100, freq="15min")
    close = pd.Series(np.linspace(100, 110, 100) + np.random.normal(0, 0.1, 100), index=dates)
    # Add some "events"
    features = pd.DataFrame({
        "timestamp": dates,
        "close": close,
        "event_vol_spike": [False] * 100
    })
    features.iloc[10, features.columns.get_loc("event_vol_spike")] = True
    features.iloc[50, features.columns.get_loc("event_vol_spike")] = True
    
    spec = HypothesisSpec(
        trigger=TriggerSpec.event("vol_spike"),
        direction="long",
        horizon="5m",
        template_id="continuation",
        entry_lag=1
    )
    
    res = evaluate_hypothesis_batch([spec], features, min_sample_size=2)
    
    assert not res.empty
    assert "mae_mean_bps" in res.columns
    assert "mfe_mean_bps" in res.columns
    assert "robustness_score" in res.columns
    assert res.iloc[0]["valid"] == True
    # Long direction on uptrend should have positive return
    assert res.iloc[0]["mean_return_bps"] > 0
    # Uptrend should have minimal adverse excursion
    assert res.iloc[0]["mae_mean_bps"] >= -1.0 # 0.0 ideally


def test_excursion_stats_use_log_returns():
    """MAE/MFE must use log returns to match forward return computation."""
    from project.research.search.evaluator import _excursion_stats
    # Create a known price series: 100 -> 110 (10% simple, 9.53% log)
    close = pd.Series([100.0, 110.0, 100.0, 90.0, 100.0])
    mask = pd.Series([True, False, False, False, False])
    maes, mfes = _excursion_stats(close, mask, horizon_bars=4, direction_sign=1.0)
    # MFE should be log(110/100) = 0.09531, NOT 0.10
    assert abs(mfes.iloc[0] - np.log(110.0 / 100.0)) < 1e-6
    # MAE should be log(90/100) = -0.10536, NOT -0.10
    assert abs(maes.iloc[0] - np.log(90.0 / 100.0)) < 1e-6


def test_robustness_zero_mean_halves():
    """Two near-zero-mean halves should NOT score robustness=1.0."""
    dates = pd.date_range("2023-01-01", periods=200, freq="15min")
    # Alternating prices to produce zero mean but non-zero variance
    # [100, 101, 100, 101, ...]
    close = pd.Series([100.0, 101.0] * 100, index=dates)
    features = pd.DataFrame({
        "timestamp": dates,
        "close": close,
        "event_vol_shock": [i % 4 == 0 for i in range(200)],
        "volume": [1000] * 200
    })
    spec = HypothesisSpec(
        trigger=TriggerSpec.event("VOL_SHOCK"),
        direction="long",
        horizon="1m", # 1 bar
        template_id="continuation",
        entry_lag=0,
    )
    # With entry_lag=0, events at 0, 4, 8... 
    # Forward return for index 0 is log(close[1]/close[0]) = log(101/100)
    # Forward return for index 4 is log(close[5]/close[4]) = log(101/100)
    # WAIT: index 0 return is log(101/100), index 2 is log(101/100)
    # Let's make them alternate sign:
    close = pd.Series([100.0, 101.0, 100.0, 99.0] * 50, index=dates)
    features["close"] = close
    # Trigger at 0, 4, 8 -> all have fwd return log(101/100) > 0
    # Let's trigger at 0, 2, 4, 6...
    features["event_vol_shock"] = [i % 2 == 0 for i in range(200)]
    # idx 0: log(101/100) > 0
    # idx 2: log(99/100) < 0
    # Both halves will have one positive and one negative return -> mean ~ 0
    
    res = evaluate_hypothesis_batch([spec], features, min_sample_size=2)
    assert res.iloc[0]["valid"]
    assert res.iloc[0]["robustness_score"] < 1.0


def test_filter_template_produces_different_metrics_than_base():
    """
    A filter template hypothesis (with feature_condition) must have n <= base n,
    because the feature condition subsets the trigger population.
    """
    np.random.seed(7)
    n_bars = 500
    dates = pd.date_range("2023-01-01", periods=n_bars, freq="15min")
    close = pd.Series(100.0 + np.cumsum(np.random.normal(0, 0.1, n_bars)), index=dates)

    # Create a feature column and a filter feature column
    # trigger fires at every 5th bar
    event_col = [i % 5 == 0 for i in range(n_bars)]
    # filter feature: only True for first half of the data
    filter_col = [i < n_bars // 2 for i in range(n_bars)]

    features = pd.DataFrame({
        "timestamp": dates,
        "close": close,
        "event_vol_shock": event_col,
        "feature_test_filter": filter_col,
    })

    base_spec = HypothesisSpec(
        trigger=TriggerSpec.event("VOL_SHOCK"),
        direction="long",
        horizon="1m",
        template_id="base",
        entry_lag=0,
    )
    filter_spec = HypothesisSpec(
        trigger=TriggerSpec.event("VOL_SHOCK"),
        direction="long",
        horizon="1m",
        template_id="only_if_test",
        entry_lag=0,
        feature_condition=TriggerSpec.feature_predicate(
            feature="test_filter", operator=">", threshold=0.5
        ),
    )

    res = evaluate_hypothesis_batch([base_spec, filter_spec], features, min_sample_size=5)
    assert len(res) == 2

    base_n = res[res["template_id"] == "base"]["n"].iloc[0]
    filter_n = res[res["template_id"] == "only_if_test"]["n"].iloc[0]
    # Filter applies feature condition which restricts to first half of events
    assert filter_n < base_n, (
        f"Filter hypothesis n={filter_n} should be < base n={base_n}"
    )


def test_evaluate_emits_split_level_sample_counts():
    dates = pd.date_range("2023-01-01", periods=12, freq="5min", tz="UTC")
    close = pd.Series(np.linspace(100.0, 111.0, len(dates)), index=dates)
    features = pd.DataFrame(
        {
            "timestamp": dates,
            "close": close.values,
            "event_vol_shock": [True] * 9 + [False] * 3,
            "split_label": [
                "train",
                "train",
                "train",
                "validation",
                "validation",
                "validation",
                "test",
                "test",
                "test",
                "test",
                "test",
                "test",
            ],
        }
    )
    spec = HypothesisSpec(
        trigger=TriggerSpec.event("VOL_SHOCK"),
        direction="long",
        horizon="1m",
        template_id="continuation",
        entry_lag=0,
    )

    res = evaluate_hypothesis_batch([spec], features, min_sample_size=2)

    assert not res.empty
    row = res.iloc[0]
    assert int(row["n"]) == 9
    assert int(row["train_n_obs"]) == 3
    assert int(row["validation_n_obs"]) == 3
    assert int(row["test_n_obs"]) == 3
    assert int(row["validation_samples"]) == 3
    assert int(row["test_samples"]) == 3
