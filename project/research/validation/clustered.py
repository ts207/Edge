from __future__ import annotations

from typing import Optional, Tuple

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats


def _clean_inputs(values: pd.Series, clusters: Optional[pd.Series] = None) -> Tuple[pd.Series, Optional[pd.Series]]:
    vals = pd.to_numeric(values, errors="coerce")
    mask = vals.notna()
    vals = vals.loc[mask]
    if clusters is None:
        return vals, None
    raw_clusters = clusters.loc[mask]
    mask2 = raw_clusters.notna()
    cl = raw_clusters.loc[mask2].astype(str)
    mask2 = cl.notna() & (cl != "") & (cl.str.lower() != "nan")
    valid_index = cl.index[mask2]
    return vals.loc[valid_index], cl.loc[valid_index]


def clustered_standard_error(values: pd.Series, clusters: Optional[pd.Series] = None) -> tuple[float, int, str]:
    vals, cl = _clean_inputs(values, clusters)
    n = len(vals)
    if n == 0:
        return 0.0, 0, "empty"
    if n == 1:
        return 0.0, 1, "singleton"

    if cl is None or cl.nunique() <= 1:
        stderr = float(vals.std(ddof=1) / np.sqrt(n)) if n > 1 else 0.0
        return max(0.0, stderr), int(max(1, cl.nunique() if cl is not None else n)), "naive"

    X = np.ones((n, 1), dtype=float)
    model = sm.OLS(vals.to_numpy(dtype=float), X)
    fit = model.fit(cov_type="cluster", cov_kwds={"groups": cl.to_numpy()})
    stderr = float(fit.bse[0]) if len(fit.bse) else 0.0
    return max(0.0, stderr), int(cl.nunique()), "clustered"


def clustered_t_stat(estimate: float, stderr: float) -> float:
    if not np.isfinite(stderr) or stderr <= 0.0:
        return 0.0
    return float(estimate / stderr)


def p_value_from_t(t_stat: float, dof: int) -> float:
    if dof <= 0:
        return 1.0
    return float(2.0 * (1.0 - stats.t.cdf(abs(float(t_stat)), df=int(dof))))
