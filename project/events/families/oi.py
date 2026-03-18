from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from project.events.detectors.threshold import ThresholdDetector
from project.events.shared import EVENT_COLUMNS, emit_event, format_event_id
from project.events.sparsify import sparsify_mask
from project.features.context_guards import state_at_least, state_at_most
from project.features.rolling_thresholds import lagged_rolling_quantile
from project.research.analyzers import run_analyzer_suite


class BaseOIShockDetector(ThresholdDetector):
    """Base logic for Open Interest (OI) shock detectors."""
    required_columns = ('timestamp', 'oi_notional', 'close')
    timeframe_minutes = 5
    default_severity = 'moderate'

    def compute_direction(self, idx: int, features: dict[str, pd.Series], **params: Any) -> str:
        del params
        ret = features['close_ret'].iloc[idx]
        return 'up' if ret > 0 else 'down' if ret < 0 else 'non_directional'

    def compute_metadata(self, idx: int, features: dict[str, pd.Series], **params: Any) -> dict[str, Any]:
        del params
        return {
            'oi_z': float(np.nan_to_num(features['oi_z'].iloc[idx], nan=0.0)),
            'oi_pct_change': float(np.nan_to_num(features['oi_pct_change'].iloc[idx], nan=0.0)),
            'close_ret': float(np.nan_to_num(features['close_ret'].iloc[idx], nan=0.0)),
        }


class OISpikePositiveDetector(BaseOIShockDetector):
    """Detects positive OI spikes associated with upward price movement."""
    event_type = 'OI_SPIKE_POSITIVE'

    def prepare_features(self, df: pd.DataFrame, **params: Any) -> dict[str, pd.Series]:
        window = int(params.get('oi_window', 96))
        min_periods = int(params.get('min_periods', max(24, window // 4)))
        oi = pd.to_numeric(df['oi_notional'], errors='coerce').replace(0.0, np.nan).astype(float)
        oi_log_delta = np.log(oi).diff()
        baseline = oi_log_delta.shift(1)
        mean = baseline.rolling(window=window, min_periods=min_periods).mean()
        std = baseline.rolling(window=window, min_periods=min_periods).std()
        oi_z = (oi_log_delta - mean) / std.where(std > 0.0, 1e-12)
        close_ret = pd.to_numeric(df['close'], errors='coerce').astype(float).pct_change(1)
        spike_z_th = float(params.get('spike_z_th', params.get('threshold', 2.5)))
        mask = (oi_z >= spike_z_th) & (close_ret > 0)
        canonical_oi_accel = state_at_least(
            df,
            'ms_oi_state',
            2.0,
            min_confidence=float(params.get('context_min_confidence', 0.55)),
            max_entropy=float(params.get('context_max_entropy', 0.90)),
        )
        
        return {
            'oi_z': oi_z, 
            'close_ret': close_ret, 
            'oi_pct_change': oi.pct_change(1),
            'canonical_oi_accel': canonical_oi_accel,
            'mask': mask.fillna(False)
        }

    def compute_raw_mask(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        return (features['mask'] & features['canonical_oi_accel'].fillna(False)).fillna(False)

    def compute_intensity(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        return features['oi_z'].abs()


class OISpikeNegativeDetector(BaseOIShockDetector):
    """Detects positive OI spikes associated with downward price movement."""
    event_type = 'OI_SPIKE_NEGATIVE'

    def prepare_features(self, df: pd.DataFrame, **params: Any) -> dict[str, pd.Series]:
        window = int(params.get('oi_window', 96))
        min_periods = int(params.get('min_periods', max(24, window // 4)))
        oi = pd.to_numeric(df['oi_notional'], errors='coerce').replace(0.0, np.nan).astype(float)
        oi_log_delta = np.log(oi).diff()
        baseline = oi_log_delta.shift(1)
        mean = baseline.rolling(window=window, min_periods=min_periods).mean()
        std = baseline.rolling(window=window, min_periods=min_periods).std()
        oi_z = (oi_log_delta - mean) / std.where(std > 0.0, 1e-12)
        close_ret = pd.to_numeric(df['close'], errors='coerce').astype(float).pct_change(1)
        spike_z_th = float(params.get('spike_z_th', params.get('threshold', 2.5)))
        mask = (oi_z >= spike_z_th) & (close_ret < 0)
        canonical_oi_accel = state_at_least(
            df,
            'ms_oi_state',
            2.0,
            min_confidence=float(params.get('context_min_confidence', 0.55)),
            max_entropy=float(params.get('context_max_entropy', 0.90)),
        )
        
        return {
            'oi_z': oi_z, 
            'close_ret': close_ret, 
            'oi_pct_change': oi.pct_change(1),
            'canonical_oi_accel': canonical_oi_accel,
            'mask': mask.fillna(False)
        }

    def compute_raw_mask(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        return (features['mask'] & features['canonical_oi_accel'].fillna(False)).fillna(False)

    def compute_intensity(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        return features['oi_z'].abs()


class OIFlushDetector(BaseOIShockDetector):
    """Detects rapid declines in Open Interest (forced liquidations or deleveraging)."""
    event_type = 'OI_FLUSH'

    def prepare_features(self, df: pd.DataFrame, **params: Any) -> dict[str, pd.Series]:
        window = int(params.get('oi_window', 96))
        min_periods = int(params.get('min_periods', max(24, window // 4)))
        oi = pd.to_numeric(df['oi_notional'], errors='coerce').replace(0.0, np.nan).astype(float)
        oi_pct_change = oi.pct_change(1)
        close_ret = pd.to_numeric(df['close'], errors='coerce').astype(float).pct_change(1)
        oi_log_delta = np.log(oi).diff()
        baseline = oi_log_delta.shift(1)
        mean = baseline.rolling(window=window, min_periods=min_periods).mean()
        std = baseline.rolling(window=window, min_periods=min_periods).std()
        oi_z = (oi_log_delta - mean) / std.where(std > 0.0, 1e-12)
        
        flush_pct_th = float(params.get('flush_pct_th', -0.005))
        mask = (oi_pct_change <= flush_pct_th)
        canonical_oi_decel = state_at_most(
            df,
            'ms_oi_state',
            0.0,
            min_confidence=float(params.get('context_min_confidence', 0.55)),
            max_entropy=float(params.get('context_max_entropy', 0.90)),
        )
        
        return {
            'oi_z': oi_z, 
            'close_ret': close_ret, 
            'oi_pct_change': oi_pct_change,
            'canonical_oi_decel': canonical_oi_decel,
            'mask': mask.fillna(False)
        }

    def compute_raw_mask(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        return (features['mask'] & features['canonical_oi_decel'].fillna(False)).fillna(False)

    def compute_intensity(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        return features['oi_pct_change'].abs() * 100.0


class OIShockDetector(BaseOIShockDetector):
    """Legacy polymorphic OI shock detector for backward compatibility."""
    event_type = 'OI_SPIKE_POSITIVE'
    signal_column = 'oi_z'
    threshold = 2.5

    def prepare_features(self, df: pd.DataFrame, **params: Any) -> dict[str, pd.Series]:
        pos = OISpikePositiveDetector().prepare_features(df, **params)
        neg = OISpikeNegativeDetector().prepare_features(df, **params)
        flush = OIFlushDetector().prepare_features(df, **params)
        
        return {
            'oi_z': pos['oi_z'], 
            'close_ret': pos['close_ret'], 
            'oi_pct_change': pos['oi_pct_change'],
            'is_spike_pos': pos['mask'],
            'is_spike_neg': neg['mask'],
            'is_flush': flush['mask']
        }

    def compute_raw_mask(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        return (features['is_spike_pos'] | features['is_spike_neg'] | features['is_flush']).fillna(False)

    def compute_event_type(self, idx: int, features: dict[str, pd.Series]) -> str:
        if features['is_spike_pos'].iloc[idx]: return 'OI_SPIKE_POSITIVE'
        if features['is_spike_neg'].iloc[idx]: return 'OI_SPIKE_NEGATIVE'
        return 'OI_FLUSH'

    def compute_intensity(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        is_flush = features['is_flush'].fillna(False)
        oi_z_abs = features['oi_z'].abs()
        flush_intensity = features['oi_pct_change'].abs() * 100.0
        return np.where(is_flush, flush_intensity, oi_z_abs)


class DeleveragingWaveDetector(ThresholdDetector):
    event_type = 'DELEVERAGING_WAVE'
    required_columns = ('timestamp', 'oi_delta_1h', 'rv_96')

    def prepare_features(self, df: pd.DataFrame, **params: Any) -> dict[str, pd.Series]:
        oi_delta_1h = pd.to_numeric(df['oi_delta_1h'], errors='coerce').astype(float)
        rv_96 = pd.to_numeric(df['rv_96'], errors='coerce').ffill().astype(float)
        from project.events.thresholding import rolling_mean_std_zscore
        rv_z = rolling_mean_std_zscore(rv_96, window=288)
        
        oi_q01 = lagged_rolling_quantile(oi_delta_1h, window=2880, quantile=0.01, min_periods=288)
        rv_q90 = lagged_rolling_quantile(rv_z, window=2880, quantile=0.90, min_periods=288)
        canonical_oi_decel = state_at_most(
            df,
            'ms_oi_state',
            0.0,
            min_confidence=float(params.get('context_min_confidence', 0.55)),
            max_entropy=float(params.get('context_max_entropy', 0.90)),
        )
        canonical_high_vol = state_at_least(
            df,
            'ms_vol_state',
            2.0,
            min_confidence=float(params.get('context_min_confidence', 0.55)),
            max_entropy=float(params.get('context_max_entropy', 0.90)),
        )
        return {
            'oi_delta_1h': oi_delta_1h,
            'rv_z': rv_z,
            'oi_q01': oi_q01,
            'rv_q90': rv_q90,
            'canonical_oi_decel': canonical_oi_decel,
            'canonical_high_vol': canonical_high_vol,
        }

    def compute_raw_mask(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        return (
            features['canonical_oi_decel'].fillna(False)
            & features['canonical_high_vol'].fillna(False)
            & (features['oi_delta_1h'] <= features['oi_q01']).fillna(False)
            & (features['rv_z'] >= features['rv_q90']).fillna(False)
        ).fillna(False)

    def compute_intensity(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        return features['rv_z'].abs().fillna(0.0)

from project.events.detectors.registry import register_detector

_DETECTORS = {
    'OI_SPIKE_POSITIVE': OISpikePositiveDetector,
    'OI_SPIKE_NEGATIVE': OISpikeNegativeDetector,
    'OI_FLUSH': OIFlushDetector,
    'DELEVERAGING_WAVE': DeleveragingWaveDetector,
}

for et, cls in _DETECTORS.items():
    register_detector(et, cls)

def detect_oi_family(df: pd.DataFrame, symbol: str, event_type: str = 'OI_SPIKE_POSITIVE', **params: Any) -> pd.DataFrame:
    detector_cls = _DETECTORS.get(event_type, OIShockDetector)
    return detector_cls().detect(df, symbol=symbol, **params)


def analyze_oi_family(df: pd.DataFrame, symbol: str, event_type: str = 'OI_SPIKE_POSITIVE', **params: Any) -> tuple[pd.DataFrame, dict[str, Any]]:
    events = detect_oi_family(df, symbol, event_type=event_type, **params)
    market = df[['timestamp', 'close']].copy() if not df.empty and 'close' in df.columns else None
    analyzer_results = run_analyzer_suite(events, market=market) if not events.empty else {}
    return events, analyzer_results
