from __future__ import annotations

from typing import Any, Dict, Iterable, Optional

import numpy as np
import pandas as pd

from project.core.coercion import as_bool, safe_float
from project.research.validation.schemas import FalsificationResult


def generate_placebo_events(events: pd.DataFrame, *, time_col: str = 'timestamp', shift_bars: int = 1) -> pd.DataFrame:
    out = events.copy()
    if time_col in out.columns:
        ts = pd.to_datetime(out[time_col], utc=True, errors='coerce')
        out[time_col] = ts.shift(shift_bars)
    return out


def run_permutation_test(values: Iterable[float], labels: Iterable[int], *, n_iter: int = 250, random_seed: int = 0) -> Dict[str, Any]:
    vals = pd.to_numeric(pd.Series(list(values), dtype='float64'), errors='coerce')
    lbls = pd.to_numeric(pd.Series(list(labels), dtype='float64'), errors='coerce')
    frame = pd.DataFrame({'v': vals, 'l': lbls}).dropna()
    if frame.empty or frame['l'].nunique() < 2:
        return {'observed': 0.0, 'null_mean': 0.0, 'null_p95': 0.0, 'empirical_exceedance': 1.0}
    observed = float(frame.loc[frame['l'] > 0, 'v'].mean() - frame.loc[frame['l'] <= 0, 'v'].mean())
    rng = np.random.default_rng(random_seed)
    null = []
    labels_arr = frame['l'].to_numpy(copy=True)
    values_arr = frame['v'].to_numpy(copy=False)
    for _ in range(int(n_iter)):
        rng.shuffle(labels_arr)
        pos = values_arr[labels_arr > 0]
        neg = values_arr[labels_arr <= 0]
        if len(pos) == 0 or len(neg) == 0:
            continue
        null.append(float(pos.mean() - neg.mean()))
    if not null:
        return {'observed': observed, 'null_mean': 0.0, 'null_p95': 0.0, 'empirical_exceedance': 1.0}
    null_arr = np.asarray(null, dtype=float)
    exceed = float(np.mean(np.abs(null_arr) >= abs(observed)))
    return {
        'observed': observed,
        'null_mean': float(np.mean(null_arr)),
        'null_p95': float(np.quantile(null_arr, 0.95)),
        'empirical_exceedance': exceed,
    }


def evaluate_negative_controls(
    *,
    row: Dict[str, Any],
    control_rate: Optional[float],
    max_negative_control_pass_rate: float,
    allow_missing_negative_controls: bool,
) -> FalsificationResult:
    shift_pass = as_bool(row.get('pass_shift_placebo', False))
    random_pass = as_bool(row.get('pass_random_entry_placebo', False))
    direction_pass = as_bool(row.get('pass_direction_reversal_placebo', False))
    if control_rate is None:
        negative_control_pass = bool(allow_missing_negative_controls)
        empirical_exceedance = None
    else:
        negative_control_pass = bool(control_rate <= float(max_negative_control_pass_rate))
        empirical_exceedance = float(control_rate)
    passes_control = bool(shift_pass and random_pass and direction_pass and negative_control_pass)
    return FalsificationResult(
        shift_placebo_pass=bool(shift_pass),
        random_placebo_pass=bool(random_pass),
        direction_reversal_pass=bool(direction_pass),
        negative_control_pass=bool(negative_control_pass),
        control_pass_rate=None if control_rate is None else float(control_rate),
        empirical_exceedance=empirical_exceedance,
        null_mean=0.0,
        null_p95=float(max_negative_control_pass_rate),
        passes_control=bool(passes_control),
        details={'allow_missing_negative_controls': bool(allow_missing_negative_controls)},
    )
