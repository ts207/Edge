from __future__ import annotations

import pandas as pd

from project.research.search.bridge_adapter import hypotheses_to_bridge_candidates, split_bridge_candidates


def _make_metrics_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "hypothesis_id": "abc123",
                "trigger_type": "event",
                "trigger_key": "VOL_SPIKE",
                "direction": "long",
                "horizon": "15m",
                "template_id": "continuation",
                "n": 50,
                "mean_return_bps": 8.0,
                "t_stat": 2.1,
                "sharpe": 0.8,
                "hit_rate": 0.55,
                "cost_adjusted_return_bps": 5.0,
                "mae_mean_bps": -10.0,
                "mfe_mean_bps": 20.0,
                "robustness_score": 1.0,
                "capacity_proxy": 1000.0,
                "valid": True,
            },
            {
                "hypothesis_id": "def456",
                "trigger_type": "state",
                "trigger_key": "HIGH_FUNDING_STATE",
                "direction": "short",
                "horizon": "60m",
                "template_id": "mean_reversion",
                "n": 25,  # below default min_n=30
                "mean_return_bps": 10.0,
                "t_stat": 1.8,
                "sharpe": 0.6,
                "hit_rate": 0.6,
                "cost_adjusted_return_bps": 7.0,
                "mae_mean_bps": -15.0,
                "mfe_mean_bps": 25.0,
                "robustness_score": 0.8,
                "capacity_proxy": 500.0,
                "valid": True,
            },
            {
                "hypothesis_id": "ghi789",
                "trigger_type": "event",
                "trigger_key": "FUNDING_FLIP",
                "direction": "long",
                "horizon": "15m",
                "template_id": "continuation",
                "n": 60,
                "mean_return_bps": 2.0,
                "t_stat": 1.0,  # below default min_t_stat=1.5
                "sharpe": 0.3,
                "hit_rate": 0.52,
                "cost_adjusted_return_bps": 1.0,
                "mae_mean_bps": -5.0,
                "mfe_mean_bps": 10.0,
                "robustness_score": 0.5,
                "capacity_proxy": 2000.0,
                "valid": True,
            },
        ]
    )


def test_hypotheses_to_bridge_candidates_filters_by_t_stat_and_n():
    metrics = _make_metrics_df()
    candidates = hypotheses_to_bridge_candidates(metrics)
    # Only abc123 passes: t_stat>=1.5 AND n>=30
    assert len(candidates) == 1
    assert candidates.iloc[0]["candidate_id"] == "abc123"


def test_hypotheses_to_bridge_candidates_has_required_columns():
    metrics = _make_metrics_df()
    candidates = hypotheses_to_bridge_candidates(metrics)
    for col in ("candidate_id", "event_type", "direction", "rule_template", "horizon"):
        assert col in candidates.columns, f"Missing column: {col}"


def test_hypotheses_to_bridge_candidates_state_trigger_prefixed():
    metrics = _make_metrics_df()
    # Lower thresholds to let the state trigger through
    candidates = hypotheses_to_bridge_candidates(metrics, min_t_stat=1.5, min_n=20)
    state_row = candidates[candidates["candidate_id"] == "def456"]
    assert len(state_row) == 1
    assert state_row.iloc[0]["event_type"].startswith("STATE_")


def test_hypotheses_to_bridge_candidates_empty_input():
    empty = pd.DataFrame(columns=_make_metrics_df().columns)
    result = hypotheses_to_bridge_candidates(empty)
    assert isinstance(result, pd.DataFrame)
    assert len(result) == 0


def test_hypotheses_to_bridge_candidates_custom_thresholds():
    metrics = _make_metrics_df()
    # Accept everything
    candidates = hypotheses_to_bridge_candidates(metrics, min_t_stat=0.0, min_n=0)
    assert len(candidates) == 3


def test_bridge_candidates_have_p_value_and_family_id():
    """Adapted candidates must have p_value and family_id columns."""
    metrics = _make_metrics_df()
    candidates = hypotheses_to_bridge_candidates(metrics, min_t_stat=0.0, min_n=0)
    assert "p_value" in candidates.columns
    assert "family_id" in candidates.columns
    # p-values should be between 0 and 1
    assert (candidates["p_value"] >= 0).all()
    assert (candidates["p_value"] <= 1).all()
    # family_id should be non-empty strings
    assert (candidates["family_id"].str.len() > 0).all()


def test_bridge_candidates_p_value_from_t_stat():
    """p-value should decrease as t-stat increases."""
    metrics = _make_metrics_df()
    candidates = hypotheses_to_bridge_candidates(metrics, min_t_stat=0.0, min_n=0)
    # abc123 has t_stat=2.1, ghi789 has t_stat=1.0
    # Higher t_stat -> lower p_value
    row_high_t = candidates[candidates["candidate_id"] == "abc123"].iloc[0]
    row_low_t = candidates[candidates["candidate_id"] == "ghi789"].iloc[0]
    assert row_high_t["p_value"] < row_low_t["p_value"]


def test_split_bridge_candidates_emits_gate_failure_reasons():
    metrics = _make_metrics_df()

    candidates, failed = split_bridge_candidates(metrics)

    assert len(candidates) == 1
    assert len(failed) == 2
    assert "gate_failure_reason" in failed.columns
    assert set(failed["gate_failure_reason"].astype(str)) == {"min_sample_size", "min_t_stat"}
