import pandas as pd
import pytest
from project.events.arbitration import (
    arbitrate_events,
    ArbitrationResult,
    load_compatibility_spec,
    load_precedence_spec,
)


def _make_events(types_and_ts):
    rows = []
    for i, (et, ts) in enumerate(types_and_ts):
        rows.append({
            "event_type": et,
            "event_id": f"{et.lower()}_{i:04d}",
            "symbol": "BTCUSDT",
            "timestamp": pd.Timestamp(ts, tz="UTC"),
            "enter_ts": pd.Timestamp(ts, tz="UTC"),
            "exit_ts": pd.Timestamp(ts, tz="UTC") + pd.Timedelta(hours=1),
            "canonical_family": "LIQUIDITY_DISLOCATION",
            "evt_signal_intensity": 0.02,
            "event_tradeability_score": 0.7,
        })
    return pd.DataFrame(rows)


def test_arbitrate_returns_arbitration_result():
    df = _make_events([("LIQUIDITY_VACUUM", "2024-01-01 10:00")])
    result = arbitrate_events(df)
    assert isinstance(result, ArbitrationResult)
    assert isinstance(result.events, pd.DataFrame)
    assert isinstance(result.suppressed, pd.DataFrame)


def test_suppression_penalty_applied():
    """SPREAD_BLOWOUT active -> LIQUIDITY_VACUUM tradeability score should be reduced."""
    df = _make_events([
        ("SPREAD_BLOWOUT", "2024-01-01 10:00"),
        ("LIQUIDITY_VACUUM", "2024-01-01 10:00"),
    ])
    result = arbitrate_events(df)
    lv_rows = result.events[result.events["event_type"] == "LIQUIDITY_VACUUM"]
    assert not lv_rows.empty
    assert lv_rows["event_tradeability_score"].iloc[0] < 0.7


def test_hard_block_moves_event_to_suppressed():
    """SCHEDULED_NEWS_WINDOW_EVENT active -> VOL_SHOCK should be blocked."""
    df = _make_events([
        ("SCHEDULED_NEWS_WINDOW_EVENT", "2024-01-01 10:00"),
        ("VOL_SHOCK", "2024-01-01 10:00"),
    ])
    result = arbitrate_events(df)
    assert not (result.events["event_type"] == "VOL_SHOCK").any()
    assert (result.suppressed["event_type"] == "VOL_SHOCK").any()


def test_no_events_returns_empty():
    df = pd.DataFrame(columns=[
        "event_type", "event_id", "symbol", "timestamp",
        "enter_ts", "exit_ts", "canonical_family",
        "evt_signal_intensity", "event_tradeability_score",
    ])
    result = arbitrate_events(df)
    assert result.events.empty
    assert result.suppressed.empty


def test_load_specs_succeed():
    compat = load_compatibility_spec()
    prec = load_precedence_spec()
    assert "suppression_rules" in compat
    assert "family_precedence" in prec


def test_unrelated_events_pass_through_unchanged():
    df = _make_events([
        ("OI_FLUSH", "2024-01-01 10:00"),
        ("FUNDING_EXTREME_ONSET", "2024-01-01 11:00"),
    ])
    result = arbitrate_events(df)
    assert len(result.events) == 2
    assert result.suppressed.empty
