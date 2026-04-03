"""
Multiplicity Controls: BH/BY FDR adjustments and Family/Cluster logic.
Extracted from pipeline scripts to improve testability and separate concerns.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from project.core.stats import canonical_bh_group_key
from project.specs.ontology import state_id_to_context_column
from project.research.gating import bh_adjust

log = logging.getLogger(__name__)


def _resolve_multiplicity_p_value_column(frame: pd.DataFrame) -> str:
    """Return the operative p-value column for multiplicity controls.

    `p_value_for_fdr` is the canonical input column for BH/BY. In raw evaluator
    output it is just the unadjusted p-value; later stages may replace it with a
    shrunk or otherwise transformed value intended for multiplicity control.
    """
    for candidate in ("p_value_for_fdr", "p_value_raw", "p_value"):
        if candidate in frame.columns:
            return candidate
    raise KeyError("raw_df must contain one of p_value_for_fdr, p_value_raw, or p_value")


def make_family_id(
    symbol: str,
    event_type: str,
    rule: str,
    horizon: str,
    cond_label: str,
    *,
    canonical_family: Optional[str] = None,
    state_id: Optional[str] = None,
) -> str:
    """BH family key based on ontology axes, stratified by symbol."""
    base = canonical_bh_group_key(
        canonical_family=str(canonical_family or event_type),
        canonical_event_type=str(event_type),
        template_verb=str(rule),
        horizon=str(horizon),
        state_id=(str(state_id).strip() if state_id else None),
        symbol=None,
        include_symbol=False,
        direction_bucket=None,
    )
    return f"{str(symbol).strip().upper()}_{base}"


def resolved_sample_size(joined_event_count: int, symbol_event_count: int) -> int:
    try:
        joined = int(joined_event_count)
        symbol_total = int(symbol_event_count)
    except (TypeError, ValueError):
        return 0
    return max(0, min(joined, symbol_total if symbol_total > 0 else joined))


def resolve_state_context_column(columns: pd.Index, state_id: Optional[str]) -> Optional[str]:
    state = str(state_id or "").strip()
    if not state:
        return None
    by_id = state_id_to_context_column(state)
    for candidate in [by_id, state, state.upper(), state.lower()]:
        if candidate and candidate in columns:
            return str(candidate)
    return None


def simes_p_value(p_vals: pd.Series) -> float:
    p = p_vals.dropna().sort_values()
    m = len(p)
    if m == 0:
        return 1.0
    return float((p * m / np.arange(1, m + 1)).min())


def by_adjust(p_values: np.ndarray) -> np.ndarray:
    """Benjamini-Yekutieli FDR adjustment."""
    if len(p_values) == 0:
        return p_values
    n = len(p_values)
    idx = np.argsort(p_values)
    sorted_p = np.asarray(p_values, dtype=float)[idx]
    harmonic = float(np.sum(1.0 / np.arange(1, n + 1)))
    adj = np.zeros(n, dtype=float)
    min_p = 1.0
    for i in range(n - 1, -1, -1):
        q = sorted_p[i] * n * harmonic / float(i + 1)
        min_p = min(min_p, q)
        adj[i] = min_p
    rev_idx = np.zeros(n, dtype=int)
    rev_idx[idx] = np.arange(n)
    return np.clip(adj[rev_idx], 0.0, 1.0)


def apply_multiplicity_controls(
    raw_df: pd.DataFrame,
    max_q: float,
    *,
    mode: str = "production",
    min_sample_size: int = 0,
    enable_cluster_adjusted: bool = True,
    cluster_threshold: float = 0.85,
    enable_by_diagnostic: bool = True,
) -> pd.DataFrame:
    """Apply BH correction per-family, then a global BH over family-adjusted q-values."""
    if raw_df.empty:
        return raw_df.copy()
    out = raw_df.copy()

    # Init columns
    for col in [
        "p_value_family",
        "q_value_family",
        "q_value",
        "q_value_by",
        "p_value_cluster",
        "q_value_cluster",
    ]:
        out[col] = np.nan
    for col in [
        "is_discovery_family",
        "is_discovery",
        "is_discovery_by",
        "is_discovery_cluster",
        "multiplicity_pool_eligible",
    ]:
        out[col] = False
    out["family_cluster_id"] = ""
    out["num_tests_primary_event_id"] = 0
    out["num_tests_event_family"] = 0

    eligible_mask = pd.Series(True, index=out.index)
    if mode == "research" and min_sample_size > 0:
        eligible_mask = out.get("sample_size", pd.Series(0, index=out.index)) >= min_sample_size
    out.loc[eligible_mask, "multiplicity_pool_eligible"] = True

    eligible = out[eligible_mask].copy()
    if eligible.empty:
        return out

    p_col = _resolve_multiplicity_p_value_column(eligible)

    # 1. Family Simes p-values
    family_simes = (
        eligible.groupby("family_id")[p_col]
        .apply(simes_p_value)
        .rename("p_value_family")
        .reset_index()
    )
    family_simes["q_value_family"] = bh_adjust(family_simes["p_value_family"].values)
    family_simes["is_discovery_family"] = family_simes["q_value_family"] <= float(max_q)

    # Map family metrics back to out
    for col in ["p_value_family", "q_value_family", "is_discovery_family"]:
        mapping = dict(zip(family_simes["family_id"], family_simes[col]))
        out[col] = out["family_id"].map(mapping)

    # 2. Within-family BH for rows in discovered families
    out["q_value"] = 1.0
    for fid, group in out[out["multiplicity_pool_eligible"]].groupby("family_id"):
        if group["is_discovery_family"].any():
            qvals = bh_adjust(group[p_col].fillna(1.0).to_numpy())
            out.loc[group.index, "q_value"] = qvals

    out["is_discovery"] = out["is_discovery_family"].astype("boolean").fillna(False).astype(
        bool
    ) & (out["q_value"] <= float(max_q))

    # 3. BY Adjustment (Optional Diagnostic)
    if enable_by_diagnostic:
        p_vals_all = out.loc[out["multiplicity_pool_eligible"], p_col].fillna(1.0).to_numpy()
        if len(p_vals_all) > 0:
            q_by = by_adjust(p_vals_all)
            out.loc[out["multiplicity_pool_eligible"], "q_value_by"] = q_by
            out["is_discovery_by"] = out["q_value_by"] <= float(max_q)

    # 4. Cluster Logic
    def _cluster_key(row):
        symbol = str(row.get("symbol", "")).strip().upper()
        event = str(
            row.get("canonical_regime", "")
            or row.get("canonical_family", "")
            or row.get("event_type", "")
        ).strip()
        horizon = str(row.get("horizon", "")).strip()
        state = str(row.get("state_id", "")).strip()
        return f"{symbol}_{event}_{horizon}_{state}"

    out["family_cluster_id"] = out.apply(_cluster_key, axis=1)

    if enable_cluster_adjusted and not out[out["multiplicity_pool_eligible"]].empty:
        cluster_simes = (
            out[out["multiplicity_pool_eligible"]]
            .groupby("family_cluster_id")[p_col]
            .apply(simes_p_value)
            .rename("p_value_cluster")
            .reset_index()
        )
        cluster_simes["q_value_cluster"] = bh_adjust(cluster_simes["p_value_cluster"].values)

        for col in ["p_value_cluster", "q_value_cluster"]:
            mapping = dict(zip(cluster_simes["family_cluster_id"], cluster_simes[col]))
            out[col] = out["family_cluster_id"].map(mapping)

        out["is_discovery_cluster"] = out["q_value_cluster"] <= float(max_q)

    # 5. Metadata
    family_counts = out.groupby("family_id").size().to_dict()
    out["num_tests_primary_event_id"] = out["family_id"].map(family_counts).fillna(0).astype(int)
    out["num_tests_event_family"] = out["family_id"].map(family_counts).fillna(0).astype(int)

    out["gate_multiplicity"] = out["is_discovery"].astype(bool)
    out["gate_multiplicity_strict"] = out["is_discovery"].astype(bool) & out[
        "is_discovery_by"
    ].astype("boolean").fillna(False).astype(bool)
    return out


def build_multiplicity_diagnostics(
    scored: pd.DataFrame,
    *,
    max_q: float,
    mode: str = "production",
    min_sample_size: int = 0,
) -> dict:
    """Compute summary diagnostics for multiplicity results."""
    if scored.empty:
        return {"global": {"discovery_count": 0}, "families": {}}

    discovery_mask = scored.get("is_discovery", pd.Series(False, index=scored.index))
    family_discovery_mask = scored.get("is_discovery_family", pd.Series(False, index=scored.index))

    return {
        "global": {
            "run_id": str(scored["run_id"].iloc[0]) if "run_id" in scored.columns else "unknown",
            "max_q_threshold": float(max_q),
            "candidates_total": len(scored),
            "families_total": int(scored["family_id"].nunique())
            if "family_id" in scored.columns
            else 0,
            "eligible_candidates": int(
                scored.get("multiplicity_pool_eligible", pd.Series(False)).sum()
            ),
            "families_pool_eligible": int(
                scored[scored.get("multiplicity_pool_eligible", pd.Series(False))][
                    "family_id"
                ].nunique()
            )
            if "family_id" in scored.columns
            else 0,
            "discoveries_total": int(discovery_mask.sum()),
            "discovered_families_count": int(scored[family_discovery_mask]["family_id"].nunique())
            if "family_id" in scored.columns
            else 0,
            "discoveries_by_total": int(scored.get("is_discovery_by", pd.Series(False)).sum()),
            "discoveries_cluster_total": int(
                scored.get("is_discovery_cluster", pd.Series(False)).sum()
            ),
        },
        "by_family": scored.groupby("family_id").size().to_dict()
        if "family_id" in scored.columns
        else {},
        "by_cluster": scored.groupby("family_cluster_id").size().to_dict()
        if "family_cluster_id" in scored.columns
        else {},
    }
