# project/research/robustness/regime_labeler.py
"""
Regime labeler: assigns a discrete regime label to each bar in the features table.

Uses the 8 state columns already available in the features table (via
ColumnRegistry state column conventions) to produce a composite string label
across four dimensions: volatility, funding, trend, spread.

Label format: "high_vol.funding_pos.trend.tight" (dot-separated dimension values).
Unknown dimension (state column missing) produces "unknown_<dim>".
"""
from __future__ import annotations

import pandas as pd

from project.core.column_registry import ColumnRegistry

# Four regime dimensions, each with named states and their state_id lookup key.
# For each dimension, the first matching state determines the label.
# If no state column found in features, the dimension is labeled "unknown_<dim>".
REGIME_DIMENSIONS: dict = {
    "vol": {
        "states": {
            "high_vol_regime": "high_vol",
            "low_vol_regime": "low_vol",
        },
        "default_label": "unknown_vol",
    },
    "funding": {
        "states": {
            "funding_positive": "funding_pos",
            "funding_negative": "funding_neg",
        },
        "default_label": "unknown_funding",
    },
    "trend": {
        "states": {
            "trend_active": "trend",
            "chop_active": "chop",
        },
        "default_label": "unknown_trend",
    },
    "spread": {
        "states": {
            "spread_tight": "tight",
            "spread_wide": "wide",
        },
        "default_label": "unknown_spread",
    },
}


def _resolve_state_col(state_id: str, features: pd.DataFrame) -> str | None:
    """Return the first column name matching state_id that exists in features."""
    for col in ColumnRegistry.state_cols(state_id):
        if col in features.columns:
            return col
    return None


def label_regimes(features: pd.DataFrame) -> pd.Series:
    """
    Assign a composite regime label to each bar in features.

    Parameters
    ----------
    features : wide feature DataFrame; must have state_* or ms_* columns for
               any dimensions to be resolved

    Returns
    -------
    pd.Series of string labels, same index as features.
    Format: "high_vol.funding_pos.trend.tight" (dot-separated).
    """
    n = len(features)
    dimension_labels: list[pd.Series] = []

    for dim_name, cfg in REGIME_DIMENSIONS.items():
        default_label = cfg["default_label"]
        dim_series = pd.Series(default_label, index=features.index)

        for state_id, label in cfg["states"].items():
            col = _resolve_state_col(state_id, features)
            if col is None:
                continue
            active = pd.to_numeric(features[col], errors="coerce").fillna(0) == 1
            # Set label where this state is active (earlier states take priority)
            currently_unknown = dim_series == default_label
            dim_series = dim_series.where(~(active & currently_unknown), other=label)

        dimension_labels.append(dim_series)

    if not dimension_labels:
        return pd.Series("unknown.unknown.unknown.unknown", index=features.index)

    # Join dimension labels with "."
    result = dimension_labels[0].copy()
    for s in dimension_labels[1:]:
        result = result + "." + s

    return result
