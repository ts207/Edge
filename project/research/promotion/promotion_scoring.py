from __future__ import annotations

from typing import Any, Dict
import numpy as np
from project.research.utils.decision_safety import coerce_numeric_nan


def stability_score(row: Dict[str, Any], sign_consistency_val: float) -> float:
    effect = abs(coerce_numeric_nan(row.get("effect_shrunk_state", row.get("expectancy"))))
    volatility = abs(coerce_numeric_nan(row.get("std_return")))
    if np.isnan(effect) or np.isnan(volatility):
        return np.nan
    denominator = max(volatility, 1e-8)
    return float(sign_consistency_val * (effect / denominator))


def calculate_promotion_score(
    statistical_pass: bool,
    stability_pass: bool,
    cost_pass: bool,
    tob_pass: bool,
    oos_pass: bool,
    multiplicity_pass: bool,
    placebo_pass: bool,
    timeframe_consensus_pass: bool,
) -> float:
    score = (
        float(statistical_pass)
        + float(stability_pass)
        + float(cost_pass)
        + float(tob_pass)
        + float(oos_pass)
        + float(multiplicity_pass)
        + float(placebo_pass)
        + float(timeframe_consensus_pass)
    ) / 8.0
    return float(score)
