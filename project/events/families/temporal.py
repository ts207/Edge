from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from project.events.detectors.threshold import ThresholdDetector
from project.features.context_guards import state_at_least
from project.features.rolling_thresholds import lagged_rolling_quantile
from project.events.shared import EVENT_COLUMNS, emit_event, format_event_id
from project.research.analyzers import run_analyzer_suite
from project.spec_registry import load_event_spec

class SessionOpenDetector(ThresholdDetector):
    event_type = 'SESSION_OPEN_EVENT'
    required_columns = ('timestamp',)
    default_hours_utc = (0, 8, 13)
    default_intensity_scale = 60.0

    def prepare_features(self, df: pd.DataFrame, **params: Any) -> dict[str, pd.Series]:
        ts = pd.to_datetime(df['timestamp'], utc=True, errors='coerce')
        return {'ts': ts}

    def compute_raw_mask(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        ts = features['ts']
        spec = load_event_spec(self.event_type)
        spec_params = spec.get('parameters', {}) if isinstance(spec, dict) else {}
        hours = spec_params.get('hours_utc', list(self.default_hours_utc))
        return ((ts.dt.minute == 0) & ts.dt.hour.isin(hours)).fillna(False)

    def compute_intensity(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        ts = features['ts']
        mins = (ts.dt.minute.fillna(59)).astype(float)
        
        intensity_scale = float(params.get('intensity_scale', self.default_intensity_scale))
        return (intensity_scale - mins).clip(lower=0.0)

class SessionCloseDetector(ThresholdDetector):
    event_type = 'SESSION_CLOSE_EVENT'
    required_columns = ('timestamp',)
    default_hours_utc = (7, 12, 23)
    default_intensity_scale = 60.0

    def prepare_features(self, df: pd.DataFrame, **params: Any) -> dict[str, pd.Series]:
        ts = pd.to_datetime(df['timestamp'], utc=True, errors='coerce')
        return {'ts': ts}

    def compute_raw_mask(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        ts = features['ts']
        spec = load_event_spec(self.event_type)
        spec_params = spec.get('parameters', {}) if isinstance(spec, dict) else {}
        hours = spec_params.get('hours_utc', list(self.default_hours_utc))
        return ((ts.dt.minute >= 55) & ts.dt.hour.isin(hours)).fillna(False)

    def compute_intensity(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        ts = features['ts']
        mins_to_close = (59 - ts.dt.minute.fillna(0)).abs().astype(float)
        
        intensity_scale = float(params.get('intensity_scale', self.default_intensity_scale))
        return (intensity_scale - mins_to_close).clip(lower=0.0)

class FundingTimestampDetector(ThresholdDetector):
    event_type = 'FUNDING_TIMESTAMP_EVENT'
    required_columns = ('timestamp',)

    def prepare_features(self, df: pd.DataFrame, **params: Any) -> dict[str, pd.Series]:
        ts = pd.to_datetime(df['timestamp'], utc=True, errors='coerce')
        funding = pd.to_numeric(df.get('funding_rate_scaled'), errors='coerce') if 'funding_rate_scaled' in df.columns else pd.Series(0.0, index=df.index)
        return {'ts': ts, 'funding': funding}

    def compute_raw_mask(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        ts = features['ts']
        spec = load_event_spec(self.event_type)
        spec_params = spec.get('parameters', {}) if isinstance(spec, dict) else {}
        hours = spec_params.get('hours_utc', [0, 8, 16])
        return ((ts.dt.minute == 0) & ts.dt.hour.isin(hours)).fillna(False)

    def compute_intensity(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        return features['funding'].abs().fillna(0.0)

class ScheduledNewsDetector(ThresholdDetector):
    event_type = 'SCHEDULED_NEWS_WINDOW_EVENT'
    required_columns = ('timestamp',)

    def prepare_features(self, df: pd.DataFrame, **params: Any) -> dict[str, pd.Series]:
        ts = pd.to_datetime(df['timestamp'], utc=True, errors='coerce')
        news_mask = pd.Series(False, index=df.index, dtype=bool)
        for col in ['scheduled_news_event', 'news_event', 'has_news_event', 'econ_news_event', 'macro_news_event', 'calendar_event', 'scheduled_event']:
            if col in df.columns:
                news_mask = df[col].fillna(False).astype(bool)
                break
        
        # News intensity logic
        news_intensity_cols = [c for c in ["news_intensity", "calendar_importance", "event_importance", "headline_count"] if c in df.columns]
        if news_intensity_cols:
            intensity = sum(pd.to_numeric(df[c], errors="coerce").fillna(0.0).abs() for c in news_intensity_cols)
        else:
            intensity = pd.Series(1.0, index=df.index)
            
        return {'ts': ts, 'news_mask_col': news_mask, 'intensity': intensity}

    def compute_raw_mask(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        # Always evaluate spec windows — do not short-circuit on column presence.
        ts = features['ts']
        hh = ts.dt.hour
        mm = ts.dt.minute
        spec = load_event_spec(self.event_type)
        spec_params = spec.get('parameters', {}) if isinstance(spec, dict) else {}
        windows = spec_params.get('windows_utc', [])
        spec_mask = pd.Series(False, index=df.index, dtype=bool)
        for win in windows:
            if not isinstance(win, dict): continue
            hour = int(win.get('hour', -1))
            m_start = int(win.get('minute_start', 25))
            m_end = int(win.get('minute_end', 35))
            if hour != -1:
                spec_mask = spec_mask | ((hh == hour) & mm.between(m_start, m_end))
        # Merge column-based mask with spec windows via OR.
        return (spec_mask | features['news_mask_col']).fillna(False)

    def compute_intensity(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        return features['intensity']

class SpreadRegimeWideningDetector(ThresholdDetector):
    """Detects sustained spread widening with positive regime acceleration."""
    event_type = 'SPREAD_REGIME_WIDENING_EVENT'
    required_columns = ('timestamp', 'volume')
    min_spacing = 48

    def prepare_features(self, df: pd.DataFrame, **params: Any) -> dict[str, pd.Series]:
        if 'spread_zscore' in df.columns:
            spread = pd.to_numeric(df['spread_zscore'], errors='coerce').abs().astype(float)
        elif 'spread_bps' in df.columns:
            spread = pd.to_numeric(df['spread_bps'], errors='coerce').abs().astype(float)
        else:
            spread = pd.Series(0.0, index=df.index)
        volume = pd.to_numeric(df['volume'], errors='coerce').astype(float)
        trend_window = int(params.get('trend_window', 24))
        lookback_window = int(params.get('lookback_window', 2880))
        min_periods = int(params.get('min_periods', 288))
        low_volume_quantile = float(params.get('low_volume_quantile', 0.25))
        
        spread_avg = spread.rolling(trend_window, min_periods=max(4, trend_window // 4)).mean()
        spread_q85 = lagged_rolling_quantile(
            spread,
            window=lookback_window,
            quantile=0.85,
            min_periods=min_periods,
        )
        accel = spread_avg - spread_avg.shift(trend_window // 2 or 1)
        accel_q75 = lagged_rolling_quantile(
            accel.abs(),
            window=lookback_window,
            quantile=0.75,
            min_periods=min_periods,
        )
        volume_low_q = lagged_rolling_quantile(
            volume,
            window=lookback_window,
            quantile=low_volume_quantile,
            min_periods=min_periods,
        )
        history_ready = spread_q85.notna() & accel_q75.notna() & volume_low_q.notna()
        canonical_wide = state_at_least(
            df,
            'ms_spread_state',
            1.0,
            min_confidence=float(params.get('context_min_confidence', 0.55)),
            max_entropy=float(params.get('context_max_entropy', 0.90)),
        )
        return {
            'spread': spread,
            'spread_avg': spread_avg,
            'spread_q85': spread_q85,
            'accel': accel,
            'accel_q75': accel_q75,
            'volume': volume,
            'volume_low_q': volume_low_q,
            'history_ready': history_ready,
            'canonical_wide': canonical_wide,
        }

    def compute_raw_mask(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        del df, params
        return (
            features['history_ready']
            & features['canonical_wide']
            & (features['spread_avg'] >= features['spread_q85']).fillna(False)
            & (features['accel'] > 0).fillna(False)
            & (features['accel'] >= features['accel_q75']).fillna(False)
            & (features['volume'] <= features['volume_low_q']).fillna(False)
        ).fillna(False)

    def compute_intensity(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        return (features['spread_avg'].fillna(0.0) * (1.0 + features['accel'].clip(lower=0.0).fillna(0.0))).clip(lower=0.0)


class SlippageSpikeDetector(ThresholdDetector):
    """Detects abnormal execution slippage relative to prevailing spread conditions."""
    event_type = 'SLIPPAGE_SPIKE_EVENT'
    required_columns = ('timestamp',)

    def prepare_features(self, df: pd.DataFrame, **params: Any) -> dict[str, pd.Series]:
        if 'slippage_bps' in df.columns:
            slippage = pd.to_numeric(df['slippage_bps'], errors='coerce').abs().astype(float)
        elif 'spread_zscore' in df.columns:
            slippage = pd.to_numeric(df['spread_zscore'], errors='coerce').abs().astype(float)
        else:
            slippage = pd.Series(0.0, index=df.index)
        spread_proxy = pd.to_numeric(df.get('spread_bps', df.get('spread_zscore', pd.Series(0.0, index=df.index))), errors='coerce').abs().astype(float)
        
        lookback_window = int(params.get('lookback_window', 2880))
        min_periods = int(params.get('min_periods', 288))
        
        slip_q99 = lagged_rolling_quantile(
            slippage,
            window=lookback_window,
            quantile=0.99,
            min_periods=min_periods,
        )
        slippage_ratio = slippage / spread_proxy.replace(0.0, np.nan)
        ratio_q90 = lagged_rolling_quantile(
            slippage_ratio,
            window=lookback_window,
            quantile=0.90,
            min_periods=min_periods,
        )
        return {'slippage': slippage, 'slip_q99': slip_q99, 'slippage_ratio': slippage_ratio, 'ratio_q90': ratio_q90}

    def compute_raw_mask(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        return (
            (features['slippage'] >= features['slip_q99']).fillna(False)
            & (features['slippage_ratio'] >= features['ratio_q90']).fillna(False)
        ).fillna(False)

    def compute_intensity(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        return (features['slippage'].fillna(0.0) * features['slippage_ratio'].fillna(0.0)).clip(lower=0.0)


class FeeRegimeChangeDetector(ThresholdDetector):
    """Detects discrete fee regime steps that persist beyond one bar."""
    event_type = 'FEE_REGIME_CHANGE_EVENT'
    required_columns = ('timestamp',)
    causal = False

    def prepare_features(self, df: pd.DataFrame, **params: Any) -> dict[str, pd.Series]:
        if 'fee_bps' in df.columns:
            fee = pd.to_numeric(df['fee_bps'], errors='coerce').astype(float)
            fee_change = fee.diff(1).abs()
            fee_baseline = fee.rolling(int(params.get('baseline_window', 96)), min_periods=12).median().shift(1)
            
            lookback_window = int(params.get('lookback_window', 2880))
            min_periods = int(params.get('min_periods', 288))
            
            fee_q95 = lagged_rolling_quantile(
                fee_change,
                window=lookback_window,
                quantile=0.95,
                min_periods=min_periods,
            )
            persistent_shift = (
                fee.shift(2).notna()
                & (fee == fee.shift(1))
                & (fee != fee.shift(2))
            )
        else:
            fee_change = pd.Series(0.0, index=df.index)
            fee_baseline = pd.Series(0.0, index=df.index)
            fee_q95 = pd.Series(np.inf, index=df.index)
            persistent_shift = pd.Series(False, index=df.index)
        baseline_delta = (pd.to_numeric(df.get('fee_bps', pd.Series(0.0, index=df.index)), errors='coerce') - fee_baseline).abs()
        return {
            'fee_change': fee_change,
            'fee_q95': fee_q95,
            'persistent_shift': persistent_shift.fillna(False),
            'baseline_delta': baseline_delta.fillna(0.0),
        }

    def compute_raw_mask(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        return (
            (features['fee_change'] >= features['fee_q95']).fillna(False)
            & features['persistent_shift']
        ).fillna(False)

    def compute_intensity(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        return (features['fee_change'].fillna(0.0) + features['baseline_delta'].fillna(0.0)).clip(lower=0.0)


class CopulaPairsTradingDetector(ThresholdDetector):
    """Detects mean-reversion pairs dislocations with elevated spread z-score and reversal onset."""
    event_type = 'COPULA_PAIRS_TRADING'
    required_columns = ('timestamp', 'close')

    def prepare_features(self, df: pd.DataFrame, **params: Any) -> dict[str, pd.Series]:
        close = pd.to_numeric(df['close'], errors='coerce').astype(float)
        ret = close.pct_change(1)
        zscore_col = 'pairs_zscore' if 'pairs_zscore' in df.columns else None
        
        trend_window = int(params.get('trend_window', 96))
        
        if zscore_col:
            zscore = pd.to_numeric(df[zscore_col], errors='coerce').astype(float)
        else:
            zscore = (ret - ret.rolling(trend_window, min_periods=12).mean()) / (ret.rolling(trend_window, min_periods=12).std().replace(0.0, np.nan))
        zscore_abs = zscore.abs()
        zscore_delta = zscore.diff(1)
        mean_reversion = ((zscore.shift(1) > 0) & (zscore_delta < 0)) | ((zscore.shift(1) < 0) & (zscore_delta > 0))
        spread_proxy = pd.to_numeric(df.get('spread_zscore', pd.Series(0.0, index=df.index)), errors='coerce').abs().astype(float)
        
        lookback_window = int(params.get('lookback_window', 2880))
        min_periods = int(params.get('min_periods', 288))
        
        z_q95 = lagged_rolling_quantile(
            zscore_abs,
            window=lookback_window,
            quantile=0.95,
            min_periods=min_periods,
        )
        spread_q75 = lagged_rolling_quantile(
            spread_proxy,
            window=lookback_window,
            quantile=0.75,
            min_periods=min_periods,
        )
        return {
            'zscore': zscore,
            'zscore_abs': zscore_abs,
            'z_q95': z_q95,
            'mean_reversion': mean_reversion.fillna(False),
            'spread_proxy': spread_proxy,
            'spread_q75': spread_q75,
        }

    def compute_raw_mask(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        return (
            (features['zscore_abs'] >= features['z_q95']).fillna(False)
            & features['mean_reversion']
            & (features['spread_proxy'] >= features['spread_q75']).fillna(False)
        ).fillna(False)

    def compute_intensity(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        return (features['zscore_abs'].fillna(0.0) * (1.0 + features['spread_proxy'].fillna(0.0))).clip(lower=0.0)

    def compute_direction(self, idx: int, features: dict[str, pd.Series], **params: Any) -> str:
        del params
        zscore = float(features['zscore'].iloc[idx] if not pd.isna(features['zscore'].iloc[idx]) else 0.0)
        return 'down' if zscore > 0 else 'up' if zscore < 0 else 'non_directional'


from project.events.detectors.registry import get_detector, register_family_detectors

_DETECTORS = {
    'SESSION_OPEN_EVENT': SessionOpenDetector,
    'SESSION_CLOSE_EVENT': SessionCloseDetector,
    'FUNDING_TIMESTAMP_EVENT': FundingTimestampDetector,
    'SCHEDULED_NEWS_WINDOW_EVENT': ScheduledNewsDetector,
    'SPREAD_REGIME_WIDENING_EVENT': SpreadRegimeWideningDetector,
    'SLIPPAGE_SPIKE_EVENT': SlippageSpikeDetector,
    'FEE_REGIME_CHANGE_EVENT': FeeRegimeChangeDetector,
    'COPULA_PAIRS_TRADING': CopulaPairsTradingDetector,
}

register_family_detectors(_DETECTORS)

def detect_temporal_family(df: pd.DataFrame, symbol: str, event_type: str = 'SESSION_OPEN_EVENT', **params: Any) -> pd.DataFrame:
    detector = get_detector(event_type)
    if detector is None:
        raise ValueError(f"Unknown temporal event type: {event_type}")
    return detector.detect(df, symbol=symbol, **params)

def analyze_temporal_family(df: pd.DataFrame, symbol: str, event_type: str = 'SESSION_OPEN_EVENT', **params: Any) -> tuple[pd.DataFrame, dict[str, Any]]:
    events = detect_temporal_family(df, symbol, event_type=event_type, **params)
    market = df[['timestamp', 'close']].copy() if not df.empty and 'close' in df.columns else None
    analyzer_results = run_analyzer_suite(events, market=market) if not events.empty else {}
    return events, analyzer_results
