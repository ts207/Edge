from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from project.events.detectors.registry import register_detector
from project.events.detectors.threshold import ThresholdDetector
from project.events.shared import EVENT_COLUMNS, emit_event, format_event_id
from project.events.sparsify import sparsify_mask
from project.events.thresholding import rolling_quantile_threshold, rolling_mean_std_zscore
from project.events.event_aliases import resolve_event_alias
from project.research.analyzers import run_analyzer_suite


class _CanonicalProxyBase(ThresholdDetector):
    required_columns = ('timestamp', 'close', 'high', 'low')
    timeframe_minutes = 5
    default_severity = 'moderate'
    min_spacing = 6

    def compute_severity(self, idx: int, intensity: float, features: dict[str, pd.Series], **params: Any) -> str:
        del idx, features, params
        if intensity >= 4.0: return 'extreme'
        if intensity >= 2.5: return 'major'
        return 'moderate'

    def compute_metadata(self, idx: int, features: dict[str, pd.Series], **params: Any) -> dict[str, Any]:
        del idx, features, params
        return {
            'family': 'canonical_proxy',
            'source_event_type': self.source_event_type,
            'evidence_tier': 'proxy',
        }


def _require_columns(df: pd.DataFrame, *, event_type: str, required: tuple[str, ...]) -> None:
    missing = [column for column in required if column not in df.columns]
    if missing:
        names = ", ".join(missing)
        raise ValueError(f"{event_type} requires columns: {names}")


class PriceVolImbalanceProxyDetector(_CanonicalProxyBase):
    event_type = 'PRICE_VOL_IMBALANCE_PROXY'
    source_event_type = 'ORDERFLOW_IMBALANCE_SHOCK'
    required_columns = _CanonicalProxyBase.required_columns + ('volume', 'rv_96')
    min_spacing = 24

    def prepare_features(self, df: pd.DataFrame, **params: Any) -> dict[str, pd.Series]:
        close = pd.to_numeric(df['close'], errors='coerce').astype(float)
        volume = pd.to_numeric(df['volume'], errors='coerce').astype(float)
        rv = pd.to_numeric(df.get('rv_96'), errors='coerce').astype(float)
        ret_abs = close.pct_change(1).abs()
        ret_window = int(params.get('ret_window', 288))
        rv_window = int(params.get('rv_window', 288))
        vol_window = int(params.get('vol_window', 288))
        min_history_bars = int(params.get('min_history_bars', 288))

        rv_z = rolling_mean_std_zscore(rv.ffill(), window=rv_window)
        ret_q = rolling_quantile_threshold(
            ret_abs,
            quantile=float(params.get('ret_quantile', 0.995)),
            window=ret_window,
        )
        rv_q = rolling_quantile_threshold(
            rv_z,
            quantile=float(params.get('rv_quantile', 0.9)),
            window=rv_window,
        )
        vol_q = rolling_quantile_threshold(
            volume,
            quantile=float(params.get('volume_quantile', 0.9)),
            window=vol_window,
        )
        history_ready = pd.Series(np.arange(len(df)) >= min_history_bars, index=df.index, dtype=bool)
        signal = (
            (ret_abs / ret_q.replace(0.0, np.nan)).fillna(0.0)
            + (rv_z / rv_q.replace(0.0, np.nan)).fillna(0.0)
            + (volume / vol_q.replace(0.0, np.nan)).fillna(0.0)
        ) / 3.0
        return {
            'signal': signal,
            'ret_abs': ret_abs,
            'rv_z': rv_z,
            'volume': volume,
            'ret_q': ret_q,
            'rv_q': rv_q,
            'vol_q': vol_q,
            'history_ready': history_ready,
        }

    def compute_raw_mask(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        del df, params
        return (
            features['history_ready']
            & (features['ret_abs'] >= features['ret_q']).fillna(False)
            & (features['rv_z'] >= features['rv_q']).fillna(False)
            & (features['volume'] >= features['vol_q']).fillna(False)
        ).fillna(False)

    def compute_intensity(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        del df, params
        return features['signal'].fillna(0.0)


class WickReversalProxyDetector(_CanonicalProxyBase):
    event_type = 'WICK_REVERSAL_PROXY'
    source_event_type = 'SWEEP_STOPRUN'

    def prepare_features(self, df: pd.DataFrame, **params: Any) -> dict[str, pd.Series]:
        close = pd.to_numeric(df['close'], errors='coerce').replace(0.0, np.nan).astype(float)
        high = pd.to_numeric(df['high'], errors='coerce').astype(float)
        low = pd.to_numeric(df['low'], errors='coerce').astype(float)
        open_proxy = close.shift(1).fillna(close)
        wick_up = high - np.maximum(open_proxy, close)
        wick_down = np.minimum(open_proxy, close) - low
        wick = ((wick_up + wick_down) / close).abs().astype(float)
        wick_q = rolling_quantile_threshold(wick, quantile=float(params.get('wick_quantile', 0.97)), window=int(params.get('window', 288)))
        ret_abs = close.pct_change(1).abs()
        ret_q = rolling_quantile_threshold(ret_abs, quantile=float(params.get('ret_quantile', 0.9)), window=int(params.get('window', 288)))
        return {'wick': wick, 'wick_q': wick_q, 'ret_abs': ret_abs, 'ret_q': ret_q}

    def compute_raw_mask(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        return ((features['wick'] >= features['wick_q']).fillna(False) & (features['ret_abs'] >= features['ret_q']).fillna(False)).fillna(False)

    def compute_intensity(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        return ((features['wick'] / features['wick_q'].replace(0.0, np.nan)).fillna(0.0) + (features['ret_abs'] / features['ret_q'].replace(0.0, np.nan)).fillna(0.0)) / 2.0


class AbsorptionProxyDetector(_CanonicalProxyBase):
    event_type = 'ABSORPTION_PROXY'
    source_event_type = 'ABSORPTION_EVENT'
    min_spacing = 96

    def prepare_features(self, df: pd.DataFrame, **params: Any) -> dict[str, pd.Series]:
        _require_columns(df, event_type=self.event_type, required=('spread_zscore', 'rv_96', 'imbalance'))
        spread = pd.to_numeric(df['spread_zscore'], errors='coerce').astype(float)
        rv = pd.to_numeric(df['rv_96'], errors='coerce').astype(float)
        imbalance_abs = pd.to_numeric(df['imbalance'], errors='coerce').astype(float).abs()
        window = int(params.get('window', 288))
        min_history_bars = int(params.get('min_history_bars', 288))
        spread_hi = rolling_quantile_threshold(spread.ffill(), quantile=float(params.get('spread_quantile', 0.965)), window=window)
        rv_z = rolling_mean_std_zscore(rv.ffill(), window=window)
        rv_hi = rolling_quantile_threshold(rv_z.ffill(), quantile=float(params.get('rv_quantile', 0.90)), window=window)
        imbalance_low = rolling_quantile_threshold(
            imbalance_abs.ffill(),
            quantile=float(params.get('imbalance_abs_quantile', 0.25)),
            window=window,
        )
        history_ready = pd.Series(np.arange(len(df)) >= min_history_bars, index=df.index, dtype=bool)
        return {
            'spread': spread,
            'spread_hi': spread_hi,
            'rv_z': rv_z,
            'rv_hi': rv_hi,
            'imbalance_abs': imbalance_abs,
            'imbalance_low': imbalance_low,
            'history_ready': history_ready,
        }

    def compute_raw_mask(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        return (
            features['history_ready']
            & (features['spread'] >= features['spread_hi']).fillna(False)
            & (features['rv_z'] >= features['rv_hi']).fillna(False)
            & (features['imbalance_abs'] <= features['imbalance_low']).fillna(False)
        ).fillna(False)

    def compute_intensity(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        return (
            (features['spread'] / features['spread_hi'].replace(0.0, np.nan)).fillna(0.0)
            + (features['rv_z'] / features['rv_hi'].replace(0.0, np.nan)).fillna(0.0)
        ) / 2.0


class DepthStressProxyDetector(_CanonicalProxyBase):
    event_type = 'DEPTH_STRESS_PROXY'
    source_event_type = 'DEPTH_COLLAPSE'
    min_spacing = 96

    def prepare_features(self, df: pd.DataFrame, **params: Any) -> dict[str, pd.Series]:
        _require_columns(df, event_type=self.event_type, required=('spread_zscore', 'rv_96', 'micro_depth_depletion'))
        spread = pd.to_numeric(df['spread_zscore'], errors='coerce').astype(float)
        rv = pd.to_numeric(df['rv_96'], errors='coerce').astype(float)
        depth_depletion = pd.to_numeric(df['micro_depth_depletion'], errors='coerce').astype(float)
        window = int(params.get('window', 288))
        min_history_bars = int(params.get('min_history_bars', 288))
        spread_q = rolling_quantile_threshold(spread.ffill(), quantile=float(params.get('spread_quantile', 0.99)), window=window)
        rv_z = rolling_mean_std_zscore(rv.ffill(), window=window)
        rv_q = rolling_quantile_threshold(rv_z.ffill(), quantile=float(params.get('rv_quantile', 0.90)), window=window)
        depth_q = rolling_quantile_threshold(
            depth_depletion.ffill(),
            quantile=float(params.get('depth_quantile', 0.93)),
            window=window,
        )
        history_ready = pd.Series(np.arange(len(df)) >= min_history_bars, index=df.index, dtype=bool)
        return {
            'spread': spread,
            'spread_q': spread_q,
            'rv_z': rv_z,
            'rv_q': rv_q,
            'depth_depletion': depth_depletion,
            'depth_q': depth_q,
            'history_ready': history_ready,
        }

    def compute_raw_mask(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        return (
            features['history_ready']
            & (features['spread'] >= features['spread_q']).fillna(False)
            & (features['rv_z'] >= features['rv_q']).fillna(False)
            & (features['depth_depletion'] >= features['depth_q']).fillna(False)
        ).fillna(False)

    def compute_intensity(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        return ((features['spread'] / features['spread_q'].replace(0.0, np.nan)).fillna(0.0) + (features['rv_z'] / features['rv_q'].replace(0.0, np.nan)).fillna(0.0)) / 2.0


_DETECTORS = {
    'PRICE_VOL_IMBALANCE_PROXY': PriceVolImbalanceProxyDetector,
    'WICK_REVERSAL_PROXY': WickReversalProxyDetector,
    'ABSORPTION_PROXY': AbsorptionProxyDetector,
    'DEPTH_STRESS_PROXY': DepthStressProxyDetector,
    # Canonical alias names — same detector classes
    'ORDERFLOW_IMBALANCE_SHOCK': PriceVolImbalanceProxyDetector,
    'SWEEP_STOPRUN': WickReversalProxyDetector,
    'ABSORPTION_EVENT': AbsorptionProxyDetector,
    'DEPTH_COLLAPSE': DepthStressProxyDetector,
}

for et, cls in _DETECTORS.items():
    register_detector(et, cls)

def detect_canonical_proxy_family(df: pd.DataFrame, symbol: str, event_type: str, **params: Any) -> pd.DataFrame:
    canonical = resolve_event_alias(event_type)
    detector_cls = _DETECTORS.get(canonical)
    if detector_cls is None:
        raise ValueError(f'Unsupported canonical proxy event type: {event_type}')
    return detector_cls().detect(df, symbol=symbol, **params)



def analyze_canonical_proxy_family(df: pd.DataFrame, symbol: str, event_type: str, **params: Any) -> tuple[pd.DataFrame, dict[str, Any]]:
    events = detect_canonical_proxy_family(df, symbol, event_type, **params)
    market = df[['timestamp', 'close']].copy() if not df.empty and 'close' in df.columns else None
    analyzer_results = run_analyzer_suite(events, market=market) if not events.empty else {}
    return events, analyzer_results
