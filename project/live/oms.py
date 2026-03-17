"""
Live Order Management System (OMS) state machine.

Tracks the lifecycle of an order from submission to terminal state (FILLED, CANCELLED, REJECTED).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from typing import Any, Dict, List, Optional

import pandas as pd

from project.engine.strategy_executor import StrategyResult, build_live_order_metadata
from project.live.execution_attribution import (
    ExecutionAttributionRecord,
    build_execution_attribution_record,
    summarize_execution_attribution,
)

LOGGER = logging.getLogger(__name__)


class OrderSubmissionBlocked(RuntimeError):
    """Raised when a pre-trade guard rejects an order before OMS activation."""


class OrderStatus(Enum):
    PENDING_NEW = auto()
    NEW = auto()
    PARTIALLY_FILLED = auto()
    FILLED = auto()
    PENDING_CANCEL = auto()
    CANCELLED = auto()
    REJECTED = auto()
    EXPIRED = auto()


class OrderSide(Enum):
    BUY = auto()
    SELL = auto()


class OrderType(Enum):
    LIMIT = auto()
    MARKET = auto()


@dataclass
class LiveOrder:
    client_order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    
    # State
    status: OrderStatus = OrderStatus.PENDING_NEW
    filled_quantity: float = 0.0
    remaining_quantity: float = 0.0
    avg_fill_price: float = 0.0
    exchange_order_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self):
        if self.remaining_quantity == 0:
            self.remaining_quantity = self.quantity

    def update_status(self, new_status: OrderStatus, exchange_id: Optional[str] = None):
        self.status = new_status
        if exchange_id:
            self.exchange_order_id = exchange_id
        self.updated_at = datetime.now(timezone.utc)

    def apply_fill(self, fill_qty: float, fill_price: float):
        total_filled = self.filled_quantity + fill_qty
        # Update WAP
        self.avg_fill_price = (
            (self.avg_fill_price * self.filled_quantity) + (fill_price * fill_qty)
        ) / total_filled
        
        self.filled_quantity = total_filled
        self.remaining_quantity = max(0.0, self.quantity - self.filled_quantity)
        
        if self.remaining_quantity <= 1e-10:
            self.update_status(OrderStatus.FILLED)
        else:
            self.update_status(OrderStatus.PARTIALLY_FILLED)


class OrderManager:
    def __init__(self):
        self.active_orders: Dict[str, LiveOrder] = {}  # client_order_id -> LiveOrder
        self.order_history: List[LiveOrder] = []
        self.execution_attribution: List[ExecutionAttributionRecord] = []

    def add_order(self, order: LiveOrder):
        self.active_orders[order.client_order_id] = order

    def get_order(self, client_order_id: str) -> Optional[LiveOrder]:
        return self.active_orders.get(client_order_id)

    def submit_order(
        self,
        order: LiveOrder,
        *,
        kill_switch_manager: Any | None = None,
        market_state: Optional[Dict[str, float]] = None,
        max_spread_bps: float = 5.0,
        min_depth_usd: float = 25_000.0,
        min_tob_coverage: float = 0.80,
    ) -> Dict[str, Any]:
        """
        Activate an order only if live microstructure is tradable.

        ``add_order`` remains the raw state mutation primitive. New live order
        flow should prefer ``submit_order`` so the kill-switch can block unsafe
        conditions before the order becomes active.
        """
        gate = None
        if kill_switch_manager is not None:
            snapshot = dict(market_state or {})
            gate = kill_switch_manager.check_microstructure(
                spread_bps=snapshot.get("spread_bps"),
                depth_usd=snapshot.get("depth_usd", snapshot.get("liquidity_available")),
                tob_coverage=snapshot.get("tob_coverage"),
                max_spread_bps=max_spread_bps,
                min_depth_usd=min_depth_usd,
                min_tob_coverage=min_tob_coverage,
            )
            if not gate["is_tradable"]:
                order.update_status(OrderStatus.REJECTED)
                self.order_history.append(order)
                raise OrderSubmissionBlocked(
                    f"order {order.client_order_id} blocked by microstructure gate: "
                    f"{','.join(gate['reasons'])}"
                )

        self.add_order(order)
        return {
            "accepted": True,
            "client_order_id": order.client_order_id,
            "gate": gate,
        }

    def on_order_update(self, client_order_id: str, status: OrderStatus, **kwargs):
        order = self.get_order(client_order_id)
        if not order:
            LOGGER.warning(f"Received update for unknown order {client_order_id}")
            return

        order.update_status(status, exchange_id=kwargs.get("exchange_order_id"))
        
        if status in (OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED, OrderStatus.EXPIRED):
            self.order_history.append(order)
            del self.active_orders[client_order_id]

    def on_fill(self, client_order_id: str, fill_qty: float, fill_price: float):
        order = self.get_order(client_order_id)
        if not order:
            LOGGER.warning(f"Received fill for unknown order {client_order_id}")
            return

        order.apply_fill(fill_qty, fill_price)
        
        if order.status == OrderStatus.FILLED:
            self._record_execution_attribution(order)
            self.order_history.append(order)
            del self.active_orders[client_order_id]

    def _record_execution_attribution(self, order: LiveOrder) -> None:
        metadata = dict(order.metadata or {})
        required = {"expected_entry_price", "expected_return_bps", "expected_adverse_bps"}
        if not required.issubset(metadata):
            return

        record = build_execution_attribution_record(
            client_order_id=order.client_order_id,
            symbol=order.symbol,
            strategy=str(metadata.get("strategy", "")),
            volatility_regime=str(metadata.get("volatility_regime", "")),
            microstructure_regime=str(metadata.get("microstructure_regime", "")),
            side=order.side.name,
            quantity=order.quantity,
            signal_timestamp=str(metadata.get("signal_timestamp", order.created_at.isoformat())),
            expected_entry_price=float(metadata["expected_entry_price"]),
            realized_fill_price=float(order.avg_fill_price),
            expected_return_bps=float(metadata["expected_return_bps"]),
            expected_adverse_bps=float(metadata["expected_adverse_bps"]),
            expected_cost_bps=float(metadata.get("expected_cost_bps", 0.0) or 0.0),
            realized_fee_bps=float(metadata.get("realized_fee_bps", 0.0) or 0.0),
        )
        self.execution_attribution.append(record)

    def summarize_execution_quality(self) -> Dict[str, float]:
        return summarize_execution_attribution(self.execution_attribution)


def build_live_order_from_strategy_result(
    result: StrategyResult,
    *,
    client_order_id: str,
    timestamp: pd.Timestamp | None = None,
    order_type: OrderType = OrderType.MARKET,
    realized_fee_bps: float = 0.0,
) -> LiveOrder | None:
    frame = result.data.copy()
    if frame.empty:
        return None

    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    if timestamp is None:
        row = frame.iloc[-1]
    else:
        ts = pd.Timestamp(timestamp)
        ts = ts.tz_convert("UTC") if ts.tz is not None else ts.tz_localize("UTC")
        matched = frame.loc[frame["timestamp"] == ts]
        if matched.empty:
            raise KeyError(f"timestamp not found in strategy result: {ts}")
        row = matched.iloc[-1]

    current_target = float(row.get("target_position", 0.0) or 0.0)
    prior_position = float(row.get("prior_executed_position", 0.0) or 0.0)
    expected_entry_price = float(row.get("fill_price", row.get("close", 0.0)) or 0.0)
    delta_notional = current_target - prior_position
    if abs(delta_notional) <= 1e-12 or expected_entry_price <= 0.0:
        return None

    side = OrderSide.BUY if delta_notional > 0 else OrderSide.SELL
    quantity = abs(delta_notional) / expected_entry_price
    metadata = build_live_order_metadata(
        result,
        timestamp=row["timestamp"],
        realized_fee_bps=realized_fee_bps,
    )
    price = float(expected_entry_price) if order_type == OrderType.LIMIT else None

    return LiveOrder(
        client_order_id=client_order_id,
        symbol=str(row.get("symbol", "")).upper(),
        side=side,
        order_type=order_type,
        quantity=float(quantity),
        price=price,
        metadata=metadata,
    )
