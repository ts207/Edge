"""
E6-T2: Live OMS state machine.

Verify order status transitions and fill accounting.
"""
from __future__ import annotations

import pandas as pd
import pytest
from project.live.kill_switch import KillSwitchManager, KillSwitchReason
from project.live.oms import (
    OrderManager,
    LiveOrder,
    OrderStatus,
    OrderSide,
    OrderType,
    OrderSubmissionBlocked,
    build_live_order_from_strategy_result,
)
from project.live.state import LiveStateStore
from project.engine.strategy_executor import calculate_strategy_returns
from project.engine.exchange_constraints import SymbolConstraints


class _DummyStrategy:
    def generate_positions(self, bars: pd.DataFrame, features: pd.DataFrame, params: dict) -> pd.Series:
        out = pd.Series([0.0, 1.0, 1.0], index=pd.DatetimeIndex(bars["timestamp"]), dtype=float)
        out.attrs["strategy_metadata"] = {"family": "test"}
        return out


def _bars() -> pd.DataFrame:
    idx = pd.date_range("2024-01-01", periods=3, freq="5min", tz="UTC")
    return pd.DataFrame(
        {
            "timestamp": idx,
            "open": [100.0, 100.0, 100.0],
            "high": [100.2, 100.2, 100.2],
            "low": [99.8, 99.8, 99.8],
            "close": [100.0, 100.0, 100.0],
        }
    )


def _features() -> pd.DataFrame:
    idx = pd.date_range("2024-01-01", periods=3, freq="5min", tz="UTC")
    return pd.DataFrame(
        {
            "timestamp": idx,
            "spread_bps": [4.0, 4.0, 4.0],
            "quote_volume": [250000.0, 250000.0, 250000.0],
            "depth_usd": [50000.0, 50000.0, 50000.0],
            "tob_coverage": [1.0, 1.0, 1.0],
            "atr_14": [0.2, 0.2, 0.2],
        }
    )


def test_order_lifecycle_fill():
    mgr = OrderManager()
    order = LiveOrder(
        client_order_id="order1",
        symbol="BTCUSDT",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=1.0,
        price=60000.0
    )
    mgr.add_order(order)
    
    # 1. Update to NEW
    mgr.on_order_update("order1", OrderStatus.NEW, exchange_order_id="ex1")
    assert mgr.active_orders["order1"].status == OrderStatus.NEW
    assert mgr.active_orders["order1"].exchange_order_id == "ex1"
    
    # 2. Partial fill
    mgr.on_fill("order1", fill_qty=0.4, fill_price=60005.0)
    assert mgr.active_orders["order1"].status == OrderStatus.PARTIALLY_FILLED
    assert mgr.active_orders["order1"].filled_quantity == 0.4
    assert mgr.active_orders["order1"].remaining_quantity == 0.6
    
    # 3. Final fill
    mgr.on_fill("order1", fill_qty=0.6, fill_price=59995.0)
    
    # Order should now be in history, not active
    assert "order1" not in mgr.active_orders
    assert len(mgr.order_history) == 1
    assert mgr.order_history[0].status == OrderStatus.FILLED
    assert mgr.order_history[0].avg_fill_price == 59999.0 # (0.4*60005 + 0.6*59995) / 1.0


def test_order_fill_records_execution_attribution_when_metadata_present():
    mgr = OrderManager()
    order = LiveOrder(
        client_order_id="order1a",
        symbol="BTCUSDT",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=1.0,
        metadata={
            "strategy": "mean_revert_1",
            "signal_timestamp": "2024-01-01T00:05:00+00:00",
            "expected_entry_price": 60000.0,
            "expected_return_bps": 30.0,
            "expected_adverse_bps": 8.0,
            "expected_cost_bps": 4.0,
            "realized_fee_bps": 2.0,
        },
    )
    mgr.add_order(order)

    mgr.on_fill("order1a", fill_qty=1.0, fill_price=60018.0)

    assert len(mgr.execution_attribution) == 1
    record = mgr.execution_attribution[0]
    assert record.client_order_id == "order1a"
    assert record.strategy == "mean_revert_1"
    assert record.volatility_regime == ""
    assert record.microstructure_regime == ""
    assert record.realized_slippage_bps == pytest.approx(3.0)
    assert record.realized_total_cost_bps == pytest.approx(5.0)
    assert record.expected_net_edge_bps == pytest.approx(18.0)
    assert record.realized_net_edge_bps == pytest.approx(17.0)
    assert record.edge_decay_bps == pytest.approx(-1.0)
    summary = mgr.summarize_execution_quality()
    assert summary["fills"] == 1.0
    assert summary["avg_realized_net_edge_bps"] == pytest.approx(17.0)


def test_order_cancellation():
    mgr = OrderManager()
    order = LiveOrder("order2", "ETHUSDT", OrderSide.SELL, OrderType.LIMIT, 10.0, 3000.0)
    mgr.add_order(order)
    
    mgr.on_order_update("order2", OrderStatus.CANCELLED)
    
    assert "order2" not in mgr.active_orders
    assert mgr.order_history[0].status == OrderStatus.CANCELLED


def test_submit_order_accepts_safe_microstructure():
    mgr = OrderManager()
    kill_switch = KillSwitchManager(LiveStateStore())
    order = LiveOrder("order3", "BTCUSDT", OrderSide.BUY, OrderType.MARKET, 1.0)

    result = mgr.submit_order(
        order,
        kill_switch_manager=kill_switch,
        market_state={"spread_bps": 2.0, "depth_usd": 100000.0, "tob_coverage": 0.95},
        max_spread_bps=5.0,
        min_depth_usd=25000.0,
        min_tob_coverage=0.80,
    )

    assert result["accepted"] is True
    assert "order3" in mgr.active_orders
    assert kill_switch.status.is_active is False


def test_build_live_order_from_strategy_result_attaches_execution_metadata(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("project.engine.strategy_executor.get_strategy", lambda _: _DummyStrategy())
    monkeypatch.setattr(
        "project.engine.strategy_executor.load_symbol_constraints",
        lambda symbol, meta_dir: SymbolConstraints(tick_size=None, step_size=None, min_notional=None),
    )

    result = calculate_strategy_returns(
        "BTCUSDT",
        _bars(),
        _features(),
        "dummy_strategy",
        {
            "position_scale": 1000.0,
            "execution_lag_bars": 0,
            "expected_return_bps": 25.0,
            "expected_adverse_bps": 5.0,
            "execution_model": {"cost_model": "static", "base_fee_bps": 2.0, "base_slippage_bps": 1.0},
        },
        0.0,
        tmp_path,
    )

    order = build_live_order_from_strategy_result(
        result,
        client_order_id="auto-order-1",
        realized_fee_bps=1.5,
    )

    assert order is not None
    assert order.client_order_id == "auto-order-1"
    assert order.side == OrderSide.BUY
    assert order.order_type == OrderType.MARKET
    assert order.quantity == pytest.approx(10.0)
    assert order.metadata["expected_entry_price"] == pytest.approx(100.0)
    assert order.metadata["strategy"] == "dummy_strategy"
    assert order.metadata["signal_timestamp"].startswith("2024-01-01T00:10:00")
    assert order.metadata["volatility_regime"] == "elevated"
    assert order.metadata["microstructure_regime"] == "healthy"
    assert order.metadata["expected_return_bps"] == pytest.approx(25.0)
    assert order.metadata["expected_adverse_bps"] == pytest.approx(5.0)
    assert order.metadata["expected_cost_bps"] == pytest.approx(3.0)
    assert order.metadata["realized_fee_bps"] == pytest.approx(1.5)


def test_build_live_order_from_strategy_result_returns_none_without_position_delta() -> None:
    frame = pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=1, freq="5min", tz="UTC"),
            "symbol": ["BTCUSDT"],
            "target_position": [0.0],
            "prior_executed_position": [0.0],
            "fill_price": [100.0],
            "close": [100.0],
            "expected_return_bps": [20.0],
            "expected_adverse_bps": [5.0],
            "expected_cost_bps": [3.0],
            "expected_net_edge_bps": [12.0],
        }
    )

    from project.engine.strategy_executor import StrategyResult

    result = StrategyResult(
        name="dummy",
        data=frame,
        diagnostics={},
        strategy_metadata={},
        trace=pd.DataFrame(),
    )

    assert build_live_order_from_strategy_result(result, client_order_id="flat-order") is None


def test_submit_order_blocks_on_microstructure_breakdown():
    mgr = OrderManager()
    kill_switch = KillSwitchManager(LiveStateStore())
    order = LiveOrder("order4", "BTCUSDT", OrderSide.BUY, OrderType.MARKET, 1.0)

    with pytest.raises(OrderSubmissionBlocked, match="spread_blowout,depth_collapse,cost_model_invalid"):
        mgr.submit_order(
            order,
            kill_switch_manager=kill_switch,
            market_state={"spread_bps": 12.0, "depth_usd": 5000.0, "tob_coverage": 0.40},
            max_spread_bps=5.0,
            min_depth_usd=25000.0,
            min_tob_coverage=0.80,
        )

    assert "order4" not in mgr.active_orders
    assert mgr.order_history[-1].status == OrderStatus.REJECTED
    assert kill_switch.status.is_active is True
    assert kill_switch.status.reason == KillSwitchReason.MICROSTRUCTURE_BREAKDOWN


def test_submit_order_respects_microstructure_recovery_cooldown():
    mgr = OrderManager()
    kill_switch = KillSwitchManager(LiveStateStore(), microstructure_recovery_streak=2)

    with pytest.raises(OrderSubmissionBlocked):
        mgr.submit_order(
            LiveOrder("order5", "BTCUSDT", OrderSide.BUY, OrderType.MARKET, 1.0),
            kill_switch_manager=kill_switch,
            market_state={"spread_bps": 12.0, "depth_usd": 5000.0, "tob_coverage": 0.40},
            max_spread_bps=5.0,
            min_depth_usd=25000.0,
            min_tob_coverage=0.80,
        )

    with pytest.raises(OrderSubmissionBlocked, match="microstructure_cooldown"):
        mgr.submit_order(
            LiveOrder("order6", "BTCUSDT", OrderSide.BUY, OrderType.MARKET, 1.0),
            kill_switch_manager=kill_switch,
            market_state={"spread_bps": 2.0, "depth_usd": 100000.0, "tob_coverage": 0.95},
            max_spread_bps=5.0,
            min_depth_usd=25000.0,
            min_tob_coverage=0.80,
        )

    accepted = mgr.submit_order(
        LiveOrder("order7", "BTCUSDT", OrderSide.BUY, OrderType.MARKET, 1.0),
        kill_switch_manager=kill_switch,
        market_state={"spread_bps": 2.0, "depth_usd": 100000.0, "tob_coverage": 0.95},
        max_spread_bps=5.0,
        min_depth_usd=25000.0,
        min_tob_coverage=0.80,
    )

    assert accepted["accepted"] is True
    assert "order7" in mgr.active_orders
    assert kill_switch.status.is_active is False
