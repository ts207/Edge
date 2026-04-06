import pandas as pd
import numpy as np
import pytest
from project.live.runner import _classify_canonical_regime
from project.core.regime_classifier import RegimeName, ClassificationMode


def test_regime_classifier_runtime_approximation():
    """
    Verify that the shared regime classifier correctly falls back to 
    bps-based approximation when research features are missing.
    
    This tests helper behavior, not full research/live parity.
    """
    # 1. High Vol (> 80 bps move)
    res = _classify_canonical_regime(move_bps=85.0)
    assert res["canonical_regime"] == RegimeName.HIGH_VOL.value
    assert res["regime_mode"] == ClassificationMode.RUNTIME_APPROX.value
    assert res["regime_metadata"]["move_bps"] == 85.0
    
    # 2. Low Vol (< 20 bps move)
    res = _classify_canonical_regime(move_bps=10.0)
    assert res["canonical_regime"] == RegimeName.LOW_VOL.value
    
    # 3. Bull Trend (moderate positive)
    res = _classify_canonical_regime(move_bps=30.0)
    assert res["canonical_regime"] == RegimeName.BULL_TREND.value

    # 4. Bear Trend (moderate negative)
    res = _classify_canonical_regime(move_bps=-30.0)
    assert res["canonical_regime"] == RegimeName.BEAR_TREND.value


def test_regime_classifier_research_exact():
    """
    Verify that the shared regime classifier uses exact research semantics
    when research features are provided.
    
    This tests helper behavior, not full research/live parity.
    """
    # High Vol (rv_pct >= 80)
    res = _classify_canonical_regime(move_bps=0.0, rv_pct=85.0, ms_trend_state=1.0)
    assert res["canonical_regime"] == RegimeName.HIGH_VOL.value
    assert res["regime_mode"] == ClassificationMode.RESEARCH_EXACT.value
    
    # Bull Trend (rv_pct normal, ms_trend_state=1)
    res = _classify_canonical_regime(move_bps=0.0, rv_pct=50.0, ms_trend_state=1.0)
    assert res["canonical_regime"] == RegimeName.BULL_TREND.value
    
    # Chop (rv_pct normal, ms_trend_state=0)
    res = _classify_canonical_regime(move_bps=0.0, rv_pct=50.0, ms_trend_state=0.0)
    assert res["canonical_regime"] == RegimeName.CHOP.value


def test_regime_classifier_output_contract():
    """
    Verify that _classify_canonical_regime returns all required fields.
    This is a contract test for the helper, not a parity test.
    """
    expected_fields = {
        "canonical_regime", "regime_mode", 
        "regime_confidence", "regime_metadata"
    }
    
    # Test 1: Runtime approximation when research features unavailable
    result = _classify_canonical_regime(move_bps=30.0)
    assert set(result.keys()) >= expected_fields
    assert result["canonical_regime"] == RegimeName.BULL_TREND.value
    assert result["regime_mode"] == ClassificationMode.RUNTIME_APPROX.value
    assert 0.0 < result["regime_confidence"] <= 1.0
    
    # Test 2: Research exact when all features available
    result = _classify_canonical_regime(
        move_bps=0.0, 
        rv_pct=50.0, 
        ms_trend_state=0.0
    )
    assert result["canonical_regime"] == RegimeName.CHOP.value
    assert result["regime_mode"] == ClassificationMode.RESEARCH_EXACT.value
    
    # Test 3: CHOP is a valid canonical regime
    result = _classify_canonical_regime(move_bps=0.0, rv_pct=50.0, ms_trend_state=0.0)
    assert result["canonical_regime"] in [r.value for r in RegimeName]
    assert "move_bps" in result["regime_metadata"]
