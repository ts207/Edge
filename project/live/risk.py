from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pandas as pd

_LOG = logging.getLogger(__name__)


@dataclass(frozen=True)
class RuntimeRiskCaps:
    max_gross_exposure: float = 1_000_000.0
    max_symbol_exposure: float = 250_000.0
    max_family_exposure: float = 500_000.0
    max_active_theses: int = 20
    reject_on_breach: bool = True  # If False, clip to cap


@dataclass(frozen=True)
class CapBreachEvent:
    timestamp: str
    thesis_id: str
    symbol: str
    cap_type: str  # gross, symbol, family, count
    attempted_value: float
    cap_value: float
    action: str  # rejected, clipped


class RiskEnforcer:
    def __init__(self, caps: RuntimeRiskCaps):
        self.caps = caps
        self.breach_history: List[CapBreachEvent] = []

    def check_and_apply_caps(
        self,
        *,
        thesis_id: str,
        symbol: str,
        family: str,
        attempted_notional: float,
        portfolio_state: Dict[str, Any],
        active_thesis_ids: List[str],
        timestamp: str,
    ) -> tuple[float, Optional[CapBreachEvent]]:
        """
        Enforce risk caps on a single trade intent.
        Returns (effective_notional, Optional breach event).
        """
        effective_notional = attempted_notional
        
        # 1. Max Active Theses
        if thesis_id not in active_thesis_ids:
            if len(active_thesis_ids) >= self.caps.max_active_theses:
                event = CapBreachEvent(
                    timestamp=timestamp,
                    thesis_id=thesis_id,
                    symbol=symbol,
                    cap_type="count",
                    attempted_value=float(len(active_thesis_ids) + 1),
                    cap_value=float(self.caps.max_active_theses),
                    action="rejected"
                )
                self.breach_history.append(event)
                return 0.0, event

        # 2. Per-Symbol Cap
        # portfolio_state["positions"] should contain current notional per symbol
        current_symbol_notional = portfolio_state.get("symbol_exposures", {}).get(symbol, 0.0)
        total_symbol_notional = abs(current_symbol_notional) + abs(attempted_notional)
        if total_symbol_notional > self.caps.max_symbol_exposure:
            available = max(0.0, self.caps.max_symbol_exposure - abs(current_symbol_notional))
            if self.caps.reject_on_breach:
                event = CapBreachEvent(
                    timestamp=timestamp,
                    thesis_id=thesis_id,
                    symbol=symbol,
                    cap_type="symbol",
                    attempted_value=total_symbol_notional,
                    cap_value=self.caps.max_symbol_exposure,
                    action="rejected"
                )
                self.breach_history.append(event)
                return 0.0, event
            else:
                effective_notional = available
                event = CapBreachEvent(
                    timestamp=timestamp,
                    thesis_id=thesis_id,
                    symbol=symbol,
                    cap_type="symbol",
                    attempted_value=total_symbol_notional,
                    cap_value=self.caps.max_symbol_exposure,
                    action="clipped"
                )
                self.breach_history.append(event)

        # 3. Per-Family Cap
        current_family_notional = portfolio_state.get("family_exposures", {}).get(family, 0.0)
        total_family_notional = abs(current_family_notional) + abs(effective_notional)
        if total_family_notional > self.caps.max_family_exposure:
            available = max(0.0, self.caps.max_family_exposure - abs(current_family_notional))
            if self.caps.reject_on_breach:
                event = CapBreachEvent(
                    timestamp=timestamp,
                    thesis_id=thesis_id,
                    symbol=symbol,
                    cap_type="family",
                    attempted_value=total_family_notional,
                    cap_value=self.caps.max_family_exposure,
                    action="rejected"
                )
                self.breach_history.append(event)
                return 0.0, event
            else:
                effective_notional = available
                event = CapBreachEvent(
                    timestamp=timestamp,
                    thesis_id=thesis_id,
                    symbol=symbol,
                    cap_type="family",
                    attempted_value=total_family_notional,
                    cap_value=self.caps.max_family_exposure,
                    action="clipped"
                )
                self.breach_history.append(event)

        # 4. Max Gross Exposure
        current_gross = portfolio_state.get("gross_exposure", 0.0)
        total_gross = current_gross + abs(effective_notional)
        if total_gross > self.caps.max_gross_exposure:
            available = max(0.0, self.caps.max_gross_exposure - current_gross)
            if self.caps.reject_on_breach:
                event = CapBreachEvent(
                    timestamp=timestamp,
                    thesis_id=thesis_id,
                    symbol=symbol,
                    cap_type="gross",
                    attempted_value=total_gross,
                    cap_value=self.caps.max_gross_exposure,
                    action="rejected"
                )
                self.breach_history.append(event)
                return 0.0, event
            else:
                effective_notional = available
                event = CapBreachEvent(
                    timestamp=timestamp,
                    thesis_id=thesis_id,
                    symbol=symbol,
                    cap_type="gross",
                    attempted_value=total_gross,
                    cap_value=self.caps.max_gross_exposure,
                    action="clipped"
                )
                self.breach_history.append(event)

        return effective_notional, None
