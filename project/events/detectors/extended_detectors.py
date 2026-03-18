from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from project.events.detectors.exhaustion import PostDeleveragingReboundDetector
from project.events.detectors.funding import BaseFundingDetector
from project.events.detectors.liquidity import DirectLiquidityStressDetector
from project.events.detectors.registry import register_detector
from project.events.detectors.sequence import EventSequenceDetector
from project.events.detectors.volatility import BreakoutTriggerDetector
from project.events.families.basis import BasisDislocationDetector, CrossVenueDesyncDetector
from project.events.families.oi import BaseOIShockDetector


def _recent_true(mask: pd.Series, window: int) -> pd.Series:
    return (
        mask.fillna(False)
        .astype(bool)
        .rolling(window=max(int(window), 1), min_periods=1)
        .max()
        .shift(1)
        .fillna(0)
        .astype(bool)
    )


class BasisSnapbackDetector(BasisDislocationDetector):
    event_type = "BASIS_SNAPBACK"

    def prepare_features(self, df: pd.DataFrame, **params: Any) -> dict[str, pd.Series]:
        features = super().prepare_features(df, **params)
        abs_z = pd.to_numeric(features["basis_zscore"], errors="coerce").abs()
        dynamic_th = pd.to_numeric(features["dynamic_th"], errors="coerce")
        snapback_window = int(params.get("snapback_window", 24))
        snapback_z_th = float(params.get("snapback_z_th", 0.75))
        recent_extreme = _recent_true(abs_z >= dynamic_th, snapback_window)
        features.update(
            {
                "basis_abs_z": abs_z,
                "recent_extreme": recent_extreme,
                "snapback_mask": (
                    recent_extreme
                    & (abs_z <= snapback_z_th).fillna(False)
                    & (abs_z.shift(1) > snapback_z_th).fillna(False)
                ).fillna(False),
            }
        )
        return features

    def compute_raw_mask(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        del df, params
        return features["snapback_mask"]


class CrossVenueCatchupDetector(CrossVenueDesyncDetector):
    event_type = "CROSS_VENUE_CATCHUP"

    def prepare_features(self, df: pd.DataFrame, **params: Any) -> dict[str, pd.Series]:
        features = super().prepare_features(df, **params)
        abs_z = pd.to_numeric(features["basis_zscore"], errors="coerce").abs()
        dynamic_th = pd.to_numeric(features["dynamic_th"], errors="coerce")
        catchup_window = int(params.get("catchup_window", 12))
        catchup_abs_z_th = float(params.get("catchup_abs_z_th", 1.0))
        recent_dislocation = _recent_true(abs_z >= dynamic_th, catchup_window)
        features.update(
            {
                "basis_abs_z": abs_z,
                "catchup_mask": (
                    recent_dislocation
                    & (abs_z <= catchup_abs_z_th).fillna(False)
                    & (abs_z.shift(1) > catchup_abs_z_th).fillna(False)
                ).fillna(False),
            }
        )
        return features

    def compute_raw_mask(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        del df, params
        return features["catchup_mask"]


class FundingExtremeBreakoutDetector(BaseFundingDetector):
    event_type = "FUNDING_EXTREME_BREAKOUT"
    required_columns = ("timestamp", "funding_abs_pct", "funding_abs", "close")

    def prepare_features(self, df: pd.DataFrame, **params: Any) -> dict[str, pd.Series]:
        funding_abs_pct = pd.to_numeric(df["funding_abs_pct"], errors="coerce").astype(float)
        funding_abs = pd.to_numeric(df["funding_abs"], errors="coerce").astype(float)
        funding_signed = self._signed_funding(df)
        close = pd.to_numeric(df["close"], errors="coerce").astype(float)
        breakout_window = int(params.get("breakout_window", 96))
        breakout_ret_abs_th = float(params.get("breakout_ret_abs_th", 0.01))
        threshold_bps = float(params.get("threshold_bps", 2.0))
        ret_abs = close.pct_change(breakout_window).abs()
        extreme = (funding_abs * 10000.0 >= threshold_bps).fillna(False)
        mask = (
            extreme
            & (ret_abs >= breakout_ret_abs_th).fillna(False)
            & (ret_abs.shift(1) < breakout_ret_abs_th).fillna(False)
        ).fillna(False)
        return {
            "funding_abs_pct": funding_abs_pct,
            "funding_abs": funding_abs,
            "funding_signed": funding_signed,
            "ret_abs": ret_abs,
            "mask": mask,
        }

    def compute_raw_mask(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        del df, params
        return features["mask"]

    def compute_intensity(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        del df, params
        return (features["funding_abs_pct"] / 100.0).fillna(0.0) + features["ret_abs"].fillna(0.0)


class FundingExtremeStagnationDetector(BaseFundingDetector):
    event_type = "FUNDING_EXTREME_STAGNATION"
    required_columns = ("timestamp", "funding_abs_pct", "funding_abs", "close")

    def prepare_features(self, df: pd.DataFrame, **params: Any) -> dict[str, pd.Series]:
        funding_abs_pct = pd.to_numeric(df["funding_abs_pct"], errors="coerce").astype(float)
        funding_abs = pd.to_numeric(df["funding_abs"], errors="coerce").astype(float)
        funding_signed = self._signed_funding(df)
        close = pd.to_numeric(df["close"], errors="coerce").astype(float)
        stagnation_window = int(params.get("stagnation_window", 96))
        stagnation_ret_abs_th = float(params.get("stagnation_ret_abs_th", 0.005))
        threshold_bps = float(params.get("threshold_bps", 2.0))
        ret_abs = close.pct_change(stagnation_window).abs()
        extreme = (funding_abs * 10000.0 >= threshold_bps).fillna(False)
        mask = (
            extreme
            & (ret_abs <= stagnation_ret_abs_th).fillna(False)
            & (ret_abs.shift(1) > stagnation_ret_abs_th).fillna(False)
        ).fillna(False)
        return {
            "funding_abs_pct": funding_abs_pct,
            "funding_abs": funding_abs,
            "funding_signed": funding_signed,
            "ret_abs": ret_abs,
            "mask": mask,
        }

    def compute_raw_mask(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        del df, params
        return features["mask"]

    def compute_intensity(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        del df, params
        return (features["funding_abs_pct"] / 100.0).fillna(0.0)


class LiquidationExhaustionReversalDetector(PostDeleveragingReboundDetector):
    event_type = "LIQUIDATION_EXHAUSTION_REVERSAL"


class DepthRecoveryEventDetector(DirectLiquidityStressDetector):
    event_type = "DEPTH_RECOVERY_EVENT"

    def prepare_features(self, df: pd.DataFrame, **params: Any) -> dict[str, pd.Series]:
        features = super().prepare_features(df, **params)
        spread = pd.to_numeric(features["spread"], errors="coerce").astype(float)
        depth = pd.to_numeric(features["depth"], errors="coerce").astype(float)
        depth_median = pd.to_numeric(features["depth_median"], errors="coerce").astype(float)
        lookback_window = int(params.get("lookback_window", 288))
        recovery_lookback = int(params.get("recovery_lookback", 24))
        prior_spread_q = float(params.get("prior_spread_q", 0.9))
        recovery_spread_q = float(params.get("recovery_spread_q", 0.8))
        prior_spread_hi = spread.shift(1).rolling(lookback_window, min_periods=max(8, lookback_window // 12)).quantile(prior_spread_q)
        recovery_spread = spread.shift(1).rolling(recovery_lookback, min_periods=1).quantile(recovery_spread_q)
        recent_stress = _recent_true((spread >= prior_spread_hi).fillna(False), recovery_lookback)
        volume = pd.to_numeric(
            df.get("quote_volume", df.get("volume", pd.Series(0.0, index=df.index))),
            errors="coerce",
        ).fillna(0.0)
        min_volume = volume.shift(1).rolling(lookback_window, min_periods=max(8, lookback_window // 12)).quantile(
            float(params.get("min_volume_quantile", 0.2))
        )
        features.update(
            {
                "recovery_mask": (
                    recent_stress
                    & (spread <= recovery_spread).fillna(False)
                    & (depth >= depth_median).fillna(False)
                    & (volume >= min_volume.fillna(0.0)).fillna(False)
                ).fillna(False),
                "spread": spread,
                "recovery_spread": recovery_spread,
            }
        )
        return features

    def compute_raw_mask(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        del df, params
        return features["recovery_mask"]

    def compute_intensity(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        del df, params
        recovery = (features["recovery_spread"] / features["spread"].replace(0.0, np.nan)).fillna(0.0)
        return recovery.clip(lower=0.0)


class ImbalanceAbsorptionReversalDetector(DirectLiquidityStressDetector):
    event_type = "IMBALANCE_ABSORPTION_REVERSAL"

    def prepare_features(self, df: pd.DataFrame, **params: Any) -> dict[str, pd.Series]:
        features = super().prepare_features(df, **params)
        close = pd.to_numeric(df["close"], errors="coerce").astype(float)
        imbalance = pd.to_numeric(
            df.get("ms_imbalance_24", pd.Series(0.0, index=df.index)),
            errors="coerce",
        ).fillna(0.0)
        ret = close.pct_change(int(params.get("reversal_lookahead", 3))).fillna(0.0)
        lookback_window = int(params.get("lookback_window", 288))
        imbalance_q = imbalance.abs().shift(1).rolling(
            lookback_window,
            min_periods=max(8, lookback_window // 12),
        ).quantile(float(params.get("min_volume_quantile", 0.2)))
        ret_q = ret.abs().shift(1).rolling(
            lookback_window,
            min_periods=max(8, lookback_window // 12),
        ).quantile(float(params.get("ret_q", 0.9)))
        spread = pd.to_numeric(features["spread"], errors="coerce").astype(float)
        spread_median = pd.to_numeric(features["spread_median"], errors="coerce").astype(float)
        reversal = np.sign(ret) == -np.sign(imbalance.replace(0.0, np.nan))
        features.update(
            {
                "reversal_mask": (
                    (imbalance.abs() >= imbalance_q.fillna(0.0)).fillna(False)
                    & reversal.fillna(False)
                    & (ret.abs() >= ret_q.fillna(0.0)).fillna(False)
                    & (spread <= spread_median).fillna(False)
                ).fillna(False),
                "imbalance_abs": imbalance.abs(),
                "ret_abs": ret.abs(),
            }
        )
        return features

    def compute_raw_mask(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        del df, params
        return features["reversal_mask"]

    def compute_intensity(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        del df, params
        return features["imbalance_abs"].fillna(0.0) + (features["ret_abs"].fillna(0.0) * 10000.0)


class OIVolDivergenceDetector(BaseOIShockDetector):
    event_type = "OI_VOL_DIVERGENCE"
    required_columns = ("timestamp", "oi_notional", "close", "rv_96")

    def prepare_features(self, df: pd.DataFrame, **params: Any) -> dict[str, pd.Series]:
        window = int(params.get("oi_window", 96))
        min_periods = int(params.get("min_periods", max(24, window // 4)))
        oi = pd.to_numeric(df["oi_notional"], errors="coerce").replace(0.0, np.nan).astype(float)
        oi_log_delta = np.log(oi).diff()
        baseline = oi_log_delta.shift(1)
        mean = baseline.rolling(window=window, min_periods=min_periods).mean()
        std = baseline.rolling(window=window, min_periods=min_periods).std()
        oi_z = (oi_log_delta - mean) / std.where(std > 0.0, 1e-12)
        close_ret = pd.to_numeric(df["close"], errors="coerce").astype(float).pct_change(1)
        rv = pd.to_numeric(df["rv_96"], errors="coerce").astype(float).ffill()
        vol_q = rv.shift(1).rolling(
            int(params.get("vol_window", 96)),
            min_periods=max(24, int(params.get("vol_window", 96)) // 4),
        ).quantile(float(params.get("vol_low_quantile", 0.3)))
        oi_z_th = float(params.get("oi_z_th", 2.0))
        mask = ((oi_z.abs() >= oi_z_th).fillna(False) & (rv <= vol_q).fillna(False)).fillna(False)
        return {
            "oi_z": oi_z,
            "close_ret": close_ret,
            "oi_pct_change": oi.pct_change(1),
            "mask": mask,
        }

    def compute_raw_mask(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        del df, params
        return features["mask"]

    def compute_intensity(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        del df, params
        return features["oi_z"].abs()


class OIVolCompressionBuildupDetector(BaseOIShockDetector):
    event_type = "OI_VOL_COMPRESSION_BUILDUP"
    required_columns = ("timestamp", "oi_notional", "close", "range_96", "range_med_2880")

    def prepare_features(self, df: pd.DataFrame, **params: Any) -> dict[str, pd.Series]:
        window = int(params.get("oi_window", 96))
        min_periods = int(params.get("min_periods", max(24, window // 4)))
        oi = pd.to_numeric(df["oi_notional"], errors="coerce").replace(0.0, np.nan).astype(float)
        oi_log_delta = np.log(oi).diff()
        baseline = oi_log_delta.shift(1)
        mean = baseline.rolling(window=window, min_periods=min_periods).mean()
        std = baseline.rolling(window=window, min_periods=min_periods).std()
        oi_z = (oi_log_delta - mean) / std.where(std > 0.0, 1e-12)
        close_ret = pd.to_numeric(df["close"], errors="coerce").astype(float).pct_change(1)
        range_96 = pd.to_numeric(df["range_96"], errors="coerce").astype(float)
        range_med = pd.to_numeric(df["range_med_2880"], errors="coerce").replace(0.0, np.nan).astype(float)
        comp_ratio = (range_96 / range_med).astype(float)
        comp_q = comp_ratio.shift(1).rolling(
            int(params.get("vol_window", 288)),
            min_periods=max(24, int(params.get("vol_window", 288)) // 4),
        ).quantile(float(params.get("vol_low_quantile", 0.2)))
        oi_drift_z_th = float(params.get("oi_drift_z_th", 1.5))
        mask = ((oi_z >= oi_drift_z_th).fillna(False) & (comp_ratio <= comp_q).fillna(False)).fillna(False)
        return {
            "oi_z": oi_z,
            "close_ret": close_ret,
            "oi_pct_change": oi.pct_change(1),
            "comp_ratio": comp_ratio,
            "mask": mask,
        }

    def compute_raw_mask(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        del df, params
        return features["mask"]

    def compute_intensity(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        del df, params
        return features["oi_z"].fillna(0.0) * (1.0 / features["comp_ratio"].clip(lower=0.1))


class VolCompressionBreakoutDetector(BreakoutTriggerDetector):
    event_type = "VOL_COMPRESSION_BREAKOUT"

    def compute_raw_mask(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        adjusted = dict(params)
        adjusted.setdefault("compression_ratio_max", float(params.get("comp_ratio_th", 0.75)))
        return super().compute_raw_mask(df, features=features, **adjusted)


class SeqFundingExtremeThenBreakoutDetector(EventSequenceDetector):
    def __init__(self) -> None:
        super().__init__(
            sequence_name="SEQ_FND_EXTREME_THEN_BREAKOUT",
            events=["FUNDING_EXTREME_ONSET", "BREAKOUT_TRIGGER"],
            max_gaps=["480min"],
        )


class SeqLiqCascadeThenExhaustDetector(EventSequenceDetector):
    def __init__(self) -> None:
        super().__init__(
            sequence_name="SEQ_LIQ_CASCADE_THEN_EXHAUST",
            events=["LIQUIDATION_CASCADE", "LIQUIDATION_EXHAUSTION_REVERSAL"],
            max_gaps=["120min"],
        )


class SeqLiqVacuumThenDepthRecoveryDetector(EventSequenceDetector):
    def __init__(self) -> None:
        super().__init__(
            sequence_name="SEQ_LIQ_VACUUM_THEN_DEPTH_RECOVERY",
            events=["LIQUIDITY_VACUUM", "DEPTH_RECOVERY_EVENT"],
            max_gaps=["240min"],
        )


class SeqOiSpikePositiveThenVolSpikeDetector(EventSequenceDetector):
    def __init__(self) -> None:
        super().__init__(
            sequence_name="SEQ_OI_SPIKEPOS_THEN_VOL_SPIKE",
            events=["OI_SPIKE_POSITIVE", "VOL_SPIKE"],
            max_gaps=["240min"],
        )


class SeqVolCompressionThenBreakoutDetector(EventSequenceDetector):
    def __init__(self) -> None:
        super().__init__(
            sequence_name="SEQ_VOL_COMP_THEN_BREAKOUT",
            events=["RANGE_COMPRESSION_END", "BREAKOUT_TRIGGER"],
            max_gaps=["240min"],
        )


_LEGACY_ALIAS_DETECTORS = {
    "BASIS_SNAPBACK": BasisSnapbackDetector,
    "CROSS_VENUE_CATCHUP": CrossVenueCatchupDetector,
    "FUNDING_EXTREME_BREAKOUT": FundingExtremeBreakoutDetector,
    "FUNDING_EXTREME_STAGNATION": FundingExtremeStagnationDetector,
    "LIQUIDATION_EXHAUSTION_REVERSAL": LiquidationExhaustionReversalDetector,
    "DEPTH_RECOVERY_EVENT": DepthRecoveryEventDetector,
    "IMBALANCE_ABSORPTION_REVERSAL": ImbalanceAbsorptionReversalDetector,
    "OI_VOL_DIVERGENCE": OIVolDivergenceDetector,
    "OI_VOL_COMPRESSION_BUILDUP": OIVolCompressionBuildupDetector,
    "VOL_COMPRESSION_BREAKOUT": VolCompressionBreakoutDetector,
    "SEQ_FND_EXTREME_THEN_BREAKOUT": SeqFundingExtremeThenBreakoutDetector,
    "SEQ_LIQ_CASCADE_THEN_EXHAUST": SeqLiqCascadeThenExhaustDetector,
    "SEQ_LIQ_VACUUM_THEN_DEPTH_RECOVERY": SeqLiqVacuumThenDepthRecoveryDetector,
    "SEQ_OI_SPIKEPOS_THEN_VOL_SPIKE": SeqOiSpikePositiveThenVolSpikeDetector,
    "SEQ_VOL_COMP_THEN_BREAKOUT": SeqVolCompressionThenBreakoutDetector,
}


for event_type, detector_cls in _LEGACY_ALIAS_DETECTORS.items():
    register_detector(event_type, detector_cls)
