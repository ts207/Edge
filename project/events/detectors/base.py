from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Mapping

import numpy as np
import pandas as pd

from project.events.shared import emit_event, format_event_id, EVENT_COLUMNS


class BaseEventDetector(ABC):
    event_type: str = "UNKNOWN"
    required_columns: tuple[str, ...] = ("timestamp",)
    timeframe_minutes: int = 5
    default_severity: str = "moderate"

    def check_required_columns(self, df: pd.DataFrame) -> None:
        missing = [column for column in self.required_columns if column not in df.columns]
        if missing:
            raise ValueError(f"{self.__class__.__name__} missing required columns: {missing}")

    def prepare_features(self, df: pd.DataFrame, **params: Any) -> Mapping[str, pd.Series]:
        return {}

    @abstractmethod
    def compute_raw_mask(self, df: pd.DataFrame, *, features: Mapping[str, pd.Series], **params: Any) -> pd.Series:
        raise NotImplementedError

    def compute_intensity(self, df: pd.DataFrame, *, features: Mapping[str, pd.Series], **params: Any) -> pd.Series:
        mask = self.compute_raw_mask(df, features=features, **params)
        return pd.Series(mask.fillna(False).astype(float), index=df.index, dtype=float)

    def compute_severity(
        self,
        idx: int,
        intensity: float,
        features: Mapping[str, pd.Series],
        **params: Any,
    ) -> str:
        """Return a severity label for the event at the given index."""
        return self.default_severity

    def compute_direction(
        self,
        idx: int,
        features: Mapping[str, pd.Series],
        **params: Any,
    ) -> str:
        """Return a direction label (up, down, neutral) for the event."""
        return "non_directional"

    def compute_event_type(self, idx: int, features: Mapping[str, pd.Series]) -> str:
        """Return the event type for the event at the given index."""
        return self.event_type

    def compute_metadata(
        self,
        idx: int,
        features: Mapping[str, pd.Series],
        **params: Any,
    ) -> Mapping[str, Any]:
        """Return a dictionary of additional metadata for the event."""
        return {}

    def event_indices(
        self,
        df: pd.DataFrame,
        *,
        features: Mapping[str, pd.Series],
        **params: Any,
    ) -> list[int]:
        mask = self.compute_raw_mask(df, features=features, **params)
        return np.flatnonzero(mask.fillna(False).to_numpy()).astype(int).tolist()

    def detect(self, df: pd.DataFrame, *, symbol: str, **params: Any) -> pd.DataFrame:
        self.check_required_columns(df)
        if df.empty:
            return pd.DataFrame(columns=EVENT_COLUMNS)
        
        # Reset index to ensure integer alignment
        work = df.copy().reset_index(drop=True)
        work["timestamp"] = pd.to_datetime(work["timestamp"], utc=True, errors="coerce")
        
        features = self.prepare_features(work, **params)
        intensity_series = self.compute_intensity(work, features=features, **params)
        
        rows = []
        for sub_idx, idx in enumerate(self.event_indices(work, features=features, **params)):
            ts = work.at[idx, "timestamp"]
            if pd.isna(ts):
                continue
                
            intensity_val = intensity_series.iloc[idx] if hasattr(intensity_series, "iloc") else intensity_series[idx]
            intensity = float(np.nan_to_num(intensity_val, nan=1.0))
            current_event_type = self.compute_event_type(idx, features)
            severity = self.compute_severity(idx, intensity, features, **params)
            direction = self.compute_direction(idx, features, **params)
            meta = self.compute_metadata(idx, features, **params)
            
            row = emit_event(
                event_type=current_event_type,
                symbol=symbol,
                event_id=format_event_id(current_event_type, symbol, int(idx), sub_idx),
                eval_bar_ts=ts,
                intensity=max(intensity, 1e-9),
                severity=severity,
                timeframe_minutes=self.timeframe_minutes,
                direction=direction,
                sign=1 if direction == "up" else -1 if direction == "down" else 0,
                metadata={
                    "event_idx": int(idx),
                    **meta
                },
            )
            rows.append(row)
            
        events = pd.DataFrame(rows) if rows else pd.DataFrame(columns=EVENT_COLUMNS)
        
        # Post-process for legacy compatibility
        if not events.empty:
            events["timestamp"] = events["signal_ts"]
            if "duration_bars" not in events.columns:
                events["duration_bars"] = 1
                
        return events
