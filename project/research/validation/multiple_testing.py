from __future__ import annotations

from typing import Iterable, Sequence

import numpy as np
import pandas as pd
from statsmodels.stats.multitest import multipletests


def assign_test_families(
    df: pd.DataFrame,
    *,
    family_cols: Sequence[str],
    out_col: str = "correction_family_id",
) -> pd.DataFrame:
    out = df.copy()
    def _compose(row: pd.Series) -> str:
        parts = []
        for col in family_cols:
            parts.append(str(row.get(col, "")))
        return "::".join(parts)
    out[out_col] = out.apply(_compose, axis=1)
    return out


def _adjust(p_values: Iterable[float], method: str) -> np.ndarray:
    arr = np.asarray(list(p_values), dtype=float)
    if arr.size == 0:
        return arr
    arr = np.where(np.isfinite(arr), np.clip(arr, 0.0, 1.0), 1.0)
    if method == "bh":
        return multipletests(arr, method="fdr_bh")[1]
    if method == "by":
        return multipletests(arr, method="fdr_by")[1]
    if method == "holm":
        return multipletests(arr, method="holm")[1]
    raise ValueError(f"Unsupported correction method: {method}")


def adjust_pvalues_bh(p_values: Iterable[float]) -> np.ndarray:
    return _adjust(p_values, "bh")


def adjust_pvalues_by(p_values: Iterable[float]) -> np.ndarray:
    return _adjust(p_values, "by")


def adjust_pvalues_holm(p_values: Iterable[float]) -> np.ndarray:
    return _adjust(p_values, "holm")


def apply_multiple_testing(
    df: pd.DataFrame,
    *,
    p_col: str = "p_value_raw",
    family_col: str = "correction_family_id",
    method: str = "bh",
    out_col: str = "p_value_adj",
) -> pd.DataFrame:
    out = df.copy()
    out[out_col] = np.nan
    if out.empty or p_col not in out.columns:
        return out
    if family_col not in out.columns:
        out[out_col] = _adjust(out[p_col].fillna(1.0), method)
        return out
    for _, group in out.groupby(family_col, dropna=False):
        adj = _adjust(group[p_col].fillna(1.0), method)
        out.loc[group.index, out_col] = adj
    return out
