from __future__ import annotations

import logging
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass

import numpy as np
import pandas as pd

_LOG = logging.getLogger(__name__)

@dataclass
class WindowResult:
    train_range: Tuple[pd.Timestamp, pd.Timestamp]
    test_range: Tuple[pd.Timestamp, pd.Timestamp]
    train_metrics: Dict[str, float]
    test_metrics: Dict[str, float]

def generate_walkforward_windows(
    index: pd.DatetimeIndex,
    train_size_bars: int,
    test_size_bars: int,
    step_size_bars: int,
) -> List[Tuple[pd.DatetimeIndex, pd.DatetimeIndex]]:
    """
    Generate training and testing window indices.
    """
    windows = []
    total_len = len(index)
    
    start = 0
    while start + train_size_bars + test_size_bars <= total_len:
        train_idx = index[start : start + train_size_bars]
        test_idx = index[start + train_size_bars : start + train_size_bars + test_size_bars]
        windows.append((train_idx, test_idx))
        start += step_size_bars
        
    return windows

def evaluate_walkforward_stability(
    results: List[WindowResult],
) -> Dict[str, Any]:
    """
    Calculate stability metrics across walk-forward windows.
    """
    if not results:
        return {}
    
    test_expectancies = [r.test_metrics.get("expectancy_bps", 0.0) for r in results]
    train_expectancies = [r.train_metrics.get("expectancy_bps", 0.0) for r in results]
    
    # Expectancy Stability: Standard deviation of expectancy / mean expectancy
    avg_exp = np.mean(test_expectancies)
    std_exp = np.std(test_expectancies)
    expectancy_stability = 1.0 - (std_exp / max(1e-6, abs(avg_exp)))
    
    # Sign Consistency: Percentage of windows with positive expectancy
    sign_consistency = np.mean([1.0 if e > 0 else 0.0 for e in test_expectancies])
    
    # Degradation: ratio of means is more stable than mean(test/train) near zero.
    avg_train = np.mean(train_expectancies)
    degradation = (avg_exp / avg_train) if abs(avg_train) > 1e-6 else 0.0

    return {
        "avg_test_expectancy_bps": float(avg_exp),
        "avg_train_expectancy_bps": float(avg_train),
        "expectancy_stability": float(np.clip(expectancy_stability, 0.0, 1.0)),
        "sign_consistency": float(sign_consistency),
        "avg_train_test_degradation": float(degradation),
        "n_windows": len(results),
    }
