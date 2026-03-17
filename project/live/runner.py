from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List

from project.live.kill_switch import KillSwitchManager, KillSwitchReason
from project.live.oms import OrderManager, OrderType, OrderStatus, build_live_order_from_strategy_result
from project.live.state import LiveStateStore
from project.live.execution_attribution import summarize_execution_attribution_by

_LOG = logging.getLogger(__name__)

class LiveEngineRunner:
    def __init__(
        self,
        symbols: List[str],
        *,
        snapshot_path: str | Path | None = None,
        microstructure_recovery_streak: int = 3,
        account_sync_interval_seconds: float = 30.0,
        account_sync_failure_threshold: int = 3,
        account_snapshot_fetcher: Callable[[], Awaitable[Dict[str, Any]]] | None = None,
        execution_quality_report_path: str | Path | None = None,
        execution_degradation_min_samples: int = 3,
        execution_degradation_warn_edge_bps: float = 0.0,
        execution_degradation_block_edge_bps: float = -5.0,
        execution_degradation_throttle_scale: float = 0.5,
        order_manager: OrderManager | None = None,
        data_manager: Any | None = None,
    ):
        self.symbols = symbols
        if data_manager is None:
            from project.live.ingest.manager import LiveDataManager

            data_manager = LiveDataManager(symbols)
        self.data_manager = data_manager
        self.state_store = LiveStateStore(snapshot_path=snapshot_path)
        self.kill_switch = KillSwitchManager(
            self.state_store,
            microstructure_recovery_streak=microstructure_recovery_streak,
        )
        self.order_manager = order_manager or OrderManager()
        self.execution_quality_report_path = (
            Path(execution_quality_report_path) if execution_quality_report_path is not None else None
        )
        self.account_sync_interval_seconds = max(1.0, float(account_sync_interval_seconds))
        self.account_sync_failure_threshold = max(1, int(account_sync_failure_threshold))
        self.execution_degradation_min_samples = max(1, int(execution_degradation_min_samples))
        self.execution_degradation_warn_edge_bps = float(execution_degradation_warn_edge_bps)
        self.execution_degradation_block_edge_bps = float(execution_degradation_block_edge_bps)
        self.execution_degradation_throttle_scale = min(
            1.0, max(0.0, float(execution_degradation_throttle_scale))
        )
        self.account_snapshot_fetcher = account_snapshot_fetcher
        self.account_sync_failure_count = 0
        self._running = False
        self._tasks: List[asyncio.Task] = []

    @property
    def session_metadata(self) -> Dict[str, Any]:
        return {
            "symbols": list(self.symbols),
            "live_state_snapshot_path": (
                str(self.state_store._snapshot_path) if self.state_store._snapshot_path is not None else ""
            ),
            "live_state_auto_persist_enabled": bool(self.state_store._snapshot_path is not None),
            "kill_switch_recovery_streak": int(self.kill_switch.microstructure_recovery_streak),
            "account_sync_interval_seconds": float(self.account_sync_interval_seconds),
            "account_sync_failure_threshold": int(self.account_sync_failure_threshold),
            "execution_degradation_min_samples": int(self.execution_degradation_min_samples),
            "execution_degradation_warn_edge_bps": float(self.execution_degradation_warn_edge_bps),
            "execution_degradation_block_edge_bps": float(self.execution_degradation_block_edge_bps),
            "execution_degradation_throttle_scale": float(self.execution_degradation_throttle_scale),
            "execution_quality_report_path": (
                str(self.execution_quality_report_path) if self.execution_quality_report_path is not None else ""
            ),
        }

    def _assess_execution_degradation(self, order: Any) -> Dict[str, float | str]:
        metadata = dict(getattr(order, "metadata", {}) or {})
        bucket_records = [
            item
            for item in self.order_manager.execution_attribution
            if item.symbol == str(order.symbol).upper()
            and item.strategy == str(metadata.get("strategy", ""))
            and item.volatility_regime == str(metadata.get("volatility_regime", ""))
            and item.microstructure_regime == str(metadata.get("microstructure_regime", ""))
        ]
        sample_count = len(bucket_records)
        if sample_count < self.execution_degradation_min_samples:
            return {"action": "allow", "sample_count": float(sample_count), "avg_realized_net_edge_bps": 0.0}

        avg_realized_net_edge_bps = sum(float(item.realized_net_edge_bps) for item in bucket_records) / float(sample_count)
        if avg_realized_net_edge_bps <= self.execution_degradation_block_edge_bps:
            return {
                "action": "block",
                "sample_count": float(sample_count),
                "avg_realized_net_edge_bps": float(avg_realized_net_edge_bps),
            }
        if avg_realized_net_edge_bps <= self.execution_degradation_warn_edge_bps:
            return {
                "action": "throttle",
                "sample_count": float(sample_count),
                "avg_realized_net_edge_bps": float(avg_realized_net_edge_bps),
            }
        return {
            "action": "allow",
            "sample_count": float(sample_count),
            "avg_realized_net_edge_bps": float(avg_realized_net_edge_bps),
        }

    def submit_strategy_result(
        self,
        result: Any,
        *,
        client_order_id: str,
        timestamp: Any | None = None,
        order_type: OrderType = OrderType.MARKET,
        realized_fee_bps: float = 0.0,
        market_state: Dict[str, float] | None = None,
        max_spread_bps: float = 5.0,
        min_depth_usd: float = 25_000.0,
        min_tob_coverage: float = 0.80,
    ) -> Dict[str, Any] | None:
        order = build_live_order_from_strategy_result(
            result,
            client_order_id=client_order_id,
            timestamp=timestamp,
            order_type=order_type,
            realized_fee_bps=realized_fee_bps,
        )
        if order is None:
            return None
        degradation = self._assess_execution_degradation(order)
        order.metadata["execution_degradation_action"] = str(degradation["action"])
        order.metadata["execution_degradation_sample_count"] = float(degradation["sample_count"])
        order.metadata["execution_degradation_avg_realized_net_edge_bps"] = float(
            degradation["avg_realized_net_edge_bps"]
        )
        if degradation["action"] == "block":
            order.update_status(OrderStatus.REJECTED)
            self.order_manager.order_history.append(order)
            return {
                "accepted": False,
                "client_order_id": order.client_order_id,
                "blocked_by": "execution_degradation",
                "degradation": degradation,
            }
        if degradation["action"] == "throttle":
            original_quantity = float(order.quantity)
            order.quantity = original_quantity * self.execution_degradation_throttle_scale
            order.remaining_quantity = order.quantity
            order.metadata["execution_degradation_original_quantity"] = original_quantity
            order.metadata["execution_degradation_applied_scale"] = float(self.execution_degradation_throttle_scale)
        return self.order_manager.submit_order(
            order,
            kill_switch_manager=self.kill_switch,
            market_state=market_state,
            max_spread_bps=max_spread_bps,
            min_depth_usd=min_depth_usd,
            min_tob_coverage=min_tob_coverage,
        )

    def on_order_fill(self, client_order_id: str, fill_qty: float, fill_price: float) -> None:
        self.order_manager.on_fill(client_order_id, fill_qty=fill_qty, fill_price=fill_price)
        self.persist_execution_quality_report()

    def execution_quality_summary(self) -> Dict[str, float]:
        return self.order_manager.summarize_execution_quality()

    def persist_execution_quality_report(self) -> Path | None:
        if self.execution_quality_report_path is None:
            return None
        target = self.execution_quality_report_path
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "summary": self.execution_quality_summary(),
            "by_symbol": summarize_execution_attribution_by(self.order_manager.execution_attribution, "symbol"),
            "by_strategy": summarize_execution_attribution_by(self.order_manager.execution_attribution, "strategy"),
            "by_volatility_regime": summarize_execution_attribution_by(
                self.order_manager.execution_attribution, "volatility_regime"
            ),
            "by_microstructure_regime": summarize_execution_attribution_by(
                self.order_manager.execution_attribution, "microstructure_regime"
            ),
            "records": [
                {
                    "client_order_id": item.client_order_id,
                    "symbol": item.symbol,
                    "strategy": item.strategy,
                    "volatility_regime": item.volatility_regime,
                    "microstructure_regime": item.microstructure_regime,
                    "side": item.side,
                    "quantity": float(item.quantity),
                    "signal_timestamp": item.signal_timestamp,
                    "expected_net_edge_bps": float(item.expected_net_edge_bps),
                    "realized_net_edge_bps": float(item.realized_net_edge_bps),
                    "edge_decay_bps": float(item.edge_decay_bps),
                    "created_at": item.created_at,
                }
                for item in self.order_manager.execution_attribution
            ],
        }
        target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return target

    async def start(self):
        _LOG.info("Starting Live Engine for %s", self.symbols)
        if self.state_store._snapshot_path is not None:
            _LOG.info("Live state auto-persist enabled at %s", self.state_store._snapshot_path)
        self._running = True
        
        # Start the data ingestion manager
        await self.data_manager.start()
        
        # Start consumers
        self._tasks.append(asyncio.create_task(self._consume_klines()))
        self._tasks.append(asyncio.create_task(self._consume_tickers()))
        if self.account_snapshot_fetcher is not None:
            self._tasks.append(asyncio.create_task(self._sync_account_state()))
        
        # Keep running
        while self._running:
            await asyncio.sleep(1)

    async def stop(self):
        _LOG.info("Stopping Live Engine...")
        self._running = False
        await self.data_manager.stop()
        for task in self._tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    async def _consume_klines(self):
        while self._running:
            try:
                event = await self.data_manager.kline_queue.get()
                # Here we would update the live engine's feature state
                _LOG.debug(f"Consumed kline: {event.symbol} {event.timeframe} close={event.close} final={event.is_final}")
                self.data_manager.kline_queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                _LOG.error(f"Error consuming kline: {e}")

    async def _consume_tickers(self):
        while self._running:
            try:
                event = await self.data_manager.ticker_queue.get()
                # Here we would update order execution state, bid/ask spread, etc.
                _LOG.debug(f"Consumed ticker: {event.symbol} bid={event.best_bid_price} ask={event.best_ask_price}")
                self.data_manager.ticker_queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                _LOG.error(f"Error consuming ticker: {e}")

    async def _sync_account_state(self):
        while self._running:
            try:
                snapshot = await self.account_snapshot_fetcher()
                if isinstance(snapshot, dict):
                    self.state_store.update_from_exchange_snapshot(snapshot)
                    self.account_sync_failure_count = 0
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.account_sync_failure_count += 1
                _LOG.error(f"Error syncing account state: {e}")
                if self.account_sync_failure_count >= self.account_sync_failure_threshold:
                    self.kill_switch.trigger(
                        KillSwitchReason.ACCOUNT_SYNC_LOSS,
                        (
                            "Authenticated account sync failed "
                            f"{self.account_sync_failure_count} times consecutively"
                        ),
                    )
            await asyncio.sleep(self.account_sync_interval_seconds)

async def main(snapshot_path: str | Path | None = None):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    runner = LiveEngineRunner(["btcusdt", "ethusdt"], snapshot_path=snapshot_path)
    
    loop = asyncio.get_running_loop()
    import signal
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, lambda: asyncio.create_task(runner.stop()))
        except NotImplementedError:
            pass
            
    await runner.start()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
