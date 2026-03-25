import yaml
import pytest
from pathlib import Path

def test_regime_gate_min_per_regime_is_meaningful():
    """regime_ess_min_per_regime must be at least 10.0"""
    gates_path = Path("spec/gates.yaml")
    if not gates_path.exists():
        pytest.skip("spec/gates.yaml not found")
    with open(gates_path) as f:
        gates = yaml.safe_load(f)
    phase2 = gates.get("gate_v1_phase2", {})
    assert float(phase2.get("regime_ess_min_per_regime", 0)) >= 10.0, (
        "regime_ess_min_per_regime must be at least 10 — a value of 1 provides no robustness check"
    )
    assert int(phase2.get("regime_ess_min_regimes", 0)) >= 2, (
        "regime_ess_min_regimes must be at least 2"
    )

def test_timeframe_consensus_thresholds():
    """timeframe_consensus thresholds must be meaningful"""
    gates_path = Path("spec/gates.yaml")
    if not gates_path.exists():
        pytest.skip("spec/gates.yaml not found")
    with open(gates_path) as f:
        gates = yaml.safe_load(f)
    phase2 = gates.get("gate_v1_phase2", {})
    assert float(phase2.get("timeframe_consensus_min_ratio", 0)) >= 0.5
    assert int(phase2.get("timeframe_consensus_min_timeframes", 0)) >= 2
