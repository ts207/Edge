from __future__ import annotations

import re
from datetime import timedelta
from typing import Iterable, List, Optional

import pandas as pd

from project.research.validation.schemas import ValidationSplit


DEFAULT_BAR_DURATION_MINUTES = 5
_DEFAULT_SPLIT_SCHEME_ID = "WF_60_20_20"
_SPLIT_SCHEME_ALIASES = {
    "SMOKE_TVT": (0.6, 0.2),
    "WF_60_20_20": (0.6, 0.2),
    "TVT_60_20_20": (0.6, 0.2),
}


def normalize_timestamp(value: str | pd.Timestamp) -> pd.Timestamp:
    ts = pd.Timestamp(value)
    if ts.tz is None:
        return ts.tz_localize("UTC")
    return ts.tz_convert("UTC")


def bars_to_timedelta(bars: int, *, bar_duration_minutes: int = DEFAULT_BAR_DURATION_MINUTES) -> pd.Timedelta:
    return pd.Timedelta(minutes=max(0, int(bars)) * max(1, int(bar_duration_minutes)))


def resolve_split_scheme(split_scheme_id: str | None) -> tuple[str, float, float]:
    raw = str(split_scheme_id or _DEFAULT_SPLIT_SCHEME_ID).strip().upper() or _DEFAULT_SPLIT_SCHEME_ID
    if raw in _SPLIT_SCHEME_ALIASES:
        train_frac, validation_frac = _SPLIT_SCHEME_ALIASES[raw]
        return raw, float(train_frac), float(validation_frac)

    match = re.fullmatch(r"(?:WF|TVT)_(\d{1,2})_(\d{1,2})_(\d{1,2})", raw)
    if match:
        train_pct, validation_pct, test_pct = (int(token) for token in match.groups())
        total = train_pct + validation_pct + test_pct
        if total != 100:
            raise ValueError(f"split_scheme_id must sum to 100, got {raw!r}")
        return raw, float(train_pct) / 100.0, float(validation_pct) / 100.0

    raise ValueError(f"unsupported split_scheme_id: {split_scheme_id!r}")


def build_validation_splits(
    *,
    start: str | pd.Timestamp,
    end: str | pd.Timestamp,
    train_frac: float = 0.6,
    validation_frac: float = 0.2,
    embargo_bars: int = 0,
    purge_bars: int = 0,
    bar_duration_minutes: int = DEFAULT_BAR_DURATION_MINUTES,
) -> List[ValidationSplit]:
    start_ts = normalize_timestamp(start)
    end_ts = normalize_timestamp(end)
    if start_ts > end_ts:
        raise ValueError("start must be <= end")
    if not (0.0 < float(train_frac) < 1.0):
        raise ValueError("train_frac must be in (0,1)")
    if not (0.0 < float(validation_frac) < 1.0):
        raise ValueError("validation_frac must be in (0,1)")
    if float(train_frac) + float(validation_frac) >= 1.0:
        raise ValueError("train_frac + validation_frac must be < 1")

    duration = end_ts - start_ts
    embargo_delta = bars_to_timedelta(embargo_bars, bar_duration_minutes=bar_duration_minutes)
    purge_delta = bars_to_timedelta(purge_bars, bar_duration_minutes=bar_duration_minutes)

    train_start = start_ts
    train_end_nominal = train_start + duration * float(train_frac)
    train_end = train_end_nominal - purge_delta

    validation_start = train_end_nominal + embargo_delta
    validation_duration = duration * float(validation_frac)
    validation_end_nominal = validation_start + validation_duration
    validation_end = validation_end_nominal - purge_delta

    test_start = validation_end_nominal + embargo_delta
    test_end = end_ts

    windows: List[ValidationSplit] = []
    if train_end < train_start:
        raise ValueError("purge_bars trims train window below zero length")
    windows.append(
        ValidationSplit(
            label="train",
            start=train_start,
            end=train_end,
            purge_bars=int(purge_bars),
            embargo_bars=int(embargo_bars),
            bar_duration_minutes=int(bar_duration_minutes),
        )
    )
    if validation_end >= validation_start:
        windows.append(
            ValidationSplit(
                label="validation",
                start=validation_start,
                end=validation_end,
                purge_bars=int(purge_bars),
                embargo_bars=int(embargo_bars),
                bar_duration_minutes=int(bar_duration_minutes),
            )
        )
    if test_end >= test_start:
        windows.append(
            ValidationSplit(
                label="test",
                start=test_start,
                end=test_end,
                purge_bars=int(purge_bars),
                embargo_bars=int(embargo_bars),
                bar_duration_minutes=int(bar_duration_minutes),
            )
        )
    if not windows:
        raise ValueError("No validation windows produced")
    return windows


def assign_split_labels(
    df: pd.DataFrame,
    *,
    time_col: str,
    train_frac: float = 0.6,
    validation_frac: float = 0.2,
    embargo_bars: int = 0,
    purge_bars: int = 0,
    bar_duration_minutes: int = DEFAULT_BAR_DURATION_MINUTES,
    split_col: str = "split_label",
) -> pd.DataFrame:
    if df.empty or time_col not in df.columns:
        return df.copy()

    out = df.copy()
    ts = pd.to_datetime(out[time_col], utc=True, errors="coerce")
    out[time_col] = ts
    valid = ts.notna()
    if valid.sum() < 2:
        out[split_col] = "train"
        out["non_promotable"] = True
        return out

    windows = build_validation_splits(
        start=ts[valid].min(),
        end=ts[valid].max(),
        train_frac=train_frac,
        validation_frac=validation_frac,
        embargo_bars=embargo_bars,
        purge_bars=purge_bars,
        bar_duration_minutes=bar_duration_minutes,
    )
    labels = pd.Series([pd.NA] * len(out), index=out.index, dtype="object")
    for window in windows:
        if window.label == "test":
            mask = valid & (ts >= window.start) & (ts <= window.end)
        else:
            mask = valid & (ts >= window.start) & (ts < window.end)
        labels.loc[mask] = window.label

    excluded_mask = valid & labels.isna()
    if bool(excluded_mask.any()):
        out = out.loc[~excluded_mask].copy()
        labels = labels.loc[out.index]
    out[split_col] = labels.astype(str)
    out["split_plan_id"] = f"TVT_{int(round(train_frac*100))}_{int(round(validation_frac*100))}_{100-int(round((train_frac+validation_frac)*100))}"
    out["purge_bars_used"] = int(purge_bars)
    out["embargo_bars_used"] = int(embargo_bars)
    out["bar_duration_minutes"] = int(bar_duration_minutes)
    return out


def serialize_splits(splits: Iterable[ValidationSplit]) -> list[dict]:
    return [split.to_dict() for split in splits]
