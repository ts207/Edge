from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

_LOG = logging.getLogger(__name__)


@dataclass(frozen=True)
class DecayRule:
    rule_id: str
    metric: str  # edge, hit_rate, payoff, slippage
    threshold: float
    window_samples: int
    action: str  # warn, downsize, disable
    downsize_factor: float = 0.5


@dataclass
class ThesisHealthSnapshot:
    thesis_id: str
    timestamp: str
    health_state: str  # healthy, watch, degraded, disabled
    realized_edge_bps: float
    expected_edge_bps: float
    hit_rate: float
    sample_count: int
    actions_taken: List[str] = field(default_factory=list)
    reason_codes: List[str] = field(default_factory=list)


class DecayMonitor:
    def __init__(self, rules: List[DecayRule]):
        self.rules = rules
        self.health_history: List[ThesisHealthSnapshot] = []

    def assess_thesis_health(
        self,
        thesis_id: str,
        realized_metrics: Dict[str, Any],
        expected_metrics: Dict[str, Any],
    ) -> ThesisHealthSnapshot:
        """
        Assess health of a single thesis based on realized vs expected performance.
        """
        realized_edge = float(realized_metrics.get("avg_realized_net_edge_bps", 0.0))
        expected_edge = float(expected_metrics.get("net_expectancy_bps", 0.0))
        realized_hit_rate = float(realized_metrics.get("hit_rate", 0.0))
        sample_count = int(realized_metrics.get("sample_count", 0))
        
        health_state = "healthy"
        actions = []
        reasons = []
        
        for rule in self.rules:
            if sample_count < rule.window_samples:
                continue
                
            triggered = False
            if rule.metric == "edge":
                if realized_edge < rule.threshold * expected_edge:
                    triggered = True
            elif rule.metric == "hit_rate":
                if realized_hit_rate < rule.threshold:
                    triggered = True
            
            if triggered:
                reasons.append(f"decay_{rule.metric}")
                if rule.action == "disable":
                    health_state = "disabled"
                    actions.append("disable")
                elif rule.action == "downsize" and health_state != "disabled":
                    health_state = "degraded"
                    actions.append(f"downsize_{rule.downsize_factor}")
                elif rule.action == "warn" and health_state not in ("disabled", "degraded"):
                    health_state = "watch"
                    actions.append("warn")

        snapshot = ThesisHealthSnapshot(
            thesis_id=thesis_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            health_state=health_state,
            realized_edge_bps=realized_edge,
            expected_edge_bps=expected_edge,
            hit_rate=realized_hit_rate,
            sample_count=sample_count,
            actions_taken=actions,
            reason_codes=reasons
        )
        self.health_history.append(snapshot)
        return snapshot
