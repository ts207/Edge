from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd

from project.events.event_flags import load_registry_flags
from project.research.phase2 import load_features as load_features_impl
from project.research.validation import assign_split_labels
from project.specs.ontology import MATERIALIZED_STATE_COLUMNS_BY_ID


def _load_features_wrapper(
    run_id: str,
    symbol: str,
    timeframe: str = "5m",
    data_root: Path | None = None,
) -> pd.DataFrame:
    from project.core.config import get_data_root

    return load_features_impl(
        data_root=data_root or get_data_root(),
        run_id=run_id,
        symbol=symbol,
        timeframe=timeframe,
    )


def normalize_search_feature_columns(features: pd.DataFrame) -> pd.DataFrame:
    if features.empty:
        return features

    out = features.copy()

    for state_id, source_col in MATERIALIZED_STATE_COLUMNS_BY_ID.items():
        canonical_col = str(state_id).strip().lower()
        if canonical_col in out.columns or source_col not in out.columns:
            continue
        out[canonical_col] = pd.to_numeric(out[source_col], errors="coerce").fillna(0.0)

    if "carry_state_code" in out.columns:
        carry_code = pd.to_numeric(out["carry_state_code"], errors="coerce").fillna(0.0)
        if "funding_positive" not in out.columns:
            out["funding_positive"] = (carry_code > 0).astype(float)
        if "funding_negative" not in out.columns:
            out["funding_negative"] = (carry_code < 0).astype(float)

    if "chop_state" not in out.columns and "chop_regime" in out.columns:
        out["chop_state"] = pd.to_numeric(out["chop_regime"], errors="coerce").fillna(0.0)
    if "trending_state" not in out.columns:
        bull_source = out["bull_trend_regime"] if "bull_trend_regime" in out.columns else pd.Series(0.0, index=out.index)
        bear_source = out["bear_trend_regime"] if "bear_trend_regime" in out.columns else pd.Series(0.0, index=out.index)
        bull = pd.to_numeric(bull_source, errors="coerce").fillna(0.0)
        bear = pd.to_numeric(bear_source, errors="coerce").fillna(0.0)
        out["trending_state"] = ((bull > 0) | (bear > 0)).astype(float)

    return out


def prepare_search_features_for_symbol(
    *,
    run_id: str,
    symbol: str,
    timeframe: str,
    data_root: Path,
    load_features_fn=_load_features_wrapper,
) -> pd.DataFrame:
    features = load_features_fn(run_id=run_id, symbol=symbol, timeframe=timeframe, data_root=data_root)
    if features.empty:
        return features

    features = normalize_search_feature_columns(features)
    event_flags = load_registry_flags(data_root=data_root, run_id=run_id)
    sym_flags = pd.DataFrame()
    if not event_flags.empty:
        sym_flags = event_flags[event_flags["symbol"] == str(symbol).upper()].copy()
        if not sym_flags.empty:
            features = pd.merge(features, sym_flags, on=["timestamp", "symbol"], how="left")
            flag_cols = [c for c in sym_flags.columns if c not in ["timestamp", "symbol"]]
            features[flag_cols] = features[flag_cols].fillna(False)

    if "split_label" not in features.columns:
        features = assign_split_labels(features, time_col="timestamp")

    return features


def load_search_feature_frame(
    *,
    run_id: str,
    symbols: Iterable[str],
    timeframe: str,
    data_root: Path,
) -> pd.DataFrame:
    parts: list[pd.DataFrame] = []
    for raw_symbol in symbols:
        symbol = str(raw_symbol).strip().upper()
        if not symbol:
            continue
        features = prepare_search_features_for_symbol(
            run_id=run_id,
            symbol=symbol,
            timeframe=timeframe,
            data_root=data_root,
        )
        if not features.empty:
            parts.append(features)
    if not parts:
        return pd.DataFrame()
    return pd.concat(parts, ignore_index=True)
