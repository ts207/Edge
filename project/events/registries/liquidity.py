from __future__ import annotations

from project.events.detectors.liquidity import (
    LIQUIDITY_FAMILY_DETECTORS,
    DirectLiquidityStressDetector,
    LiquidityGapDetector,
    LiquidityStressDetector,
    LiquidityVacuumDetector,
    ProxyLiquidityStressDetector,
    SpreadBlowoutDetector,
)
from project.events.detectors.registry import register_detector


# Preserve existing registry behavior: only this subset was registered at import time.
LIQUIDITY_REGISTERED_DETECTORS = {
    "LIQUIDITY_SHOCK": LiquidityStressDetector,
    "LIQUIDITY_STRESS_DIRECT": DirectLiquidityStressDetector,
    "LIQUIDITY_STRESS_PROXY": ProxyLiquidityStressDetector,
    "LIQUIDITY_VACUUM": LiquidityVacuumDetector,
    "LIQUIDITY_GAP_PRINT": LiquidityGapDetector,
    "SPREAD_BLOWOUT": SpreadBlowoutDetector,
}


def ensure_liquidity_detectors_registered() -> None:
    for event_type, detector_cls in LIQUIDITY_REGISTERED_DETECTORS.items():
        register_detector(event_type, detector_cls)


__all__ = [
    "LIQUIDITY_FAMILY_DETECTORS",
    "LIQUIDITY_REGISTERED_DETECTORS",
    "ensure_liquidity_detectors_registered",
]
