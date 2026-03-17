from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class ExecutionAttributionRecord:
    client_order_id: str
    symbol: str
    strategy: str
    volatility_regime: str
    microstructure_regime: str
    side: str
    quantity: float
    signal_timestamp: str
    expected_entry_price: float
    expected_return_bps: float
    expected_adverse_bps: float
    expected_cost_bps: float
    expected_net_edge_bps: float
    realized_fill_price: float
    realized_fee_bps: float
    realized_slippage_bps: float
    realized_total_cost_bps: float
    realized_net_edge_bps: float
    edge_decay_bps: float
    created_at: str


def build_execution_attribution_record(
    *,
    client_order_id: str,
    symbol: str,
    strategy: str,
    volatility_regime: str,
    microstructure_regime: str,
    side: str,
    quantity: float,
    signal_timestamp: str,
    expected_entry_price: float,
    realized_fill_price: float,
    expected_return_bps: float,
    expected_adverse_bps: float,
    expected_cost_bps: float,
    realized_fee_bps: float,
) -> ExecutionAttributionRecord:
    entry_price = max(float(expected_entry_price), 1e-12)
    fill_price = float(realized_fill_price)
    signed_slippage_bps = ((fill_price - entry_price) / entry_price) * 10000.0
    side_norm = str(side).strip().upper()
    realized_slippage_bps = signed_slippage_bps if side_norm == "BUY" else -signed_slippage_bps
    realized_total_cost_bps = float(realized_fee_bps) + float(realized_slippage_bps)
    expected_net_edge_bps = float(expected_return_bps) - float(expected_adverse_bps) - float(expected_cost_bps)
    realized_net_edge_bps = float(expected_return_bps) - float(expected_adverse_bps) - realized_total_cost_bps
    edge_decay_bps = realized_net_edge_bps - expected_net_edge_bps
    return ExecutionAttributionRecord(
        client_order_id=str(client_order_id),
        symbol=str(symbol).upper(),
        strategy=str(strategy),
        volatility_regime=str(volatility_regime),
        microstructure_regime=str(microstructure_regime),
        side=side_norm,
        quantity=float(quantity),
        signal_timestamp=str(signal_timestamp),
        expected_entry_price=float(expected_entry_price),
        expected_return_bps=float(expected_return_bps),
        expected_adverse_bps=float(expected_adverse_bps),
        expected_cost_bps=float(expected_cost_bps),
        expected_net_edge_bps=float(expected_net_edge_bps),
        realized_fill_price=fill_price,
        realized_fee_bps=float(realized_fee_bps),
        realized_slippage_bps=float(realized_slippage_bps),
        realized_total_cost_bps=float(realized_total_cost_bps),
        realized_net_edge_bps=float(realized_net_edge_bps),
        edge_decay_bps=float(edge_decay_bps),
        created_at=_utcnow().isoformat(),
    )


def summarize_execution_attribution(records: List[ExecutionAttributionRecord]) -> Dict[str, float]:
    if not records:
        return {
            "fills": 0.0,
            "avg_expected_net_edge_bps": 0.0,
            "avg_realized_net_edge_bps": 0.0,
            "avg_edge_decay_bps": 0.0,
            "avg_realized_fee_bps": 0.0,
            "avg_realized_slippage_bps": 0.0,
            "win_rate_vs_expected_edge": 0.0,
        }

    count = float(len(records))
    expected_net = [float(item.expected_net_edge_bps) for item in records]
    realized_net = [float(item.realized_net_edge_bps) for item in records]
    edge_decay = [float(item.edge_decay_bps) for item in records]
    fees = [float(item.realized_fee_bps) for item in records]
    slippage = [float(item.realized_slippage_bps) for item in records]
    wins = sum(1 for item in records if item.realized_net_edge_bps >= 0.0)
    return {
        "fills": count,
        "avg_expected_net_edge_bps": sum(expected_net) / count,
        "avg_realized_net_edge_bps": sum(realized_net) / count,
        "avg_edge_decay_bps": sum(edge_decay) / count,
        "avg_realized_fee_bps": sum(fees) / count,
        "avg_realized_slippage_bps": sum(slippage) / count,
        "win_rate_vs_expected_edge": wins / count,
    }


def summarize_execution_attribution_by(records: List[ExecutionAttributionRecord], key: str) -> Dict[str, Dict[str, float]]:
    grouped: Dict[str, List[ExecutionAttributionRecord]] = {}
    for record in records:
        group_value = str(getattr(record, key, "") or "")
        grouped.setdefault(group_value, []).append(record)
    return {
        group: summarize_execution_attribution(items)
        for group, items in sorted(grouped.items(), key=lambda item: item[0])
    }


def record_to_dict(record: ExecutionAttributionRecord) -> Dict[str, Any]:
    return asdict(record)
