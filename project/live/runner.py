from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List

from project.live.kill_switch import KillSwitchManager, KillSwitchReason
from project.live.oms import (
    OrderManager,
    OrderType,
    OrderStatus,
    OrderSubmissionFailed,
    build_live_order_from_strategy_result,
)
from project.live.binance_client import BinanceFuturesClient
from project.live.state import LiveStateStore
from project.live.execution_attribution import summarize_execution_attribution_by
from project.live.health_checks import DataHealthMonitor
from project.portfolio.incubation import IncubationLedger
from project import PROJECT_ROOT

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
        health_check_interval_seconds: float = 5.0,
        stale_threshold_sec: float = 10.0,
        reconcile_at_startup: bool = True,
        runtime_mode: str = "monitor_only",
        strategy_runtime: Dict[str, Any] | None = None,
    ):
        # Phase 3: Native REST Client for Initialization & Recovery
        self.rest_client = BinanceFuturesClient(
            api_key="", # To be provided by environment/caller
            api_secret="",
        )

        self.symbols = symbols
        self.state_store = LiveStateStore(snapshot_path=snapshot_path)
        self.kill_switch = KillSwitchManager(
            self.state_store,
            microstructure_recovery_streak=microstructure_recovery_streak,
        )
        self.kill_switch.register_callback(self._on_kill_switch_triggered)
        if data_manager is None:
            from project.live.ingest.manager import LiveDataManager

            data_manager = LiveDataManager(
                symbols,
                on_reconnect_exhausted=self._on_ws_reconnect_exhausted,
                rest_client=self.rest_client,
            )
        self.data_manager = data_manager
        self.order_manager = order_manager or OrderManager(exchange_client=self.rest_client)
        self.execution_quality_report_path = (
            Path(execution_quality_report_path)
            if execution_quality_report_path is not None
            else None
        )
        self.account_sync_interval_seconds = max(1.0, float(account_sync_interval_seconds))
        self.account_sync_failure_threshold = max(1, int(account_sync_failure_threshold))
        self.execution_degradation_min_samples = max(1, int(execution_degradation_min_samples))
        self.execution_degradation_warn_edge_bps = float(execution_degradation_warn_edge_bps)
        self.execution_degradation_block_edge_bps = float(execution_degradation_block_edge_bps)
        self.execution_degradation_throttle_scale = min(
            1.0, max(0.0, float(execution_degradation_throttle_scale))
        )
        self.health_monitor = DataHealthMonitor(stale_threshold_sec=stale_threshold_sec)
        if hasattr(self.data_manager, "health_monitor_keys"):
            self.health_monitor.register_streams(self.data_manager.health_monitor_keys())
        self.health_check_interval_seconds = max(1.0, float(health_check_interval_seconds))
        self.reconcile_at_startup = bool(reconcile_at_startup)
        self.account_snapshot_fetcher = account_snapshot_fetcher
        self.account_sync_failure_count = 0
        self.runtime_mode = str(runtime_mode or "monitor_only").strip().lower()
        self.strategy_runtime = dict(strategy_runtime or {})
        if order_manager is None and self.runtime_mode != "trading":
            self.order_manager = OrderManager()
        
        # Phase 5: Incubation Ledger
        self.incubation_ledger = IncubationLedger(
            PROJECT_ROOT / "project" / "live" / "incubation_ledger.json"
        )
        
        self._running = False
        self._tasks: List[asyncio.Task] = []
        self._kill_switch_task: asyncio.Task | None = None

    @property
    def session_metadata(self) -> Dict[str, Any]:
        return {
            "symbols": list(self.symbols),
            "live_state_snapshot_path": (
                str(self.state_store._snapshot_path)
                if self.state_store._snapshot_path is not None
                else ""
            ),
            "live_state_auto_persist_enabled": bool(self.state_store._snapshot_path is not None),
            "kill_switch_recovery_streak": int(self.kill_switch.microstructure_recovery_streak),
            "account_sync_interval_seconds": float(self.account_sync_interval_seconds),
            "account_sync_failure_threshold": int(self.account_sync_failure_threshold),
            "execution_degradation_min_samples": int(self.execution_degradation_min_samples),
            "execution_degradation_warn_edge_bps": float(self.execution_degradation_warn_edge_bps),
            "execution_degradation_block_edge_bps": float(
                self.execution_degradation_block_edge_bps
            ),
            "execution_degradation_throttle_scale": float(
                self.execution_degradation_throttle_scale
            ),
            "execution_quality_report_path": (
                str(self.execution_quality_report_path)
                if self.execution_quality_report_path is not None
                else ""
            ),
            "runtime_mode": self.runtime_mode,
            "strategy_runtime_implemented": bool(self.strategy_runtime.get("implemented", False)),
        }

    def _ensure_runtime_mode_known(self) -> None:
        if self.runtime_mode not in {"monitor_only", "trading"}:
            raise RuntimeError(
                f"Unsupported runtime_mode '{self.runtime_mode}'. Expected 'monitor_only' or 'trading'."
            )

    def _ensure_runtime_ready_for_start(self) -> None:
        self._ensure_runtime_mode_known()
        if self.runtime_mode == "trading" and not bool(self.strategy_runtime.get("implemented", False)):
            raise RuntimeError(
                "runtime_mode='trading' requires strategy_runtime.implemented=true"
            )

    def _ensure_trading_enabled(self) -> None:
        self._ensure_runtime_ready_for_start()
        if self.runtime_mode != "trading":
            raise RuntimeError(
                "Order submission is disabled when runtime_mode='monitor_only'."
            )

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
            return {
                "action": "allow",
                "sample_count": float(sample_count),
                "avg_realized_net_edge_bps": 0.0,
            }

        avg_realized_net_edge_bps = sum(
            float(item.realized_net_edge_bps) for item in bucket_records
        ) / float(sample_count)
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
        self._ensure_trading_enabled()
        prepared = self._prepare_strategy_order(
            result,
            client_order_id=client_order_id,
            timestamp=timestamp,
            order_type=order_type,
            realized_fee_bps=realized_fee_bps,
        )
        if prepared is None:
            return None
        order, blocked = prepared
        if blocked is not None:
            return blocked
        if getattr(self.order_manager, "exchange_client", None) is not None:
            raise OrderSubmissionFailed(
                "exchange-backed live submission requires await submit_strategy_result_async(...)"
            )
        return self.order_manager.submit_order(
            order,
            kill_switch_manager=self.kill_switch,
            market_state=market_state,
            max_spread_bps=max_spread_bps,
            min_depth_usd=min_depth_usd,
            min_tob_coverage=min_tob_coverage,
        )

    async def submit_strategy_result_async(
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
        self._ensure_trading_enabled()
        prepared = self._prepare_strategy_order(
            result,
            client_order_id=client_order_id,
            timestamp=timestamp,
            order_type=order_type,
            realized_fee_bps=realized_fee_bps,
        )
        if prepared is None:
            return None
        order, blocked = prepared
        if blocked is not None:
            return blocked
        return await self.order_manager.submit_order_async(
            order,
            kill_switch_manager=self.kill_switch,
            market_state=market_state,
            max_spread_bps=max_spread_bps,
            min_depth_usd=min_depth_usd,
            min_tob_coverage=min_tob_coverage,
        )

    def _prepare_strategy_order(
        self,
        result: Any,
        *,
        client_order_id: str,
        timestamp: Any | None,
        order_type: OrderType,
        realized_fee_bps: float,
    ) -> tuple[Any, Dict[str, Any] | None] | None:
        order = build_live_order_from_strategy_result(
            result,
            client_order_id=client_order_id,
            timestamp=timestamp,
            order_type=order_type,
            realized_fee_bps=realized_fee_bps,
        )
        if order is None:
            return None

        # Fail closed: a trading submission must already be fully graduated.
        strategy_id = str(order.metadata.get("strategy", "")).strip()
        if not strategy_id:
            order.update_status(OrderStatus.REJECTED)
            self.order_manager.order_history.append(order)
            return order, {
                "accepted": False,
                "client_order_id": order.client_order_id,
                "blocked_by": "missing_strategy_provenance",
            }
        if not self.incubation_ledger.is_graduated(strategy_id):
            _LOG.warning(
                "Strategy %s is still in incubation; rejecting live submission.", strategy_id
            )
            order.update_status(OrderStatus.REJECTED)
            self.order_manager.order_history.append(order)
            return order, {
                "accepted": False,
                "client_order_id": order.client_order_id,
                "blocked_by": "incubation_gate",
                "strategy_id": strategy_id,
            }

        degradation = self._assess_execution_degradation(order)
        order.metadata["execution_degradation_action"] = str(degradation["action"])
        order.metadata["execution_degradation_sample_count"] = float(degradation["sample_count"])
        order.metadata["execution_degradation_avg_realized_net_edge_bps"] = float(
            degradation["avg_realized_net_edge_bps"]
        )
        if degradation["action"] == "block":
            order.update_status(OrderStatus.REJECTED)
            self.order_manager.order_history.append(order)
            return order, {
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
            order.metadata["execution_degradation_applied_scale"] = float(
                self.execution_degradation_throttle_scale
            )
        return order, None

    def _get_portfolio_state_for_sizing(self) -> Dict[str, Any]:
        """
        Produce a portfolio state snapshot suitable for the sizer, 
        including active cluster counts for the 'Portfolio Matrix' gate.
        """
        with self.state_store._lock:
            acc = self.state_store.account
            cluster_counts: Dict[int, int] = {}
            for pos in acc.positions.values():
                if pos.cluster_id is not None:
                    cluster_counts[pos.cluster_id] = cluster_counts.get(pos.cluster_id, 0) + 1
            
            return {
                "portfolio_value": float(acc.wallet_balance + acc.total_unrealized_pnl),
                "gross_exposure": float(sum(abs(p.quantity * p.mark_price) for p in acc.positions.values())),
                "max_gross_leverage": 1.0, # Placeholder or from config
                "target_vol": 0.1, # Placeholder
                "current_vol": 0.1, # Placeholder
                "bucket_exposures": {},
                "active_cluster_counts": cluster_counts,
            }

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
            "by_symbol": summarize_execution_attribution_by(
                self.order_manager.execution_attribution, "symbol"
            ),
            "by_strategy": summarize_execution_attribution_by(
                self.order_manager.execution_attribution, "strategy"
            ),
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
        self._ensure_runtime_ready_for_start()
        if self.state_store._snapshot_path is not None:
            _LOG.info("Live state auto-persist enabled at %s", self.state_store._snapshot_path)

        if self.reconcile_at_startup and self.account_snapshot_fetcher is not None:
            _LOG.info("Performing strict startup reconciliation...")
            exchange_snapshot = await self.account_snapshot_fetcher()
            discrepancies = self.state_store.reconcile(exchange_snapshot)
            if discrepancies:
                for error in discrepancies:
                    _LOG.error(f"RECONCILIATION ERROR: {error}")
                raise RuntimeError(
                    f"Startup reconciliation failed with {len(discrepancies)} discrepancies. "
                    "Aborting startup for safety."
                )
            _LOG.info("Reconciliation successful.")

        self._running = True

        # Start the data ingestion manager
        await self.data_manager.start()

        # Start consumers
        self._tasks.append(asyncio.create_task(self._consume_klines()))
        self._tasks.append(asyncio.create_task(self._consume_tickers()))
        self._tasks.append(asyncio.create_task(self._monitor_data_health()))
        if self.account_snapshot_fetcher is not None:
            self._tasks.append(asyncio.create_task(self._sync_account_state()))

        # Keep running
        while self._running:
            await asyncio.sleep(1)

    async def stop(self):
        _LOG.info("Stopping Live Engine...")
        self._running = False
        await self._shutdown_runtime()

    async def _shutdown_runtime(self) -> None:
        try:
            await self.data_manager.stop()
        except Exception as exc:
            _LOG.error("Failed to stop data manager during shutdown: %s", exc)

        for task in self._tasks:
            task.cancel()
        for task in self._tasks:
            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception as exc:
                _LOG.error("Background task shutdown failed: %s", exc)
        self._tasks = []
        if hasattr(self.order_manager, "close"):
            try:
                await self.order_manager.close()
            except Exception as exc:
                _LOG.error("Failed to close order manager during shutdown: %s", exc)

    def _on_kill_switch_triggered(self, reason: KillSwitchReason, message: str) -> None:
        self._running = False
        if self._kill_switch_task is not None and not self._kill_switch_task.done():
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            _LOG.error(
                "Kill-switch triggered without an active event loop; async unwind could not start."
            )
            return
        self._kill_switch_task = loop.create_task(
            self._handle_kill_switch_trigger(reason, message)
        )

    async def _handle_kill_switch_trigger(
        self, reason: KillSwitchReason, message: str
    ) -> None:
        _LOG.critical("Actuating kill-switch %s: %s", reason.name, message)
        try:
            await self._shutdown_runtime()
            if self.runtime_mode == "trading":
                await self.order_manager.cancel_all_orders()
                await self.order_manager.flatten_all_positions(self.state_store)
        except Exception as exc:
            _LOG.error("Kill-switch actuation failed: %s", exc)

    async def _consume_klines(self):
        while self._running:
            try:
                event = await self.data_manager.kline_queue.get()
                # Here we would update the live engine's feature state
                _LOG.debug(
                    f"Consumed kline: {event.symbol} {event.timeframe} close={event.close} final={event.is_final}"
                )
                self.health_monitor.on_event(event.symbol, f"kline:{event.timeframe}")
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
                _LOG.debug(
                    f"Consumed ticker: {event.symbol} bid={event.best_bid_price} ask={event.best_ask_price}"
                )
                self.health_monitor.on_event(event.symbol, "ticker")
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

    async def _monitor_data_health(self):
        while self._running:
            try:
                report = self.health_monitor.check_health()
                if not report["is_healthy"]:
                    self.kill_switch.trigger(
                        KillSwitchReason.STALE_DATA,
                        (
                            f"Stale data feeds detected: {report['stale_count']} streams "
                            f"(max_staleness={report['max_last_seen_sec_ago']}s)"
                        ),
                    )
            except asyncio.CancelledError:
                break
            except Exception as e:
                _LOG.error(f"Error monitoring data health: {e}")
            await asyncio.sleep(self.health_check_interval_seconds)

    def _on_ws_reconnect_exhausted(self) -> None:
        """Callback invoked when the WebSocket client exhausts all reconnect attempts."""
        _LOG.error(
            "WebSocket reconnect retries exhausted; triggering EXCHANGE_DISCONNECT kill-switch."
        )
        self.kill_switch.trigger(
            KillSwitchReason.EXCHANGE_DISCONNECT,
            "WebSocket connection lost and all reconnect attempts exhausted",
        )


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
