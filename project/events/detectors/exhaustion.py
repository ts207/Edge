from __future__ import annotations

from typing import Any, Mapping

import numpy as np
import pandas as pd

from project.events.detectors.composite import CompositeDetector
from project.events.detectors.threshold import ThresholdDetector
from project.events.thresholding import rolling_mean_std_zscore


def past_quantile(series: pd.Series, q: float, window: int = 2880) -> pd.Series:
    return series.rolling(window, min_periods=window // 10).quantile(q).shift(1)


def _onset_mask(mask: pd.Series) -> pd.Series:
    typed = mask.astype("boolean")
    return (typed & ~typed.shift(1, fill_value=False)).astype(bool)


class FlowExhaustionDetector(CompositeDetector):
    event_type = "FLOW_EXHAUSTION_PROXY"
    required_columns = ("timestamp", "close", "high", "low", "rv_96", "oi_delta_1h", "liquidation_notional")
    min_spacing = 24
    default_threshold_window = 2880
    default_oi_drop_quantile = 0.80
    default_liquidation_quantile = 0.85
    default_spread_quantile = 0.70
    default_return_quantile = 0.75
    default_rebound_window = 6
    default_reversal_window = 3
    default_reversal_quantile = 0.65
    default_oi_drop_abs_min = 5.0
    default_liquidation_abs_min = 25.0
    default_liquidation_multiplier = 0.9
    default_return_abs_min = 0.0025
    default_spread_abs_min = 5.0
    default_rv_decay_ratio = 0.99

    def prepare_features(self, df: pd.DataFrame, **params: Any) -> dict[str, pd.Series]:
        close = pd.to_numeric(df["close"], errors="coerce").astype(float)
        rv_96 = pd.to_numeric(df["rv_96"], errors="coerce").ffill().astype(float)
        oi_delta = pd.to_numeric(df.get("oi_delta_1h", pd.Series(0.0, index=df.index)), errors="coerce").fillna(0.0)
        liq_notional = pd.to_numeric(df.get("liquidation_notional", pd.Series(0.0, index=df.index)), errors="coerce").fillna(0.0)
        spread_bps = pd.to_numeric(df.get("spread_bps", pd.Series(0.0, index=df.index)), errors="coerce").fillna(0.0)
        ret_1 = close.pct_change(1).fillna(0.0)
        ret_abs = ret_1.abs()

        oi_drop = (-oi_delta).clip(lower=0.0)
        
        window = int(params.get("threshold_window", self.default_threshold_window))
        oi_drop_q80 = past_quantile(oi_drop, float(params.get("oi_drop_quantile", self.default_oi_drop_quantile)), window=window)
        liq_q85 = past_quantile(liq_notional, float(params.get("liquidation_quantile", self.default_liquidation_quantile)), window=window)
        spread_q70 = past_quantile(spread_bps, float(params.get("spread_quantile", self.default_spread_quantile)), window=window)
        ret_q75 = past_quantile(ret_abs, float(params.get("return_quantile", self.default_return_quantile)), window=window)
        
        rebound_ret = close.pct_change(int(params.get("rebound_window", self.default_rebound_window))).fillna(0.0)
        reversal_impulse = close.pct_change(int(params.get("reversal_window", self.default_reversal_window))).abs()
        reversal_q65 = past_quantile(reversal_impulse, float(params.get("reversal_quantile", self.default_reversal_quantile)), window=window)

        oi_drop_abs_min = float(params.get("oi_drop_abs_min", self.default_oi_drop_abs_min))
        liquidation_abs_min = float(params.get("liquidation_abs_min", self.default_liquidation_abs_min))
        liquidation_multiplier = float(params.get("liquidation_multiplier", self.default_liquidation_multiplier))
        return_abs_min = float(params.get("return_abs_min", self.default_return_abs_min))
        spread_abs_min = float(params.get("spread_abs_min", self.default_spread_abs_min))

        forced_flow = (
            (
                (oi_drop >= np.maximum(oi_drop_q80.fillna(0.0), oi_drop_abs_min)).fillna(False)
                & (
                    liq_notional
                    >= np.maximum(liq_q85.fillna(0.0), liquidation_abs_min)
                ).fillna(False)
            )
            | (
                (
                    liq_notional
                    >= np.maximum(
                        liq_q85.fillna(0.0) * liquidation_multiplier,
                        liquidation_abs_min,
                    )
                ).fillna(False)
                & (ret_abs >= np.maximum(ret_q75.fillna(0.0), return_abs_min)).fillna(False)
                & (
                    spread_bps
                    >= np.maximum(
                        spread_q70.fillna(0.0),
                        spread_abs_min,
                    )
                ).fillna(False)
            )
        )

        rv_curr = rv_96
        rv_prev = rv_96.shift(1)
        rv_decay_ratio = float(params.get("rv_decay_ratio", self.default_rv_decay_ratio))
        exhaustion = (
            (rv_curr < rv_prev).fillna(False)
            & (rv_curr <= rv_prev * rv_decay_ratio).fillna(False)
        )
        direction = np.sign(ret_1).replace(0.0, np.nan).ffill().fillna(0.0)

        return {
            "direction": pd.Series(direction, index=df.index),
            "ret_1": ret_1,
            "rebound_ret": rebound_ret,
            "oi_drop": oi_drop,
            "oi_drop_q80": oi_drop_q80,
            "liquidation_notional": liq_notional,
            "liq_q85": liq_q85,
            "spread_bps": spread_bps,
            "spread_q70": spread_q70,
            "ret_abs": ret_abs,
            "ret_q75": ret_q75,
            "forced_flow": forced_flow,
            "exhaustion": exhaustion,
            "rv_96": rv_96,
            "reversal_impulse": reversal_impulse,
            "reversal_q65": reversal_q65,
        }

    def compute_raw_mask(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        del df, params
        return (features["forced_flow"] & features["exhaustion"]).fillna(False)

    def compute_intensity(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        del df, params
        return (features["ret_abs"] * 1000.0) + (features["liquidation_notional"] / 100.0)

    def compute_direction(self, idx: int, features: Mapping[str, pd.Series], **params: Any) -> str:
        del params
        direction = float(features["direction"].iloc[idx] if not pd.isna(features["direction"].iloc[idx]) else 0.0)
        return "long" if direction < 0 else "short" if direction > 0 else "non_directional"

    def event_indices(self, df: pd.DataFrame, *, features: Mapping[str, pd.Series], **params: Any) -> list[int]:
        mask = self.compute_raw_mask(df, features=features, **params)
        onset = _onset_mask(mask)
        from project.events.sparsify import sparsify_mask

        spacing = int(params.get("cooldown_bars", params.get("min_spacing", self.min_spacing)))
        return sparsify_mask(onset, min_spacing=spacing)


class PostDeleveragingReboundDetector(CompositeDetector):
    event_type = "POST_DELEVERAGING_REBOUND"
    required_columns = ("timestamp", "close", "rv_96", "oi_delta_1h", "liquidation_notional")
    min_spacing = 12
    default_threshold_window = 2880
    default_oi_drop_quantile = 0.80
    default_liquidation_quantile = 0.85
    default_spread_quantile = 0.70
    default_return_quantile = 0.75
    default_wick_quantile = 0.70
    default_rebound_window = 6
    default_rebound_quantile = 0.70
    default_reversal_window = 3
    default_reversal_quantile = 0.65
    default_oi_drop_abs_min = 5.0
    default_liquidation_abs_min = 25.0
    default_liquidation_multiplier = 0.9
    default_return_abs_min = 0.0025
    default_spread_abs_min = 5.0
    default_cluster_window = 12
    default_rebound_window_bars = 6
    default_post_cluster_lookback = 48
    default_rv_peak_decay_ratio = 0.99
    default_liq_cooldown_ratio = 0.50
    default_liquidation_cooldown_abs_max = 500.0
    default_rebound_return_min = 0.0015
    default_wick_ratio_min = 0.55

    def prepare_features(self, df: pd.DataFrame, **params: Any) -> dict[str, pd.Series]:
        close = pd.to_numeric(df["close"], errors="coerce").astype(float)
        rv_96 = pd.to_numeric(df["rv_96"], errors="coerce").ffill().astype(float)
        oi_delta = pd.to_numeric(df.get("oi_delta_1h", pd.Series(0.0, index=df.index)), errors="coerce").fillna(0.0)
        liq_notional = pd.to_numeric(
            df.get("liquidation_notional", pd.Series(0.0, index=df.index)),
            errors="coerce",
        ).fillna(0.0)
        spread_bps = pd.to_numeric(df.get("spread_bps", pd.Series(0.0, index=df.index)), errors="coerce").fillna(0.0)
        ret_1 = close.pct_change(1).fillna(0.0)
        ret_abs = ret_1.abs()
        oi_drop = (-oi_delta).clip(lower=0.0)
        liq_delta = liq_notional.diff().fillna(0.0)
        wick_ratio = pd.Series(0.0, index=df.index, dtype=float)
        if "high" in df.columns and "low" in df.columns:
            high = pd.to_numeric(df["high"], errors="coerce").astype(float)
            low = pd.to_numeric(df["low"], errors="coerce").astype(float)
            open_proxy = close.shift(1).fillna(close)
            body = (close - open_proxy).abs()
            wick = (
                (high - np.maximum(open_proxy, close))
                + (np.minimum(open_proxy, close) - low)
            ).clip(lower=0.0)
            wick_ratio = (wick / (body + wick).replace(0.0, np.nan)).fillna(0.0)

        window = int(params.get("threshold_window", self.default_threshold_window))
        oi_drop_q80 = past_quantile(oi_drop, float(params.get("oi_drop_quantile", self.default_oi_drop_quantile)), window=window)
        liq_q85 = past_quantile(liq_notional, float(params.get("liquidation_quantile", self.default_liquidation_quantile)), window=window)
        spread_q70 = past_quantile(spread_bps, float(params.get("spread_quantile", self.default_spread_quantile)), window=window)
        ret_q75 = past_quantile(ret_abs, float(params.get("return_quantile", self.default_return_quantile)), window=window)
        wick_q70 = past_quantile(wick_ratio, float(params.get("wick_quantile", self.default_wick_quantile)), window=window)
        
        rebound_window = int(params.get("rebound_window", self.default_rebound_window))
        rebound_ret = close.pct_change(rebound_window).fillna(0.0)
        rebound_ret_q70 = past_quantile(rebound_ret.abs(), float(params.get("rebound_quantile", self.default_rebound_quantile)), window=window)
        
        reversal_window = int(params.get("reversal_window", self.default_reversal_window))
        reversal_impulse = close.pct_change(reversal_window).abs()
        reversal_q65 = past_quantile(reversal_impulse, float(params.get("reversal_quantile", self.default_reversal_quantile)), window=window)
        
        oi_drop_abs_min = float(params.get("oi_drop_abs_min", self.default_oi_drop_abs_min))
        liquidation_abs_min = float(params.get("liquidation_abs_min", self.default_liquidation_abs_min))
        liquidation_multiplier = float(params.get("liquidation_multiplier", self.default_liquidation_multiplier))
        return_abs_min = float(params.get("return_abs_min", self.default_return_abs_min))
        spread_abs_min = float(params.get("spread_abs_min", self.default_spread_abs_min))

        forced_flow = (
            (
                (oi_drop >= np.maximum(oi_drop_q80.fillna(0.0), oi_drop_abs_min)).fillna(False)
                & (
                    liq_notional
                    >= np.maximum(liq_q85.fillna(0.0), liquidation_abs_min)
                ).fillna(False)
            )
            | (
                (
                    liq_notional
                    >= np.maximum(
                        liq_q85.fillna(0.0) * liquidation_multiplier,
                        liquidation_abs_min,
                    )
                ).fillna(False)
                & (ret_abs >= np.maximum(ret_q75.fillna(0.0), return_abs_min)).fillna(False)
                & (
                    spread_bps
                    >= np.maximum(
                        spread_q70.fillna(0.0),
                        spread_abs_min,
                    )
                ).fillna(False)
            )
        )
        cluster_direction = np.sign(ret_1.where(forced_flow, 0.0)).replace(0.0, np.nan).ffill().fillna(0.0)
        return {
            "close": close,
            "ret_1": ret_1,
            "ret_abs": ret_abs,
            "rv_96": rv_96,
            "oi_drop": oi_drop,
            "oi_drop_q80": oi_drop_q80,
            "liquidation_notional": liq_notional,
            "liq_q85": liq_q85,
            "liq_delta": liq_delta,
            "spread_bps": spread_bps,
            "spread_q70": spread_q70,
            "forced_flow": forced_flow,
            "cluster_direction": pd.Series(cluster_direction, index=df.index),
            "rebound_ret": rebound_ret,
            "rebound_ret_q70": rebound_ret_q70,
            "reversal_impulse": reversal_impulse,
            "reversal_q65": reversal_q65,
            "wick_ratio": wick_ratio,
            "wick_q70": wick_q70,
        }

    def compute_raw_mask(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        del df
        cluster_window = int(params.get("cluster_window", self.default_cluster_window))
        rebound_window = int(params.get("rebound_window_bars", self.default_rebound_window_bars))
        post_cluster_lookback = int(params.get("post_cluster_lookback", self.default_post_cluster_lookback))
        forced_flow = features["forced_flow"].fillna(False)
        recent_cluster = forced_flow.rolling(post_cluster_lookback, min_periods=1).max().fillna(0).astype(bool)
        cluster_direction = np.sign(
            features["ret_1"].where(forced_flow, 0.0).rolling(post_cluster_lookback, min_periods=1).sum().shift(1)
        ).replace(0.0, np.nan).ffill().fillna(0.0)

        rv_peak = features["rv_96"].rolling(cluster_window, min_periods=1).max().shift(1)
        rv_peak_decay_ratio = float(params.get("rv_peak_decay_ratio", self.default_rv_peak_decay_ratio))
        liq_cooldown_ratio = float(params.get("liq_cooldown_ratio", self.default_liq_cooldown_ratio))
        liquidation_cooldown_abs_max = float(
            params.get("liquidation_cooldown_abs_max", self.default_liquidation_cooldown_abs_max)
        )

        vol_cooldown = (
            (features["rv_96"] <= rv_peak * rv_peak_decay_ratio).fillna(False)
            & (
                features["liquidation_notional"]
                <= np.maximum(
                    features["liq_q85"].fillna(0.0) * liq_cooldown_ratio,
                    liquidation_cooldown_abs_max,
                )
            ).fillna(False)
            & (features["liq_delta"] <= 0.0).fillna(False)
        )
        
        rebound_return_min = float(params.get("rebound_return_min", self.default_rebound_return_min))
        rebound = (
            (features["rebound_ret"].abs() >= features["rebound_ret_q70"]).fillna(False)
            & (features["rebound_ret"].abs() >= rebound_return_min).fillna(False)
            & (np.sign(features["rebound_ret"]) == -cluster_direction).fillna(False)
        )
        reversal_impulse = (features["reversal_impulse"] >= features["reversal_q65"]).fillna(False)
        
        wick_ratio_min = float(params.get("wick_ratio_min", self.default_wick_ratio_min))
        wick_confirm = (
            (features["wick_ratio"] >= features["wick_q70"]).fillna(False)
            | (features["wick_ratio"] >= wick_ratio_min).fillna(False)
        )
        return (
            recent_cluster
            & ~forced_flow
            & cluster_direction.ne(0.0)
            & ~(
                forced_flow.rolling(rebound_window, min_periods=1).max().shift(1).fillna(0).astype(bool)
            )
            & vol_cooldown
            & rebound
            & (reversal_impulse | wick_confirm)
        ).fillna(False)

    def event_indices(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> list[int]:
        mask = self.compute_raw_mask(df, features=features, **params)
        onset = _onset_mask(mask)
        spacing = int(params.get("cooldown_bars", params.get("min_spacing", self.min_spacing)))
        from project.events.sparsify import sparsify_mask

        return sparsify_mask(onset, min_spacing=spacing)

    def compute_intensity(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        del df, params
        liq_ratio = features["liquidation_notional"] / features["liq_q85"].replace(0.0, np.nan)
        return (
            features["rebound_ret"].abs().fillna(0.0) * 100.0
            + features["reversal_impulse"].fillna(0.0) * 100.0
            + (1.0 - liq_ratio.fillna(0.0).clip(lower=0.0, upper=1.0))
        ).clip(lower=0.0)

    def compute_direction(self, idx: int, features: dict[str, pd.Series], **params: Any) -> str:
        del params
        rebound = float(features["rebound_ret"].iloc[idx] if not pd.isna(features["rebound_ret"].iloc[idx]) else 0.0)
        return "long" if rebound > 0 else "short" if rebound < 0 else "non_directional"


class TrendExhaustionDetector(CompositeDetector):
    event_type = "TREND_EXHAUSTION_TRIGGER"
    required_columns = ("timestamp", "close", "rv_96")
    min_spacing = 48

    def prepare_features(self, df: pd.DataFrame, **params: Any) -> dict[str, pd.Series]:
        close = pd.to_numeric(df["close"], errors="coerce").astype(float)
        rv_96 = pd.to_numeric(df["rv_96"], errors="coerce").ffill().astype(float)
        
        trend_window = int(params.get("trend_window", 96))
        trend = close.pct_change(trend_window)
        trend_abs = trend.abs()
        
        vol_window = int(params.get("vol_window", 288))
        rv_z = rolling_mean_std_zscore(rv_96, window=vol_window)
        rv_median = rv_96.rolling(vol_window, min_periods=12).median().shift(1)
        
        slope_fast = close.diff(int(params.get("slope_fast_window", 12)))
        slope_slow = close.diff(int(params.get("slope_slow_window", 48)))
        
        pullback_window = int(params.get("pullback_window", 96))
        rolling_high = close.rolling(pullback_window, min_periods=12).max().shift(1)
        rolling_low = close.rolling(pullback_window, min_periods=12).min().shift(1)
        pullback_up = ((rolling_high - close) / rolling_high.replace(0.0, np.nan)).clip(lower=0.0)
        pullback_down = ((close - rolling_low) / rolling_low.replace(0.0, np.nan)).clip(lower=0.0)
        
        threshold_window = int(params.get("threshold_window", 2880))
        trend_q_extreme = past_quantile(trend_abs, float(params.get("trend_quantile", 0.95)), window=threshold_window)
        trend_median = trend_abs.rolling(trend_window, min_periods=12).median().shift(1)
        
        rv_q35 = past_quantile(rv_z, float(params.get("cooldown_quantile", 0.35)), window=threshold_window)
        
        pullback_quantile = float(params.get("pullback_quantile", 0.70))
        pullback_q70 = past_quantile(pd.concat([pullback_up, pullback_down], axis=1).max(axis=1), pullback_quantile, window=threshold_window)
        
        reversal_window = int(params.get("reversal_window", 3))
        reversal_impulse = close.pct_change(reversal_window).abs()
        reversal_q65 = past_quantile(reversal_impulse, float(params.get("reversal_quantile", 0.65)), window=threshold_window)
        
        return {
            "trend": trend,
            "trend_abs": trend_abs,
            "rv_z": rv_z,
            "rv_96": rv_96,
            "rv_median": rv_median,
            "slope_fast": slope_fast,
            "slope_slow": slope_slow,
            "pullback_up": pullback_up,
            "pullback_down": pullback_down,
            "trend_q_extreme": trend_q_extreme,
            "trend_median": trend_median,
            "rv_q35": rv_q35,
            "pullback_q70": pullback_q70,
            "reversal_impulse": reversal_impulse,
            "reversal_q65": reversal_q65,
        }

    def compute_raw_mask(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        del df
        # 1. Structural Signal: Trend must be at a historical extreme
        trend_peak_multiplier = float(params.get("trend_peak_multiplier", 1.10))
        trend_strength_ratio = float(params.get("trend_strength_ratio", 2.2))
        
        trend_peak = (
            (features["trend_abs"] >= features["trend_q_extreme"] * trend_peak_multiplier).fillna(False)
            | (features["trend_abs"] >= features["trend_median"] * trend_strength_ratio).fillna(False)
        )
        
        # 2. Cooldown Guard: Volatility must be decelerating or low
        cooldown_ratio = float(params.get("cooldown_ratio", 0.90))
        cooldown = (
            (features["rv_z"] <= features["rv_q35"]).fillna(False)
            | (features["rv_96"] <= features["rv_median"] * cooldown_ratio).fillna(False)
        )
        
        # 3. Reversal Guard: Look for immediate counter-trend impulse or weakening
        reversal_window = int(params.get("reversal_alignment_window", 3))
        
        weakening_up = (features["trend"].shift(1) > 0).fillna(False) & (
            (features["slope_fast"] <= 0).fillna(False)
            | (features["pullback_up"] >= features["pullback_q70"]).fillna(False)
        )
        weakening_down = (features["trend"].shift(1) < 0).fillna(False) & (
            (features["slope_fast"] >= 0).fillna(False)
            | (features["pullback_down"] >= features["pullback_q70"]).fillna(False)
        )
        slope_cross = ((features["slope_fast"] * features["slope_slow"]) <= 0).fillna(False)
        
        reversal_confirmed = (
            (features["reversal_impulse"] >= features["reversal_q65"]).fillna(False)
            | (
                (features["pullback_up"] >= features["pullback_q70"]).fillna(False)
                | (features["pullback_down"] >= features["pullback_q70"]).fillna(False)
            )
        )
        
        any_reversal = (weakening_up | weakening_down | slope_cross | reversal_confirmed).fillna(False)
        any_reversal_flex = any_reversal.rolling(window=reversal_window, min_periods=1).max().astype(bool)
        
        return (trend_peak & cooldown & any_reversal_flex).fillna(False)

    def compute_intensity(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        del df, params
        pullback = pd.concat([features["pullback_up"], features["pullback_down"]], axis=1).max(axis=1)
        return (features["trend_abs"].fillna(0.0) * (1.0 + pullback.fillna(0.0))).clip(lower=0.0)

    def compute_direction(self, idx: int, features: Mapping[str, pd.Series], **params: Any) -> str:
        del params
        trend = float(features["trend"].iloc[idx] if not pd.isna(features["trend"].iloc[idx]) else 0.0)
        return "short" if trend > 0 else "long" if trend < 0 else "non_directional"

    def event_indices(self, df: pd.DataFrame, *, features: Mapping[str, pd.Series], **params: Any) -> list[int]:
        mask = self.compute_raw_mask(df, features=features, **params)
        onset = _onset_mask(mask)
        from project.events.sparsify import sparsify_mask
        spacing = int(params.get("cooldown_bars", params.get("min_spacing", self.min_spacing)))
        return sparsify_mask(onset, min_spacing=spacing)


class MomentumDivergenceDetector(ThresholdDetector):
    event_type = "MOMENTUM_DIVERGENCE_TRIGGER"
    required_columns = ("timestamp", "close")
    min_spacing = 48
    min_trend_extension_quantile: float = 0.90

    def prepare_features(self, df: pd.DataFrame, **params: Any) -> dict[str, pd.Series]:
        close = pd.to_numeric(df["close"], errors="coerce").astype(float)
        
        fast_window = int(params.get("fast_window", 12))
        slow_window = int(params.get("slow_window", 96))
        mom_fast = close.pct_change(fast_window)
        mom_slow = close.pct_change(slow_window)
        accel = mom_fast - mom_slow
        
        ext_window = int(params.get("extension_window", 96))
        rolling_high = close.rolling(ext_window, min_periods=12).max().shift(1)
        rolling_low = close.rolling(ext_window, min_periods=12).min().shift(1)
        
        extension_up = ((close - rolling_low) / rolling_low.replace(0.0, np.nan)).clip(lower=0.0)
        extension_down = ((rolling_high - close) / rolling_high.replace(0.0, np.nan)).clip(lower=0.0)
        extension_max = pd.concat([extension_up, extension_down], axis=1).max(axis=1)
        
        divergence = (mom_fast * mom_slow < 0).fillna(False)
        
        reversal_window = int(params.get("reversal_window", 3))
        reversal_impulse = close.pct_change(reversal_window).abs()
        
        accel_abs = accel.abs()
        threshold_window = int(params.get("threshold_window", 2880))
        
        accel_q_threshold = past_quantile(accel_abs, float(params.get("accel_quantile", 0.90)), window=threshold_window)
        ext_q = float(params.get("min_trend_extension_quantile", self.min_trend_extension_quantile))
        extension_q_threshold = past_quantile(extension_max, ext_q, window=threshold_window)
        
        reversal_q70 = past_quantile(reversal_impulse, float(params.get("reversal_quantile", 0.70)), window=threshold_window)
        divergence_turn = (mom_fast.shift(1) * mom_fast <= 0).fillna(False)
        
        return {
            "mom_fast": mom_fast,
            "mom_slow": mom_slow,
            "divergence": divergence,
            "reversal_impulse": reversal_impulse,
            "accel_abs": accel_abs,
            "extension_max": extension_max,
            "accel_q_threshold": accel_q_threshold,
            "extension_q_threshold": extension_q_threshold,
            "reversal_q70": reversal_q70,
            "divergence_turn": divergence_turn,
        }

    def compute_raw_mask(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        del df, params
        # Must be extended relative to history to fire divergence
        is_extended = (features["extension_max"] >= features["extension_q_threshold"]).fillna(False)
        
        return (
            features["divergence"]
            & features["divergence_turn"]
            & is_extended
            & (
                (features["accel_abs"] >= features["accel_q_threshold"]).fillna(False)
                | (features["reversal_impulse"] >= features["reversal_q70"]).fillna(False)
            )
        ).fillna(False)

    def compute_intensity(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        del df, params
        # Use simple name for max extension from prepare_features
        extension = features["extension_max"]
        return (features["accel_abs"].fillna(0.0) * (1.0 + extension.fillna(0.0))).clip(lower=0.0)

    def compute_direction(self, idx: int, features: Mapping[str, pd.Series], **params: Any) -> str:
        del params
        accel = float(features["mom_fast"].iloc[idx] - features["mom_slow"].iloc[idx])
        return "short" if accel < 0 else "long" if accel > 0 else "non_directional"


class ClimaxVolumeDetector(ThresholdDetector):
    event_type = "CLIMAX_VOLUME_BAR"
    required_columns = ("timestamp", "close", "high", "low", "volume")
    min_spacing = 12

    def prepare_features(self, df: pd.DataFrame, **params: Any) -> dict[str, pd.Series]:
        vol = pd.to_numeric(df["volume"], errors="coerce").astype(float)
        close = pd.to_numeric(df["close"], errors="coerce").astype(float)
        high = pd.to_numeric(df["high"], errors="coerce").astype(float)
        low = pd.to_numeric(df["low"], errors="coerce").astype(float)
        ret_abs = close.pct_change(1).abs()
        bar_range = (high - low) / close.replace(0.0, np.nan)
        
        window = int(params.get("threshold_window", 2880))
        vol_q97 = past_quantile(vol, float(params.get("vol_quantile", 0.97)), window=window)
        ret_q97 = past_quantile(ret_abs, float(params.get("ret_quantile", 0.97)), window=window)
        range_q97 = past_quantile(bar_range, float(params.get("range_quantile", 0.97)), window=window)
        return {
            "vol": vol,
            "ret_abs": ret_abs,
            "bar_range": bar_range,
            "vol_q97": vol_q97,
            "ret_q97": ret_q97,
            "range_q97": range_q97,
        }

    def compute_raw_mask(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        del df, params
        return (
            (features["vol"] >= features["vol_q97"]).fillna(False)
            & (
                (features["ret_abs"] >= features["ret_q97"]).fillna(False)
                | (features["bar_range"] >= features["range_q97"]).fillna(False)
            )
        ).fillna(False)

    def compute_intensity(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        del df, params
        return (features["vol"] / features["vol_q97"]).fillna(0.0)


class FailedContinuationDetector(ThresholdDetector):
    event_type = "FAILED_CONTINUATION"
    required_columns = ("timestamp", "close", "high", "low")
    min_spacing = 24

    def prepare_features(self, df: pd.DataFrame, **params: Any) -> dict[str, pd.Series]:
        close = pd.to_numeric(df["close"], errors="coerce").astype(float)
        high = pd.to_numeric(df["high"], errors="coerce").astype(float)
        low = pd.to_numeric(df["low"], errors="coerce").astype(float)
        
        breakout_window = int(params.get("breakout_window", 48))
        reversal_window = int(params.get("reversal_window", 12))
        
        trend = close.pct_change(breakout_window)
        prior_high = high.rolling(breakout_window, min_periods=max(6, breakout_window // 4)).max().shift(1)
        prior_low = low.rolling(breakout_window, min_periods=max(6, breakout_window // 4)).min().shift(1)
        
        breakout_up = (close.shift(1) >= prior_high.shift(1)).fillna(False)
        breakout_dn = (close.shift(1) <= prior_low.shift(1)).fillna(False)
        breakout_strength_up = ((close.shift(1) - prior_high.shift(1)) / close.shift(1).replace(0.0, np.nan)).clip(lower=0.0)
        breakout_strength_dn = ((prior_low.shift(1) - close.shift(1)) / close.shift(1).replace(0.0, np.nan)).clip(lower=0.0)
        
        recent_window = int(params.get("recent_breakout_window", 6))
        breakout_up_recent = breakout_up.rolling(window=recent_window, min_periods=1).max().astype(bool)
        breakout_dn_recent = breakout_dn.rolling(window=recent_window, min_periods=1).max().astype(bool)
        recent_breakout_strength_up = breakout_strength_up.rolling(window=recent_window, min_periods=1).max()
        recent_breakout_strength_dn = breakout_strength_dn.rolling(window=recent_window, min_periods=1).max()
        
        reentry_up = (close < prior_high).fillna(False)
        reentry_dn = (close > prior_low).fillna(False)
        reversal_fast = close.pct_change(max(1, reversal_window // 2))
        
        breakout_strength_min = float(params.get("breakout_strength_min", 0.0010))
        reentry_min = float(params.get("reentry_min", 0.0010))
        reversal_return_min = float(params.get("reversal_return_min", 0.0010))

        failed_up = (
            breakout_up_recent
            & (recent_breakout_strength_up >= breakout_strength_min).fillna(False)
            & reentry_up
            & (close < prior_high * (1.0 - reentry_min)).fillna(False)
            & (reversal_fast < -reversal_return_min).fillna(False)
        )
        failed_dn = (
            breakout_dn_recent
            & (recent_breakout_strength_dn >= breakout_strength_min).fillna(False)
            & reentry_dn
            & (close > prior_low * (1.0 + reentry_min)).fillna(False)
            & (reversal_fast > reversal_return_min).fillna(False)
        )
        
        ret_abs = close.pct_change(1).abs()
        threshold_window = int(params.get("threshold_window", 2880))
        reversal_quantile = float(params.get("reversal_quantile", 0.40))
        ret_q60 = past_quantile(ret_abs, reversal_quantile, window=threshold_window)
        
        range_width = (prior_high - prior_low).replace(0.0, np.nan)
        reentry_distance = pd.concat([
            ((prior_high - close) / range_width).clip(lower=0.0),
            ((close - prior_low) / range_width).clip(lower=0.0),
        ], axis=1).max(axis=1)
        
        return {
            "trend": trend,
            "failed_up": failed_up,
            "failed_dn": failed_dn,
            "ret_abs": ret_abs,
            "ret_q60": ret_q60,
            "reentry_distance": reentry_distance.fillna(0.0),
        }

    def compute_raw_mask(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        del df, params
        return (
            (features["failed_up"] | features["failed_dn"]).fillna(False)
            & (features["ret_abs"] >= features["ret_q60"]).fillna(False)
        ).fillna(False)

    def compute_intensity(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        del df, params
        return (features["ret_abs"].fillna(0.0) * (1.0 + features["reentry_distance"].fillna(0.0))).clip(lower=0.0)

    def compute_direction(self, idx: int, features: Mapping[str, pd.Series], **params: Any) -> str:
        del params
        if bool(features["failed_up"].iloc[idx]):
            return "short"
        if bool(features["failed_dn"].iloc[idx]):
            return "long"
        return "non_directional"

    def event_indices(self, df: pd.DataFrame, *, features: Mapping[str, pd.Series], **params: Any) -> list[int]:
        mask = self.compute_raw_mask(df, features=features, **params)
        onset = _onset_mask(mask)
        from project.events.sparsify import sparsify_mask

        spacing = int(params.get("cooldown_bars", params.get("min_spacing", self.min_spacing)))
        return sparsify_mask(onset, min_spacing=spacing)


EXHAUSTION_DETECTORS = {
    "FLOW_EXHAUSTION_PROXY": FlowExhaustionDetector,
    "FORCED_FLOW_EXHAUSTION": FlowExhaustionDetector,
    "POST_DELEVERAGING_REBOUND": PostDeleveragingReboundDetector,
    "TREND_EXHAUSTION_TRIGGER": TrendExhaustionDetector,
    "MOMENTUM_DIVERGENCE_TRIGGER": MomentumDivergenceDetector,
    "CLIMAX_VOLUME_BAR": ClimaxVolumeDetector,
    "FAILED_CONTINUATION": FailedContinuationDetector,
}


__all__ = [
    "ClimaxVolumeDetector",
    "EXHAUSTION_DETECTORS",
    "FailedContinuationDetector",
    "FlowExhaustionDetector",
    "MomentumDivergenceDetector",
    "PostDeleveragingReboundDetector",
    "TrendExhaustionDetector",
]
