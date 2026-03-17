import numpy as np
import pandas as pd
import pytest
from project.features.context_states import (
    calculate_ms_vol_state,
    calculate_ms_liq_state,
    calculate_ms_oi_state,
    calculate_ms_funding_state,
    calculate_ms_trend_state,
    calculate_ms_spread_state,
    encode_context_state_code,
)

def test_calculate_ms_vol_state():
    rv_pct = pd.Series([10.0, 50.0, 80.0, 98.0])
    states = calculate_ms_vol_state(rv_pct)
    assert states.iloc[0] == 0.0 # LOW
    assert states.iloc[1] == 1.0 # MID
    assert states.iloc[2] == 2.0 # HIGH
    assert states.iloc[3] == 3.0 # SHOCK

def test_calculate_ms_liq_state():
    # Sine wave ensures we hit all quantiles
    vol = pd.Series(np.sin(np.linspace(0, 10, 500)) + 2.0)
    states = calculate_ms_liq_state(vol, window=100)
    
    # Peak of sine is max -> FLUSH (2.0)
    # Trough of sine is min -> THIN (0.0)
    # Somewhere in between -> NORMAL (1.0)
    
    assert 2.0 in states.values
    assert 0.0 in states.values
    assert 1.0 in states.values

def test_calculate_ms_oi_state():
    # Constant OI delta -> z-score will be 0 (STABLE)
    oi_delta = pd.Series([10.0] * 100)
    states = calculate_ms_oi_state(oi_delta, window=50)
    assert states.iloc[-1] == 1.0
    
    # Large spike
    oi_delta.iloc[-1] = 1000.0
    states = calculate_ms_oi_state(oi_delta, window=50)
    assert states.iloc[-1] == 2.0 # ACCEL

def test_calculate_ms_funding_state():
    # With insufficient long-window history, state should remain NEUTRAL.
    fnd = pd.Series([0.5] * 100)
    states = calculate_ms_funding_state(fnd, window=20)
    assert states.iloc[-1] == 0.0

    # Persistent positive funding once long-window quantiles are available.
    states_ready = calculate_ms_funding_state(fnd, window=20, window_long=60)
    assert states_ready.iloc[-1] == 1.0  # PERSISTENT

    # Extreme positive funding
    fnd_ext = pd.Series([5.0] * 100)
    states_ext = calculate_ms_funding_state(fnd_ext, window=5, window_long=60)
    assert states_ext.iloc[-1] == 2.0  # EXTREME

def test_calculate_ms_trend_state():
    # With insufficient long-window history, state should remain CHOP.
    assert calculate_ms_trend_state(pd.Series([0.005])).iloc[0] == 0.0
    assert calculate_ms_trend_state(pd.Series([-0.005])).iloc[0] == 0.0

    rv = pd.Series([0.001] * 120)

    # Bull once long-window quantiles are available.
    ret_bull = pd.Series(np.linspace(-0.002, 0.006, 120))
    bull_state = calculate_ms_trend_state(ret_bull, rv=rv, window_long=60)
    assert bull_state.iloc[-1] == 1.0

    # Bear once long-window quantiles are available.
    ret_bear = pd.Series(np.linspace(0.006, -0.002, 120))
    bear_state = calculate_ms_trend_state(ret_bear, rv=rv, window_long=60)
    assert bear_state.iloc[-1] == 2.0

def test_calculate_ms_spread_state():
    # Tight
    spread = pd.Series([0.1])
    assert calculate_ms_spread_state(spread).iloc[0] == 0.0
    # Wide
    spread = pd.Series([0.6])
    assert calculate_ms_spread_state(spread).iloc[0] == 1.0

def test_encode_context_state_code():
    vol = pd.Series([3.0])
    liq = pd.Series([0.0])
    oi = pd.Series([2.0])
    fnd = pd.Series([1.0])
    trend = pd.Series([1.0])
    spread = pd.Series([0.0])
    code = encode_context_state_code(vol, liq, oi, fnd, trend, spread)
    # V L O F T S
    # 3 0 2 1 1 0
    assert code.iloc[0] == 302110.0
