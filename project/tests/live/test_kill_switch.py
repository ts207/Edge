"""
E6-T3: Live Kill-switch and Unwind.

Verify that the KillSwitchManager correctly detects risk and triggers.
"""
from __future__ import annotations

import pytest
from project.live.kill_switch import KillSwitchManager, KillSwitchReason, KillSwitchStatus
from project.live.state import LiveStateStore, PositionState


def test_drawdown_trigger():
    store = LiveStateStore()
    mgr = KillSwitchManager(store)
    
    # Setup account: $1000 balance, but -$200 unrealized PnL (20% drawdown)
    store.account.wallet_balance = 1000.0
    store.account.update_position(PositionState(
        symbol="BTCUSDT", side="LONG", quantity=1.0, 
        entry_price=60000.0, mark_price=59800.0, unrealized_pnl=-200.0
    ))
    
    mgr.check_drawdown(max_drawdown_pct=0.15)
    
    assert mgr.status.is_active
    assert mgr.status.reason == KillSwitchReason.EXCESSIVE_DRAWDOWN
    assert "20.00%" in mgr.status.message


def test_callback_triggered():
    store = LiveStateStore()
    mgr = KillSwitchManager(store)
    
    triggered_count = 0
    def my_cb(reason, msg):
        nonlocal triggered_count
        triggered_count += 1
        
    mgr.register_callback(my_cb)
    mgr.trigger(KillSwitchReason.MANUAL, "test message")
    
    assert triggered_count == 1
    assert mgr.status.is_active
    
    # Should not trigger again if already active
    mgr.trigger(KillSwitchReason.FEATURE_DRIFT, "should not see this")
    assert triggered_count == 1


def test_reset():
    store = LiveStateStore()
    mgr = KillSwitchManager(store)
    
    mgr.trigger(KillSwitchReason.MANUAL)
    assert mgr.status.is_active
    
    mgr.reset()
    assert not mgr.status.is_active
    assert mgr.status.reason is None


def test_microstructure_breakdown_trigger() -> None:
    store = LiveStateStore()
    mgr = KillSwitchManager(store)

    gate = mgr.check_microstructure(
        spread_bps=15.0,
        depth_usd=10_000.0,
        tob_coverage=0.50,
        max_spread_bps=5.0,
        min_depth_usd=25_000.0,
        min_tob_coverage=0.80,
    )

    assert gate["is_tradable"] is False
    assert mgr.status.is_active
    assert mgr.status.reason == KillSwitchReason.MICROSTRUCTURE_BREAKDOWN
    assert "spread_blowout" in mgr.status.message
    assert "depth_collapse" in mgr.status.message
    assert "cost_model_invalid" in mgr.status.message


def test_microstructure_check_does_not_trigger_when_safe() -> None:
    store = LiveStateStore()
    mgr = KillSwitchManager(store)

    gate = mgr.check_microstructure(
        spread_bps=2.0,
        depth_usd=100_000.0,
        tob_coverage=0.95,
        max_spread_bps=5.0,
        min_depth_usd=25_000.0,
        min_tob_coverage=0.80,
    )

    assert gate["is_tradable"] is True
    assert mgr.status.is_active is False


def test_microstructure_recovery_requires_healthy_streak() -> None:
    store = LiveStateStore()
    mgr = KillSwitchManager(store, microstructure_recovery_streak=3)

    failing = mgr.check_microstructure(
        spread_bps=15.0,
        depth_usd=10_000.0,
        tob_coverage=0.50,
        max_spread_bps=5.0,
        min_depth_usd=25_000.0,
        min_tob_coverage=0.80,
    )
    first_recovery = mgr.check_microstructure(
        spread_bps=2.0,
        depth_usd=100_000.0,
        tob_coverage=0.95,
        max_spread_bps=5.0,
        min_depth_usd=25_000.0,
        min_tob_coverage=0.80,
    )
    second_recovery = mgr.check_microstructure(
        spread_bps=2.0,
        depth_usd=100_000.0,
        tob_coverage=0.95,
        max_spread_bps=5.0,
        min_depth_usd=25_000.0,
        min_tob_coverage=0.80,
    )
    final_recovery = mgr.check_microstructure(
        spread_bps=2.0,
        depth_usd=100_000.0,
        tob_coverage=0.95,
        max_spread_bps=5.0,
        min_depth_usd=25_000.0,
        min_tob_coverage=0.80,
    )

    assert failing["is_tradable"] is False
    assert first_recovery["is_tradable"] is False
    assert first_recovery["reasons"] == ["microstructure_cooldown"]
    assert first_recovery["recovery_streak"] == 1
    assert second_recovery["is_tradable"] is False
    assert second_recovery["recovery_streak"] == 2
    assert final_recovery["is_tradable"] is True
    assert final_recovery["recovered"] is True
    assert mgr.status.is_active is False


def test_non_microstructure_kill_switch_keeps_gate_blocked() -> None:
    store = LiveStateStore()
    mgr = KillSwitchManager(store)
    mgr.trigger(KillSwitchReason.MANUAL, "manual halt")

    gate = mgr.check_microstructure(
        spread_bps=2.0,
        depth_usd=100_000.0,
        tob_coverage=0.95,
        max_spread_bps=5.0,
        min_depth_usd=25_000.0,
        min_tob_coverage=0.80,
    )

    assert gate["is_tradable"] is False
    assert "kill_switch_active" in gate["reasons"]


def test_kill_switch_state_persists_across_manager_restart() -> None:
    store = LiveStateStore()
    mgr = KillSwitchManager(store, microstructure_recovery_streak=2)

    mgr.check_microstructure(
        spread_bps=15.0,
        depth_usd=10_000.0,
        tob_coverage=0.50,
        max_spread_bps=5.0,
        min_depth_usd=25_000.0,
        min_tob_coverage=0.80,
    )
    mgr.check_microstructure(
        spread_bps=2.0,
        depth_usd=100_000.0,
        tob_coverage=0.95,
        max_spread_bps=5.0,
        min_depth_usd=25_000.0,
        min_tob_coverage=0.80,
    )

    restarted = KillSwitchManager(store, microstructure_recovery_streak=2)
    gate = restarted.check_microstructure(
        spread_bps=2.0,
        depth_usd=100_000.0,
        tob_coverage=0.95,
        max_spread_bps=5.0,
        min_depth_usd=25_000.0,
        min_tob_coverage=0.80,
    )

    assert restarted.status.is_active is False
    assert gate["is_tradable"] is True
    assert gate["recovered"] is True


def test_kill_switch_state_persists_across_disk_snapshot(tmp_path) -> None:
    store = LiveStateStore()
    mgr = KillSwitchManager(store, microstructure_recovery_streak=2)

    mgr.check_microstructure(
        spread_bps=15.0,
        depth_usd=10_000.0,
        tob_coverage=0.50,
        max_spread_bps=5.0,
        min_depth_usd=25_000.0,
        min_tob_coverage=0.80,
    )
    mgr.check_microstructure(
        spread_bps=2.0,
        depth_usd=100_000.0,
        tob_coverage=0.95,
        max_spread_bps=5.0,
        min_depth_usd=25_000.0,
        min_tob_coverage=0.80,
    )

    snapshot_path = store.save_snapshot(tmp_path / "live_state.json")
    restored_store = LiveStateStore.load_snapshot(snapshot_path)
    restarted = KillSwitchManager(restored_store, microstructure_recovery_streak=2)

    gate = restarted.check_microstructure(
        spread_bps=2.0,
        depth_usd=100_000.0,
        tob_coverage=0.95,
        max_spread_bps=5.0,
        min_depth_usd=25_000.0,
        min_tob_coverage=0.80,
    )

    assert restarted.status.is_active is False
    assert gate["is_tradable"] is True
    assert gate["recovered"] is True


def test_kill_switch_auto_persists_via_state_store_snapshot_path(tmp_path) -> None:
    snapshot_path = tmp_path / "live_state.json"
    store = LiveStateStore(snapshot_path=snapshot_path)
    mgr = KillSwitchManager(store)

    mgr.check_microstructure(
        spread_bps=15.0,
        depth_usd=10_000.0,
        tob_coverage=0.50,
        max_spread_bps=5.0,
        min_depth_usd=25_000.0,
        min_tob_coverage=0.80,
    )

    restored_store = LiveStateStore.load_snapshot(snapshot_path)
    assert restored_store.get_kill_switch_snapshot()["is_active"] is True
    assert restored_store.get_kill_switch_snapshot()["reason"] == "MICROSTRUCTURE_BREAKDOWN"
