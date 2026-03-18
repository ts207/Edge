from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

try:
    from scipy import stats as scipy_stats
except ModuleNotFoundError:  # pragma: no cover - environment-specific fallback
    scipy_stats = None

# Re-export so downstream `from project.core.stats import stats` resolves to scipy.stats
# rather than to this module itself.
stats = scipy_stats


def calculate_kendalls_tau(x: np.ndarray | pd.Series, y: np.ndarray | pd.Series) -> float:
    """
    Calculate Kendall's Tau rank correlation.
    """
    try:
        from scipy import stats as scipy_stats
        tau, _ = scipy_stats.kendalltau(x, y)
    except ImportError:
        tau, _ = _StatsCompat.kendalltau(x, y)
    return float(tau)


def test_cointegration(x: pd.Series, y: pd.Series) -> float:
    """
    Engle-Granger-style cointegration test.
    Returns the p-value for the residual unit-root test.
    Uses statsmodels when available and falls back to a residual ADF-style t test.
    """
    aligned = pd.concat([
        pd.to_numeric(pd.Series(x), errors="coerce"),
        pd.to_numeric(pd.Series(y), errors="coerce"),
    ], axis=1).dropna()
    if len(aligned) < 20:
        return 1.0

    xa = aligned.iloc[:, 0].to_numpy(dtype=float)
    ya = aligned.iloc[:, 1].to_numpy(dtype=float)
    try:
        from statsmodels.tsa.stattools import coint
        _stat, pvalue, _crit = coint(xa, ya)
        return float(np.clip(pvalue, 0.0, 1.0))
    except Exception:
        pass

    X = np.column_stack([np.ones(len(xa)), xa])
    beta, *_ = np.linalg.lstsq(X, ya, rcond=None)
    resid = ya - X @ beta
    if len(resid) < 10 or np.allclose(resid, resid[0]):
        return 1.0

    lagged = resid[:-1]
    delta = np.diff(resid)
    design = np.column_stack([np.ones(len(lagged)), lagged])
    coef, *_ = np.linalg.lstsq(design, delta, rcond=None)
    fitted = design @ coef
    errors = delta - fitted
    dof = max(len(delta) - design.shape[1], 1)
    sse = float(np.sum(errors ** 2))
    sigma2 = sse / dof
    xtx_inv = np.linalg.pinv(design.T @ design)
    se_gamma = math.sqrt(max(sigma2 * xtx_inv[1, 1], 1e-18))
    gamma_t = float(coef[1] / se_gamma)
    pvalue = float(2.0 * _student_t_sf(abs(gamma_t), dof))
    return float(np.clip(pvalue, 0.0, 1.0))


def _to_array(values: object) -> np.ndarray:
    return np.asarray(values, dtype=float)


def _to_output(values: np.ndarray, original: object) -> float | np.ndarray:
    if np.isscalar(original):
        return float(values.reshape(-1)[0])
    return values


def _norm_cdf(x: object) -> float | np.ndarray:
    arr = _to_array(x)
    out = 0.5 * (1.0 + np.vectorize(math.erf)(arr / math.sqrt(2.0)))
    return _to_output(out, x)


def _norm_ppf(p: object) -> float | np.ndarray:
    arr = np.clip(_to_array(p), 1e-12, 1.0 - 1e-12)
    a = np.array([-3.969683028665376e01, 2.209460984245205e02, -2.759285104469687e02, 1.383577518672690e02, -3.066479806614716e01, 2.506628277459239e00], dtype=float)
    b = np.array([-5.447609879822406e01, 1.615858368580409e02, -1.556989798598866e02, 6.680131188771972e01, -1.328068155288572e01], dtype=float)
    c = np.array([-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e00, -2.549732539343734e00, 4.374664141464968e00, 2.938163982698783e00], dtype=float)
    d = np.array([7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e00, 3.754408661907416e00], dtype=float)
    plow = 0.02425
    phigh = 1.0 - plow
    x = np.zeros_like(arr, dtype=float)
    low_mask = arr < plow
    high_mask = arr > phigh
    mid_mask = ~(low_mask | high_mask)
    if np.any(low_mask):
        q = np.sqrt(-2.0 * np.log(arr[low_mask]))
        x[low_mask] = (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0)
    if np.any(mid_mask):
        q = arr[mid_mask] - 0.5
        r = q * q
        x[mid_mask] = (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1.0)
    if np.any(high_mask):
        q = np.sqrt(-2.0 * np.log(1.0 - arr[high_mask]))
        # Note: Rational part is negative for these coefficients, so multiply by -1.0 to get positive x (Finding 94)
        x[high_mask] = -1.0 * (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0)
    return _to_output(x, p)


def _student_t_pdf(x: np.ndarray, df: float) -> np.ndarray:
    if df > 100:
        # Normal approximation for large df
        return (1.0 / math.sqrt(2 * math.pi)) * np.exp(-0.5 * x**2)
    
    try:
        coeff = math.gamma((df + 1.0) / 2.0) / (math.sqrt(df * math.pi) * math.gamma(df / 2.0))
    except OverflowError:
        # Fallback if gamma still overflows
        return (1.0 / math.sqrt(2 * math.pi)) * np.exp(-0.5 * x**2)
        
    return coeff * np.power(1.0 + (x * x) / df, -(df + 1.0) / 2.0)


def _student_t_cdf_scalar(x: float, df: float) -> float:
    if not np.isfinite(x):
        return 0.0 if x < 0 else 1.0
    if not np.isfinite(df) or df <= 0:
        return float(_norm_cdf(x))
    if x == 0.0:
        return 0.5
    upper = abs(float(x))
    n_steps = int(min(4000, max(400, math.ceil(upper * 200))))
    grid = np.linspace(0.0, upper, n_steps + 1)
    y = _student_t_pdf(grid, float(df))
    # NumPy 2.0 compatibility: trapz -> trapezoid
    if hasattr(np, "trapezoid"):
        area = np.trapezoid(y, grid)
    elif hasattr(np, "trapz"):
        area = np.trapz(y, grid)
    else:
        # manual trapezoidal rule
        area = float(np.sum((y[:-1] + y[1:]) / 2.0 * np.diff(grid)))
    cdf = 0.5 + math.copysign(area, x)
    return float(np.clip(cdf, 0.0, 1.0))


def _student_t_cdf(x: object, df: object) -> float | np.ndarray:
    arr = _to_array(x)
    if np.isscalar(df):
        out = np.vectorize(lambda v: _student_t_cdf_scalar(float(v), float(df)))(arr)
    else:
        df_arr = _to_array(df)
        out = np.vectorize(lambda v, d: _student_t_cdf_scalar(float(v), float(d)))(arr, df_arr)
    return _to_output(out, x)


def _student_t_sf(x: object, df: object) -> float | np.ndarray:
    cdf = _to_array(_student_t_cdf(x, df))
    out = np.clip(1.0 - cdf, 0.0, 1.0)
    return _to_output(out, x)


def _skew(values: Iterable[float]) -> float:
    arr = _to_array(list(values))
    arr = arr[np.isfinite(arr)]
    n = arr.size
    if n < 3:
        return 0.0
    centered = arr - float(np.mean(arr))
    m2 = float(np.mean(centered**2))
    if m2 <= 0.0:
        return 0.0
    m3 = float(np.mean(centered**3))
    return float(m3 / (m2 ** 1.5))


def _kurtosis(values: Iterable[float], fisher: bool = True) -> float:
    arr = _to_array(list(values))
    arr = arr[np.isfinite(arr)]
    n = arr.size
    if n < 4:
        return 0.0
    centered = arr - float(np.mean(arr))
    m2 = float(np.mean(centered**2))
    if m2 <= 0.0:
        return 0.0
    m4 = float(np.mean(centered**4))
    raw = float(m4 / (m2 * m2))
    return float(raw - 3.0) if fisher else float(raw)


def _kendalltau(x: object, y: object) -> Tuple[float, float]:
    xa = _to_array(x)
    ya = _to_array(y)
    mask = np.isfinite(xa) & np.isfinite(ya)
    xa = xa[mask]
    ya = ya[mask]
    n = xa.size
    if n < 2:
        return 0.0, 1.0

    concordant = 0
    discordant = 0
    ties_x = 0
    ties_y = 0
    for i in range(n - 1):
        dx = xa[i + 1:] - xa[i]
        dy = ya[i + 1:] - ya[i]
        sx = np.sign(dx)
        sy = np.sign(dy)
        prod = sx * sy
        concordant += int(np.sum(prod > 0))
        discordant += int(np.sum(prod < 0))
        ties_x += int(np.sum((sx == 0) & (sy != 0)))
        ties_y += int(np.sum((sy == 0) & (sx != 0)))
    denom = math.sqrt(max((concordant + discordant + ties_x) * (concordant + discordant + ties_y), 0))
    tau = 0.0 if denom == 0.0 else float((concordant - discordant) / denom)
    if n < 3 or not np.isfinite(tau):
        return tau, 1.0
    variance = 2.0 * (2.0 * n + 5.0) / (9.0 * n * (n - 1.0))
    z = tau / math.sqrt(max(variance, 1e-18))
    p_value = float(2.0 * _norm_cdf(-abs(z)))
    return tau, float(np.clip(p_value, 0.0, 1.0))


@dataclass(frozen=True)
class NeweyWestMeanResult:
    t_stat: float
    se: float
    mean: float
    n: int
    max_lag: int

    @property
    def lag(self) -> int:
        return self.max_lag


@dataclass(frozen=True)
class NonOverlappingSubsampleResult:
    selected_positions: np.ndarray
    sample_size: int
    min_separation: int


@dataclass(frozen=True)
class _NormCompat:
    def cdf(self, x: object) -> float | np.ndarray:
        return _norm_cdf(x)

    def ppf(self, p: object) -> float | np.ndarray:
        return _norm_ppf(p)


@dataclass(frozen=True)
class _TCompat:
    def cdf(self, x: object, df: object) -> float | np.ndarray:
        return _student_t_cdf(x, df)

    def sf(self, x: object, df: object) -> float | np.ndarray:
        return _student_t_sf(x, df)


@dataclass(frozen=True)
class _StatsCompat:
    norm: _NormCompat = _NormCompat()
    t: _TCompat = _TCompat()

    @staticmethod
    def kendalltau(x: object, y: object) -> Tuple[float, float]:
        return _kendalltau(x, y)

    @staticmethod
    def skew(values: Iterable[float]) -> float:
        return _skew(values)

    @staticmethod
    def kurtosis(values: Iterable[float], fisher: bool = True) -> float:
        return _kurtosis(values, fisher=fisher)


try:
    from scipy import stats as scipy_stats
except ImportError:
    stats = _StatsCompat()

# --- Appended from bh_fdr_grouping.py ---

def canonical_bh_group_key(
    *,
    canonical_family: str,
    canonical_event_type: str,
    template_verb: str,
    horizon: str,
    state_id: Optional[str] = None,
    symbol: Optional[str] = None,
    include_symbol: bool = True,
    direction_bucket: Optional[str] = None,
) -> str:
    """Canonical BH-FDR grouping key.

    Primary ontology dimensions:
      (canonical_family, canonical_event_type, template_verb, horizon)
    Optional dimensions:
      state_id (when statistically stable), direction_bucket, symbol.
    """
    family = str(canonical_family or "").strip().upper()
    event_type = str(canonical_event_type or "").strip().upper()
    verb = str(template_verb or "").strip()
    h = str(horizon or "").strip()
    state = str(state_id or "").strip().upper()
    sym = str(symbol or "").strip().upper()
    direction = str(direction_bucket or "").strip().lower()

    parts = [family or "UNKNOWN_FAMILY", event_type or "UNKNOWN_EVENT_TYPE", verb or "UNKNOWN_VERB", h or "UNKNOWN_HORIZON"]
    if state:
        parts.append(state)
    if direction:
        parts.append(direction)
    if include_symbol and sym:
        parts.append(sym)
    return "::".join(parts)


def newey_west_t_stat_for_mean(values: object, max_lag: Optional[int] = None) -> NeweyWestMeanResult:
    """Compute a HAC/Newey-West t-statistic for the sample mean."""
    arr = pd.to_numeric(pd.Series(values), errors="coerce").to_numpy(dtype=float)
    arr = arr[np.isfinite(arr)]
    n = int(arr.size)
    if n < 2:
        return NeweyWestMeanResult(t_stat=float("nan"), se=float("nan"), mean=float("nan"), n=n, max_lag=0)
    mean = float(np.mean(arr))
    centered = arr - mean
    if max_lag is None:
        max_lag = int(max(1, min(n - 1, math.floor(4.0 * ((n / 100.0) ** (2.0 / 9.0))))))
    max_lag = int(max(0, min(max_lag, n - 1)))
    gamma0 = float(np.dot(centered, centered) / n)
    lr_var = gamma0
    for lag in range(1, max_lag + 1):
        weight = 1.0 - lag / (max_lag + 1.0)
        cov = float(np.dot(centered[lag:], centered[:-lag]) / n)
        lr_var += 2.0 * weight * cov
    if not np.isfinite(lr_var) or lr_var <= 0.0:
        return NeweyWestMeanResult(t_stat=float("nan"), se=float("nan"), mean=mean, n=n, max_lag=max_lag)
    se = math.sqrt(lr_var / n)
    t_stat = float(mean / se) if se > 0.0 else float("nan")
    return NeweyWestMeanResult(t_stat=t_stat, se=float(se), mean=mean, n=n, max_lag=max_lag)


def bh_adjust(p_values: np.ndarray) -> np.ndarray:
    """Benjamini-Hochberg FDR adjustment. Returns adjusted p-values clipped to [0, 1]."""
    arr = np.asarray(p_values, dtype=float)
    n = len(arr)
    if n == 0:
        return arr
    idx = np.argsort(arr)
    sorted_p = arr[idx]
    adj = np.zeros(n)
    min_p = 1.0
    for i in range(n - 1, -1, -1):
        q = sorted_p[i] * n / (i + 1)
        min_p = min(min_p, q)
        adj[idx[i]] = min_p
    return np.clip(adj, 0.0, 1.0)


def subsample_non_overlapping_positions(positions: object, min_separation: int) -> NonOverlappingSubsampleResult:
    arr = pd.to_numeric(pd.Series(positions), errors="coerce").to_numpy(dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        out = np.asarray([], dtype=int)
        return NonOverlappingSubsampleResult(selected_positions=out, sample_size=0, min_separation=int(max(1, min_separation)))
    pos = np.sort(arr.astype(int, copy=False))
    selected = [int(pos[0])]
    min_sep = int(max(1, min_separation))
    for value in pos[1:]:
        if int(value) - int(selected[-1]) >= min_sep:
            selected.append(int(value))
    out = np.asarray(selected, dtype=int)
    return NonOverlappingSubsampleResult(selected_positions=out, sample_size=int(out.size), min_separation=min_sep)
