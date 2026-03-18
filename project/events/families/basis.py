from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from project.events.detectors.dislocation import DislocationDetector
from project.events.shared import EVENT_COLUMNS, emit_event, format_event_id
from project.events.sparsify import sparsify_mask
from project.events.thresholding import rolling_robust_zscore, dynamic_quantile_floor, rolling_vol_regime_factor
from project.features.context_guards import state_at_least
from project.research.analyzers import run_analyzer_suite


class BasisDislocationDetector(DislocationDetector):
    event_type = 'BASIS_DISLOC'
    required_columns = ('timestamp', 'close_perp', 'close_spot')
    signal_column = 'basis_zscore'
    threshold = 3.5
    min_spacing = 24
    timeframe_minutes = 5
    default_severity = 'moderate'

    def prepare_features(self, df: pd.DataFrame, **params: Any) -> dict[str, pd.Series]:
        lookback_window = int(params.get('lookback_window', params.get('basis_lookback', 288)))
        min_periods = int(params.get('min_periods', max(24, lookback_window // 10)))
        close_perp = pd.to_numeric(df['close_perp'], errors='coerce')
        close_spot = pd.to_numeric(df['close_spot'], errors='coerce').replace(0.0, np.nan)
        basis_bps = (close_perp - close_spot) / close_spot * 10000.0
        basis_zscore = rolling_robust_zscore(basis_bps, window=lookback_window, min_periods=min_periods, shift=1)
        
        logret = np.log(close_perp / close_perp.shift(1))
        rv_proxy = logret.rolling(96, min_periods=24).std()
        vol_factor = rolling_vol_regime_factor(rv_proxy, window=2880)
        
        # Adaptive threshold based on rolling quantile of absolute Z-score
        dynamic_th = dynamic_quantile_floor(
            basis_zscore.abs(), 
            window=2880, 
            quantile=float(params.get('anchor_quantile', params.get('threshold_quantile', 0.99))),
            floor=float(params.get('z_threshold', params.get('threshold', self.threshold))),
        )
        # Apply vol factor if requested
        if bool(params.get('vol_scaled_threshold', False)):
            dynamic_th = dynamic_th * vol_factor.clip(0.8, 1.5)

        return {
            'basis_bps': basis_bps,
            'basis_zscore': basis_zscore,
            'rv_proxy': rv_proxy,
            'vol_factor': vol_factor,
            'dynamic_th': dynamic_th,
            'vol_regime': vol_factor.map(lambda x: 'high' if x > 1.2 else 'low' if x < 0.8 else 'mid'),
        }

    def compute_threshold(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        return features['dynamic_th']

    def compute_intensity(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        return pd.to_numeric(features['basis_zscore'], errors='coerce').abs()

    def event_indices(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> list[int]:
        mask = self.compute_raw_mask(df, features=features, **params)
        mask = mask.astype("boolean")
        mask = (mask & ~mask.shift(1, fill_value=False)).astype(bool)
        spacing = int(params.get('cooldown_bars', params.get('min_spacing', self.min_spacing)))
        return sparsify_mask(mask, min_spacing=spacing)

    def detect(self, df: pd.DataFrame, *, symbol: str, **params: Any) -> pd.DataFrame:
        self.check_required_columns(df)
        if df.empty:
            return pd.DataFrame(columns=EVENT_COLUMNS)
        features = self.prepare_features(df, **params)
        intensity = self.compute_intensity(df, features=features, **params)
        rows: list[dict[str, Any]] = []
        for sub_idx, idx in enumerate(self.event_indices(df, features=features, **params)):
            ts = pd.to_datetime(df.at[idx, 'timestamp'], utc=True, errors='coerce')
            if pd.isna(ts): continue
            z = float(pd.to_numeric(features['basis_zscore'], errors='coerce').iloc[idx])
            basis_bps = float(pd.to_numeric(features['basis_bps'], errors='coerce').iloc[idx])
            severity = 'extreme' if abs(z) >= 5.0 else 'major' if abs(z) >= 4.0 else 'moderate'
            rows.append(
                emit_event(
                    event_type=self.event_type,
                    symbol=symbol,
                    event_id=format_event_id(self.event_type, symbol, int(idx), sub_idx),
                    eval_bar_ts=ts,
                    intensity=float(np.nan_to_num(intensity.iloc[idx], nan=1.0)),
                    severity=severity,
                    timeframe_minutes=self.timeframe_minutes,
                    direction='up' if basis_bps >= 0 else 'down',
                    causal=self.causal,
                    metadata={
                        'event_idx': int(idx),
                        'basis_bps': basis_bps,
                        'basis_zscore': z,
                        'vol_regime': str(features['vol_regime'].iloc[idx]),
                    },
                )
            )
        events = pd.DataFrame(rows) if rows else pd.DataFrame(columns=EVENT_COLUMNS)
        if not events.empty:
            events['timestamp'] = events['signal_ts']
            if 'duration_bars' not in events.columns:
                events['duration_bars'] = 1
        return events


class CrossVenueDesyncDetector(BasisDislocationDetector):
    event_type = 'CROSS_VENUE_DESYNC'
    required_columns = ('timestamp', 'close_perp', 'close_spot')

    def prepare_features(self, df: pd.DataFrame, **params: Any) -> dict[str, pd.Series]:
        # Accept older column aliases, but prefer the canonical dual-market feature names.
        work = df.rename(columns={'close': 'close_spot', 'perp_close': 'close_perp'})
        features = super().prepare_features(work, **params)
        persistence_bars = int(params.get('persistence_bars', 2))
        features['persistent_shock'] = (
            features['basis_zscore'].abs()
            .rolling(persistence_bars, min_periods=persistence_bars)
            .min()
        )
        return features

    def compute_raw_mask(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        threshold = self.compute_threshold(df, features=features, **params)
        persistent = (features['persistent_shock'] >= threshold).fillna(False)
        return persistent


class FndDislocDetector(BasisDislocationDetector):
    event_type = 'FND_DISLOC'

    def prepare_features(self, df: pd.DataFrame, **params: Any) -> dict[str, pd.Series]:
        features = super().prepare_features(df, **params)
        if 'funding_rate_scaled' not in df.columns:
            raise ValueError("FND_DISLOC requires canonical funding_rate_scaled")
        funding = pd.to_numeric(df['funding_rate_scaled'], errors='coerce')
        funding_abs = funding.abs()
        threshold_bps = float(params.get('threshold_bps', 2.0))
        funding_q95 = dynamic_quantile_floor(
            funding_abs,
            window=2880,
            quantile=float(params.get('funding_quantile', 0.90)),
            floor=threshold_bps / 10_000.0,
        )
        features.update(
            {
                'funding_rate_scaled': funding,
                'funding_abs': funding_abs,
                'funding_q95': funding_q95,
                'funding_sign': np.sign(funding.fillna(0.0)),
                'canonical_funding_extreme': state_at_least(
                    df,
                    'ms_funding_state',
                    2.0,
                    min_confidence=float(params.get('context_min_confidence', 0.55)),
                    max_entropy=float(params.get('context_max_entropy', 0.90)),
                ),
            }
        )
        return features

    def compute_raw_mask(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        basis_mask = super().compute_raw_mask(df, features=features, **params)
        funding_extreme = (
            (features['funding_abs'] >= features['funding_q95']).fillna(False)
            & features['canonical_funding_extreme'].fillna(False)
        )
        
        # Allow alignment within a window (e.g. 3 bars) to improve recall
        alignment_window = int(params.get('alignment_window', 5))
        basis_active = basis_mask.rolling(window=alignment_window, min_periods=1).max().astype(bool)
        
        sign_align = (
            np.sign(features['basis_bps'].fillna(0.0)) == features['funding_sign'].fillna(0.0)
        )
        return (basis_active & funding_extreme & sign_align).fillna(False)


class SpotPerpBasisShockDetector(BasisDislocationDetector):
    event_type = 'SPOT_PERP_BASIS_SHOCK'

    def prepare_features(self, df: pd.DataFrame, **params: Any) -> dict[str, pd.Series]:
        features = super().prepare_features(df, **params)
        shock_change = features['basis_zscore'].diff().abs()
        shock_q90 = dynamic_quantile_floor(
            shock_change,
            window=2880,
            quantile=float(params.get('shock_change_quantile', 0.90)),
            floor=float(params.get('shock_change_floor', 0.75)),
        )
        features.update({'shock_change': shock_change, 'shock_q90': shock_q90})
        return features

    def compute_raw_mask(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        basis_mask = super().compute_raw_mask(df, features=features, **params)
        shock_mask = (features['shock_change'] >= features['shock_q90']).fillna(False)
        return (basis_mask & shock_mask).fillna(False)


def _merge_perp_spot(perp_df: pd.DataFrame, spot_df: pd.DataFrame) -> pd.DataFrame:
    p_df = perp_df.copy()
    s_df = spot_df.copy()
    p_df['timestamp'] = pd.to_datetime(p_df['timestamp'], utc=True, errors='coerce')
    s_df['timestamp'] = pd.to_datetime(s_df['timestamp'], utc=True, errors='coerce')
    p_df = p_df.sort_values('timestamp').reset_index(drop=True)
    s_df = s_df.sort_values('timestamp').reset_index(drop=True)
    merged = pd.merge(
        p_df[['timestamp', 'close']],
        s_df[['timestamp', 'close']],
        on='timestamp',
        suffixes=('_perp', '_spot'),
    ).dropna().reset_index(drop=True)
    return merged


from project.events.detectors.registry import register_detector

_DETECTORS = {
    'BASIS_DISLOC': BasisDislocationDetector,
    'CROSS_VENUE_DESYNC': CrossVenueDesyncDetector,
    'FND_DISLOC': FndDislocDetector,
    'SPOT_PERP_BASIS_SHOCK': SpotPerpBasisShockDetector,
}

for et, cls in _DETECTORS.items():
    register_detector(et, cls)

def detect_basis_family(
    perp_df: pd.DataFrame,
    spot_df: pd.DataFrame,
    symbol: str,
    *,
    event_type: str = 'BASIS_DISLOC',
    z_threshold: float = 3.0,
    lookback_window: int = 288,
    cooldown_bars: int = 12,
) -> pd.DataFrame:
    merged = _merge_perp_spot(perp_df, spot_df)
    if merged.empty:
        return pd.DataFrame(columns=EVENT_COLUMNS)
    
    detector_cls = _DETECTORS.get(event_type, BasisDislocationDetector)
    detector = detector_cls()
    
    events = detector.detect(
        merged,
        symbol=symbol,
        threshold=float(z_threshold),
        lookback_window=int(lookback_window),
        cooldown_bars=int(cooldown_bars),
    )
    if not events.empty:
        events['timestamp'] = events['signal_ts']
        events['severity'] = events.get('event_score', events['evt_signal_intensity'])
        events['intensity'] = events.get('evt_signal_intensity', events.get('event_score'))
        if 'duration_bars' not in events.columns:
            events['duration_bars'] = 1
        else:
            events['duration_bars'] = pd.to_numeric(events['duration_bars'], errors='coerce').fillna(1)
    return events


def analyze_basis_family(
    perp_df: pd.DataFrame,
    spot_df: pd.DataFrame,
    symbol: str,
    *,
    z_threshold: float = 3.0,
    lookback_window: int = 288,
    cooldown_bars: int = 12,
    include_overlap: bool = False,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    events = detect_basis_family(
        perp_df,
        spot_df,
        symbol,
        z_threshold=z_threshold,
        lookback_window=lookback_window,
        cooldown_bars=cooldown_bars,
    )
    merged_market = _merge_perp_spot(perp_df, spot_df)
    market = merged_market.rename(columns={'close_perp': 'close'})[['timestamp', 'close']] if not merged_market.empty else None
    analyzer_results = run_analyzer_suite(events, market=market, include_overlap=include_overlap) if not events.empty else {}
    return events, analyzer_results
