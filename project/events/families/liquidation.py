from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from project.events.detectors.episode import EpisodeDetector
from project.events.episodes import build_episodes
from project.events.shared import EVENT_COLUMNS, emit_event, format_event_id
from project.research.analyzers import run_analyzer_suite


class LiquidationCascadeDetector(EpisodeDetector):
    event_type = "LIQUIDATION_CASCADE"
    required_columns = (
        "timestamp",
        "liquidation_notional",
        "oi_delta_1h",
        "oi_notional",
        "close",
        "high",
        "low",
    )
    signal_column = "liquidation_notional"
    threshold = 1.0
    timeframe_minutes = 5
    max_gap = 0
    anchor_rule = "peak"
    default_severity = "major"
    default_liq_multiplier = 3.0
    default_oi_drop_pct_threshold = 0.005

    def prepare_features(self, df: pd.DataFrame, **params: Any) -> dict[str, pd.Series]:
        liq_window = int(params.get("liq_median_window", 288))
        min_periods = int(params.get("min_periods", min(liq_window, 24)))
        liq = pd.to_numeric(df["liquidation_notional"], errors="coerce").astype(float)
        liq_median = (
            liq.shift(1).rolling(window=liq_window, min_periods=min_periods).median().fillna(0.0)
        )

        liq_multiplier = float(params.get("liq_multiplier", self.default_liq_multiplier))
        liq_th = liq_median * liq_multiplier

        oi_delta = pd.to_numeric(df["oi_delta_1h"], errors="coerce").astype(float)
        oi_notional = pd.to_numeric(df["oi_notional"], errors="coerce").astype(float)
        close = pd.to_numeric(df["close"], errors="coerce").astype(float)
        low = pd.to_numeric(df["low"], errors="coerce").astype(float)
        return {
            "liquidation_notional": liq,
            "liq_median": liq_median,
            "liq_th": liq_th,
            "oi_delta_1h": oi_delta,
            "oi_notional": oi_notional,
            "close": close,
            "low": low,
        }

    def compute_raw_mask(
        self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any
    ) -> pd.Series:
        liq = features["liquidation_notional"]
        liq_th = features["liq_th"]
        oi_delta = features["oi_delta_1h"]
        oi_notional = features["oi_notional"]

        oi_drop_pct_th = float(params.get("oi_drop_pct_th", self.default_oi_drop_pct_threshold))

        mask = ((liq > liq_th) & (liq > 0) & (oi_delta < -(oi_notional * oi_drop_pct_th))).fillna(
            False
        )
        return mask

    def compute_intensity(
        self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any
    ) -> pd.Series:
        baseline = features["liq_th"].replace(0.0, np.nan)
        intensity = features["liquidation_notional"] / baseline
        return intensity.replace([np.inf, -np.inf], np.nan)

    def detect(self, df: pd.DataFrame, *, symbol: str, **params: Any) -> pd.DataFrame:
        self.check_required_columns(df)
        if df.empty:
            return pd.DataFrame(columns=EVENT_COLUMNS)
        features = self.prepare_features(df, **params)
        mask = self.compute_raw_mask(df, features=features, **params)
        intensity = self.compute_intensity(df, features=features, **params)
        episodes = build_episodes(
            mask, score=intensity, max_gap=int(params.get("max_gap", self.max_gap))
        )
        rows = []
        for sub_idx, episode in enumerate(episodes):
            idx = int(
                episode.peak_idx
                if str(params.get("anchor_rule", self.anchor_rule)).lower() == "peak"
                else episode.start_idx
            )
            ts = pd.to_datetime(df.at[idx, "timestamp"], utc=True, errors="coerce")
            if pd.isna(ts):
                continue
            row = emit_event(
                event_type=self.event_type,
                symbol=symbol,
                event_id=format_event_id(self.event_type, symbol, idx, sub_idx),
                eval_bar_ts=ts,
                direction="down",
                intensity=float(np.nan_to_num(intensity.iloc[idx], nan=1.0)),
                severity=self.default_severity,
                timeframe_minutes=self.timeframe_minutes,
                causal=self.causal,
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

        events = pd.DataFrame(rows) if rows else pd.DataFrame(columns=EVENT_COLUMNS)
        if not events.empty:
            # Reconstruct total_liquidation_notional and oi_reduction_pct
            def enrich_row(row):
                start = row.get("start_idx")
                end = row.get("end_idx")
                if pd.notna(start) and pd.notna(end):
                    subset = df.iloc[int(start) : int(end) + 1]
                    row["total_liquidation_notional"] = float(subset["liquidation_notional"].sum())

                    # Compute OI reduction across the whole episode
                    oi_start = float(df["oi_notional"].iloc[max(0, int(start) - 1)])
                    oi_end = float(df["oi_notional"].iloc[int(end)])
                    row["oi_reduction_pct"] = (
                        (oi_start - oi_end) / oi_start if oi_start > 0 else 0.0
                    )
                    # Compute price drawdown
                    p_start = float(df["close"].iloc[max(0, int(start) - 1)])
                    p_low = float(subset["low"].min())
                    row["price_drawdown"] = (p_start - p_low) / p_start if p_start > 0 else 0.0
                else:
                    row["total_liquidation_notional"] = 0.0
                    row["oi_reduction_pct"] = 0.0
                    row["price_drawdown"] = 0.0
                return row

            events = events.apply(enrich_row, axis=1)
        return events


from project.events.detectors.registry import register_detector

register_detector("LIQUIDATION_CASCADE", LiquidationCascadeDetector)


def detect_liquidation_family(df: pd.DataFrame, symbol: str, **params: Any) -> pd.DataFrame:
    detector = LiquidationCascadeDetector()
    return detector.detect(df, symbol=symbol, **params)


def analyze_liquidation_family(
    df: pd.DataFrame, symbol: str, **params: Any
) -> tuple[pd.DataFrame, dict[str, Any]]:
    events = detect_liquidation_family(df, symbol, **params)
    market = df[["timestamp", "close"]].copy() if not df.empty and "close" in df.columns else None
    analyzer_results = run_analyzer_suite(events, market=market) if not events.empty else {}
    return events, analyzer_results
