from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from project.domain.compiled_registry import get_domain_registry

from project.events.detectors.threshold import ThresholdDetector
from project.events.detectors.composite import CompositeDetector
from project.events.shared import EVENT_COLUMNS, emit_event, format_event_id
from project.events.sparsify import sparsify_mask
from project.events.thresholding import rolling_mean_std_zscore
from project.research.analyzers import run_analyzer_suite


def _band_params() -> tuple[int, int, float]:
    try:
        payload = get_domain_registry().event_row("BAND_BREAK")
    except Exception:
        payload = {}
    params = payload.get("parameters", {}) if isinstance(payload, dict) else {}
    lookback = int(params.get("lookback_window", 96))
    min_periods = int(params.get("min_periods", max(24, lookback // 4)))
    mult = float(params.get("band_std_mult", params.get("band_z_threshold", 2.0)))
    return lookback, min_periods, mult


class StatisticalBase(ThresholdDetector):
    required_columns = ("timestamp", "close", "rv_96")
    timeframe_minutes = 5
    default_severity = "moderate"

    def compute_severity(
        self, idx: int, intensity: float, features: dict[str, pd.Series], **params: Any
    ) -> str:
        del idx, features, params
        if intensity >= 4.0:
            return "extreme"
        if intensity >= 2.5:
            return "major"
        return "moderate"

    def compute_metadata(
        self, idx: int, features: dict[str, pd.Series], **params: Any
    ) -> dict[str, Any]:
        del params
        return {
            "family": "statistical_dislocation",
            **{
                k: float(v.iloc[idx]) if hasattr(v, "iloc") else v
                for k, v in features.items()
                if k not in ["mask", "intensity", "close"]
            },
        }


class ZScoreStretchDetector(StatisticalBase):
    event_type = "ZSCORE_STRETCH"

    def prepare_features(self, df: pd.DataFrame, **params: Any) -> dict[str, pd.Series]:
        close = df["close"]
        px_z = rolling_mean_std_zscore(close.pct_change(12).fillna(0.0), window=288)
        px_abs = px_z.abs()
        px_q96 = px_abs.rolling(2880, min_periods=288).quantile(0.96).shift(1)
        return {"px_abs": px_abs, "px_q96": px_q96}

    def compute_raw_mask(
        self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any
    ) -> pd.Series:
        px_abs = features["px_abs"]
        px_q96 = features["px_q96"]
        threshold = px_q96.where(px_q96 >= 2.0, 2.0)
        return (px_abs >= threshold).fillna(False)

    def compute_intensity(
        self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any
    ) -> pd.Series:
        return features["px_abs"]


class BandBreakDetector(StatisticalBase):
    event_type = "BAND_BREAK"

    def prepare_features(self, df: pd.DataFrame, **params: Any) -> dict[str, pd.Series]:
        close = df["close"]
        lookback, min_periods, mult = _band_params()
        ma = close.rolling(lookback, min_periods=min_periods).mean()
        sd = close.rolling(lookback, min_periods=min_periods).std().replace(0.0, np.nan)
        return {"close": close, "ma": ma, "sd": sd, "mult": pd.Series(mult, index=df.index)}

    def compute_raw_mask(
        self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any
    ) -> pd.Series:
        close = features["close"]
        ma = features["ma"]
        sd = features["sd"]
        mult = features["mult"]
        return ((close > (ma + mult * sd)) | (close < (ma - mult * sd))).fillna(False)

    def compute_intensity(
        self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any
    ) -> pd.Series:
        ma = features["ma"]
        sd = features["sd"]
        return (df["close"] - ma).abs() / sd.fillna(1.0)


class OvershootDetector(StatisticalBase):
    event_type = "OVERSHOOT_AFTER_SHOCK"

    def prepare_features(self, df: pd.DataFrame, **params: Any) -> dict[str, pd.Series]:
        close = df["close"]
        rv_96 = df["rv_96"].ffill()
        rv_z = rolling_mean_std_zscore(rv_96, window=288)
        px_z = rolling_mean_std_zscore(close.pct_change(12).fillna(0.0), window=288)
        px_abs = px_z.abs()
        px_q95 = px_abs.rolling(2880, min_periods=288).quantile(0.95).shift(1)
        rv_q95 = rv_z.rolling(2880, min_periods=288).quantile(0.95).shift(1)
        return {"rv_z": rv_z, "px_abs": px_abs, "px_q95": px_q95, "rv_q95": rv_q95}

    def compute_raw_mask(
        self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any
    ) -> pd.Series:
        rv_z = features["rv_z"]
        px_abs = features["px_abs"]
        px_q95 = features["px_q95"]
        rv_q95 = features["rv_q95"]
        return ((rv_z.shift(1) >= rv_q95).fillna(False) & (px_abs >= px_q95).fillna(False)).fillna(
            False
        )

    def compute_intensity(
        self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any
    ) -> pd.Series:
        return features["px_abs"] + features["rv_z"].abs()


class GapOvershootDetector(StatisticalBase):
    event_type = "GAP_OVERSHOOT"

    def prepare_features(self, df: pd.DataFrame, **params: Any) -> dict[str, pd.Series]:
        ret_abs = df["close"].pct_change(1).abs()
        ret_q995 = ret_abs.rolling(2880, min_periods=288).quantile(0.995).shift(1)
        return {"ret_abs": ret_abs, "ret_q995": ret_q995}

    def compute_raw_mask(
        self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any
    ) -> pd.Series:
        return (features["ret_abs"] >= features["ret_q995"]).fillna(False)

    def compute_intensity(
        self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any
    ) -> pd.Series:
        return features["ret_abs"] * 10000.0  # bps


from project.events.detectors.registry import register_detector

_DETECTORS = {
    "ZSCORE_STRETCH": ZScoreStretchDetector,
    "BAND_BREAK": BandBreakDetector,
    "OVERSHOOT_AFTER_SHOCK": OvershootDetector,
    "GAP_OVERSHOOT": GapOvershootDetector,
}

for et, cls in _DETECTORS.items():
    register_detector(et, cls)


def detect_statistical_family(
    df: pd.DataFrame, symbol: str, event_type: str, **params: Any
) -> pd.DataFrame:
    detector_cls = _DETECTORS.get(event_type)
    if detector_cls is None:
        raise ValueError(f"Unknown statistical event type: {event_type}")
    return detector_cls().detect(df, symbol=symbol, **params)


def analyze_statistical_family(
    df: pd.DataFrame, symbol: str, event_type: str, **params: Any
) -> tuple[pd.DataFrame, dict[str, Any]]:
    events = detect_statistical_family(df, symbol, event_type, **params)
    market = df[["timestamp", "close"]].copy() if not df.empty and "close" in df.columns else None
    results = run_analyzer_suite(events, market=market) if not events.empty else {}
    return events, results
