from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from project.events.detectors.threshold import ThresholdDetector
from project.events.detectors.composite import CompositeDetector
from project.events.shared import EVENT_COLUMNS, emit_event, format_event_id
from project.research.analyzers import run_analyzer_suite
from project.events.detectors.registry import register_detector


class CrossAssetInteractionDetector(CompositeDetector):
    """Detects predictive interactions across different assets.
    
    Concretely: Does an OI spike on ETH predict a volatility transition on BTC?
    Does a liquidity vacuum on SOL create a spread opportunity against ETH?
    """
    event_type = "CROSS_ASSET_INTERACTION"
    required_columns = ("timestamp",)

    def prepare_features(self, df: pd.DataFrame, **params: Any) -> dict[str, pd.Series]:
        # Expects multi-asset features to be merged into the dataframe
        # e.g., 'oi_spike_eth', 'vol_btc', 'liq_vacuum_sol', etc.
        features = {}
        for key in df.columns:
            if any(p in key for p in ["oi_spike", "vol_", "liq_vacuum", "spread_"]):
                features[key] = df[key]
        return features

    def compute_raw_mask(
        self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any
    ) -> pd.Series:
        # Placeholder for complex interaction logic
        # Typically used via explicit hypothesis search over interactions
        return pd.Series(False, index=df.index)

    def compute_intensity(
        self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any
    ) -> pd.Series:
        return pd.Series(0.0, index=df.index)


_DETECTORS = {
    "CROSS_ASSET_INTERACTION": CrossAssetInteractionDetector,
}

for et, cls in _DETECTORS.items():
    register_detector(et, cls)


def detect_interaction_family(
    df: pd.DataFrame, symbol: str, event_type: str = "CROSS_ASSET_INTERACTION", **params: Any
) -> pd.DataFrame:
    from project.events.detectors.registry import get_detector
    detector = get_detector(event_type)
    if detector is None:
        raise ValueError(f"Unknown interaction event type: {event_type}")
    return detector.detect(df, symbol=symbol, **params)
