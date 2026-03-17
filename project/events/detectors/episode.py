from __future__ import annotations

from typing import Any, Mapping

import numpy as np
import pandas as pd

from project.events.detectors.threshold import ThresholdDetector
from project.events.episodes import build_episodes
from project.events.shared import emit_event, format_event_id, EVENT_COLUMNS


class EpisodeDetector(ThresholdDetector):
    max_gap: int = 0
    anchor_rule: str = "peak"

    def detect(self, df: pd.DataFrame, *, symbol: str, **params: Any) -> pd.DataFrame:
        self.check_required_columns(df)
        if df.empty:
            return pd.DataFrame(columns=EVENT_COLUMNS)
        features = self.prepare_features(df, **params)
        mask = self.compute_raw_mask(df, features=features, **params)
        intensity = self.compute_intensity(df, features=features, **params)
        episodes = build_episodes(mask, score=intensity, max_gap=int(params.get("max_gap", self.max_gap)))
        rows = []
        for sub_idx, episode in enumerate(episodes):
            idx = int(episode.peak_idx if str(params.get("anchor_rule", self.anchor_rule)).lower() == "peak" else episode.start_idx)
            ts = pd.to_datetime(df.at[idx, "timestamp"], utc=True, errors="coerce")
            if pd.isna(ts):
                continue
            row = emit_event(
                event_type=self.event_type,
                symbol=symbol,
                event_id=format_event_id(self.event_type, symbol, idx, sub_idx),
                eval_bar_ts=ts,
                intensity=float(np.nan_to_num(intensity.iloc[idx], nan=1.0)),
                severity=self.default_severity,
                timeframe_minutes=self.timeframe_minutes,
                metadata={
                    "start_idx": int(episode.start_idx),
                    "end_idx": int(episode.end_idx),
                    "peak_idx": int(episode.peak_idx),
                    "duration_bars": int(episode.duration_bars),
                    "episode_id": f"{self.event_type.lower()}_{symbol}_{sub_idx:04d}",
                },
            )
            row["event_idx"] = idx
            rows.append(row)
        return pd.DataFrame(rows) if rows else pd.DataFrame(columns=EVENT_COLUMNS)
