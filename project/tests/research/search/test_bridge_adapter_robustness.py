# tests/research/search/test_bridge_adapter_robustness.py
from __future__ import annotations
import pandas as pd
from project.research.search.bridge_adapter import hypotheses_to_bridge_candidates

def test_bridge_adapter_maps_new_robustness_fields():
    metrics = pd.DataFrame([
        {
            "hypothesis_id": "hypo1",
            "trigger_type": "event",
            "trigger_key": "event:TEST",
            "direction": "long",
            "horizon": "15m",
            "template_id": "base",
            "n": 100,
            "mean_return_bps": 10.0,
            "t_stat": 3.0,
            "cost_adjusted_return_bps": 8.0,
            "mae_mean_bps": -5.0,
            "mfe_mean_bps": 20.0,
            "robustness_score": 0.85, # Should pass 0.6 threshold
            "stress_score": 0.75,
            "kill_switch_count": 2,
            "capacity_proxy": 1000.0,
            "valid": True,
        }
    ])
    
    candidates = hypotheses_to_bridge_candidates(metrics, min_t_stat=1.5, min_n=30)
    assert not candidates.empty
    
    # New columns
    assert "stress_test_survival" in candidates.columns
    assert "kill_switch_count" in candidates.columns
    assert candidates.iloc[0]["stress_test_survival"] == 0.75
    assert candidates.iloc[0]["kill_switch_count"] == 2
    
    # Gate updates
    assert candidates.iloc[0]["gate_c_regime_stable"] == True
    
    # Low robustness should fail regime stable gate
    metrics.loc[0, "robustness_score"] = 0.4
    candidates2 = hypotheses_to_bridge_candidates(metrics, min_t_stat=1.5, min_n=30)
    assert candidates2.iloc[0]["gate_c_regime_stable"] == False
