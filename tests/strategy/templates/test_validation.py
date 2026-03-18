"""
Tests for blueprint validation of PIT (Point-In-Time) temporal contracts.
Ensures blueprints cannot be built using non-PIT features.
"""
import pytest
import pandas as pd
from typing import Dict, Any


def _base_blueprint() -> Dict[str, Any]:
    return {
        "id": "bp_test_pit",
        "run_id": "r1",
        "event_type": "VOL_SHOCK",
        "candidate_id": "cand_1",
        "symbol_scope": {"mode": "single_symbol", "symbols": ["BTCUSDT"], "candidate_symbol": "BTCUSDT"},
        "direction": "long",
        "entry": {
            "triggers": ["spread_guard_pass"],
            "conditions": [],
            "confirmations": [],
            "delay_bars": 0,
            "cooldown_bars": 0,
            "condition_logic": "all",
            "condition_nodes": [],
        },
        "exit": {
            "time_stop_bars": 10,
            "stop_type": "percent",
            "stop_value": 0.01,
            "target_type": "percent",
            "target_value": 0.02,
        },
        "sizing": {"mode": "fixed_risk", "risk_per_trade": 0.01},
        "overlays": [],
        "evaluation": {"min_trades": 1, "cost_model": {}, "robustness_flags": {}},
        "lineage": {"source_path": "dummy", "compiler_version": "v1", "generated_at_utc": "2026-01-01T00:00:00Z"},
    }


def test_validation_rejects_non_pit_feature_in_conditions():
    """
    Features used in blueprint conditions must have TemporalContract(invariance='pit').
    """
    from project.strategy.templates.validation import validate_blueprint_temporal_integrity
    
    bp = _base_blueprint()
    bp["entry"]["condition_nodes"] = [
        {
            "feature": "non_pit_feature_example",
            "operator": ">",
            "value": 0.0,
        }
    ]
    
    # We expect this to raise a ValueError because 'non_pit_feature_example' 
    # will not be found in the PIT-safe registry or won't have the PIT contract.
    with pytest.raises(ValueError, match="is not PIT-safe"):
        validate_blueprint_temporal_integrity(bp)


def test_validation_accepts_pit_feature():
    """
    Features with PIT contract should pass validation.
    """
    from project.strategy.templates.validation import validate_blueprint_temporal_integrity
    
    bp = _base_blueprint()
    # 'close' is typically PIT-safe in this framework
    bp["entry"]["condition_nodes"] = [
        {
            "feature": "close",
            "operator": ">",
            "value": 0.0,
        }
    ]
    
    # Should not raise
    validate_blueprint_temporal_integrity(bp)
