from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from project.events.detectors.threshold import ThresholdDetector
from project.events.detectors.transition import TransitionDetector
from project.events.detectors.composite import CompositeDetector
from project.events.shared import EVENT_COLUMNS, emit_event, format_event_id
from project.events.thresholding import rolling_mean_std_zscore
from project.research.analyzers import run_analyzer_suite

def past_quantile(series: pd.Series, q: float, window: int = 2880) -> pd.Series:
    return series.rolling(window, min_periods=window//10).quantile(q).shift(1)

class VolRegimeShiftDetector(TransitionDetector):
    event_type = 'VOL_REGIME_SHIFT_EVENT'
    required_columns = ('timestamp', 'rv_96')

    def prepare_features(self, df: pd.DataFrame, **params: Any) -> dict[str, pd.Series]:
        rv_96 = df['rv_96'].ffill()
        window = int(params.get('lookback_window', 2880))
        rv_low_th = past_quantile(rv_96, 0.33, window=window)
        rv_high_th = past_quantile(rv_96, 0.66, window=window)
        return {'rv_96': rv_96, 'rv_low_th': rv_low_th, 'rv_high_th': rv_high_th}

    def compute_raw_mask(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        rv = features['rv_96']
        hi = features['rv_high_th']
        lo = features['rv_low_th']
        up_shift = (rv > hi).fillna(False) & (rv.shift(1) <= hi.shift(1)).fillna(False)
        down_shift = (rv < lo).fillna(False) & (rv.shift(1) >= lo.shift(1)).fillna(False)
        return (up_shift | down_shift).fillna(False)

    def compute_intensity(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        return features['rv_96']

    def compute_direction(self, idx: int, features: dict[str, pd.Series], **params: Any) -> str:
        del params
        rv = features['rv_96'].iloc[idx]
        hi = features['rv_high_th'].iloc[idx]
        return "long" if rv >= hi else "short"

class TrendToChopDetector(TransitionDetector):
    event_type = 'TREND_TO_CHOP_SHIFT'
    required_columns = ('timestamp', 'close', 'rv_96')

    def prepare_features(self, df: pd.DataFrame, **params: Any) -> dict[str, pd.Series]:
        close = df['close']
        rv_96 = df['rv_96'].ffill()
        trend_abs = close.pct_change(96).abs()
        trend_hi = past_quantile(trend_abs, 0.70)
        trend_lo = past_quantile(trend_abs, 0.35)
        rv_lo = past_quantile(rv_96, 0.35)
        return {'trend_abs': trend_abs, 'rv_96': rv_96, 'trend_hi': trend_hi, 'trend_lo': trend_lo, 'rv_lo': rv_lo}

    def compute_raw_mask(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        return (
            (features['trend_abs'].shift(1) >= features['trend_hi'].shift(1)).fillna(False)
            & (features['trend_abs'] <= features['trend_lo']).fillna(False)
            & (features['rv_96'] <= features['rv_lo']).fillna(False)
        ).fillna(False)

    def compute_intensity(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        return features['trend_abs']

class ChopToTrendDetector(TransitionDetector):
    event_type = 'CHOP_TO_TREND_SHIFT'
    required_columns = ('timestamp', 'close', 'rv_96')

    def prepare_features(self, df: pd.DataFrame, **params: Any) -> dict[str, pd.Series]:
        close = df['close']
        rv_96 = df['rv_96'].ffill()
        trend_abs = close.pct_change(96).abs()
        trend_hi = past_quantile(trend_abs, 0.70)
        trend_lo = past_quantile(trend_abs, 0.35)
        rv_hi = past_quantile(rv_96, 0.70)
        return {'trend_abs': trend_abs, 'rv_96': rv_96, 'trend_hi': trend_hi, 'trend_lo': trend_lo, 'rv_hi': rv_hi}

    def compute_raw_mask(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        return (
            (features['trend_abs'].shift(1) <= features['trend_lo'].shift(1)).fillna(False)
            & (features['trend_abs'] >= features['trend_hi']).fillna(False)
            & (features['rv_96'] >= features['rv_hi']).fillna(False)
        ).fillna(False)

    def compute_intensity(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        return features['trend_abs']

class CorrelationBreakdownDetector(CompositeDetector):
    event_type = 'CORRELATION_BREAKDOWN_EVENT'
    required_columns = ('timestamp', 'close', 'spread_zscore')

    def prepare_features(self, df: pd.DataFrame, **params: Any) -> dict[str, pd.Series]:
        close = df['close']
        ret_1 = close.pct_change(1)
        spread_z = df['spread_zscore']
        basis_z = df.get('basis_zscore', df.get('cross_exchange_spread_z', pd.Series(0.0, index=df.index)))
        basis_abs = basis_z.abs()
        spread_abs = spread_z.abs()
        basis_hi = past_quantile(basis_abs, 0.92)
        spread_hi = past_quantile(spread_abs, 0.80)
        return {'ret_1': ret_1, 'basis_z': basis_z, 'basis_abs': basis_abs, 'spread_abs': spread_abs, 'basis_hi': basis_hi, 'spread_hi': spread_hi}

    def compute_raw_mask(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        desync = (features['basis_abs'] >= features['basis_hi']).fillna(False) & (features['spread_abs'] >= features['spread_hi']).fillna(False)
        direction_conflict = ((features['ret_1'] * features['basis_z']) < 0).fillna(False)
        return (desync & direction_conflict).fillna(False)

    def compute_intensity(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        return features['basis_abs'] + features['spread_abs']

class BetaSpikeDetector(CompositeDetector):
    event_type = 'BETA_SPIKE_EVENT'
    required_columns = ('timestamp', 'close', 'rv_96')

    def prepare_features(self, df: pd.DataFrame, **params: Any) -> dict[str, pd.Series]:
        close = df['close']
        ret_abs = close.pct_change(1).abs()
        rv_96 = df['rv_96'].ffill()
        basis_z = df.get('basis_zscore', df.get('cross_exchange_spread_z', pd.Series(0.0, index=df.index)))
        basis_abs = basis_z.abs()
        ret_tail = past_quantile(ret_abs, 0.99)
        basis_med_hi = past_quantile(basis_abs, 0.85)
        rv_hi = past_quantile(rv_96, 0.70)
        return {'ret_abs': ret_abs, 'rv_96': rv_96, 'basis_abs': basis_abs, 'ret_tail': ret_tail, 'basis_med_hi': basis_med_hi, 'rv_hi': rv_hi}

    def compute_raw_mask(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        return (
            (features['ret_abs'] >= features['ret_tail']).fillna(False)
            & (features['basis_abs'] >= features['basis_med_hi']).fillna(False)
            & (features['rv_96'] >= features['rv_hi']).fillna(False)
        ).fillna(False)

    def compute_intensity(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        return features['ret_abs'] + features['basis_abs'] + features['rv_96']

from project.events.detectors.registry import register_detector

_DETECTORS = {
    'VOL_REGIME_SHIFT': VolRegimeShiftDetector,
    'VOL_REGIME_SHIFT_EVENT': VolRegimeShiftDetector,
    'TREND_TO_CHOP_SHIFT': TrendToChopDetector,
    'CHOP_TO_TREND_SHIFT': ChopToTrendDetector,
    'CORRELATION_BREAKDOWN_EVENT': CorrelationBreakdownDetector,
    'BETA_SPIKE_EVENT': BetaSpikeDetector,
}

for et, cls in _DETECTORS.items():
    register_detector(et, cls)

def detect_regime_family(df: pd.DataFrame, symbol: str, event_type: str = 'VOL_REGIME_SHIFT_EVENT', **params: Any) -> pd.DataFrame:
    detector_cls = _DETECTORS.get(event_type)
    if detector_cls is None:
        raise ValueError(f"Unknown regime event type: {event_type}")
    return detector_cls().detect(df, symbol=symbol, **params)

def analyze_regime_family(df: pd.DataFrame, symbol: str, event_type: str = 'VOL_REGIME_SHIFT_EVENT', **params: Any) -> tuple[pd.DataFrame, dict[str, Any]]:
    events = detect_regime_family(df, symbol, event_type=event_type, **params)
    market = df[['timestamp', 'close']].copy() if not df.empty and 'close' in df.columns else None
    analyzer_results = run_analyzer_suite(events, market=market) if not events.empty else {}
    return events, analyzer_results
