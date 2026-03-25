from __future__ import annotations

from typing import Literal

import numpy as np
import pandas as pd

from .base import BaseGenerator, GeneratorConfig


class PriceSeriesGenerator(BaseGenerator):
    """Generates synthetic OHLCV price series for trend/volatility scenarios."""

    def required_columns(self) -> tuple[str, ...]:
        return ("timestamp", "close", "high", "low", "open", "volume")

    def generate_base(self, config: GeneratorConfig) -> pd.DataFrame:
        rng = np.random.default_rng(config.seed)
        n = config.n_bars

        close = config.base_price * np.exp(np.cumsum(rng.normal(0.0001, 0.001, n)))
        open_arr = np.roll(close, 1)
        open_arr[0] = config.base_price

        high = np.maximum(close, open_arr) * (1 + rng.uniform(0.0003, 0.001, n))
        low = np.minimum(close, open_arr) * (1 - rng.uniform(0.0003, 0.001, n))
        volume = rng.uniform(800, 1200, n).astype(float)

        df = pd.DataFrame(
            {
                "close": close,
                "open": open_arr,
                "high": high,
                "low": low,
                "volume": volume,
            }
        )
        df = self._ensure_timestamp(df, config)
        return df

    def inject_signal(self, df: pd.DataFrame, config: GeneratorConfig) -> pd.DataFrame:
        return df

    def inject_trending(
        self,
        df: pd.DataFrame,
        config: GeneratorConfig,
        direction: Literal["up", "down"] = "up",
        magnitude_pct: float = 5.0,
    ) -> pd.DataFrame:
        df = df.copy()
        ip = config.injection_point
        dur = config.injection_duration

        sign = 1 if direction == "up" else -1
        target_ret = sign * magnitude_pct / 100

        close_arr = df["close"].to_numpy().copy()
        base_close = close_arr[ip]
        for i in range(ip, min(len(close_arr), ip + dur)):
            progress = (i - ip) / max(1, dur)
            close_arr[i] = base_close * (1 + progress * target_ret)
        df["close"] = close_arr

        mult = 1 + abs(target_ret) * 2
        df["volume"] = self._smooth_transition(
            df["volume"].to_numpy(), ip, dur, df["volume"].iloc[ip] * mult
        )

        high_arr = df["high"].to_numpy().copy()
        high_arr[ip:ip + dur] = df["close"].iloc[ip:ip + dur].to_numpy() * 1.003
        df["high"] = high_arr

        low_arr = df["low"].to_numpy().copy()
        low_arr[ip:ip + dur] = df["close"].iloc[ip:ip + dur].to_numpy() * 0.997
        df["low"] = low_arr

        return df

    def inject_mean_reverting(
        self,
        df: pd.DataFrame,
        config: GeneratorConfig,
        oscillation_pct: float = 2.0,
        frequency: int = 10,
    ) -> pd.DataFrame:
        df = df.copy()
        n = len(df)

        t = np.arange(n) - config.injection_point
        wave = oscillation_pct / 100 * np.sin(2 * np.pi * t / frequency)

        close_arr = df["close"].to_numpy().copy()
        for i in range(max(0, config.injection_point - frequency), min(n, config.injection_point + config.injection_duration + frequency)):
            idx = i - config.injection_point
            close_arr[i] *= (1 + oscillation_pct / 100 * np.sin(2 * np.pi * idx / frequency))
        df["close"] = close_arr

        return df

    def inject_volatility_spike(
        self,
        df: pd.DataFrame,
        config: GeneratorConfig,
        vol_mult: float = 4.0,
        wick_mult: float = 3.0,
    ) -> pd.DataFrame:
        df = df.copy()
        ip = config.injection_point
        dur = config.injection_duration

        base_vol = df["volume"].iloc[ip]
        df["volume"] = self._smooth_transition(
            df["volume"].to_numpy(), ip, dur, base_vol * vol_mult
        )

        close_arr = df["close"].to_numpy()
        high_arr = df["high"].to_numpy().copy()
        low_arr = df["low"].to_numpy().copy()

        for i in range(ip, min(len(df), ip + dur)):
            center = (close_arr[i - 1] if i > 0 else close_arr[0])
            move = np.abs(close_arr[i] - center)
            high_arr[i] = close_arr[i] + move * wick_mult
            low_arr[i] = close_arr[i] - move * wick_mult

        df["high"] = high_arr
        df["low"] = low_arr

        return df
