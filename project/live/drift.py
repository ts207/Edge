from __future__ import annotations

import logging
from typing import Dict, Any, List

import numpy as np
import pandas as pd

_LOG = logging.getLogger(__name__)


def _population_stability_index(
    research_samples: pd.Series,
    live_samples: pd.Series,
    *,
    n_bins: int = 10,
) -> float:
    research = pd.to_numeric(research_samples, errors="coerce").dropna().to_numpy(dtype=float)
    live = pd.to_numeric(live_samples, errors="coerce").dropna().to_numpy(dtype=float)
    if research.size == 0 or live.size == 0:
        return 0.0

    if np.allclose(research, research[0]) and np.allclose(live, live[0]):
        return 0.0 if np.isclose(research[0], live[0]) else float('inf')

    quantiles = np.linspace(0.0, 1.0, num=max(3, n_bins) + 1)
    edges = np.unique(np.quantile(research, quantiles))
    if edges.size < 2:
        min_edge = float(min(np.min(research), np.min(live)))
        max_edge = float(max(np.max(research), np.max(live)))
        if np.isclose(min_edge, max_edge):
            return 0.0
        edges = np.array([min_edge, max_edge], dtype=float)
    else:
        edges[0] = min(edges[0], float(np.min(live)))
        edges[-1] = max(edges[-1], float(np.max(live)))

    # Expand outer edges slightly so boundary values are counted reliably.
    eps = max(1e-12, float(np.finfo(float).eps))
    edges = edges.astype(float, copy=False)
    edges[0] -= eps
    edges[-1] += eps

    expected, _ = np.histogram(research, bins=edges)
    actual, _ = np.histogram(live, bins=edges)
    expected = expected.astype(float)
    actual = actual.astype(float)

    expected_pct = expected / max(1.0, expected.sum())
    actual_pct = actual / max(1.0, actual.sum())

    smoothing = 1e-12
    expected_pct = np.clip(expected_pct, smoothing, None)
    actual_pct = np.clip(actual_pct, smoothing, None)
    expected_pct /= expected_pct.sum()
    actual_pct /= actual_pct.sum()

    return float(np.sum((actual_pct - expected_pct) * np.log(actual_pct / expected_pct)))


def calculate_feature_drift(
    research_feature_samples: pd.Series,
    live_feature_samples: pd.Series,
    threshold: float = 0.2,
) -> Dict[str, Any]:
    """
    Calculate feature drift using Population Stability Index (PSI).
    """
    if research_feature_samples.empty or live_feature_samples.empty:
        return {}

    psi = _population_stability_index(research_feature_samples, live_feature_samples)
    research_mean = float(pd.to_numeric(research_feature_samples, errors="coerce").mean())
    live_mean = float(pd.to_numeric(live_feature_samples, errors="coerce").mean())

    return {
        "drift_score": float(psi),
        "psi": float(psi),
        "is_drifting": bool(psi > threshold),
        "research_mean": research_mean,
        "live_mean": live_mean,
    }

def monitor_execution_drift(
    research_slippage_bps: float,
    live_slippage_bps: float,
    research_fill_rate: float,
    live_fill_rate: float,
) -> Dict[str, Any]:
    """
    Monitor if execution conditions are worse than research assumptions.
    """
    slippage_drift = live_slippage_bps / max(1.0, research_slippage_bps)
    fill_rate_drift = live_fill_rate / max(1e-6, research_fill_rate)

    return {
        "slippage_drift_ratio": float(slippage_drift),
        "fill_rate_drift_ratio": float(fill_rate_drift),
        "alert": bool(slippage_drift > 2.0 or fill_rate_drift < 0.5),
    }
