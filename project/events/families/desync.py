from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from project.events.detectors.threshold import ThresholdDetector
from project.events.detectors.composite import CompositeDetector
from project.events.shared import EVENT_COLUMNS, emit_event, format_event_id
from project.events.thresholding import rolling_mean_std_zscore
from project.research.analyzers import run_analyzer_suite

def past_quantile(series: pd.Series, q: float, window: int = 2880) -> pd.Series:
    return series.rolling(window, min_periods=window//10).quantile(q).shift(1)

class IndexComponentDivergenceDetector(CompositeDetector):
    event_type = 'INDEX_COMPONENT_DIVERGENCE'
    required_columns = ('timestamp', 'close')

    def prepare_features(self, df: pd.DataFrame, **params: Any) -> dict[str, pd.Series]:
        close = df['close']
        ret_abs = close.pct_change(1).abs()
        basis_z = df.get('basis_zscore', df.get('cross_exchange_spread_z', pd.Series(0.0, index=df.index)))
        basis_abs = basis_z.abs()
        basis_q93 = past_quantile(basis_abs, 0.93)
        ret_q75 = past_quantile(ret_abs, 0.75)
        return {'basis_abs': basis_abs, 'ret_abs': ret_abs, 'basis_q93': basis_q93, 'ret_q75': ret_q75}

    def compute_raw_mask(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        return ((features['basis_abs'] >= features['basis_q93']).fillna(False) & (features['ret_abs'] >= features['ret_q75']).fillna(False)).fillna(False)

    def compute_intensity(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        return features['basis_abs']

class LeadLagBreakDetector(ThresholdDetector):
    event_type = 'LEAD_LAG_BREAK'
    required_columns = ('timestamp',)

    def prepare_features(self, df: pd.DataFrame, **params: Any) -> dict[str, pd.Series]:
        basis_z = df.get('basis_zscore', df.get('cross_exchange_spread_z', pd.Series(0.0, index=df.index)))
        basis_diff_abs = basis_z.diff().abs()
        basis_diff_q99 = past_quantile(basis_diff_abs, 0.99)
        return {'basis_diff_abs': basis_diff_abs, 'basis_diff_q99': basis_diff_q99}

    def compute_raw_mask(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        return (features['basis_diff_abs'] >= features['basis_diff_q99']).fillna(False)

    def compute_intensity(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        return features['basis_diff_abs']

from project.events.detectors.registry import register_detector

_DETECTORS = {
    'INDEX_COMPONENT_DIVERGENCE': IndexComponentDivergenceDetector,
    'LEAD_LAG_BREAK': LeadLagBreakDetector,
}

for et, cls in _DETECTORS.items():
    register_detector(et, cls)

def detect_desync_family(df: pd.DataFrame, symbol: str, event_type: str = 'INDEX_COMPONENT_DIVERGENCE', **params: Any) -> pd.DataFrame:
    detector_cls = _DETECTORS.get(event_type)
    if detector_cls is None:
        # Fallback to BasisDislocationDetector if it's BASIS related
        from project.events.families.basis import BasisDislocationDetector
        if event_type in {'BASIS_DISLOC', 'SPOT_PERP_BASIS_SHOCK'}:
            # Map columns for BasisDislocationDetector
            work = df.copy()
            if 'close' in work.columns and 'close_perp' not in work.columns:
                work['close_perp'] = work['close']
            if 'spot_close' in work.columns and 'close_spot' not in work.columns:
                work['close_spot'] = work['spot_close']
            if 'close_spot' not in work.columns:
                # Last resort fallback
                work['close_spot'] = work['close'] # Should not happen if canonical feature building is correct
            return BasisDislocationDetector().detect(work, symbol=symbol, **params)
        raise ValueError(f"Unknown desync event type: {event_type}")
    return detector_cls().detect(df, symbol=symbol, **params)

def analyze_desync_family(df: pd.DataFrame, symbol: str, event_type: str = 'INDEX_COMPONENT_DIVERGENCE', **params: Any) -> tuple[pd.DataFrame, dict[str, Any]]:
    events = detect_desync_family(df, symbol, event_type=event_type, **params)
    market = df[['timestamp', 'close']].copy() if not df.empty and 'close' in df.columns else None
    analyzer_results = run_analyzer_suite(events, market=market) if not events.empty else {}
    return events, analyzer_results
