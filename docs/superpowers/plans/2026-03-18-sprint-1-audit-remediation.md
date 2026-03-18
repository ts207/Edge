# Sprint 1 Audit Remediation Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the 7 highest-risk audit findings from the 4-wave code audit, restoring research integrity and eliminating critical runtime defects.

**Architecture:** Each ticket is an independent patch; order matters only where stated (TICKET-002 depends on TICKET-001). All changes are small and targeted — no refactors beyond the minimum scope. TDD throughout.

**Tech Stack:** Python 3.11+, pytest, pandas, PyYAML, git

---

## File Map

| Ticket | File | Action |
|--------|------|--------|
| T-001  | `tests/pipelines/research/test_phase2_feature_serving_contract.py` | Create |
| T-002  | `docs/generated/**` | Regenerate via script |
| T-004  | `project/eval/splits.py` | Modify (default embargo) |
| T-004  | `tests/eval/test_splits.py` | Modify (add default-embargo regression) |
| T-005  | `project/research/services/candidate_discovery_service.py` | Modify (sample floors) |
| T-005  | `tests/research/services/test_candidate_discovery_service.py` | Modify (update assertions) |
| T-005  | `docs/RESEARCH_CALIBRATION_BASELINE.md` | Modify (update baseline record) |
| T-007  | `project/strategy/runtime/dsl_runtime/signal_resolution.py` | Modify (rename signal) |
| T-007  | `tests/runtime/test_signal_resolution_no_ops.py` | Create |
| T-008  | `project/strategy/runtime/exits.py` | Modify (add Tuple import) |
| T-008  | `tests/runtime/test_exits.py` | Create |
| T-009  | `project/strategy/templates/validation.py` | Modify (real checks) |
| T-009  | `project/strategy/templates/compiler.py` | Modify (block on PIT fail) |
| T-009  | `tests/strategy/templates/test_validation.py` | Create |

---

## Task 1: TICKET-001 — Phase-2 Feature-Serving Contract Test

The working tree is already clean (prior commits). The remaining acceptance criterion is a behavioral equivalence/contract test for the refactored phase-2 feature-serving path (`search_feature_frame.py` deleted, `phase2_search_engine.py` refactored to use `search_feature_utils`).

**Files:**
- Create: `tests/pipelines/research/test_phase2_feature_serving_contract.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/pipelines/research/test_phase2_feature_serving_contract.py
"""
Contract test: phase2_search_engine uses search_feature_utils to serve features,
not the deleted search_feature_frame module. This test guards the new feature-serving
boundary against regression.
"""
import importlib
import pytest


def test_search_feature_frame_not_importable():
    """search_feature_frame was deleted — it must not be importable."""
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("project.pipelines.research.search_feature_frame")


def test_search_engine_imports_search_feature_utils():
    """phase2_search_engine must import from search_feature_utils, not from the deleted module."""
    import project.pipelines.research.phase2_search_engine as eng
    source = open(eng.__file__).read()
    assert "search_feature_utils" in source, (
        "phase2_search_engine must use search_feature_utils for feature serving"
    )
    assert "search_feature_frame" not in source, (
        "phase2_search_engine must not reference deleted search_feature_frame"
    )


def test_search_feature_utils_importable():
    """The new feature-serving module must be importable."""
    from project.research.search.search_feature_utils import (
        normalize_search_feature_columns,
        prepare_search_features_for_symbol,
    )
    assert callable(normalize_search_feature_columns)
    assert callable(prepare_search_features_for_symbol)
```

- [ ] **Step 2: Run test to verify it passes (or diagnose failure)**

```bash
.venv/bin/python -m pytest tests/pipelines/research/test_phase2_feature_serving_contract.py -v
```

Expected: PASS (working tree is clean; the deletion and refactor are already committed)

If any test fails, diagnose and fix the import path before continuing.

- [ ] **Step 3: Commit**

```bash
git add tests/pipelines/research/test_phase2_feature_serving_contract.py
git commit -m "test: add phase-2 feature-serving contract test (TICKET-001)"
```

---

## Task 2: TICKET-002 — Regenerate Machine-Owned Artifacts

**Files:**
- Modify: `docs/generated/architecture_metrics.json`, `docs/generated/detector_coverage.json`, `docs/generated/detector_coverage.md`, `docs/generated/ontology_audit.json`, `docs/generated/system_map.json`, `docs/generated/system_map.md`

- [ ] **Step 1: Run regeneration script**

```bash
bash scripts/regenerate_artifacts.sh
```

Expected: script completes without errors and updates the 6 files in `docs/generated/`.

- [ ] **Step 2: Verify outputs are current**

```bash
git diff --stat docs/generated/
```

Expected: files show modifications (or no diff if already current). Confirm `architecture_metrics.json` snapshot date reflects today.

- [ ] **Step 3: Run contract tests**

```bash
.venv/bin/python -m pytest tests/contracts/ -v
```

Expected: all pass.

- [ ] **Step 4: Commit regenerated artifacts**

```bash
git add docs/generated/
git commit -m "chore: regenerate machine-owned artifacts from clean baseline (TICKET-002)"
```

---

## Task 3: TICKET-004 — Enforce Non-Zero Embargo in Time Splits

**Why:** `build_time_splits` defaults `embargo_days=0`, allowing temporal contamination between train/validation/test boundaries at 5m bar resolution.

**Files:**
- Modify: `project/eval/splits.py:33`
- Modify: `tests/eval/test_splits.py`

- [ ] **Step 1: Write the failing regression test**

Add to `tests/eval/test_splits.py`:

```python
def test_default_embargo_is_nonzero():
    """Regression: build_time_splits default embargo must be >= 5 days.
    If this test fails, zero-embargo was re-introduced as the default.
    """
    import inspect
    from project.eval.splits import build_time_splits
    sig = inspect.signature(build_time_splits)
    default_embargo = sig.parameters["embargo_days"].default
    assert default_embargo >= 5, (
        f"build_time_splits embargo_days default must be >= 5; got {default_embargo}. "
        "Zero-default embargo allows temporal contamination between train/validation/test splits."
    )
```

- [ ] **Step 2: Run test to verify it fails**

```bash
.venv/bin/python -m pytest tests/eval/test_splits.py::test_default_embargo_is_nonzero -v
```

Expected: FAIL — `AssertionError: build_time_splits embargo_days default must be >= 5; got 0`.

- [ ] **Step 3: Fix the default in splits.py**

In `project/eval/splits.py`, line 33, change:
```python
# Before
    embargo_days: int = 0,
```
to:
```python
# After — 5-day default prevents contamination from rolling features that
# span the split boundary (autocorrelation in crypto at 5m bar resolution).
    embargo_days: int = 5,
```

Note: `build_time_splits_with_purge` delegates to `build_time_splits`, so it inherits the new default. `build_repeated_walk_forward_folds` also delegates. No other changes needed.

- [ ] **Step 4: Run full splits test file**

```bash
.venv/bin/python -m pytest tests/eval/test_splits.py -v
```

Expected: all pass. If existing tests hardcode `embargo_days=0` positionally, they will still work because the parameter is keyword-only. If any test calls without `embargo_days` and asserts zero-gap timestamps, update that test to pass `embargo_days=0` explicitly.

- [ ] **Step 5: Commit**

```bash
git add project/eval/splits.py tests/eval/test_splits.py
git commit -m "fix: enforce non-zero embargo default in build_time_splits (TICKET-004)

Default embargo_days raised from 0 to 5 to prevent temporal contamination
between train/validation/test boundaries in 5m bar crypto research.
"
```

---

## Task 4: TICKET-005 — Raise Minimum Sample Floors

**Why:** `min_validation_n_obs: 2` and `min_test_n_obs: 2` allow candidates with near-zero split evidence to pass service-layer quality gates.

**Files:**
- Modify: `project/research/services/candidate_discovery_service.py:42-46`
- Modify: `tests/research/services/test_candidate_discovery_service.py:340-341`
- Modify: `docs/RESEARCH_CALIBRATION_BASELINE.md:25-26`

- [ ] **Step 1: Write failing tests**

In `tests/research/services/test_candidate_discovery_service.py`, find the assertions at lines 340–342 and add a new dedicated test:

```python
def test_standard_sample_quality_floors_are_defensible():
    """Regression: standard sample quality floors must be >= 10 for credible split evidence.
    Floors of 2 are not statistically defensible.
    """
    from project.research.services.candidate_discovery_service import DEFAULT_SAMPLE_QUALITY_POLICY
    standard = DEFAULT_SAMPLE_QUALITY_POLICY["standard"]
    assert standard["min_validation_n_obs"] >= 10, (
        f"min_validation_n_obs must be >= 10; got {standard['min_validation_n_obs']}. "
        "Two events in a holdout split provide near-zero statistical power."
    )
    assert standard["min_test_n_obs"] >= 10, (
        f"min_test_n_obs must be >= 10; got {standard['min_test_n_obs']}."
    )
```

- [ ] **Step 2: Run test to verify it fails**

```bash
.venv/bin/python -m pytest tests/research/services/test_candidate_discovery_service.py::test_standard_sample_quality_floors_are_defensible -v
```

Expected: FAIL — `AssertionError: min_validation_n_obs must be >= 10; got 2`.

- [ ] **Step 3: Update DEFAULT_SAMPLE_QUALITY_POLICY in candidate_discovery_service.py**

In `project/research/services/candidate_discovery_service.py`, change lines 42–46:

```python
# Before
DEFAULT_SAMPLE_QUALITY_POLICY: Dict[str, Dict[str, int]] = {
    "standard": {
        "min_validation_n_obs": 2,
        "min_test_n_obs": 2,
        "min_total_n_obs": 10,
    },
```

```python
# After
DEFAULT_SAMPLE_QUALITY_POLICY: Dict[str, Dict[str, int]] = {
    "standard": {
        # Raised from 2 to 10 (TICKET-005): two events provide near-zero statistical power.
        "min_validation_n_obs": 10,
        "min_test_n_obs": 10,
        "min_total_n_obs": 30,
    },
```

Note: `min_total_n_obs` is also raised from 10 to 30 to maintain internal consistency (total >= val + test minimums).

- [ ] **Step 4: Update the hardcoded assertions in the existing test file**

Find the existing assertions at approximately lines 340–342 in `tests/research/services/test_candidate_discovery_service.py` and `tests/docs/test_research_calibration_baseline.py`:

In `tests/research/services/test_candidate_discovery_service.py` — find and update:
```python
# Before
assert standard["min_validation_n_obs"] == 2
assert standard["min_test_n_obs"] == 2
assert standard["min_total_n_obs"] == 10
```
```python
# After
assert standard["min_validation_n_obs"] == 10
assert standard["min_test_n_obs"] == 10
assert standard["min_total_n_obs"] == 30
```

Also find any test that calls `apply_sample_quality_gates` or service functions with hardcoded `min_validation_n_obs=2, min_test_n_obs=2` (e.g. line 231) — these explicit call-site values can stay as-is since they are testing with explicit overrides, not defaults.

- [ ] **Step 5: Update docs/RESEARCH_CALIBRATION_BASELINE.md**

In `docs/RESEARCH_CALIBRATION_BASELINE.md`, find and update the baseline record:
```markdown
# Before
  - `min_validation_n_obs = 2`
  - `min_test_n_obs = 2`
  - `min_total_n_obs = 10`
```
```markdown
# After
  - `min_validation_n_obs = 10`  (raised from 2; TICKET-005)
  - `min_test_n_obs = 10`        (raised from 2; TICKET-005)
  - `min_total_n_obs = 30`       (raised from 10; TICKET-005)
```

- [ ] **Step 6: Update test_research_calibration_baseline.py if it asserts the old values**

```bash
grep -n "min_total_n_obs = 10\|min_validation_n_obs = 2\|min_test_n_obs = 2" tests/docs/test_research_calibration_baseline.py
```

Update any matching assertions to reflect the new values.

- [ ] **Step 7: Run test suite for affected files**

```bash
.venv/bin/python -m pytest tests/research/services/test_candidate_discovery_service.py tests/docs/test_research_calibration_baseline.py -v
```

Expected: all pass.

- [ ] **Step 8: Commit**

```bash
git add project/research/services/candidate_discovery_service.py \
        tests/research/services/test_candidate_discovery_service.py \
        docs/RESEARCH_CALIBRATION_BASELINE.md \
        tests/docs/test_research_calibration_baseline.py
git commit -m "fix: raise standard sample quality floors to 10/10 (TICKET-005)

min_validation_n_obs and min_test_n_obs raised from 2 to 10.
min_total_n_obs raised from 10 to 30 for internal consistency.
Two events in a holdout split provide near-zero statistical power.
"
```

---

## Task 5: TICKET-008 — Fix exits.py NameError

**Why:** `project/strategy/runtime/exits.py` uses `Tuple[bool, str]` as the return annotation for `check_exit_conditions` but never imports `Tuple` from `typing`. Any direct call raises `NameError`.

**Files:**
- Modify: `project/strategy/runtime/exits.py`
- Create: `tests/runtime/test_exits.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/runtime/test_exits.py
"""Direct-call test for exits.py. Guards against NameError from missing imports."""
import pandas as pd


def _make_bar(close: float = 100.0) -> pd.Series:
    return pd.Series({"close": close, "atr": 1.0})


def test_exits_module_imports_cleanly():
    """Importing exits must not raise NameError."""
    import project.strategy.runtime.exits  # noqa: F401


def test_check_exit_conditions_time_stop():
    from project.strategy.runtime.exits import check_exit_conditions
    bar = _make_bar()
    exited, reason = check_exit_conditions(
        bar=bar,
        position_entry_price=100.0,
        is_long=True,
        blueprint_exit={"time_stop_bars": 5},
        bars_held=5,
    )
    assert exited is True
    assert reason == "time_stop"


def test_check_exit_conditions_no_exit():
    from project.strategy.runtime.exits import check_exit_conditions
    bar = _make_bar(close=100.5)
    exited, reason = check_exit_conditions(
        bar=bar,
        position_entry_price=100.0,
        is_long=True,
        blueprint_exit={"time_stop_bars": 96, "target_value": 0.05, "stop_value": 0.03},
        bars_held=1,
    )
    assert exited is False
    assert reason == ""


def test_check_exit_conditions_stop_hit():
    from project.strategy.runtime.exits import check_exit_conditions
    bar = _make_bar(close=96.0)  # 4% down from 100 → exceeds 3% stop
    exited, reason = check_exit_conditions(
        bar=bar,
        position_entry_price=100.0,
        is_long=True,
        blueprint_exit={"time_stop_bars": 96, "target_value": 0.05, "stop_value": 0.03},
        bars_held=3,
    )
    assert exited is True
    assert reason == "stop_hit"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
.venv/bin/python -m pytest tests/runtime/test_exits.py -v
```

Expected: FAIL — `NameError: name 'Tuple' is not defined` on import.

- [ ] **Step 3: Fix exits.py — add Tuple import**

In `project/strategy/runtime/exits.py`, update line 4:

```python
# Before
from typing import Dict, Any, Optional
```

```python
# After
from typing import Dict, Any, Optional, Tuple
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/bin/python -m pytest tests/runtime/test_exits.py -v
```

Expected: all 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add project/strategy/runtime/exits.py tests/runtime/test_exits.py
git commit -m "fix: add missing Tuple import to exits.py; add direct-call tests (TICKET-008)"
```

---

## Task 6: TICKET-007 — Replace Inert oos_validation_pass Signal

**Why:** `signal_mask("oos_validation_pass", ...)` in `signal_resolution.py` unconditionally returns `True`. Blueprints using it as a runtime gate receive no protection.

**Scope:** Rename the signal to make the no-op explicit; block production blueprints from silently using it.

**Files:**
- Modify: `project/strategy/runtime/dsl_runtime/signal_resolution.py`
- Create: `tests/runtime/test_signal_resolution_no_ops.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/runtime/test_signal_resolution_no_ops.py
"""
Tests that confirm the explicit no-op semantics of oos_validation_pass
and that the legacy name raises an error so production blueprints cannot
silently rely on a phantom safety surface.
"""
import pandas as pd
import pytest
from unittest.mock import MagicMock


def _make_frame(n: int = 5) -> pd.DataFrame:
    return pd.DataFrame({"spread_abs": [0.5] * n, "funding_bps_abs": [1.0] * n})


def _make_blueprint() -> MagicMock:
    bp = MagicMock()
    bp.id = "test_bp"
    bp.overlays = []
    return bp


def test_oos_validation_pass_raises_unknown_signal():
    """The legacy oos_validation_pass signal must not silently pass.
    Production blueprints referencing it should fail at evaluation time.
    """
    from project.strategy.runtime.dsl_runtime.signal_resolution import signal_mask
    frame = _make_frame()
    bp = _make_blueprint()
    with pytest.raises(ValueError, match="unknown trigger signals"):
        signal_mask(signal="oos_validation_pass", frame=frame, blueprint=bp)


def test_event_detected_raises_unknown_signal():
    """event_detected must not unconditionally pass. Production blueprints
    must not silently bypass event detection via this phantom signal.
    """
    from project.strategy.runtime.dsl_runtime.signal_resolution import signal_mask
    frame = _make_frame()
    bp = _make_blueprint()
    with pytest.raises(ValueError, match="unknown trigger signals"):
        signal_mask(signal="event_detected", frame=frame, blueprint=bp)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/bin/python -m pytest tests/runtime/test_signal_resolution_no_ops.py -v
```

Expected: FAIL — both signals currently return `pd.Series(True, ...)` instead of raising.

- [ ] **Step 3: Update signal_resolution.py**

In `project/strategy/runtime/dsl_runtime/signal_resolution.py`, lines 25–28, change:

```python
# Before
    if signal == "event_detected":
        return pd.Series(True, index=frame.index, dtype=bool)
    if signal == "oos_validation_pass":
        return pd.Series(True, index=frame.index, dtype=bool)
```

```python
# After — these signals were unconditional no-ops. They are removed from the
# production signal surface. Any blueprint referencing them will now fail at
# evaluation time, making the phantom gate visible rather than silent.
# To use OOS validation: implement a stored OOS result lookup and add a new
# signal name (e.g., "oos_result_pass") backed by real data.
```

(Delete the two `if` blocks entirely — do not replace with a pass or comment inside them.)

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/bin/python -m pytest tests/runtime/test_signal_resolution_no_ops.py -v
```

Expected: PASS.

- [ ] **Step 5: Run broader signal resolution tests to check for regressions**

```bash
.venv/bin/python -m pytest tests/ -k "signal" -v
```

If any existing test asserts that `event_detected` or `oos_validation_pass` returns `True`, update it to expect `ValueError`. These tests were asserting phantom behavior.

- [ ] **Step 6: Commit**

```bash
git add project/strategy/runtime/dsl_runtime/signal_resolution.py \
        tests/runtime/test_signal_resolution_no_ops.py
git commit -m "fix: remove phantom oos_validation_pass and event_detected no-op signals (TICKET-007)

Both signals unconditionally returned True, providing no runtime gate.
Removed from signal surface so blueprints referencing them fail at evaluation
time rather than silently receiving false protection.
"
```

---

## Task 7: TICKET-009 — Real PIT Template Validation Checks

**Why:** `validate_pit_invariants` and `check_closed_left_rolling` in `project/strategy/templates/validation.py` are stubs that always return `True`. Template evaluation never blocks on lookahead.

**Scope:**
1. `validate_pit_invariants(signal)` — verify index is strictly monotone increasing.
2. `check_closed_left_rolling(window)` — verify window index is monotone and non-empty.
3. Wire blocking into `compiler.py` so templates fail on PIT violation.

**Files:**
- Modify: `project/strategy/templates/validation.py`
- Modify: `project/strategy/templates/compiler.py`
- Create: `tests/strategy/templates/test_validation.py`

- [ ] **Step 1: Write failing adversarial tests**

```python
# tests/strategy/templates/test_validation.py
import pandas as pd
import pytest


def test_validate_pit_invariants_valid_series_passes():
    from project.strategy.templates.validation import validate_pit_invariants
    idx = pd.date_range("2024-01-01", periods=5, freq="5min", tz="UTC")
    signal = pd.Series([1, 2, 3, 4, 5], index=idx)
    assert validate_pit_invariants(signal) is True


def test_validate_pit_invariants_non_monotone_index_fails():
    """A series with a non-monotone index fails PIT validation."""
    from project.strategy.templates.validation import validate_pit_invariants
    idx = pd.to_datetime(["2024-01-01 00:05", "2024-01-01 00:00", "2024-01-01 00:10"], utc=True)
    signal = pd.Series([1, 2, 3], index=idx)
    assert validate_pit_invariants(signal) is False


def test_validate_pit_invariants_duplicate_index_fails():
    """A series with duplicate timestamps fails PIT validation (not strictly monotone)."""
    from project.strategy.templates.validation import validate_pit_invariants
    idx = pd.to_datetime(["2024-01-01 00:00", "2024-01-01 00:00", "2024-01-01 00:05"], utc=True)
    signal = pd.Series([1, 1, 2], index=idx)
    # duplicates make index non-strictly-monotone
    assert validate_pit_invariants(signal) is False


def test_validate_pit_invariants_empty_passes():
    from project.strategy.templates.validation import validate_pit_invariants
    assert validate_pit_invariants(pd.Series([], dtype=float)) is True


def test_check_closed_left_rolling_valid_passes():
    from project.strategy.templates.validation import check_closed_left_rolling
    idx = pd.date_range("2024-01-01", periods=10, freq="5min", tz="UTC")
    window = pd.Series(range(10), index=idx)
    assert check_closed_left_rolling(window) is True


def test_check_closed_left_rolling_non_monotone_fails():
    from project.strategy.templates.validation import check_closed_left_rolling
    idx = pd.to_datetime(["2024-01-01 00:10", "2024-01-01 00:05", "2024-01-01 00:15"], utc=True)
    window = pd.Series([3, 2, 4], index=idx)
    assert check_closed_left_rolling(window) is False


def test_check_closed_left_rolling_empty_passes():
    from project.strategy.templates.validation import check_closed_left_rolling
    assert check_closed_left_rolling(pd.Series([], dtype=float)) is True


def test_compiler_blocks_on_non_monotone_entry_signal(monkeypatch):
    """compile_positions must raise if the entry signal index is not monotone."""
    import pandas as pd
    import numpy as np
    from project.strategy.templates.spec import StrategySpec
    from project.strategy.templates.data_bundle import DataBundle
    from project.strategy.templates import compiler

    idx_bad = pd.to_datetime(["2024-01-01 00:05", "2024-01-01 00:00", "2024-01-01 00:10"], utc=True)
    idx_good = pd.date_range("2024-01-01", periods=3, freq="5min", tz="UTC")

    # Patch get_event_signal to return non-monotone entry signals
    class _BadBundle:
        prices = pd.DataFrame({"close": [1.0, 2.0, 3.0]}, index=idx_bad)
        def get_event_signal(self, family, signal):
            return pd.Series([True, False, True], index=idx_bad)

    spec = StrategySpec(
        strategy_id="test",
        event_family="TEST_FAM",
        entry_signal="enter",
        exit_signal="exit",
        position_cap=1.0,
        cooldown_bars=0,
        params={},
    )

    with pytest.raises(ValueError, match="PIT"):
        compiler.compile_positions(spec, _BadBundle())
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/bin/python -m pytest tests/strategy/templates/test_validation.py -v
```

Expected: most tests FAIL — `validate_pit_invariants` returns True for duplicates, `check_closed_left_rolling` always returns True, `compile_positions` does not raise on bad PIT.

- [ ] **Step 3: Implement real checks in validation.py**

Replace the content of `project/strategy/templates/validation.py`:

```python
import pandas as pd


def validate_pit_invariants(signal: pd.Series) -> bool:
    """Return True iff the signal index is strictly monotone increasing.

    A non-monotone index indicates potential lookahead or unsorted data,
    both of which violate point-in-time discipline.
    """
    if signal.empty:
        return True
    return bool(signal.index.is_monotonic_increasing) and not bool(signal.index.duplicated().any())


def check_closed_left_rolling(window: pd.Series) -> bool:
    """Return True iff the rolling window index is monotone increasing.

    A properly constructed closed-left rolling window [T-N, T-1] must have
    a monotone index. A non-monotone window suggests unsorted or incorrectly
    sliced data that could include the current evaluation bar.
    """
    if window.empty:
        return True
    return bool(window.index.is_monotonic_increasing)
```

- [ ] **Step 4: Add PIT blocking to compiler.py**

In `project/strategy/templates/compiler.py`, add a PIT guard at the start of `compile_positions`, after computing `entries` and `exits`:

```python
# After line: exits = bundle.get_event_signal(spec.event_family, spec.exit_signal)
# Add:
from project.strategy.templates.validation import validate_pit_invariants
if not validate_pit_invariants(entries):
    raise ValueError(
        f"PIT violation in entry signal for spec '{spec.strategy_id}': "
        "index is not strictly monotone increasing. "
        "This indicates unsorted or lookahead-contaminated data."
    )
if not validate_pit_invariants(exits):
    raise ValueError(
        f"PIT violation in exit signal for spec '{spec.strategy_id}': "
        "index is not strictly monotone increasing."
    )
```

The import should be placed at the top of `compiler.py`, not inside the function. Move it to the module-level imports.

- [ ] **Step 5: Run all validation tests**

```bash
.venv/bin/python -m pytest tests/strategy/templates/test_validation.py -v
```

Expected: all pass.

- [ ] **Step 6: Run broader template tests to catch regressions**

```bash
.venv/bin/python -m pytest tests/ -k "template or compiler or spec" -v
```

Fix any failures caused by test fixtures that use non-monotone indices (update those fixtures to use proper date ranges).

- [ ] **Step 7: Commit**

```bash
git add project/strategy/templates/validation.py \
        project/strategy/templates/compiler.py \
        tests/strategy/templates/test_validation.py
git commit -m "fix: implement real PIT validation checks; block compiler on violation (TICKET-009)

validate_pit_invariants now enforces strictly-monotone index (rejects duplicates).
check_closed_left_rolling enforces monotone window index.
compile_positions raises ValueError on PIT violation in entry/exit signals.
"
```

---

## Completion Checklist

- [ ] T-001: phase-2 feature-serving contract test passes
- [ ] T-002: `docs/generated/` artifacts regenerated and committed
- [ ] T-004: `build_time_splits` default embargo >= 5; regression test in place
- [ ] T-005: standard sample floors at 10/10/30; all related tests pass
- [ ] T-007: `oos_validation_pass` and `event_detected` removed from production signal surface
- [ ] T-008: `exits.py` imports cleanly; direct-call tests pass
- [ ] T-009: PIT validation is real; compiler blocks on violation

Run final smoke check:
```bash
.venv/bin/python -m pytest tests/ -x --timeout=120 -q 2>&1 | tail -20
```

---

## Known Dependencies

- T-002 must run after T-001 (regenerate from clean + tested tree)
- T-007 may reveal blueprints in fixtures that reference the removed signals — fix those fixtures to use valid signal names or `spread_guard_pass`
- T-009 compiler change may reveal test fixtures with unsorted indices — fix those fixtures rather than bypassing the guard
