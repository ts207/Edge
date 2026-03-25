from __future__ import annotations

import pandas as pd
import numpy as np


def compute_discovery_quality_kpis(candidates: pd.DataFrame, min_fdr: float = 0.05) -> dict:
    if candidates.empty:
        return {}

    if "q_value" in candidates.columns:
        qvals = pd.to_numeric(candidates["q_value"], errors="coerce")
        promoted = candidates.loc[qvals.le(min_fdr) & qvals.notna()]
    else:
        promoted = candidates
    if promoted.empty:
        return {}

    # Depth Coverage
    has_sequence = (
        promoted["canonical_event_type"].astype(str).str.contains("->", regex=False).mean()
        if "canonical_event_type" in promoted.columns
        else np.nan
    )
    num_logical_nodes = (
        (promoted["condition"].astype(str).str.count(" and ").mean() + 1)
        if "condition" in promoted.columns and promoted["condition"].notna().any()
        else np.nan
    )

    # Diversity
    families = (
        promoted["canonical_family"].dropna().astype(str).value_counts(normalize=True)
        if "canonical_family" in promoted.columns
        else pd.Series(dtype=float)
    )
    concentration = families.iloc[0] if not families.empty else np.nan

    # Generalization proxy (if test metrics exist)
    test_val_corr = float("nan")
    if "val_t_stat" in promoted.columns and "test_t_stat" in promoted.columns:
        test_val_corr = promoted[["val_t_stat", "test_t_stat"]].corr().iloc[0, 1]

    return {
        "depth_coverage": {
            "sequence_ratio": None if pd.isna(has_sequence) else float(has_sequence),
            "avg_logical_nodes": None if pd.isna(num_logical_nodes) else float(num_logical_nodes),
        },
        "diversity": {
            "family_concentration": None if pd.isna(concentration) else float(concentration),
            "num_families_discovered": len(families),
        },
        "generalization": {
            "test_val_correlation": float(test_val_corr) if not pd.isna(test_val_corr) else None,
        },
    }
