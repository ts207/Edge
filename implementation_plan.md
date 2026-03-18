# Audit Remediation Plan

Phased plan to address all findings from the deep repository audit. Grouped by dependency order and severity.

## User Review Required

> [!IMPORTANT]
> **Phase 1 (Critical Runtime)** should be merged first — these are broken-at-runtime or data-corruption bugs. All other phases can proceed independently after Phase 1.

> [!WARNING]
> **Phase 2 (PIT Safety)** changes `basis_bps` and `ms_imbalance_24` feature semantics. Any downstream artifacts or cached feature parquets will need to be regenerated after this change.

> [!CAUTION]
> **Phase 3 (Statistical Inference)** changes will affect t-stats and Sharpe ratios, potentially changing which candidates pass gates. Recommend running a baseline comparison before/after.

---

## Phase 1 — Critical Runtime Fixes

Low-risk, high-urgency fixes that prevent crashes or corrupt outputs. No behavioral changes to correct paths.

---

### Core Imports & Namespace

#### [MODIFY] [stats.py](file:///home/tstuv/workspace/trading/EDGEE/project/core/stats.py)

Fix the [stats](file:///home/tstuv/workspace/trading/EDGEE/project/research/discovery.py#151-163) namespace shadow. The `from scipy import stats` inside [try](file:///home/tstuv/workspace/trading/EDGEE/project/research/phase2.py#44-54) doesn't bind at module scope when scipy is present. Change to:

```diff
 try:
-    from scipy import stats
+    from scipy import stats as scipy_stats
 except ModuleNotFoundError:
-    pass
+    from project.core.stats_compat import stats as scipy_stats
```

Then update all internal references from `stats.` to `scipy_stats.` within this file. The 6 downstream `from project.core.stats import stats` callers will need to be updated to `from project.core.stats import scipy_stats as stats` or the module can re-export: `stats = scipy_stats`.

#### [MODIFY] [core.py](file:///home/tstuv/workspace/trading/EDGEE/project/research/promotion/core.py)

Add missing top-level imports:

```diff
 from project.core.config import get_data_root
 from project.research.utils.decision_safety import coerce_numeric_nan
+import numpy as np
+import pandas as pd
```

#### [MODIFY] [validation.py](file:///home/tstuv/workspace/trading/EDGEE/project/core/validation.py)

Fix [validate_strategy_family_params](file:///home/tstuv/workspace/trading/EDGEE/project/core/validation.py#261-348) — validated params in [norm](file:///home/tstuv/workspace/trading/EDGEE/project/core/stats.py#88-112) are never inserted into [out](file:///home/tstuv/workspace/trading/EDGEE/project/core/stats.py#76-80). Add `out[family] = norm` before each family block ends:

```diff
         if family == "Carry":
             ...
             norm["sizing_curve"] = curve
+        out[family] = norm

         elif family == "MeanReversion":
             ...
             norm["stop_zscore_abs"] = stop_z
+        out[family] = norm

         elif family == "Spread":
             ...
             norm["max_hold_bars"] = hold
+        out[family] = norm
```

---

### Detector Base Class

#### [MODIFY] [base.py](file:///home/tstuv/workspace/trading/EDGEE/project/events/detectors/base.py)

Remove the first [compute_direction](file:///home/tstuv/workspace/trading/EDGEE/project/events/detectors/base.py#27-33) (lines 27-32) from [MarketEventDetector](file:///home/tstuv/workspace/trading/EDGEE/project/events/detectors/base.py#20-143). The second definition (lines 60-67) is the canonical override point. Subclasses that need `close_ret`-based direction should override [compute_direction](file:///home/tstuv/workspace/trading/EDGEE/project/events/detectors/base.py#27-33) explicitly.

---

## Phase 2 — PIT Safety & Temporal Leak Fixes

Feature table corrections to ensure all columns are point-in-time safe.

---

#### [MODIFY] [build_features.py](file:///home/tstuv/workspace/trading/EDGEE/project/pipelines/features/build_features.py)

**Fix 1 — PIT-lag `basis_bps` (line ~170):**

Apply `.shift(1)` to `basis_bps` before z-scoring. This makes the basis feature consistent with `rv_96`, `funding_abs`, etc.

```diff
         out.loc[valid.values, "basis_bps"] = (
             (merged.loc[valid, "close"] / merged.loc[valid, "spot_close"] - 1.0) * 10_000.0
         ).values
+    out["basis_bps"] = out["basis_bps"].shift(1)
```

**Fix 2 — PIT-lag `ms_imbalance_24` (line ~440):**

```diff
-    out["ms_imbalance_24"] = calculate_imbalance(buy_volume, sell_volume, window=24)
+    out["ms_imbalance_24"] = calculate_imbalance(buy_volume, sell_volume, window=24).shift(1)
```

**Fix 3 — `rv_pct_17280` warmup fill (line ~494):**

Replace the 50.0 fill with NaN to avoid warmup bias:

```diff
-    out["rv_pct_17280"] = _rolling_percentile(out["rv_96"], window=rv_pct_window).shift(1).fillna(50.0)
+    out["rv_pct_17280"] = _rolling_percentile(out["rv_96"], window=rv_pct_window).shift(1)
```

---

## Phase 3 — Statistical Inference Quality

Fixes to improve the correctness and consistency of t-stats, Sharpe, and robustness scores across the research pipeline.

---

#### [MODIFY] [evaluator.py](file:///home/tstuv/workspace/trading/EDGEE/project/research/search/evaluator.py)

**Fix 1 — Remove dead overlap_density correction (lines 262-263):**

The `n_eff` variable is computed but never used. Remove it to avoid confusion. Keep Newey-West as the sole overlap correction.

```diff
-        # Simple overlap correction: n_eff = n_eff_w / (1 + (hbars-1) * overlap_density)
-        overlap_density = n / len(features)
-        n_eff = n_eff_w / (1.0 + (hbars - 1) * overlap_density)
```

**Fix 2 — Raise stress survival threshold (line 327):**

```diff
-            stress_survived = (valid_stress["t_stat"] > 0).sum()
+            stress_survived = (valid_stress["t_stat"] > 1.0).sum()
```

**Fix 3 — Cap Sharpe annualization for sparse triggers (lines 352-353):**

```diff
         trades_per_year = n * (ann / len(features))
+        trades_per_year = min(trades_per_year, ann)  # Cap at theoretical max
         sharpe = (weighted_mean / weighted_std) * np.sqrt(trades_per_year)
```

---

#### [MODIFY] [discovery.py](file:///home/tstuv/workspace/trading/EDGEE/project/research/discovery.py)

**Fix 1 — Apply overlap adjustment to [series_stats](file:///home/tstuv/workspace/trading/EDGEE/project/research/discovery.py#151-163) (line 161):**

```diff
-    t_stat = (mu / (sigma / np.sqrt(n))) if sigma > 1e-9 and n > 1 else 0.0
-    return {"n": n, "mean": mu, "std": sigma, "t_stat": t_stat}
+    t_stat_raw = (mu / (sigma / np.sqrt(n))) if sigma > 1e-9 and n > 1 else 0.0
+    return {"n": n, "mean": mu, "std": sigma, "t_stat": t_stat_raw}
```

> [!NOTE]
> A deeper fix would compute the proper overlap-adjusted t-stat, but that requires a [horizon_bars](file:///home/tstuv/workspace/trading/EDGEE/project/research/search/evaluator_utils.py#48-55) argument. For now, documenting this as a known limitation and adding a comment is the conservative choice. Full unification with the evaluator path is a follow-up.

**Fix 2 — Replace O(n²) sequence trigger with searchsorted (lines 382-389):**

```python
# Replace DataFrame.apply with vectorized searchsorted
e1_ts_vals = e1_times.values.astype(np.int64)
bar_ts_vals = working["enter_ts"].values.astype(np.int64)
gap_ns = int(pd.Timedelta(minutes=gap * 5).value)
idx = np.searchsorted(e1_ts_vals, bar_ts_vals, side="right") - 1
has_e1 = (idx >= 0) & ((bar_ts_vals - e1_ts_vals[np.maximum(idx, 0)]) <= gap_ns)
trigger_mask &= pd.Series(has_e1 & (working["event_type"] == e2).values, index=working.index)
```

---

## Phase 4 — Architecture & Structural Cleanup

DRY refactoring, dead code removal, and architectural improvements.

---

#### [MODIFY] [oi.py](file:///home/tstuv/workspace/trading/EDGEE/project/events/families/oi.py)

Extract shared z-score computation into a helper method on [BaseOIShockDetector](file:///home/tstuv/workspace/trading/EDGEE/project/events/families/oi.py#18-29):

```python
def _compute_oi_z(self, df, **params):
    window = int(params.get('oi_window', 96))
    min_periods = int(params.get('min_periods', max(24, window // 4)))
    oi = pd.to_numeric(df['oi_notional'], errors='coerce').replace(0.0, np.nan).astype(float)
    oi_log_delta = np.log(oi).diff()
    baseline = oi_log_delta.shift(1)
    mean = baseline.rolling(window=window, min_periods=min_periods).mean()
    std = baseline.rolling(window=window, min_periods=min_periods).std()
    oi_z = (oi_log_delta - mean) / std.where(std > 0.0, 1e-12)
    close_ret = pd.to_numeric(df['close'], errors='coerce').astype(float).pct_change(periods=1)
    return oi_z, close_ret, oi.pct_change(periods=1)
```

Then each subclass calls `oi_z, close_ret, oi_pct = self._compute_oi_z(df, **params)`.

#### [MODIFY] [update_campaign_memory.py](file:///home/tstuv/workspace/trading/EDGEE/project/pipelines/research/update_campaign_memory.py)

Extract [_gate_rank](file:///home/tstuv/workspace/trading/EDGEE/project/pipelines/research/update_campaign_memory.py#111-116) to module level:

```diff
+def _gate_rank(val) -> int:
+    val = str(val).strip().lower()
+    if val in ("pass", "true", "1", "1.0"): return 2
+    if val in ("fail", "false", "0", "0.0"): return 1
+    return 0
+
 def _build_belief_state(...):
-    def _gate_rank(val) -> int: ...
     ...
 def _build_next_actions(...):
-    def _gate_rank(val) -> int: ...
```

#### [MODIFY] [risk_allocator.py](file:///home/tstuv/workspace/trading/EDGEE/project/engine/risk_allocator.py)

**Fix 1 — Add logging to correlation allocation fallback (line 408):**

```diff
     except Exception:
-        pass
+        log.warning("Correlation allocation failed, falling back to equal-weight", exc_info=True)
```

**Fix 2 — Single-source [_clamp_positions](file:///home/tstuv/workspace/trading/EDGEE/project/engine/risk_allocator.py#42-56) (lines 23-55):**

Define the pure-Python version first, then conditionally wrap with `@njit`:

```python
def _clamp_positions_py(raw: np.ndarray, max_new: float) -> np.ndarray:
    # ... single implementation
    
try:
    from numba import njit
    _clamp_positions = njit(cache=True)(_clamp_positions_py)
except Exception:
    _clamp_positions = _clamp_positions_py
```

#### [MODIFY] [basis.py](file:///home/tstuv/workspace/trading/EDGEE/project/events/families/basis.py)

Remove the [detect()](file:///home/tstuv/workspace/trading/EDGEE/project/events/families/basis.py#70-108) override on [BasisDislocationDetector](file:///home/tstuv/workspace/trading/EDGEE/project/events/families/basis.py#16-108) (lines 70-107). Move the basis-specific metadata into [compute_metadata()](file:///home/tstuv/workspace/trading/EDGEE/project/events/families/oi.py#22-29):

```python
def compute_metadata(self, idx, features, **params):
    return {
        'basis_bps': float(features['basis_bps'].iloc[idx]),
        'basis_zscore': float(features['basis_zscore'].iloc[idx]),
        'vol_regime': str(features['vol_regime'].iloc[idx]),
    }
```

#### [DELETE] Root-level migration scripts

Archive to `scripts/archive/` or delete:
- [fix_imports.py](file:///home/tstuv/workspace/trading/EDGEE/fix_imports.py)
- [fix_temporal.py](file:///home/tstuv/workspace/trading/EDGEE/fix_temporal.py)
- [migrate_strategies.py](file:///home/tstuv/workspace/trading/EDGEE/migrate_strategies.py)
- [rename_imports.py](file:///home/tstuv/workspace/trading/EDGEE/rename_imports.py)

---

## Phase 5 — Systemic Improvements

Broader patterns that reduce tech debt and prevent regression.

---

#### [NEW] Bare-exception audit sweep

Replace the highest-risk bare `except Exception: pass` handlers with `except Exception as e: log.warning(...)`. Priority targets:
- [risk_allocator.py](file:///home/tstuv/workspace/trading/EDGEE/project/engine/risk_allocator.py) (correlation allocation, pairwise correlation)
- [evaluator.py](file:///home/tstuv/workspace/trading/EDGEE/project/research/search/evaluator.py) (timeframe inference)
- [build_features.py](file:///home/tstuv/workspace/trading/EDGEE/project/pipelines/features/build_features.py) ([_load_spot_close_reference](file:///home/tstuv/workspace/trading/EDGEE/project/pipelines/features/build_features.py#123-146))

#### [NEW] Feature PIT assertion

Add a debug assertion in [_ensure_feature_contract_columns](file:///home/tstuv/workspace/trading/EDGEE/project/pipelines/features/build_features.py#383-442) that logs a warning if any features that should be lagged are not, using a known laglist:

```python
_PIT_LAGGED_FEATURES = {"rv_96", "rv_pct_17280", "funding_abs", "funding_abs_pct", 
                         "basis_bps", "basis_zscore", "ms_imbalance_24", ...}
```

---

## Verification Plan

### Automated Tests

All phases will be verified against the existing 114-file test suite. Key commands:

**Phase 1 verification:**
```bash
PYTHONPATH=. .venv/bin/python -m pytest tests/core/ -x -q --tb=short
PYTHONPATH=. .venv/bin/python -m pytest tests/eval/ -x -q --tb=short
PYTHONPATH=. .venv/bin/python -m pytest tests/events/ -x -q --tb=short
```

**Phase 2 verification:**
```bash
PYTHONPATH=. .venv/bin/python -m pytest tests/pipelines/features/ -x -q --tb=short
PYTHONPATH=. .venv/bin/python -m pytest tests/audit/test_pipeline_leaks.py -x -q --tb=short
```

**Phase 3 verification:**
```bash
PYTHONPATH=. .venv/bin/python -m pytest tests/research/ -x -q --tb=short
PYTHONPATH=. .venv/bin/python -m pytest tests/eval/test_overfitting_detectors.py -x -q --tb=short 2>&1 | tail -20
```

**Phase 4 verification:**
```bash
PYTHONPATH=. .venv/bin/python -m pytest tests/engine/test_risk_allocator.py tests/engine/test_allocator_integration.py -x -q --tb=short
PYTHONPATH=. .venv/bin/python -m pytest tests/events/ -x -q --tb=short
```

**Full regression:**
```bash
PYTHONPATH=. .venv/bin/python -m pytest tests/ -x -q --tb=short 2>&1 | tail -30
```

### New Tests to Add

| Test | Target | What it verifies |
|------|--------|-----------------|
| `test_stats_namespace_binding` | [core/stats.py](file:///home/tstuv/workspace/trading/EDGEE/project/core/stats.py) | `from project.core.stats import scipy_stats` returns the scipy.stats module |
| `test_validate_strategy_family_params_output` | [core/validation.py](file:///home/tstuv/workspace/trading/EDGEE/project/core/validation.py) | Output dict contains validated family params (currently would fail) |
| `test_basis_bps_pit_lag` | [features/build_features.py](file:///home/tstuv/workspace/trading/EDGEE/project/pipelines/features/build_features.py) | `basis_bps[t]` uses only `close[t-1]` and earlier |
| `test_overlap_adj_removed_from_evaluator` | [search/evaluator.py](file:///home/tstuv/workspace/trading/EDGEE/project/research/search/evaluator.py) | No `n_eff` dead variable in the evaluation path |

### Manual Verification

After Phase 2, a single `plan_only` research run should be executed to confirm feature outputs haven't structurally changed:

```bash
.venv/bin/python -m project.research.agent_io.execute_proposal \
  --proposal <existing_proposal.yaml> \
  --run_id audit_verification_001 \
  --registry_root project/configs/registries \
  --out_dir /tmp/audit_verify \
  --plan_only 1
```
