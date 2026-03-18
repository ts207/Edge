# Technical Debt Remediation Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Address all actionable findings from the March 2026 Technical Debt Audit — removing dead code, fixing a confirmed PIT violation, eliminating compat wrappers, and parameterizing hardcoded limits — without breaking the pipeline or any existing tests.

**Architecture:** Work proceeds in risk-ordered tiers: pure deletion first, correctness-critical bug fixes second, structural removals third, and parameterization last. Each task is self-contained and leaves the test suite passing.

**Tech Stack:** Python 3.11+, pytest, project pipeline (`project/pipelines/run_all.py`), ruff for lint.

---

## Scope

### IN-SCOPE (this plan)

| Finding | Description |
|---|---|
| DC-001 | Delete `project/scripts/tmp_debug_eval.py` dead debug script |
| LI-002 | Remove `tests/test_legacy_wrapper_packages_removed.py` meta-test |
| TS-001 | Remove `tests/compat/test_legacy_surfaces_removed.py` scaffolding |
| TS-002 | Remove `tests/test_no_legacy_wrapper_imports.py` redundant lint test |
| TS-003 | Remove `tests/scripts/test_review_tool_history.sh` fragile shell test |
| LT-003 | Fix PIT violation in `FeeRegimeChangeDetector` (`shift(-1)` lookahead) |
| LT-004 | Fix `ScheduledNewsDetector` ignoring spec params when any news column present |
| RD-001 | Remove `project/execution/backtest/engine.py` compat wrapper |
| RD-002 | Remove `project/execution/runtime/dsl_interpreter.py` compat wrapper |
| IP-003 | Remove `project/infra/orchestration/run_all.py` compat wrapper |
| RL-002 | Remove unused ms_roll_24, ms_amihud_24, ms_kyle_24, ms_vpin_24 from features |
| LI-003 | Rename `legacy_aliases.py` to `extended_detectors.py` — real detectors wrongly named |
| IP-001 | Parameterize hardcoded `concentration_cap` (5%) in `sizing.py` |
| IP-002 | Parameterize hardcoded kelly `confidence_multiplier` clip (5.0) in `sizing.py` |

### OUT-OF-SCOPE (needs separate plans or research decisions)

| Finding | Reason |
|---|---|
| DC-002 | Old plans in `docs/plans/` — no action needed; they are reference history |
| LI-001 | `project/strategy/runtime/` has real modules mirroring `project/strategy/`; requires migration plan, callers in 9 files |
| RL-001 | `build_context_features.py` identity pass has downstream consumers (`validate_context_entropy`); requires pipeline contract rewrite |
| RL-003 | Detector base class unification — significant refactor of detection hierarchy |
| LT-001 | Redundant market states — research decision on hypothesis pruning |
| LT-002 | OI data source mismatch (1m vs 5m) — data pipeline investigation |
| LT-005 | Unshifted rolling quantile audit — systematic audit across all detectors needed |
| RD-003/4/5 | Internal code consolidation (`detect_temporal_family`, `core.py`, `validation.py`) |
| SF-001–004 | Statistical fragility — algorithm design decisions |
| SL-001–004 | Scaling bottlenecks — infrastructure architecture decisions |

---

## File Map

**Deleted:**
- `project/scripts/tmp_debug_eval.py`
- `tests/test_legacy_wrapper_packages_removed.py`
- `tests/compat/test_legacy_surfaces_removed.py`
- `tests/test_no_legacy_wrapper_imports.py`
- `tests/scripts/test_review_tool_history.sh`
- `project/execution/backtest/engine.py`
- `project/execution/runtime/dsl_interpreter.py`
- `project/infra/orchestration/run_all.py`

**Modified:**
- `project/events/families/temporal.py` — fix PIT violation (LT-003), fix ScheduledNewsDetector (LT-004)
- `project/pipelines/features/build_features.py` — remove 4 unused ms_* features (RL-002)
- `project/events/detectors/legacy_aliases.py` → rename to `extended_detectors.py`
- `project/events/detectors/__init__.py` — update import to new filename
- `project/events/detectors/catalog.py` — update import if present
- `project/execution/backtest/__init__.py` — import directly from `project.engine.runner`
- `project/execution/runtime/__init__.py` — import directly from `project.strategy.runtime`
- `project/execution/__init__.py` — import directly from canonical sources
- `project/infra/orchestration/__init__.py` — import directly from `project.pipelines.run_all`
- `tests/contracts/test_cosmetic_package_layout.py` — update imports after compat removal
- `project/portfolio/sizing.py` — parameterize concentration_cap and kelly clip

**Created:**
- `tests/events/test_fee_regime_pit_fix.py` — regression test for LT-003
- `tests/events/test_scheduled_news_detector.py` — regression test for LT-004
- `tests/pipelines/features/test_unused_ms_features_removed.py` — guard for RL-002

---

## Task 1: Safe Deletions

**Files:**
- Delete: `project/scripts/tmp_debug_eval.py`
- Delete: `tests/test_legacy_wrapper_packages_removed.py`
- Delete: `tests/compat/test_legacy_surfaces_removed.py`
- Delete: `tests/test_no_legacy_wrapper_imports.py`
- Delete: `tests/scripts/test_review_tool_history.sh`

- [ ] **Step 1: Verify no callers for tmp_debug_eval.py**

```bash
PYTHONPATH=. grep -r "tmp_debug_eval" project/ tests/ --include="*.py" | grep -v "tmp_debug_eval.py"
```

Expected: no output (zero callers).

- [ ] **Step 2: Verify no callers for the test files being removed**

```bash
PYTHONPATH=. grep -r "test_legacy_wrapper_packages_removed\|test_legacy_surfaces_removed\|test_no_legacy_wrapper_imports\|test_review_tool_history" project/ tests/ --include="*.py" --include="*.sh" --include="*.yaml" | grep -v "^tests/test_legacy_wrapper_packages_removed\|^tests/compat\|^tests/test_no_legacy_wrapper\|^tests/scripts/test_review_tool"
```

Expected: no output.

- [ ] **Step 3: Delete the files**

```bash
rm project/scripts/tmp_debug_eval.py
rm tests/test_legacy_wrapper_packages_removed.py
rm tests/compat/test_legacy_surfaces_removed.py
rm tests/test_no_legacy_wrapper_imports.py
rm tests/scripts/test_review_tool_history.sh
```

- [ ] **Step 4: Remove now-empty compat dir if empty**

```bash
rmdir tests/compat 2>/dev/null || echo "compat not empty, leave it"
```

- [ ] **Step 5: Run tests to confirm nothing broke**

```bash
PYTHONPATH=. python -m pytest tests/ -x -q --tb=short 2>&1 | tail -20
```

Expected: all tests pass (no collection errors for missing files).

- [ ] **Step 6: Commit**

```bash
git add -u
git commit -m "chore: remove dead debug script and obsolete meta-tests (DC-001, LI-002, TS-001, TS-002, TS-003)"
```

---

## Task 2: Fix PIT Violation in FeeRegimeChangeDetector (LT-003)

**Files:**
- Modify: `project/events/families/temporal.py:263`
- Create: `tests/events/families/test_fee_regime_pit_fix.py`

**Background:** Line 263 of `temporal.py` uses `fee.shift(-1)` — a forward lookahead. The original intent is to detect "fee changes that persist". The PIT-safe equivalent: fire on the *second* bar at the new fee level, i.e., when `fee[T] == fee[T-1]` AND `fee[T] != fee[T-2]`. This is fully historical at bar T.

- [ ] **Step 1: Write the failing test**

Create `tests/events/test_fee_regime_pit_fix.py` (place in the existing `tests/events/` directory):

```python
"""Regression test: FeeRegimeChangeDetector must not use future data."""
from __future__ import annotations
import pandas as pd
import numpy as np
from project.events.families.temporal import FeeRegimeChangeDetector


def _make_fee_df(fee_values: list[float]) -> pd.DataFrame:
    n = len(fee_values)
    ts = pd.date_range("2024-01-01", periods=n, freq="5min", tz="UTC")
    return pd.DataFrame({
        "timestamp": ts,
        "fee_bps": fee_values,
        "close": np.ones(n),
    })


def test_fee_regime_detector_no_future_lookahead():
    """Detector must not fire on the bar BEFORE a fee change is confirmed.

    Bars 0-9: fee=1.0 (stable baseline)
    Bar 10:   fee=2.0 (first bar at new level — NOT confirmed yet, must NOT fire)
    Bar 11+:  fee=2.0 (second+ bar — confirmed, detector MAY fire starting here)
    """
    fees = [1.0] * 10 + [2.0] * 5
    df = _make_fee_df(fees)
    det = FeeRegimeChangeDetector()
    events = det.detect(df, symbol="BTC")

    # Bar index 10 timestamp = 2024-01-01 00:50:00 UTC
    # First permissible fire is bar 11 = 2024-01-01 00:55:00 UTC
    forbidden_ts = pd.Timestamp("2024-01-01 00:50:00", tz="UTC")
    fire_times = [pd.to_datetime(e["timestamp"]) for e in events]
    assert forbidden_ts not in fire_times, (
        f"Detector fired at {forbidden_ts} — the first bar of a fee change before "
        "it was confirmed. This indicates future lookahead (LT-003)."
    )


def test_fee_regime_fires_only_after_confirmation():
    """Detector must fire at the confirmed bar (second bar at new level), not before.

    Bar 0-19: fee=1.0 (stable)
    Bar 20:   fee=3.0 (unconfirmed — must NOT fire)
    Bar 21:   fee=3.0 (confirmed — detector should fire here)
    Bar 22+:  fee=3.0 (stable at new level)
    """
    fees = [1.0] * 20 + [3.0] * 5
    df = _make_fee_df(fees)
    det = FeeRegimeChangeDetector()
    events = det.detect(df, symbol="BTC")

    fire_times = [pd.to_datetime(e["timestamp"]) for e in events]
    # Bar 20 (index 20): 2024-01-01 01:40:00 UTC — must NOT fire
    # Bar 21 (index 21): 2024-01-01 01:45:00 UTC — may fire
    forbidden = pd.Timestamp("2024-01-01 01:40:00", tz="UTC")
    assert forbidden not in fire_times, (
        "Detector fired at bar 20 (first bar of change) — future lookahead present."
    )
    # At least one event should exist (at bar 21 or later)
    assert len(events) > 0, "Detector produced no events at all for a clear regime change."
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
PYTHONPATH=. python -m pytest tests/events/test_fee_regime_pit_fix.py -v
```

Expected: FAIL — `test_fee_regime_detector_no_future_lookahead` fires at the forbidden bar due to `shift(-1)` lookahead.

- [ ] **Step 3: Read the current implementation**

Read `project/events/families/temporal.py` lines 242–285 to confirm the exact location before editing.

- [ ] **Step 4: Fix the PIT violation**

In `project/events/families/temporal.py`, replace the lookahead with a confirmed-shift detection:

Find:
```python
            persistent_shift = (fee != fee.shift(1)) & (fee.shift(-1) == fee)
```

Replace with:
```python
            # PIT-safe: fires on the second bar at the new fee level (fully historical).
            # fee[T] == fee[T-1] means fee has persisted for at least one bar.
            # fee[T] != fee[T-2] means the previous bar was a regime change.
            # fee.shift(2).notna() guard prevents spurious fires at series start (bars 0-1).
            persistent_shift = (
                fee.shift(2).notna()
                & (fee == fee.shift(1))
                & (fee != fee.shift(2))
            )
```

- [ ] **Step 5: Run the test to verify it passes**

```bash
PYTHONPATH=. python -m pytest tests/events/test_fee_regime_pit_fix.py -v
```

Expected: PASS.

- [ ] **Step 6: Run the full event family tests**

```bash
PYTHONPATH=. python -m pytest tests/events/ -x -q --tb=short 2>&1 | tail -20
```

Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add project/events/families/temporal.py tests/events/test_fee_regime_pit_fix.py
git commit -m "fix: replace shift(-1) lookahead in FeeRegimeChangeDetector with PIT-safe confirmed-shift logic (LT-003)"
```

---

## Task 3: Fix ScheduledNewsDetector Spec Parameter Bypass (LT-004)

**Files:**
- Modify: `project/events/families/temporal.py:103–121`
- Create: `tests/events/families/test_scheduled_news_detector.py`

**Background:** `compute_raw_mask` short-circuits to `return features['news_mask_col']` as soon as *any* column named `scheduled_news_event`, `news_event`, etc. is present, completely bypassing the `spec_params.get('windows_utc', [])` logic. The fix: always merge the column-based mask with the spec-window mask using OR. If neither source has data, return all-False.

- [ ] **Step 1: Write the failing test**

Create `tests/events/test_scheduled_news_detector.py` (place in the existing `tests/events/` directory):

```python
"""Regression: ScheduledNewsDetector must apply spec windows even when news columns exist."""
from __future__ import annotations
import pandas as pd
import numpy as np
from unittest.mock import patch
from project.events.families.temporal import ScheduledNewsDetector


def _make_df(n: int = 100, add_news_col: bool = False) -> pd.DataFrame:
    ts = pd.date_range("2024-01-01 12:00", periods=n, freq="5min", tz="UTC")
    df = pd.DataFrame({"timestamp": ts, "close": np.ones(n)})
    if add_news_col:
        # Column present but all-False — should NOT mask out spec windows
        df["scheduled_news_event"] = False
    return df


def test_spec_windows_applied_when_news_col_all_false():
    """When news column exists but is all-False, spec windows should still trigger."""
    df = _make_df(add_news_col=True)

    fake_spec = {
        "parameters": {
            "windows_utc": [{"hour": 12, "minute_start": 0, "minute_end": 10}]
        }
    }
    det = ScheduledNewsDetector()
    with patch("project.events.families.temporal.load_event_spec", return_value=fake_spec):
        events = det.detect(df, symbol="BTC")

    # bars 0–2 are in 12:00–12:10 UTC window
    assert len(events) > 0, (
        "Detector returned no events even though spec window covers 12:00-12:10 "
        "and news column is all-False. LT-004 not fixed."
    )


def test_news_col_true_takes_precedence():
    """When news column has True entries, those bars should still fire."""
    df = _make_df(add_news_col=False)
    df["scheduled_news_event"] = False
    df.loc[5, "scheduled_news_event"] = True

    det = ScheduledNewsDetector()
    with patch("project.events.families.temporal.load_event_spec", return_value={"parameters": {"windows_utc": []}}):
        events = det.detect(df, symbol="BTC")

    fire_times = {pd.to_datetime(e["timestamp"]) for e in events}
    expected = df["timestamp"].iloc[5]
    assert expected in fire_times, "Bar with news_col=True should fire even with empty spec windows."
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
PYTHONPATH=. python -m pytest tests/events/test_scheduled_news_detector.py -v
```

Expected: `test_spec_windows_applied_when_news_col_all_false` FAILS.

- [ ] **Step 3: Fix the bypass logic**

In `project/events/families/temporal.py`, replace the `compute_raw_mask` for `ScheduledNewsDetector`:

Find (lines ~103-121):
```python
    def compute_raw_mask(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        if features['news_mask_col'].any():
            return features['news_mask_col']

        ts = features['ts']
        hh = ts.dt.hour
        mm = ts.dt.minute
        spec = load_event_spec(self.event_type)
        spec_params = spec.get('parameters', {}) if isinstance(spec, dict) else {}
        windows = spec_params.get('windows_utc', [])
        mask = pd.Series(False, index=df.index, dtype=bool)
        for win in windows:
            if not isinstance(win, dict): continue
            hour = int(win.get('hour', -1))
            m_start = int(win.get('minute_start', 25))
            m_end = int(win.get('minute_end', 35))
            if hour != -1:
                mask = mask | ((hh == hour) & mm.between(m_start, m_end))
        return mask.fillna(False)
```

Replace with:
```python
    def compute_raw_mask(self, df: pd.DataFrame, *, features: dict[str, pd.Series], **params: Any) -> pd.Series:
        # Always evaluate spec windows — do not short-circuit on column presence.
        ts = features['ts']
        hh = ts.dt.hour
        mm = ts.dt.minute
        spec = load_event_spec(self.event_type)
        spec_params = spec.get('parameters', {}) if isinstance(spec, dict) else {}
        windows = spec_params.get('windows_utc', [])
        spec_mask = pd.Series(False, index=df.index, dtype=bool)
        for win in windows:
            if not isinstance(win, dict): continue
            hour = int(win.get('hour', -1))
            m_start = int(win.get('minute_start', 25))
            m_end = int(win.get('minute_end', 35))
            if hour != -1:
                spec_mask = spec_mask | ((hh == hour) & mm.between(m_start, m_end))
        # Merge column-based mask with spec windows via OR.
        return (spec_mask | features['news_mask_col']).fillna(False)
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
PYTHONPATH=. python -m pytest tests/events/test_scheduled_news_detector.py -v
```

Expected: both tests PASS.

- [ ] **Step 5: Run full events test suite**

```bash
PYTHONPATH=. python -m pytest tests/events/ -x -q --tb=short 2>&1 | tail -20
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add project/events/families/temporal.py tests/events/test_scheduled_news_detector.py
git commit -m "fix: ScheduledNewsDetector now merges spec-window mask with column mask instead of bypassing spec (LT-004)"
```

---

## Task 4: Remove Compat Wrappers (RD-001, RD-002, IP-003)

**Files:**
- Delete: `project/execution/backtest/engine.py`
- Delete: `project/execution/runtime/dsl_interpreter.py`
- Delete: `project/infra/orchestration/run_all.py`
- Modify: `project/execution/backtest/__init__.py`
- Modify: `project/execution/runtime/__init__.py`
- Modify: `project/execution/__init__.py`
- Modify: `project/infra/orchestration/__init__.py`
- Modify: `tests/contracts/test_cosmetic_package_layout.py`

**Background:** Each compat wrapper is a 3–5 line file that re-exports from the canonical source. The fix is to make the `__init__.py` of the parent package import directly from the canonical source, then delete the wrapper file. The contract test also imports directly from the wrapper paths and needs updating.

- [ ] **Step 1: Run the contract test baseline**

```bash
PYTHONPATH=. python -m pytest tests/contracts/test_cosmetic_package_layout.py -v
```

Expected: all pass (baseline).

- [ ] **Step 2: Update execution/backtest/__init__.py**

Read `project/execution/backtest/__init__.py`, then change:

```python
from project.execution.backtest.engine import run_engine
```

to:

```python
from project.engine.runner import run_engine
```

- [ ] **Step 3: Update execution/runtime/__init__.py**

Read `project/execution/runtime/__init__.py`, then change (check what is currently there; it currently imports from `dsl_interpreter`):

```python
from project.strategy.runtime import DslInterpreterV1, generate_positions_numba
```

(If the file is currently importing from `dsl_interpreter`, replace with the direct canonical import.)

- [ ] **Step 4: Update execution/__init__.py**

Read `project/execution/__init__.py`, then change:

```python
from project.execution.backtest.engine import run_engine
from project.execution.runtime.dsl_interpreter import DslInterpreterV1
```

to:

```python
from project.engine.runner import run_engine
from project.strategy.runtime import DslInterpreterV1
```

- [ ] **Step 5: Update infra/orchestration/__init__.py**

Read `project/infra/orchestration/__init__.py`, then change:

```python
from project.infra.orchestration.run_all import main as run_all_main
```

to:

```python
from project.pipelines.run_all import main as run_all_main
```

- [ ] **Step 6: Update the contract test**

Read `tests/contracts/test_cosmetic_package_layout.py` lines 16–19, then change:

```python
from project.execution.backtest.engine import run_engine
from project.execution.runtime.dsl_interpreter import DslInterpreterV1
from project.infra.orchestration.run_all import main as run_all_main
```

to:

```python
from project.engine.runner import run_engine
from project.strategy.runtime import DslInterpreterV1
from project.pipelines.run_all import main as run_all_main
```

- [ ] **Step 7: Delete the wrapper files**

```bash
rm project/execution/backtest/engine.py
rm project/execution/runtime/dsl_interpreter.py
rm project/infra/orchestration/run_all.py
```

- [ ] **Step 8: Run the contract test to confirm it still passes**

```bash
PYTHONPATH=. python -m pytest tests/contracts/test_cosmetic_package_layout.py -v
```

Expected: all pass.

- [ ] **Step 9: Run the full test suite**

```bash
PYTHONPATH=. python -m pytest tests/ -x -q --tb=short 2>&1 | tail -20
```

Expected: all pass.

- [ ] **Step 10: Commit**

```bash
git add -u
git commit -m "refactor: remove compat wrappers for execution/backtest, execution/runtime, infra/orchestration (RD-001, RD-002, IP-003)"
```

---

## Task 5: Remove Unused Microstructure Features (RL-002)

**Files:**
- Modify: `project/pipelines/features/build_features.py:437–440`
- Create: `tests/pipelines/features/test_unused_ms_features_removed.py`

**Background:** `ms_roll_24`, `ms_amihud_24`, `ms_kyle_24`, `ms_vpin_24` are computed in `build_features.py` but grep confirms zero detectors reference these columns. Removing them saves ~15% storage per run.

- [ ] **Step 1: Confirm zero detector usage**

```bash
PYTHONPATH=. grep -r "ms_roll_24\|ms_amihud_24\|ms_kyle_24\|ms_vpin_24" project/events/ project/features/ --include="*.py"
```

Expected: no output (zero callers in detector/feature code).

- [ ] **Step 2: Write the guard test**

Create `tests/pipelines/features/test_unused_ms_features_removed.py` (in the existing directory):

```python
"""Guard: unused microstructure features must not be computed in build_features."""
from __future__ import annotations
import ast
from pathlib import Path

REMOVED_COLUMNS = {"ms_roll_24", "ms_amihud_24", "ms_kyle_24", "ms_vpin_24"}
# Anchor the path to this file's location so the test works from any working directory.
BUILD_FEATURES_PATH = Path(__file__).resolve().parents[3] / "project" / "pipelines" / "features" / "build_features.py"


def test_removed_ms_features_not_assigned():
    source = BUILD_FEATURES_PATH.read_text()
    tree = ast.parse(source)
    assigned_keys = set()
    for node in ast.walk(tree):
        # Catch `out["ms_roll_24"] = ...` patterns
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Subscript):
                    if isinstance(target.slice, ast.Constant):
                        assigned_keys.add(target.slice.value)
    still_present = REMOVED_COLUMNS & assigned_keys
    assert not still_present, f"Removed ms_* features still assigned: {still_present}"
```

- [ ] **Step 3: Run the test to verify it fails**

```bash
PYTHONPATH=. python -m pytest tests/pipelines/features/test_unused_ms_features_removed.py -v
```

Expected: FAIL (features are still assigned).

- [ ] **Step 4: Read the build_features.py section to remove**

Read `project/pipelines/features/build_features.py` lines 430–445 to see surrounding context.

- [ ] **Step 5: Remove the four ms_* assignments**

In `project/pipelines/features/build_features.py`, remove the four lines:

```python
    out["ms_roll_24"] = calculate_roll_spread_bps(close, window=24)
    out["ms_amihud_24"] = calculate_amihud_illiquidity(close, total_volume, window=24)
    out["ms_kyle_24"] = calculate_kyle_lambda(close, buy_volume, sell_volume, window=24)
    out["ms_vpin_24"] = calculate_vpin_score(total_volume, buy_volume, window=24)
```

Also check whether `calculate_roll_spread_bps`, `calculate_amihud_illiquidity`, `calculate_kyle_lambda`, `calculate_vpin_score` are used elsewhere in the file. If these are the only call sites, remove their imports too. Run:

```bash
PYTHONPATH=. grep -n "calculate_roll_spread_bps\|calculate_amihud_illiquidity\|calculate_kyle_lambda\|calculate_vpin_score" project/pipelines/features/build_features.py
```

If each appears only once (the removed line), also remove the corresponding import.

- [ ] **Step 6: Run the guard test to verify it passes**

```bash
PYTHONPATH=. python -m pytest tests/pipelines/features/test_unused_ms_features_removed.py -v
```

Expected: PASS.

- [ ] **Step 7: Run full tests**

```bash
PYTHONPATH=. python -m pytest tests/ -x -q --tb=short 2>&1 | tail -25
```

Expected: all pass.

- [ ] **Step 8: Commit**

```bash
git add project/pipelines/features/build_features.py tests/pipelines/features/test_unused_ms_features_removed.py
git commit -m "perf: remove unused ms_roll_24/amihud/kyle/vpin features from build_features (~15% storage reduction) (RL-002)"
```

---

## Task 6: Rename legacy_aliases.py to extended_detectors.py (LI-003)

**Files:**
- Delete: `project/events/detectors/legacy_aliases.py`
- Create: `project/events/detectors/extended_detectors.py` (same content, new name)
- Modify: any files importing from `legacy_aliases`

**Background:** `legacy_aliases.py` contains real, actively-used detector classes (BasisSnapbackDetector, OIVolDivergenceDetector, etc.). The filename implies they are aliases of renamed events — they are not. Renaming to `extended_detectors.py` removes that false impression and reduces registry bloat perception.

- [ ] **Step 1: Find all importers of legacy_aliases**

```bash
PYTHONPATH=. grep -r "legacy_aliases" project/ tests/ --include="*.py" -l
```

Note every file returned.

- [ ] **Step 2: Create extended_detectors.py with the same content**

Read `project/events/detectors/legacy_aliases.py` in full, then write `project/events/detectors/extended_detectors.py` with identical content (no logic changes).

- [ ] **Step 3: Update all import sites**

For each file found in Step 1, change:

```python
from project.events.detectors.legacy_aliases import ...
# or
import project.events.detectors.legacy_aliases
```

to the equivalent using `extended_detectors`.

- [ ] **Step 4: Delete the old file**

```bash
rm project/events/detectors/legacy_aliases.py
```

- [ ] **Step 5: Run the detector registry test**

```bash
PYTHONPATH=. python -m pytest tests/events/ tests/contracts/ -x -q --tb=short 2>&1 | tail -20
```

Expected: all pass (all detectors still register correctly).

- [ ] **Step 6: Commit**

```bash
git add -u project/events/detectors/
git commit -m "refactor: rename legacy_aliases.py to extended_detectors.py — these are real detectors, not aliases (LI-003)"
```

---

## Task 7: Parameterize Hardcoded Portfolio Limits (IP-001, IP-002)

**Files:**
- Modify: `project/portfolio/sizing.py:70,81`
- Test: existing sizing tests in `tests/portfolio/`

**Background:** `concentration_cap = portfolio_value * 0.05` (line 81) and `np.clip(edge / risk_variance, 0.0, 5.0)` (line 70) are hardcoded. These should be read from a `SizingPolicy` or function parameters so that research and live configurations can differ without code changes.

- [ ] **Step 1: Read the full sizing function**

Read `project/portfolio/sizing.py` lines 60–115.

- [ ] **Step 2: Find existing tests**

```bash
PYTHONPATH=. python -m pytest tests/engine/ --collect-only -q 2>&1 | grep -i sizing | head -20
```

Note existing test names covering the sizing function. The relevant file is `tests/engine/test_portfolio_aggregation.py`.

- [ ] **Step 3: Write failing tests for parameterized limits**

Create `tests/engine/test_sizing_parameterized.py` (in the existing `tests/engine/` directory):

```python
"""Tests that sizing limits are not hardcoded and can be overridden."""
from project.portfolio.sizing import calculate_target_notional  # adjust to actual fn name


def test_concentration_cap_is_overridable():
    """concentration_cap must not be hardcoded — caller can supply a different value."""
    base = calculate_target_notional(
        edge=0.01,
        risk_variance=0.001,
        portfolio_value=100_000,
    )
    # A doubled concentration cap should allow a larger position
    higher_cap = calculate_target_notional(
        edge=0.01,
        risk_variance=0.001,
        portfolio_value=100_000,
        concentration_cap_pct=0.10,  # 10% instead of hardcoded 5%
    )
    assert higher_cap >= base, "Higher concentration cap should allow equal-or-larger position."


def test_kelly_clip_is_overridable():
    """Kelly confidence multiplier clip must not be hardcoded."""
    base = calculate_target_notional(
        edge=0.10,  # very high edge to saturate the clip
        risk_variance=0.001,
        portfolio_value=100_000,
    )
    clipped_lower = calculate_target_notional(
        edge=0.10,
        risk_variance=0.001,
        portfolio_value=100_000,
        max_kelly_multiplier=2.0,  # tighter clip
    )
    assert clipped_lower <= base, "Lower kelly clip must reduce or equal the position size."
```

*Note: adjust the function name and parameter names to match the actual signature in `sizing.py` after reading it.*

- [ ] **Step 4: Run the tests to verify they fail**

```bash
PYTHONPATH=. python -m pytest tests/engine/test_sizing_parameterized.py -v
```

Expected: FAIL (parameters not accepted yet).

- [ ] **Step 5: Add keyword parameters to the sizing function**

In `project/portfolio/sizing.py`, add `concentration_cap_pct: float = 0.05` and `max_kelly_multiplier: float = 5.0` as keyword-only parameters (using `*`). Replace the hardcoded values:

```python
# Before:
confidence_multiplier = np.clip(edge / risk_variance, 0.0, 5.0)
# ...
concentration_cap = portfolio_value * 0.05

# After (add these as keyword args with defaults):
confidence_multiplier = np.clip(edge / risk_variance, 0.0, max_kelly_multiplier)
# ...
concentration_cap = portfolio_value * concentration_cap_pct
```

- [ ] **Step 6: Run the parameterization tests**

```bash
PYTHONPATH=. python -m pytest tests/engine/test_sizing_parameterized.py -v --tb=short 2>&1 | tail -20
```

Expected: both new tests pass.

- [ ] **Step 7: Run the full test suite**

```bash
PYTHONPATH=. python -m pytest tests/ -x -q --tb=short 2>&1 | tail -20
```

Expected: all pass.

- [ ] **Step 8: Commit**

```bash
git add project/portfolio/sizing.py tests/engine/test_sizing_parameterized.py
git commit -m "feat: parameterize concentration_cap and kelly multiplier clip in sizing.py (IP-001, IP-002)"
```

---

## Final Verification

- [ ] **Step 1: Run the full test suite**

```bash
PYTHONPATH=. python -m pytest tests/ -q --tb=short 2>&1 | tail -30
```

Expected: all pass, no warnings about missing files or imports.

- [ ] **Step 2: Lint check**

```bash
PYTHONPATH=. python -m ruff check project/ tests/ 2>&1 | head -30
```

Expected: no new errors introduced.

- [ ] **Step 3: Verify event registry integrity**

```bash
PYTHONPATH=. python -c "from project.events.detectors.catalog import load_detector_catalog; c = load_detector_catalog(); print(f'Loaded {len(c)} detectors OK')"
```

Expected: same detector count as before (all detectors from `extended_detectors.py` still registered).

- [ ] **Step 4: Audit closing summary**

Run `git log --oneline -10` and confirm 7 commits are present covering: safe deletions, LT-003 fix, LT-004 fix, compat wrapper removal, RL-002 ms_* removal, LI-003 rename, IP-001/002 parameterization.

---

## Deferred Items Requiring Separate Plans

These findings are confirmed real but require more investigation or research decisions before implementation:

| Finding | Next Action |
|---|---|
| LI-001 `project/strategy/runtime/` | Audit 9 callers; plan migration to `project.strategy.*` |
| RL-001 context_features identity pass | Map all `context_features` readers; plan pipeline stage removal |
| RL-003 detector base class fragmentation | Design unified base class hierarchy; write separate plan |
| LT-001 correlated market states | Research decision: prune hypotheses after significance review |
| LT-002 OI data source mismatch | Data pipeline investigation: align 1m/5m OI source |
| LT-005 unshifted quantile audit | Systematic grep + manual review across all detectors |
| RD-003/4/5 internal consolidation | Read and plan: `detect_temporal_family`, `core.py`, `validation.py` |
| SF-001–004 statistical fragility | Algorithm design decisions — separate research plan |
| SL-001–004 scaling bottlenecks | Infrastructure architecture — separate engineering plan |
