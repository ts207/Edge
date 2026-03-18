"""
Live state tracking for account and positions.

Provides a unified 'LiveState' container to track balance, active positions,
and exchange status in real-time.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class PositionState:
    symbol: str
    side: str               # "LONG" | "SHORT"
    quantity: float
    entry_price: float
    mark_price: float
    unrealized_pnl: float
    liquidation_price: Optional[float] = None
    leverage: float = 1.0
    margin_type: str = "ISOLATED"
    update_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self):
        self.symbol = self.symbol.upper()
        self.side = self.side.upper()


@dataclass
class AccountState:
    wallet_balance: float = 0.0
    margin_balance: float = 0.0
    available_balance: float = 0.0
    total_unrealized_pnl: float = 0.0
    positions: Dict[str, PositionState] = field(default_factory=dict)
    update_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    exchange_status: str = "NORMAL" # NORMAL | DEGRADED | DOWN

    def update_position(self, pos: PositionState):
        self.positions[pos.symbol] = pos
        self._recalculate_totals()

    def remove_position(self, symbol: str):
        if symbol.upper() in self.positions:
            del self.positions[symbol.upper()]
            self._recalculate_totals()

    def _recalculate_totals(self):
        self.total_unrealized_pnl = sum(p.unrealized_pnl for p in self.positions.values())
        self.update_time = datetime.now(timezone.utc)


@dataclass
class KillSwitchSnapshot:
    is_active: bool = False
    reason: Optional[str] = None
    triggered_at: Optional[str] = None
    message: str = ""
    recovery_streak: int = 0


class LiveStateStore:
    """Thread-safe or async-safe store for LiveState (to be expanded)."""
    def __init__(self, *, snapshot_path: str | Path | None = None):
        self.account = AccountState()
        self._last_snapshot_time: Optional[datetime] = None
        self.kill_switch = KillSwitchSnapshot()
        self._snapshot_path = Path(snapshot_path) if snapshot_path is not None else None

    def _maybe_persist(self) -> None:
        if self._snapshot_path is not None:
            self.save_snapshot(self._snapshot_path)

    def update_from_exchange_snapshot(self, data: Dict[str, Any]):
        """
        Update state from a full exchange account/position snapshot.
        Expected format: typical CCXT or Binance account information.
        """
        self.account.wallet_balance = float(data.get("wallet_balance", self.account.wallet_balance))
        self.account.margin_balance = float(data.get("margin_balance", self.account.margin_balance))
        self.account.available_balance = float(data.get("available_balance", self.account.available_balance))
        self.account.exchange_status = str(data.get("exchange_status", self.account.exchange_status))
        
        positions_raw = data.get("positions", [])
        for p in positions_raw:
            qty = float(p.get("quantity", 0.0))
            symbol = str(p.get("symbol")).upper()
            if qty == 0:
                self.account.remove_position(symbol)
            else:
                pos = PositionState(
                    symbol=symbol,
                    side="LONG" if qty > 0 else "SHORT",
                    quantity=abs(qty),
                    entry_price=float(p.get("entry_price", 0.0)),
                    mark_price=float(p.get("mark_price", p.get("entry_price", 0.0))),
                    unrealized_pnl=float(p.get("unrealized_pnl", 0.0)),
                    liquidation_price=float(p.get("liquidation_price", 0.0)) if p.get("liquidation_price") else None,
                    leverage=float(p.get("leverage", 1.0) or 1.0),
                    margin_type=str(p.get("margin_type", "ISOLATED")),
                )
                self.account.update_position(pos)
        
        self._last_snapshot_time = self.account.update_time
        self._maybe_persist()

    def reconcile(self, exchange_data: Dict[str, Any], tolerance: float = 1e-6) -> List[str]:
        """
        Compare current state with exchange data and return a list of discrepancies.
        Discrepancies are returned as human-readable error messages.
        """
        errors = []
        
        # 1. Compare Wallet Balance
        exchange_wallet = float(exchange_data.get("wallet_balance", 0.0))
        if abs(self.account.wallet_balance - exchange_wallet) > tolerance:
            errors.append(
                f"Wallet balance mismatch: local={self.account.wallet_balance}, "
                f"exchange={exchange_wallet}"
            )
            
        # 2. Compare Positions
        exchange_positions = {
            str(p["symbol"]).upper(): p 
            for p in exchange_data.get("positions", [])
        }
        local_positions = self.account.positions
        
        all_symbols = set(exchange_positions.keys()) | set(local_positions.keys())
        for sym in all_symbols:
            e_pos = exchange_positions.get(sym)
            l_pos = local_positions.get(sym)
            
            e_qty = float(e_pos["quantity"]) if e_pos else 0.0
            l_qty = float(l_pos.quantity) if l_pos else 0.0
            if l_pos and l_pos.side == "SHORT":
                l_qty = -l_qty
                
            if abs(e_qty - l_qty) > tolerance:
                errors.append(
                    f"Position mismatch for {sym}: local_qty={l_qty}, exchange_qty={e_qty}"
                )
        
        return errors

    def set_kill_switch_snapshot(self, snapshot: Dict[str, Any]) -> None:
        self.kill_switch = KillSwitchSnapshot(
            is_active=bool(snapshot.get("is_active", False)),
            reason=str(snapshot["reason"]) if snapshot.get("reason") else None,
            triggered_at=str(snapshot["triggered_at"]) if snapshot.get("triggered_at") else None,
            message=str(snapshot.get("message", "")),
            recovery_streak=int(snapshot.get("recovery_streak", 0) or 0),
        )
        self._maybe_persist()

    def get_kill_switch_snapshot(self) -> Dict[str, Any]:
        return {
            "is_active": bool(self.kill_switch.is_active),
            "reason": self.kill_switch.reason,
            "triggered_at": self.kill_switch.triggered_at,
            "message": self.kill_switch.message,
            "recovery_streak": int(self.kill_switch.recovery_streak),
        }

    def to_snapshot(self) -> Dict[str, Any]:
        return {
            "account": {
                "wallet_balance": float(self.account.wallet_balance),
                "margin_balance": float(self.account.margin_balance),
                "available_balance": float(self.account.available_balance),
                "total_unrealized_pnl": float(self.account.total_unrealized_pnl),
                "exchange_status": str(self.account.exchange_status),
                "update_time": self.account.update_time.isoformat(),
                "positions": [
                    {
                        "symbol": pos.symbol,
                        "side": pos.side,
                        "quantity": float(pos.quantity),
                        "entry_price": float(pos.entry_price),
                        "mark_price": float(pos.mark_price),
                        "unrealized_pnl": float(pos.unrealized_pnl),
                        "liquidation_price": pos.liquidation_price,
                        "leverage": float(pos.leverage),
                        "margin_type": pos.margin_type,
                        "update_time": pos.update_time.isoformat(),
                    }
                    for pos in self.account.positions.values()
                ],
            },
            "kill_switch": self.get_kill_switch_snapshot(),
            "last_snapshot_time": (
                self._last_snapshot_time.isoformat() if self._last_snapshot_time is not None else None
            ),
        }

    @classmethod
    def from_snapshot(cls, snapshot: Dict[str, Any]) -> "LiveStateStore":
        store = cls()
        account = dict(snapshot.get("account", {}))
        store.account.wallet_balance = float(account.get("wallet_balance", 0.0))
        store.account.margin_balance = float(account.get("margin_balance", 0.0))
        store.account.available_balance = float(account.get("available_balance", 0.0))
        store.account.total_unrealized_pnl = float(account.get("total_unrealized_pnl", 0.0))
        store.account.exchange_status = str(account.get("exchange_status", "NORMAL"))
        account_update_time = account.get("update_time")
        if account_update_time:
            store.account.update_time = datetime.fromisoformat(str(account_update_time))
        store.account.positions = {}
        for raw in list(account.get("positions", [])):
            pos = PositionState(
                symbol=str(raw.get("symbol", "")),
                side=str(raw.get("side", "LONG")),
                quantity=float(raw.get("quantity", 0.0)),
                entry_price=float(raw.get("entry_price", 0.0)),
                mark_price=float(raw.get("mark_price", 0.0)),
                unrealized_pnl=float(raw.get("unrealized_pnl", 0.0)),
                liquidation_price=(
                    float(raw["liquidation_price"]) if raw.get("liquidation_price") is not None else None
                ),
                leverage=float(raw.get("leverage", 1.0)),
                margin_type=str(raw.get("margin_type", "ISOLATED")),
            )
            update_time = raw.get("update_time")
            if update_time:
                pos.update_time = datetime.fromisoformat(str(update_time))
            store.account.positions[pos.symbol] = pos
        store.set_kill_switch_snapshot(dict(snapshot.get("kill_switch", {})))
        last_snapshot_time = snapshot.get("last_snapshot_time")
        if last_snapshot_time:
            store._last_snapshot_time = datetime.fromisoformat(str(last_snapshot_time))
        return store

    def save_snapshot(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self.to_snapshot(), indent=2, sort_keys=True), encoding="utf-8")
        return target

    @classmethod
    def load_snapshot(cls, path: str | Path) -> "LiveStateStore":
        source = Path(path)
        payload = json.loads(source.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("live state snapshot must be a JSON object")
        store = cls.from_snapshot(payload)
        store._snapshot_path = source
        return store
