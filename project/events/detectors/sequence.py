from __future__ import annotations

import pandas as pd
from typing import Any

from project.events.detectors.base import BaseEventDetector

class EventSequenceDetector(BaseEventDetector):
    """
    A unified detector that orchestrates the detection of specific causal event sequences.
    Delegates heavily to the sequence_analyzer module.
    """
    def __init__(self, sequence_name: str, events: list[str], max_gaps: list[int]):
        super().__init__()
        self.sequence_name = sequence_name
        self.events = events
        self.max_gaps = max_gaps
        self.event_type = sequence_name

    def prepare_features(self, df: pd.DataFrame, **params: Any) -> dict[str, pd.Series]:
        return {}

    def compute_raw_mask(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        # EventSequenceDetector overrides detect directly, so this isn't strictly used,
        # but is required to satisfy the abstract base class contract.
        return pd.Series(False, index=df.index)

    def detect(self, df: pd.DataFrame, symbol: str, **params: Any) -> pd.DataFrame:
        """
        Detects sequences over an input DataFrame.
        Note: The input DataFrame 'df' here is expected to be an event stream,
        not a raw OHLCV tick stream, as sequences are combinations of events.
        """
        if df.empty or 'event_type' not in df.columns:
            return pd.DataFrame()
            
        from project.events.sequence_analyzer import detect_sequences
        
        # Override params if provided dynamically
        events = params.get('events', self.events)
        max_gaps = params.get('max_gaps', self.max_gaps)
        
        return detect_sequences(
            df=df,
            events=events,
            max_gaps=max_gaps,
            sequence_name=self.sequence_name
        )
