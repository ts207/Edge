# Comprehensive Repository Audit Report — Deep Edition

**Repository:** EDGEE  
**Date:** 2026-03-18  
**Scope:** Structural, statistical, logical, redundancy, dead code, temporal safety, research bias  

---

## Executive Summary

This deep audit analyzed **60+ source files** across 12 subsystems: detectors, families, feature construction, search evaluator, discovery engine, PnL engine, risk allocator, strategy executor, pipeline stages, campaign memory, robustness framework, and shrinkage/estimation.

**6 Critical**, **12 High**, **14 Medium** issues identified. Categories:

| Category | Critical | High | Medium |
|----------|----------|------|--------|
| Statistical / Research Bias | 2 | 4 | 3 |
| Temporal Safety (Look-ahead) | 1 | 2 | 2 |
| Architectural / Structural | 1 | 3 | 4 |
| Logical Traps | 2 | 2 | 2 |
| Dead Code / Redundancy | 0 | 1 | 3 |

---

## 1. Statistical & Research Bias Issues

### 1.1 — 🔴 CRITICAL: Double overlap correction in evaluator t-stat

**File:** [evaluator.py](file:///home/tstuv/workspace/trading/EDGEE/project/research/search/evaluator.py#L256-L349)

The evaluator applies **two independent overlap corrections** that partially compensate the same serial correlation:

1. **Line 263** — `n_eff = n_eff_w / (1.0 + (hbars - 1) * overlap_density)` — deflates effective sample size by overlap density
2. **Lines 287-304** — Newey-West kernel estimator accumulates autocovariance through `hbars - 1` lags, inflating `nw_var`

Both corrections target the same phenomenon (overlapping forward returns). Applying both simultaneously **over-penalizes** real signals and **under-penalizes** noise via inconsistent variance estimation. Specifically:

- The NW variance already adjusts for serial correlation in the variance estimate
- The `n_eff` deflation then further reduces the denominator of the t-stat
- But line 349 uses `n_eff_w` (NOT `n_eff`), contradicting the correction on line 263

```python
# Line 349 — uses n_eff_w, ignoring the overlap correction entirely
t_stat = weighted_mean / (weighted_std / np.sqrt(max(1.0, n_eff_w)))
```

**Impact:** The `n_eff` variable on line 263 is **computed but never used**. The t-stat effectively uses only Newey-West, making the overlap_density correction dead code. This is confusing and suggests the correction was intended but not wired.

**Fix:** Choose ONE overlap correction method. NW is more principled — remove the `n_eff` deflation entirely and use `n_eff_w` with NW variance.

---

### 1.2 — 🔴 CRITICAL: `basis_bps` feature has no PIT lag

**File:** [build_features.py](file:///home/tstuv/workspace/trading/EDGEE/project/pipelines/features/build_features.py#L148-L201)

The [_add_basis_features](file:///home/tstuv/workspace/trading/EDGEE/project/pipelines/features/build_features.py#148-202) function computes `basis_bps` and `basis_zscore` from the currentbar's [close](file:///home/tstuv/workspace/trading/EDGEE/project/pipelines/features/build_features.py#123-146) value:

```python
# Line 170-172 — uses current bar close, no shift(1)
out.loc[valid.values, "basis_bps"] = (
    (merged.loc[valid, "close"] / merged.loc[valid, "spot_close"] - 1.0) * 10_000.0
).values
```

The z-score is then computed on the current-bar `basis_bps` (line 190):

```python
out["basis_zscore"] = (out["basis_bps"] - roll_median) / roll_robust_std.replace(0.0, np.nan)
```

**No `.shift(1)` is applied to `basis_bps` or `basis_zscore`.** Compare with `rv_96` (line 493) and `funding_abs` (line 515) where `.shift(1)` is consistently applied.

**Impact:** When `basis_zscore` is used by the [BasisDislocationDetector](file:///home/tstuv/workspace/trading/EDGEE/project/events/families/basis.py#16-108) (which itself applies `shift=1` in `rolling_robust_zscore`), the detector path is safe. But when features are used directly by the evaluator or strategy executor via the feature table, the un-shifted `basis_bps` is a **potential look-ahead leak**.

**Fix:** Apply `.shift(1)` to `basis_bps` before z-scoring, consistent with other PIT-lagged features.

---

### 1.3 — 🟠 HIGH: Sharpe ratio uses realized trade frequency, not strategy frequency

**File:** [evaluator.py](file:///home/tstuv/workspace/trading/EDGEE/project/research/search/evaluator.py#L352-L353)

```python
trades_per_year = n * (ann / len(features))
sharpe = (weighted_mean / weighted_std) * np.sqrt(trades_per_year)
```

This computes `trades_per_year` from the realized number of trigger hits `n` relative to the total data length. For rare events, this can **overstate** the Sharpe ratio because the in-sample hit rate may not persist out-of-sample. For very sparse triggers (e.g., 30 events in 100K bars), the annualization factor becomes tiny and the Sharpe is unreliable.

**Fix:** Cap `trades_per_year` or use a floor annualization based on the hypothesized rebalance frequency.

---

### 1.4 — 🟠 HIGH: [series_stats](file:///home/tstuv/workspace/trading/EDGEE/project/research/discovery.py#151-163) in [discovery.py](file:///home/tstuv/workspace/trading/EDGEE/project/research/discovery.py) uses naive t-stat on overlapping returns

**File:** [discovery.py](file:///home/tstuv/workspace/trading/EDGEE/project/research/discovery.py#L151-L162)

```python
t_stat = (mu / (sigma / np.sqrt(n))) if sigma > 1e-9 and n > 1 else 0.0
```

This classic formula assumes IID observations. But [candidate_return_series](file:///home/tstuv/workspace/trading/EDGEE/project/research/discovery.py#144-150) extracts `return_{horizon_bars}` which are overlapping forward returns. With `horizon_bars = 24`, consecutive observations share 23/24 of their data, inflating the naive t-stat by up to **~5×**.

**Impact:** All candidate discovery in the legacy pipeline path relies on this inflated t-stat, meaning candidates pass statistical gates that they wouldn't pass under proper overlap-adjusted inference.

---

### 1.5 — 🟠 HIGH: Robustness score weights are arbitrary with no calibration

**File:** [robustness_scorer.py](file:///home/tstuv/workspace/trading/EDGEE/project/research/robustness/robustness_scorer.py#L17-L87)

Default weights `weight_sign=0.5, weight_min_t=0.3, weight_coverage=0.2` are hardcoded constants with no empirical backing. The `min_t` component maps `[-3, 2]` → `[0, 1]` linearly, meaning a regime with `t = -2.5` gets score 0.1 — this conflates "opposite direction" with "slightly negative."

**Fix:** Consider regime-count-aware weighting. A 2-regime hypothesis should weight differently than an 8-regime hypothesis.

---

### 1.6 — 🟠 HIGH: Stress score treats t_stat > 0 as "survived"

**File:** [evaluator.py](file:///home/tstuv/workspace/trading/EDGEE/project/research/search/evaluator.py#L324-L330)

```python
stress_survived = (valid_stress["t_stat"] > 0).sum()
stress_score = float(stress_survived / len(valid_stress))
```

`t_stat > 0` is an extremely weak survival threshold. A t-stat of 0.01 is statistically indistinguishable from zero but counts as "survived." This inflates the stress score for strategies that barely survive.

**Fix:** Use `t_stat > 1.0` or `t_stat > 0` AND `hit_rate > 0.5` as a survival criterion.

---

### 1.7 — 🟡 MEDIUM: [compute_direction](file:///home/tstuv/workspace/trading/EDGEE/project/events/detectors/base.py#27-33) defined twice on [MarketEventDetector](file:///home/tstuv/workspace/trading/EDGEE/project/events/detectors/base.py#20-143)

**File:** [base.py](file:///home/tstuv/workspace/trading/EDGEE/project/events/detectors/base.py#L27-L67)

[compute_direction](file:///home/tstuv/workspace/trading/EDGEE/project/events/detectors/base.py#27-33) is defined at line 27 and again at line 60-67. The second definition (lines 60-67) silently overrides the first and always returns `"non_directional"`. The first (lines 27-32) actually checks `close_ret`. MRO means subclasses never see the first version.

**Impact:** All detectors inheriting from [MarketEventDetector](file:///home/tstuv/workspace/trading/EDGEE/project/events/detectors/base.py#20-143) that don't override [compute_direction](file:///home/tstuv/workspace/trading/EDGEE/project/events/detectors/base.py#27-33) get `"non_directional"` instead of the `close_ret`-based direction.

---

### 1.8 — 🟡 MEDIUM: Rolling quantile percentile floored at 50

**File:** [build_features.py](file:///home/tstuv/workspace/trading/EDGEE/project/pipelines/features/build_features.py#L494)

```python
out["rv_pct_17280"] = _rolling_percentile(out["rv_96"], window=rv_pct_window).shift(1).fillna(50.0)
```

Filling NaN percentiles with **50.0** ("median") biases the warmup period to look like a "normal volatility" regime. During the first `rv_pct_window` bars, any strategy conditioning on volatility percentile gets systematically incorrect regime labels.

---

## 2. Temporal Safety (Look-ahead Bias) Issues

### 2.1 — 🟠 HIGH: [forward_log_returns](file:///home/tstuv/workspace/trading/EDGEE/project/research/search/evaluator_utils.py#57-60) uses `shift(-horizon_bars)` — correct but fragile

**File:** [evaluator_utils.py](file:///home/tstuv/workspace/trading/EDGEE/project/research/search/evaluator_utils.py#L57-L59)

```python
def forward_log_returns(close: pd.Series, horizon_bars: int) -> pd.Series:
    log_close = np.log(close.clip(lower=1e-12))
    return log_close.shift(-horizon_bars) - log_close
```

This is correct for research evaluation (you need future close to compute forward returns). However, there is **no assertion or guard** that this series is never used in feature construction or signal generation. If any path feeds these values back into the feature table without masking, it's a silent look-ahead leak.

---

### 2.2 — 🟠 HIGH: OI detector uses current-bar `pct_change` without shift

**File:** [oi.py](file:///home/tstuv/workspace/trading/EDGEE/project/events/families/oi.py#L38-L46)

```python
oi_log_delta = np.log(oi).diff()         # current bar's OI change
baseline = oi_log_delta.shift(1)          # z-score baseline is shifted
oi_z = (oi_log_delta - mean) / std        # but oi_log_delta is NOT shifted
close_ret = ... .pct_change(periods=1)    # current bar's close return
mask = (oi_z >= spike_z_th) & (close_ret > 0)
```

`oi_z` uses current-bar `oi_log_delta` against a lagged baseline — this is intentional (detecting current spikes). But `close_ret` on line 44 uses the **current bar's return** to determine direction. Since `close_ret = (close[t] / close[t-1]) - 1`, this is point-in-time safe (it only uses `close[t]` and `close[t-1]`, both available at bar `t`). **However**, the mask at line 46 means the event fires AT bar `t` with direction determined by bar `t`'s close — any strategy entering at bar `t`'s close is fine, but entering at bar `t-1`'s close would include the information that drove the signal.

---

### 2.3 — 🟡 MEDIUM: Feature table `ms_imbalance_24` uses no PIT lag

**File:** [build_features.py](file:///home/tstuv/workspace/trading/EDGEE/project/pipelines/features/build_features.py#L440)

```python
out["ms_imbalance_24"] = calculate_imbalance(buy_volume, sell_volume, window=24)
```

Unlike `rv_96` (shifted at line 493) and `funding_abs` (shifted at line 515), `ms_imbalance_24` is **not shifted** by 1 bar. If this feature is used as a context condition for strategy evaluation (e.g., via context_mask), it leaks the current bar's trade imbalance into the decision.

---

## 3. Architectural & Structural Issues

### 3.1 — 🔴 CRITICAL: Broken [stats](file:///home/tstuv/workspace/trading/EDGEE/project/research/discovery.py#151-163) namespace shadow in [core/stats.py](file:///home/tstuv/workspace/trading/EDGEE/project/core/stats.py)

*(From first audit — confirmed still present)*

**File:** [core/stats.py](file:///home/tstuv/workspace/trading/EDGEE/project/core/stats.py)

The module-level name [stats](file:///home/tstuv/workspace/trading/EDGEE/project/research/discovery.py#151-163) is **only** set in the `except ImportError` fallback:
```python
try:
    from scipy import stats  # stats bound only during import statement
except ImportError:
    from project.core.stats_compat import stats  # bound to module-level
```

When `scipy` IS installed, `from scipy import stats` executes but the name [stats](file:///home/tstuv/workspace/trading/EDGEE/project/research/discovery.py#151-163) is scoped to the try-block. Subsequent code that does `from project.core.stats import stats` gets the **module itself** (since the module IS named [stats.py](file:///home/tstuv/workspace/trading/EDGEE/project/core/stats.py)), not `scipy.stats`.

---

### 3.2 — 🟠 HIGH: Risk allocator uses naive inverse-covariance with silent failure

**File:** [risk_allocator.py](file:///home/tstuv/workspace/trading/EDGEE/project/engine/risk_allocator.py#L393-L409)

```python
if limits.enable_correlation_allocation and len(requested) > 1:
    try:
        cov = diff.cov()
        inv_cov = np.linalg.inv(cov.values)
        ones = np.ones(len(inv_cov))
        weights = inv_cov @ ones
        weights = np.clip(weights, 0.0, None)
        ...
    except Exception:
        pass  # ← SILENT FAILURE
```

Problems:
1. **No regularization**: Raw `np.linalg.inv` on a sample covariance matrix. With correlated strategies or short windows, this is numerically unstable
2. **Silent fallback**: `except Exception: pass` — if the inversion fails (singular matrix, NaN values), it silently falls through to equal weighting with no logging
3. **Clipping negative weights to zero** distorts the optimization without re-normalizing properly

---

### 3.3 — 🟠 HIGH: Pipeline stage builder has no dependency graph validation

**File:** [stages/research.py](file:///home/tstuv/workspace/trading/EDGEE/project/pipelines/stages/research.py)

The 612-line [build_research_stages](file:///home/tstuv/workspace/trading/EDGEE/project/pipelines/stages/research.py#144-612) function constructs a linear list of [(name, script, args)](file:///home/tstuv/workspace/trading/EDGEE/project/core/stats.py#264-266) tuples. Stage ordering is implicit (list position), with comments like:

```python
# finalize_experiment must run AFTER all discovery stages
# The pipeline planner will handle the dependency if we add it to the name?
# Actually, the planner uses _resolve_dependencies which looks for patterns.
# Let's check that.
```

There is no explicit dependency graph or topological sort. If stage names change or new stages are inserted, ordering correctness silently breaks.

---

### 3.4 — 🟠 HIGH: OI detector family has massive code duplication

**File:** [oi.py](file:///home/tstuv/workspace/trading/EDGEE/project/events/families/oi.py)

[OISpikePositiveDetector](file:///home/tstuv/workspace/trading/EDGEE/project/events/families/oi.py#31-68), [OISpikeNegativeDetector](file:///home/tstuv/workspace/trading/EDGEE/project/events/families/oi.py#70-107), and [OIFlushDetector](file:///home/tstuv/workspace/trading/EDGEE/project/events/families/oi.py#109-148) share **identical** z-score computation logic (lines 36-43, 74-82, 113-123). The only differences are:
- The mask condition (`close_ret > 0` vs `close_ret < 0` vs `oi_pct_change <= threshold`)
- The context guard (`state_at_least` vs `state_at_most`)

This violates DRY and means any fix to the z-score computation must be applied 3× manually.

---

### 3.5 — 🟡 MEDIUM: [_gate_rank](file:///home/tstuv/workspace/trading/EDGEE/project/pipelines/research/update_campaign_memory.py#111-116) inner function duplicated twice in campaign memory

**File:** [update_campaign_memory.py](file:///home/tstuv/workspace/trading/EDGEE/project/pipelines/research/update_campaign_memory.py#L59-L62) and [L111-L115](file:///home/tstuv/workspace/trading/EDGEE/project/pipelines/research/update_campaign_memory.py#L111-L115)

Identical [_gate_rank](file:///home/tstuv/workspace/trading/EDGEE/project/pipelines/research/update_campaign_memory.py#111-116) closure defined in both [_build_belief_state](file:///home/tstuv/workspace/trading/EDGEE/project/pipelines/research/update_campaign_memory.py#48-99) and [_build_next_actions](file:///home/tstuv/workspace/trading/EDGEE/project/pipelines/research/update_campaign_memory.py#101-172). Extract to module-level.

---

### 3.6 — 🟡 MEDIUM: Basis family [detect()](file:///home/tstuv/workspace/trading/EDGEE/project/events/families/basis.py#70-108) overrides base class with copy-paste

**File:** [basis.py](file:///home/tstuv/workspace/trading/EDGEE/project/events/families/basis.py#L70-L107)

`BasisDislocationDetector.detect()` is a full copy of `BaseEventDetector.detect()` with minor adjustments. The base class method handles all the same logic (event emission, timestamp checking, metadata). The override exists only to add `basis_bps` and `basis_zscore` to metadata — this could be done via [compute_metadata()](file:///home/tstuv/workspace/trading/EDGEE/project/events/families/oi.py#22-29) override alone.

---

### 3.7 — 🟡 MEDIUM: [detect_basis_family](file:///home/tstuv/workspace/trading/EDGEE/project/events/families/basis.py#231-264) post-processing overwrites columns inconsistently

**File:** [basis.py](file:///home/tstuv/workspace/trading/EDGEE/project/events/families/basis.py#L255-L263)

```python
events['severity'] = events.get('event_score', events['evt_signal_intensity'])
events['intensity'] = events.get('evt_signal_intensity', events.get('event_score'))
```

This swaps the semantic meaning: [severity](file:///home/tstuv/workspace/trading/EDGEE/project/events/detectors/base.py#50-59) gets the numeric score, [intensity](file:///home/tstuv/workspace/trading/EDGEE/project/events/families/oi.py#228-230) gets the same numeric score. Both are mapped from the same underlying columns. The column `event_score` may not exist, causing it to default to `evt_signal_intensity` for both.

---

## 4. Logical Traps

### 4.1 — 🔴 CRITICAL: `promote/core.py` missing [pd](file:///home/tstuv/workspace/trading/EDGEE/project/core/stats.py#114-126) and `np` imports

*(From first audit — confirmed still present)*

**File:** [promotion/core.py](file:///home/tstuv/workspace/trading/EDGEE/project/research/promotion/core.py)

Will crash with `NameError` at runtime when promotion logic executes.

---

### 4.2 — 🔴 CRITICAL: [validate_strategy_family_params](file:///home/tstuv/workspace/trading/EDGEE/project/core/validation.py#261-348) discards validated output

*(From first audit — confirmed still present)*

**File:** [core/validation.py](file:///home/tstuv/workspace/trading/EDGEE/project/core/validation.py)

Validates parameters into local [norm](file:///home/tstuv/workspace/trading/EDGEE/project/core/stats.py#88-112) dict but never inserts them into the [out](file:///home/tstuv/workspace/trading/EDGEE/project/core/stats.py#76-80) dict that gets returned.

---

### 4.3 — 🟠 HIGH: Discovery engine O(n²) sequence trigger

**File:** [discovery.py](file:///home/tstuv/workspace/trading/EDGEE/project/research/discovery.py#L382-L389)

```python
def has_recent_e1(row):
    if row["event_type"] != e2: return False
    recent = e1_times[(e1_times < row["enter_ts"]) & ...]
    return not recent.empty

trigger_mask &= working.apply(has_recent_e1, axis=1)
```

`DataFrame.apply` with a Python function that filters a Series on every row creates O(n²) complexity. For 100K event rows, this becomes impractical.

**Fix:** Use `pd.merge_asof` or `np.searchsorted` as suggested in the comment.

---

### 4.4 — 🟠 HIGH: [_clamp_positions](file:///home/tstuv/workspace/trading/EDGEE/project/engine/risk_allocator.py#42-56) dual-definition (numba / pure-Python) is brittle

**File:** [risk_allocator.py](file:///home/tstuv/workspace/trading/EDGEE/project/engine/risk_allocator.py#L23-L55)

The numba `@njit` version and the pure-Python fallback are **copy-pasted** with identical logic. If one is modified without the other, behavior silently diverges depending on whether numba is installed.

---

### 4.5 — 🟡 MEDIUM: [CrossVenueDesyncDetector](file:///home/tstuv/workspace/trading/EDGEE/project/events/families/basis.py#110-130) renames columns incorrectly

**File:** [basis.py](file:///home/tstuv/workspace/trading/EDGEE/project/events/families/basis.py#L116)

```python
work = df.rename(columns={'close': 'close_spot', 'perp_close': 'close_perp'})
```

If the input DataFrame has [close](file:///home/tstuv/workspace/trading/EDGEE/project/pipelines/features/build_features.py#123-146) (standard column), it gets renamed to `close_spot`. But if the DataFrame ALSO has `close_perp` and `close_spot` already (the required schema from line 112), the rename creates **duplicates** or overwrites the existing `close_spot` with the generic close.

---

## 5. Dead Code & Redundancy

### 5.1 — 🟠 HIGH: [shrinkage.py](file:///home/tstuv/workspace/trading/EDGEE/project/research/helpers/shrinkage.py) is a pure re-export facade

**File:** [shrinkage.py](file:///home/tstuv/workspace/trading/EDGEE/project/research/helpers/shrinkage.py)

This 60-line file contains zero logic — it only re-exports from `parameter_normalization`, `estimation_kernels`, and [diagnostics](file:///home/tstuv/workspace/trading/EDGEE/project/research/bridge_evaluation.py#79-127). The `__all__` list exposes 16 private-prefix functions (all starting with `_`). This is an API surface smell — private functions shouldn't be the public API.

---

### 5.2 — 🟡 MEDIUM: 4 root-level migration scripts that appear to be one-shot

*(From first audit)* [fix_imports.py](file:///home/tstuv/workspace/trading/EDGEE/fix_imports.py), [fix_temporal.py](file:///home/tstuv/workspace/trading/EDGEE/fix_temporal.py), [migrate_strategies.py](file:///home/tstuv/workspace/trading/EDGEE/migrate_strategies.py), `rename_imports.py` — no evidence these are part of ongoing workflow.

---

### 5.3 — 🟡 MEDIUM: [OIShockDetector](file:///home/tstuv/workspace/trading/EDGEE/project/events/families/oi.py#150-183) legacy wrapper

**File:** [oi.py](file:///home/tstuv/workspace/trading/EDGEE/project/events/families/oi.py#L150-L183)

[OIShockDetector](file:///home/tstuv/workspace/trading/EDGEE/project/events/families/oi.py#150-183) exists for "backward compatibility" but instantiates fresh `OISpikePositive/Negative/FlushDetector()` objects on every [prepare_features](file:///home/tstuv/workspace/trading/EDGEE/project/events/families/basis.py#25-56) call. It re-computes everything 3× (lines 157-159) just to merge features.

---

### 5.4 — 🟡 MEDIUM: 83+ bare `except Exception:` handlers

*(From first audit — confirmed across project.*)

Silently swallowing failures across the codebase makes it extremely difficult to diagnose production issues.

---

## 6. Security Considerations

### 6.1 — 🟡 MEDIUM: No sanitization on file paths from CLI args

**Files:** Multiple pipeline scripts accept `--concept_file`, `--experiment_config`, `--data_root` as raw paths:

- [research.py L162-163](file:///home/tstuv/workspace/trading/EDGEE/project/pipelines/stages/research.py#L162-L163) — [open(args.experiment_config, "r")](file:///home/tstuv/workspace/trading/EDGEE/project/engine/pnl.py#29-55)
- [discovery.py L202](file:///home/tstuv/workspace/trading/EDGEE/project/research/discovery.py#L202) — `load_yaml_path(concept_file)`

These are typically internal research tools, but if exposed as services, path traversal is possible.

### 6.2 — 🟡 MEDIUM: `json.loads` on unsanitized manifest data

**File:** [update_campaign_memory.py](file:///home/tstuv/workspace/trading/EDGEE/project/pipelines/research/update_campaign_memory.py#L138)

```python
recommended_experiment = json.loads(str(reflection.get("recommended_next_experiment", "{}")))
```

If `recommended_next_experiment` contains crafted JSON this passes silently; but the `except JSONDecodeError` fallback to `{}` is correct. Low real risk in a research sandbox.

---

## 7. Prioritized Action Items

### Immediate (Critical — will cause runtime failures or incorrect results)

| # | Issue | File | Action |
|---|-------|------|--------|
| 1 | Missing [pd](file:///home/tstuv/workspace/trading/EDGEE/project/core/stats.py#114-126)/`np` imports | [promotion/core.py](file:///home/tstuv/workspace/trading/EDGEE/project/research/promotion/core.py) | Add imports |
| 2 | [validate_strategy_family_params](file:///home/tstuv/workspace/trading/EDGEE/project/core/validation.py#261-348) discards output | [core/validation.py](file:///home/tstuv/workspace/trading/EDGEE/project/core/validation.py) | Insert validated params into [out](file:///home/tstuv/workspace/trading/EDGEE/project/core/stats.py#76-80) |
| 3 | Broken [stats](file:///home/tstuv/workspace/trading/EDGEE/project/research/discovery.py#151-163) namespace shadow | [core/stats.py](file:///home/tstuv/workspace/trading/EDGEE/project/core/stats.py) | Fix import binding |
| 4 | `basis_bps` missing PIT lag | `build_features.py:170` | Add `.shift(1)` |
| 5 | Double overlap correction (dead `n_eff`) | `evaluator.py:263` | Remove unused overlap_density correction |
| 6 | [compute_direction](file:///home/tstuv/workspace/trading/EDGEE/project/events/detectors/base.py#27-33) shadowed | `base.py:27+60` | Remove duplicate method |

### Short-term (High — degrades research quality)

| # | Issue | File | Action |
|---|-------|------|--------|
| 7 | Naive t-stat on overlapping returns | `discovery.py:161` | Apply overlap correction |
| 8 | Weak stress survival threshold | `evaluator.py:327` | Raise to t > 1.0 |
| 9 | Inverse-cov with silent failure | `risk_allocator.py:400` | Add regularization + logging |
| 10 | No dependency graph in stage builder | [stages/research.py](file:///home/tstuv/workspace/trading/EDGEE/project/pipelines/stages/research.py) | Add explicit DAG |
| 11 | O(n²) sequence trigger | `discovery.py:389` | Use searchsorted |
| 12 | OI detector z-score duplication | [oi.py](file:///home/tstuv/workspace/trading/EDGEE/project/events/families/oi.py) | Extract shared computation |
| 13 | `ms_imbalance_24` missing PIT lag | `build_features.py:440` | Add `.shift(1)` |
| 14 | Sharpe annualization for sparse events | `evaluator.py:352` | Floor or cap |

### Medium-term (Medium — tech debt, maintainability)

| # | Issue | File | Action |
|---|-------|------|--------|
| 15 | [_clamp_positions](file:///home/tstuv/workspace/trading/EDGEE/project/engine/risk_allocator.py#42-56) dual definition | `risk_allocator.py:23-55` | Single source |
| 16 | [_gate_rank](file:///home/tstuv/workspace/trading/EDGEE/project/pipelines/research/update_campaign_memory.py#111-116) duplication | [update_campaign_memory.py](file:///home/tstuv/workspace/trading/EDGEE/project/pipelines/research/update_campaign_memory.py) | Extract to module-level |
| 17 | [detect()](file:///home/tstuv/workspace/trading/EDGEE/project/events/families/basis.py#70-108) copy-paste in basis family | `basis.py:70-107` | Use [compute_metadata()](file:///home/tstuv/workspace/trading/EDGEE/project/events/families/oi.py#22-29) override |
| 18 | [shrinkage.py](file:///home/tstuv/workspace/trading/EDGEE/project/research/helpers/shrinkage.py) private API re-export | [shrinkage.py](file:///home/tstuv/workspace/trading/EDGEE/project/research/helpers/shrinkage.py) | Proper public interface |
| 19 | rv_pct_17280 warmup fill with 50 | `build_features.py:494` | Use NaN or regime-aware fill |
| 20 | Root-level migration scripts | root | Archive or delete |

---

## 8. Systemic Patterns

### Pattern A: "Except Exception: pass" culture
83+ instances across the codebase create a culture where failures are invisible. This is particularly dangerous in:
- Risk allocator (correlation allocation failures silently become equal-weight)
- Feature loading (missing data silently becomes NaN without logging)
- Config parsing (malformed YAML silently uses defaults)

**Recommendation:** Establish a project-wide policy: `except Exception as e: log.warning(...)` at minimum. Critical paths (risk, PnL, promotion) should raise or use explicit fallback with logging.

### Pattern B: Inconsistent PIT lag discipline
Some features apply `.shift(1)` consistently (`rv_96`, `funding_abs`, `range_med_2880`), while others don't (`basis_bps`, `ms_imbalance_24`). The PIT contract system exists (`TemporalContract`) but isn't enforced at the feature table level.

**Recommendation:** Add an assertion in [_ensure_feature_contract_columns](file:///home/tstuv/workspace/trading/EDGEE/project/pipelines/features/build_features.py#383-442) that validates all numeric features are properly lagged, or add a feature metadata registry that declares lag status.

### Pattern C: Statistical gates use inconsistent inference
The search evaluator uses Newey-West + time-decay weighting (sophisticated), while the legacy discovery path uses naive `mean / (std / sqrt(n))` (simple). Candidates promoted through different paths face different statistical bars.

**Recommendation:** Unify the statistical inference path into a single function used by both evaluator and discovery.
