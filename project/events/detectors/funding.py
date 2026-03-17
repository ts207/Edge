from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from project.events.detectors.threshold import ThresholdDetector
from project.events.sparsify import sparsify_mask
from project.events.thresholding import percentile_rank_historical


FUNDING_EVENT_TYPES = (
    "FUNDING_EXTREME_ONSET",
    "FUNDING_PERSISTENCE_TRIGGER",
    "FUNDING_NORMALIZATION_TRIGGER",
)


def _run_length(mask: pd.Series) -> pd.Series:
    out = pd.Series(0, index=mask.index, dtype=int)
    streak = 0
    for flag in mask.fillna(False).astype(bool).tolist():
        streak = streak + 1 if flag else 0
        yield streak


class BaseFundingDetector(ThresholdDetector):
    """Base logic for funding-related detectors."""
    required_columns = ("timestamp", "funding_abs_pct", "funding_abs")
    timeframe_minutes = 5
    default_severity = "moderate"
    severity_major_threshold = 0.95
    default_extreme_pct = 95.0
    default_accel_pct = 90.0
    default_persistence_pct = 85.0
    default_normalization_pct = 50.0
    default_normalization_lookback = 288

    def compute_intensity(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        del df, params
        return features["funding_abs_pct"] / 100.0

    def compute_severity(
        self,
        idx: int,
        intensity: float,
        features: dict[str, pd.Series],
        **params: Any,
    ) -> str:
        del idx, features
        threshold = float(params.get("severity_major_threshold", self.severity_major_threshold))
        return "major" if intensity >= threshold else "moderate"

    def compute_metadata(self, idx: int, features: dict[str, pd.Series], **params: Any) -> dict[str, Any]:
        del params
        f_pct = float(np.nan_to_num(features["funding_abs_pct"].iloc[idx], nan=0.0))
        return {
            "funding_abs_pct": f_pct,
            "funding_abs": float(np.nan_to_num(features["funding_abs"].iloc[idx], nan=0.0)),
            "fr_magnitude": f_pct if f_pct > 1.0 else f_pct * 10000.0,
            "fr_sign": 1.0,
        }


class FundingExtremeOnsetDetector(BaseFundingDetector):
    """Detects the initial onset of extreme funding rates."""
    event_type = "FUNDING_EXTREME_ONSET"

    def prepare_features(self, df: pd.DataFrame, **params: Any) -> dict[str, pd.Series]:
        f_pct = pd.to_numeric(df["funding_abs_pct"], errors="coerce").astype(float)
        f_abs = pd.to_numeric(df["funding_abs"], errors="coerce").astype(float)
        extreme_pct = float(params.get("extreme_pct", self.default_extreme_pct))
        mask = ((f_pct >= extreme_pct) & (f_pct.shift(1) < extreme_pct)).fillna(False)
        return {"funding_abs_pct": f_pct, "funding_abs": f_abs, "mask": mask}

    def compute_raw_mask(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        mask = features["mask"]
        cooldown = int(params.get("cooldown_bars", 0))
        if cooldown > 0:
            from project.events.sparsify import sparsify_mask
            indices = sparsify_mask(mask, min_spacing=cooldown)
            out = pd.Series(False, index=mask.index)
            out.iloc[indices] = True
            return out
        return mask


class FundingPersistenceDetector(BaseFundingDetector):
    """Detects sustained elevated funding or rapid acceleration."""
    event_type = "FUNDING_PERSISTENCE_TRIGGER"

    def prepare_features(self, df: pd.DataFrame, **params: Any) -> dict[str, pd.Series]:
        f_pct = pd.to_numeric(df["funding_abs_pct"], errors="coerce").astype(float)
        f_abs = pd.to_numeric(df["funding_abs"], errors="coerce").astype(float)
        
        accel_pct = float(params.get("accel_pct", self.default_accel_pct))
        accel_lookback = int(params.get("accel_lookback", 12))
        persistence_pct = float(params.get("persistence_pct", self.default_persistence_pct))
        persistence_bars = int(params.get("persistence_bars", 8))
        threshold_window = int(params.get("threshold_window", 2880))

        accel = f_abs - f_abs.shift(accel_lookback)
        accel = accel.where(accel > 0.0)
        accel_rank = percentile_rank_historical(accel, window=threshold_window, min_periods=max(24, accel_lookback))
        accel_raw = ((accel_rank >= accel_pct) & (accel_rank.shift(1) < accel_pct)).fillna(False)

        high = (f_pct >= persistence_pct).fillna(False)
        run_len = pd.Series(list(_run_length(high)), index=high.index)
        persistence_raw = (high & (run_len == persistence_bars)).fillna(False)
        
        return {
            "funding_abs_pct": f_pct, 
            "funding_abs": f_abs, 
            "mask": (accel_raw | persistence_raw).fillna(False)
        }

    def compute_raw_mask(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        return features["mask"]


class FundingNormalizationDetector(BaseFundingDetector):
    """Detects funding returning to baseline after extreme conditions."""
    event_type = "FUNDING_NORMALIZATION_TRIGGER"

    def prepare_features(self, df: pd.DataFrame, **params: Any) -> dict[str, pd.Series]:
        f_pct = pd.to_numeric(df["funding_abs_pct"], errors="coerce").astype(float)
        f_abs = pd.to_numeric(df["funding_abs"], errors="coerce").astype(float)
        
        extreme_pct = float(params.get("extreme_pct", self.default_extreme_pct))
        normalization_pct = float(params.get("normalization_pct", self.default_normalization_pct))
        normalization_lookback = int(
            params.get("normalization_lookback", self.default_normalization_lookback)
        )

        recent_extreme = (
            (f_pct.shift(1) >= extreme_pct)
            .rolling(window=normalization_lookback, min_periods=1)
            .max()
            .fillna(0)
            .astype(bool)
        )
        mask = (
            (f_pct <= normalization_pct)
            & (f_pct.shift(1) > normalization_pct)
            & recent_extreme
        ).fillna(False)
        
        return {"funding_abs_pct": f_pct, "funding_abs": f_abs, "mask": mask}

    def compute_raw_mask(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        return features["mask"]


class FundingDetector(BaseFundingDetector):
    """Legacy polymorphic funding detector for backward compatibility."""

    def prepare_features(self, df: pd.DataFrame, **params: Any) -> dict[str, pd.Series]:
        onset = FundingExtremeOnsetDetector().prepare_features(df, **params)
        persistence = FundingPersistenceDetector().prepare_features(df, **params)
        normalization = FundingNormalizationDetector().prepare_features(df, **params)
        
        return {
            "funding_abs_pct": onset["funding_abs_pct"],
            "funding_abs": onset["funding_abs"],
            "FUNDING_EXTREME_ONSET": onset["mask"],
            "FUNDING_PERSISTENCE_TRIGGER": persistence["mask"],
            "FUNDING_NORMALIZATION_TRIGGER": normalization["mask"],
        }

    def compute_raw_mask(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        return (
            features["FUNDING_EXTREME_ONSET"]
            | features["FUNDING_PERSISTENCE_TRIGGER"]
            | features["FUNDING_NORMALIZATION_TRIGGER"]
        ).fillna(False)

    def compute_event_type(self, idx: int, features: dict[str, pd.Series]) -> str:
        if features["FUNDING_EXTREME_ONSET"].iloc[idx]:
            return "FUNDING_EXTREME_ONSET"
        if features["FUNDING_PERSISTENCE_TRIGGER"].iloc[idx]:
            return "FUNDING_PERSISTENCE_TRIGGER"
        return "FUNDING_NORMALIZATION_TRIGGER"



class FundingFlipDetector(ThresholdDetector):
    event_type = "FUNDING_FLIP"
    required_columns = ("timestamp", "funding_rate_scaled")
    min_magnitude_quantile: float = 0.50

    def prepare_features(self, df: pd.DataFrame, **params: Any) -> dict[str, pd.Series]:
        funding = pd.to_numeric(df["funding_rate_scaled"], errors="coerce").astype(float)
        funding_abs = funding.abs()
        
        # Adaptive thresholds
        window = int(params.get("threshold_window", 2880))
        q_mag = float(params.get("min_magnitude_quantile", self.min_magnitude_quantile))
        
        funding_q_mag = funding_abs.rolling(window, min_periods=288).quantile(q_mag).shift(1)
        
        return {
            "funding": funding, 
            "funding_abs": funding_abs, 
            "funding_q_mag": funding_q_mag
        }

    def compute_raw_mask(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        del df, params
        funding = features["funding"]
        funding_abs = features["funding_abs"]
        funding_q_mag = features["funding_q_mag"]
        
        flip = (np.sign(funding) != np.sign(funding.shift(1))).fillna(False)
        significant = (funding_abs >= funding_q_mag).fillna(False)
        
        return (flip & significant).fillna(False)

    def compute_intensity(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        del df, params
        return features["funding_abs"].fillna(0.0)


__all__ = [
    "FUNDING_EVENT_TYPES",
    "BaseFundingDetector",
    "FundingDetector",
    "FundingExtremeOnsetDetector",
    "FundingFlipDetector",
    "FundingNormalizationDetector",
    "FundingPersistenceDetector",
]
