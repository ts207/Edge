from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from project.events.detectors.threshold import ThresholdDetector
from project.events.detectors.composite import CompositeDetector
from project.features.rolling_thresholds import lagged_rolling_quantile
from project.events.shared import EVENT_COLUMNS, emit_event, format_event_id
from project.events.thresholding import rolling_mean_std_zscore
from project.research.analyzers import run_analyzer_suite


class IndexComponentDivergenceDetector(CompositeDetector):
    event_type = "INDEX_COMPONENT_DIVERGENCE"
    required_columns = ("timestamp", "close")

    def prepare_features(self, df: pd.DataFrame, **params: Any) -> dict[str, pd.Series]:
        close = df["close"]
        ret_abs = close.pct_change(1).abs()
        basis_z = df.get(
            "basis_zscore", df.get("cross_exchange_spread_z", pd.Series(0.0, index=df.index))
        )
        basis_abs = basis_z.abs()
        window = int(params.get("threshold_window", 2880))
        min_periods = max(window // 10, 1)
        basis_q93 = lagged_rolling_quantile(
            basis_abs, window=window, quantile=float(params.get("basis_quantile", 0.93)), min_periods=min_periods
        )
        ret_q75 = lagged_rolling_quantile(
            ret_abs, window=window, quantile=float(params.get("ret_quantile", 0.75)), min_periods=min_periods
        )
        return {
            "basis_abs": basis_abs,
            "ret_abs": ret_abs,
            "basis_q93": basis_q93,
            "ret_q75": ret_q75,
        }

    def compute_raw_mask(
        self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any
    ) -> pd.Series:
        return (
            (features["basis_abs"] >= features["basis_q93"]).fillna(False)
            & (features["ret_abs"] >= features["ret_q75"]).fillna(False)
        ).fillna(False)

    def compute_intensity(
        self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any
    ) -> pd.Series:
        return features["basis_abs"]


class LeadLagBreakDetector(ThresholdDetector):
    event_type = "LEAD_LAG_BREAK"
    required_columns = ("timestamp",)

    def prepare_features(self, df: pd.DataFrame, **params: Any) -> dict[str, pd.Series]:
        basis_z = df.get(
            "basis_zscore", df.get("cross_exchange_spread_z", pd.Series(0.0, index=df.index))
        )
        basis_diff_abs = basis_z.diff().abs()
        window = int(params.get("threshold_window", 2880))
        min_periods = max(window // 10, 1)
        basis_diff_q99 = lagged_rolling_quantile(
            basis_diff_abs, window=window, quantile=float(params.get("basis_diff_quantile", 0.99)), min_periods=min_periods
        )
        return {"basis_diff_abs": basis_diff_abs, "basis_diff_q99": basis_diff_q99}

    def compute_raw_mask(
        self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any
    ) -> pd.Series:
        return (features["basis_diff_abs"] >= features["basis_diff_q99"]).fillna(False)

    def compute_intensity(
        self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any
    ) -> pd.Series:
        return features["basis_diff_abs"]


class CrossAssetDesyncDetector(ThresholdDetector):
    """Detects price desynchronization between correlated asset pairs.
    
    Triggered when the spread between two historically correlated assets
    (e.g., BTC and ETH, or SOL and ETH) deviates significantly from its 
    rolling mean, suggesting a lead-lag opportunity or relative value dislocation.
    """
    event_type = "CROSS_ASSET_DESYNC_EVENT"
    required_columns = ("timestamp", "close")

    def prepare_features(self, df: pd.DataFrame, **params: Any) -> dict[str, pd.Series]:
        close = pd.to_numeric(df["close"], errors="coerce").astype(float)
        paired_close = pd.to_numeric(
            df.get("pair_close", df.get("close_pair", pd.Series(np.nan, index=df.index))),
            errors="coerce"
        ).astype(float)
        
        # Fallback if paired close is missing — use return z-score of main asset
        if paired_close.isna().all():
             ret = np.log(close / close.shift(1)).fillna(0.0)
             window = int(params.get("lookback_window", 2880))
             z = (ret - ret.rolling(window).mean()) / ret.rolling(window).std().replace(0.0, np.nan)
             return {"desync_z": z.abs().fillna(0.0), "threshold": pd.Series(float(params.get("threshold_z", 3.0)), index=df.index)}
             
        # Calculate log returns and basis (spread)
        ret = np.log(close / close.shift(1)).fillna(0.0)
        paired_ret = np.log(paired_close / paired_close.shift(1)).fillna(0.0)
        basis = ret - paired_ret
        
        window = int(params.get("lookback_window", 2880))
        min_periods = max(window // 10, 1)
        
        basis_mean = basis.rolling(window, min_periods=min_periods).mean()
        basis_std = basis.rolling(window, min_periods=min_periods).std().replace(0.0, np.nan)
        desync_z = (basis - basis_mean) / basis_std
        
        threshold = float(params.get("threshold_z", 3.0))
        return {
            "desync_z": desync_z.abs().fillna(0.0),
            "threshold": pd.Series(threshold, index=df.index),
            "basis": basis
        }

    def compute_raw_mask(
        self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any
    ) -> pd.Series:
        return (features["desync_z"] >= features["threshold"]).fillna(False)

    def compute_intensity(
        self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any
    ) -> pd.Series:
        return features["desync_z"]

    def compute_direction(self, idx: int, features: dict[str, pd.Series], **params: Any) -> str:
        basis = float(features["basis"].iloc[idx]) if "basis" in features else 0.0
        return "down" if basis > 0 else "up" if basis < 0 else "non_directional"


from project.events.detectors.registry import register_detector

_DETECTORS = {
    "INDEX_COMPONENT_DIVERGENCE": IndexComponentDivergenceDetector,
    "LEAD_LAG_BREAK": LeadLagBreakDetector,
    "CROSS_ASSET_DESYNC_EVENT": CrossAssetDesyncDetector,
}

for et, cls in _DETECTORS.items():
    register_detector(et, cls)


def detect_desync_family(
    df: pd.DataFrame, symbol: str, event_type: str = "INDEX_COMPONENT_DIVERGENCE", **params: Any
) -> pd.DataFrame:
    detector_cls = _DETECTORS.get(event_type)
    if detector_cls is None:
        # Fallback to BasisDislocationDetector if it's BASIS related
        from project.events.families.basis import BasisDislocationDetector

        if event_type in {"BASIS_DISLOC", "SPOT_PERP_BASIS_SHOCK"}:
            # Map columns for BasisDislocationDetector
            work = df.copy()
            if "close" in work.columns and "close_perp" not in work.columns:
                work["close_perp"] = work["close"]
            if "spot_close" in work.columns and "close_spot" not in work.columns:
                work["close_spot"] = work["spot_close"]
            if "close_spot" not in work.columns:
                # Last resort fallback
                work["close_spot"] = work[
                    "close"
                ]  # Should not happen if canonical feature building is correct
            return BasisDislocationDetector().detect(work, symbol=symbol, **params)
        raise ValueError(f"Unknown desync event type: {event_type}")
    return detector_cls().detect(df, symbol=symbol, **params)


def analyze_desync_family(
    df: pd.DataFrame, symbol: str, event_type: str = "INDEX_COMPONENT_DIVERGENCE", **params: Any
) -> tuple[pd.DataFrame, dict[str, Any]]:
    events = detect_desync_family(df, symbol, event_type=event_type, **params)
    market = df[["timestamp", "close"]].copy() if not df.empty and "close" in df.columns else None
    analyzer_results = run_analyzer_suite(events, market=market) if not events.empty else {}
    return events, analyzer_results
