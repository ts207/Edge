from __future__ import annotations

import asyncio
import json

import pandas as pd
import pytest

from project.engine.exchange_constraints import SymbolConstraints
from project.engine.strategy_executor import StrategyResult, calculate_strategy_returns
from project.live.execution_attribution import build_execution_attribution_record
from project.live.kill_switch import KillSwitchReason
from project.live.oms import OrderManager, OrderType
from project.live.runner import LiveEngineRunner


class _DummyDataManager:
    def __init__(self) -> None:
        self.kline_queue = asyncio.Queue()
        self.ticker_queue = asyncio.Queue()

    async def start(self) -> None:
        return None

    async def stop(self) -> None:
        return None


def test_live_runner_exposes_persistent_session_metadata(tmp_path) -> None:
    snapshot_path = tmp_path / "live_session_state.json"
    report_path = tmp_path / "execution_quality.json"

    runner = LiveEngineRunner(
        ["btcusdt", "ethusdt"],
        snapshot_path=snapshot_path,
        microstructure_recovery_streak=5,
        execution_quality_report_path=report_path,
        data_manager=_DummyDataManager(),
    )

    assert runner.state_store._snapshot_path == snapshot_path
    assert runner.kill_switch.microstructure_recovery_streak == 5
    assert runner.session_metadata["live_state_snapshot_path"] == str(snapshot_path)
    assert runner.session_metadata["live_state_auto_persist_enabled"] is True
    assert runner.session_metadata["kill_switch_recovery_streak"] == 5
    assert runner.session_metadata["account_sync_interval_seconds"] == 30.0
    assert runner.session_metadata["account_sync_failure_threshold"] == 3
    assert runner.session_metadata["execution_degradation_min_samples"] == 3
    assert runner.session_metadata["execution_degradation_warn_edge_bps"] == 0.0
    assert runner.session_metadata["execution_degradation_block_edge_bps"] == -5.0
    assert runner.session_metadata["execution_degradation_throttle_scale"] == 0.5
    assert runner.session_metadata["execution_quality_report_path"] == str(report_path)


def test_live_runner_periodic_account_sync_updates_state() -> None:
    snapshots = iter(
        [
            {
                "wallet_balance": 100.0,
                "margin_balance": 105.0,
                "available_balance": 90.0,
                "exchange_status": "NORMAL",
                "positions": [],
            },
            {
                "wallet_balance": 200.0,
                "margin_balance": 210.0,
                "available_balance": 180.0,
                "exchange_status": "NORMAL",
                "positions": [],
            },
        ]
    )

    async def _fetch_snapshot():
        return next(snapshots)

    runner = LiveEngineRunner(
        ["btcusdt"],
        account_sync_interval_seconds=1.0,
        account_snapshot_fetcher=_fetch_snapshot,
        data_manager=_DummyDataManager(),
    )
    runner._running = True

    async def _exercise() -> None:
        task = asyncio.create_task(runner._sync_account_state())
        await asyncio.sleep(0.05)
        assert runner.state_store.account.wallet_balance == 100.0
        runner._running = False
        await task

    asyncio.run(_exercise())


def test_live_runner_account_sync_failures_trigger_kill_switch() -> None:
    async def _fail_snapshot():
        raise RuntimeError("auth lost")

    runner = LiveEngineRunner(
        ["btcusdt"],
        account_sync_interval_seconds=1.0,
        account_sync_failure_threshold=2,
        account_snapshot_fetcher=_fail_snapshot,
        data_manager=_DummyDataManager(),
    )
    runner._running = True

    async def _exercise() -> None:
        task = asyncio.create_task(runner._sync_account_state())
        await asyncio.sleep(1.05)
        runner._running = False
        await task

    asyncio.run(_exercise())

    assert runner.account_sync_failure_count >= 2
    assert runner.kill_switch.status.is_active is True
    assert runner.kill_switch.status.reason == KillSwitchReason.ACCOUNT_SYNC_LOSS
    assert "Authenticated account sync failed" in runner.kill_switch.status.message


def test_live_runner_account_sync_success_resets_failure_count() -> None:
    results = iter(
        [
            RuntimeError("first"),
            {
                "wallet_balance": 123.0,
                "margin_balance": 124.0,
                "available_balance": 120.0,
                "exchange_status": "NORMAL",
                "positions": [],
            },
        ]
    )

    async def _fetch_snapshot():
        item = next(results)
        if isinstance(item, Exception):
            raise item
        return item

    runner = LiveEngineRunner(
        ["btcusdt"],
        account_sync_interval_seconds=1.0,
        account_sync_failure_threshold=3,
        account_snapshot_fetcher=_fetch_snapshot,
        data_manager=_DummyDataManager(),
    )
    runner._running = True

    async def _exercise() -> None:
        task = asyncio.create_task(runner._sync_account_state())
        await asyncio.sleep(0.05)
        assert runner.account_sync_failure_count == 1
        await asyncio.sleep(1.05)
        runner._running = False
        await task

    asyncio.run(_exercise())

    assert runner.account_sync_failure_count == 0
    assert runner.state_store.account.wallet_balance == 123.0
    assert runner.kill_switch.status.is_active is False


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


def test_live_runner_submit_strategy_result_routes_order_through_oms(monkeypatch, tmp_path) -> None:
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

    runner = LiveEngineRunner(
        ["btcusdt"],
        order_manager=OrderManager(),
        data_manager=_DummyDataManager(),
    )
    accepted = runner.submit_strategy_result(
        result,
        client_order_id="runner-order-1",
        order_type=OrderType.MARKET,
        realized_fee_bps=1.5,
        market_state={"spread_bps": 2.0, "depth_usd": 100000.0, "tob_coverage": 0.95},
    )

    assert accepted is not None
    assert accepted["accepted"] is True
    order = runner.order_manager.active_orders["runner-order-1"]
    assert order.metadata["expected_return_bps"] == 25.0
    assert order.metadata["realized_fee_bps"] == 1.5
    assert order.metadata["execution_degradation_action"] == "allow"


def test_live_runner_submit_strategy_result_returns_none_for_flat_result() -> None:
    result = StrategyResult(
        name="dummy",
        data=pd.DataFrame(
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
        ),
        diagnostics={},
        strategy_metadata={},
        trace=pd.DataFrame(),
    )
    runner = LiveEngineRunner(["btcusdt"], data_manager=_DummyDataManager())

    assert runner.submit_strategy_result(result, client_order_id="flat") is None


def test_live_runner_submit_strategy_result_throttles_negative_bucket(monkeypatch, tmp_path) -> None:
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
    runner = LiveEngineRunner(
        ["btcusdt"],
        order_manager=OrderManager(),
        execution_degradation_min_samples=2,
        execution_degradation_warn_edge_bps=0.0,
        execution_degradation_block_edge_bps=-5.0,
        execution_degradation_throttle_scale=0.5,
        data_manager=_DummyDataManager(),
    )
    runner.order_manager.execution_attribution.extend(
        [
            build_execution_attribution_record(
                client_order_id="hist1",
                symbol="BTCUSDT",
                strategy="dummy_strategy",
                volatility_regime="elevated",
                microstructure_regime="healthy",
                side="BUY",
                quantity=1.0,
                signal_timestamp="2024-01-01T00:00:00+00:00",
                expected_entry_price=100.0,
                realized_fill_price=100.07,
                expected_return_bps=10.0,
                expected_adverse_bps=5.0,
                expected_cost_bps=2.0,
                realized_fee_bps=1.0,
            ),
            build_execution_attribution_record(
                client_order_id="hist2",
                symbol="BTCUSDT",
                strategy="dummy_strategy",
                volatility_regime="elevated",
                microstructure_regime="healthy",
                side="BUY",
                quantity=1.0,
                signal_timestamp="2024-01-01T00:05:00+00:00",
                expected_entry_price=100.0,
                realized_fill_price=100.06,
                expected_return_bps=10.0,
                expected_adverse_bps=5.0,
                expected_cost_bps=2.0,
                realized_fee_bps=1.0,
            ),
        ]
    )

    accepted = runner.submit_strategy_result(
        result,
        client_order_id="runner-order-throttle",
        order_type=OrderType.MARKET,
        realized_fee_bps=1.5,
        market_state={"spread_bps": 2.0, "depth_usd": 100000.0, "tob_coverage": 0.95},
    )

    assert accepted is not None
    assert accepted["accepted"] is True
    order = runner.order_manager.active_orders["runner-order-throttle"]
    assert order.quantity == pytest.approx(5.0)
    assert order.metadata["execution_degradation_action"] == "throttle"
    assert order.metadata["execution_degradation_applied_scale"] == pytest.approx(0.5)


def test_live_runner_submit_strategy_result_blocks_degraded_bucket(monkeypatch, tmp_path) -> None:
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
    runner = LiveEngineRunner(
        ["btcusdt"],
        order_manager=OrderManager(),
        execution_degradation_min_samples=2,
        execution_degradation_warn_edge_bps=0.0,
        execution_degradation_block_edge_bps=-5.0,
        execution_degradation_throttle_scale=0.5,
        data_manager=_DummyDataManager(),
    )
    runner.order_manager.execution_attribution.extend(
        [
            build_execution_attribution_record(
                client_order_id="hist3",
                symbol="BTCUSDT",
                strategy="dummy_strategy",
                volatility_regime="elevated",
                microstructure_regime="healthy",
                side="BUY",
                quantity=1.0,
                signal_timestamp="2024-01-01T00:00:00+00:00",
                expected_entry_price=100.0,
                realized_fill_price=100.3,
                expected_return_bps=5.0,
                expected_adverse_bps=5.0,
                expected_cost_bps=2.0,
                realized_fee_bps=2.0,
            ),
            build_execution_attribution_record(
                client_order_id="hist4",
                symbol="BTCUSDT",
                strategy="dummy_strategy",
                volatility_regime="elevated",
                microstructure_regime="healthy",
                side="BUY",
                quantity=1.0,
                signal_timestamp="2024-01-01T00:05:00+00:00",
                expected_entry_price=100.0,
                realized_fill_price=100.4,
                expected_return_bps=5.0,
                expected_adverse_bps=5.0,
                expected_cost_bps=2.0,
                realized_fee_bps=2.0,
            ),
        ]
    )

    blocked = runner.submit_strategy_result(
        result,
        client_order_id="runner-order-block",
        order_type=OrderType.MARKET,
        realized_fee_bps=1.5,
        market_state={"spread_bps": 2.0, "depth_usd": 100000.0, "tob_coverage": 0.95},
    )

    assert blocked is not None
    assert blocked["accepted"] is False
    assert blocked["blocked_by"] == "execution_degradation"
    assert "runner-order-block" not in runner.order_manager.active_orders
    assert runner.order_manager.order_history[-1].status.name == "REJECTED"


def test_live_runner_persists_execution_quality_report_after_fill(monkeypatch, tmp_path) -> None:
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
    report_path = tmp_path / "execution_quality.json"
    runner = LiveEngineRunner(
        ["btcusdt"],
        order_manager=OrderManager(),
        execution_quality_report_path=report_path,
        data_manager=_DummyDataManager(),
    )
    runner.submit_strategy_result(
        result,
        client_order_id="runner-order-2",
        order_type=OrderType.MARKET,
        realized_fee_bps=1.5,
        market_state={"spread_bps": 2.0, "depth_usd": 100000.0, "tob_coverage": 0.95},
    )

    runner.on_order_fill("runner-order-2", fill_qty=10.0, fill_price=100.02)

    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["summary"]["fills"] == 1.0
    assert payload["summary"]["avg_realized_net_edge_bps"] < payload["summary"]["avg_expected_net_edge_bps"]
    assert payload["records"][0]["client_order_id"] == "runner-order-2"
    assert payload["records"][0]["strategy"] == "dummy_strategy"
    assert payload["records"][0]["volatility_regime"] == "elevated"
    assert payload["records"][0]["microstructure_regime"] == "healthy"
    assert payload["by_symbol"]["BTCUSDT"]["fills"] == 1.0
    assert payload["by_strategy"]["dummy_strategy"]["fills"] == 1.0
    assert payload["by_volatility_regime"]["elevated"]["fills"] == 1.0
    assert payload["by_microstructure_regime"]["healthy"]["fills"] == 1.0


def test_live_runner_persist_execution_quality_report_returns_none_without_path() -> None:
    runner = LiveEngineRunner(["btcusdt"], data_manager=_DummyDataManager())
    assert runner.persist_execution_quality_report() is None
