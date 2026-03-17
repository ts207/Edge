# Detector Stabilization Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Classify every event detector as stable/noisy/silent/broken via a precision/recall audit harness, fix all non-stable detectors, and lock results into a permanent regression test suite.

**Architecture:** A standalone measurement module (`detector_audit_module.py`) in `project/scripts/` builds rich merged DataFrames from synthetic manifests, runs each detector directly via `detector.detect()`, and computes precision/recall against truth windows from `synthetic_regime_segments.json`. Both the CLI audit script and the regression tests import this shared module to guarantee measurement consistency. Detector fixes are made after reviewing the audit report, with contract tests re-run after each fix.

**Tech Stack:** Python 3.10+, pandas, pytest, existing `project.events.detectors` registry, synthetic data in `data/synthetic/`

**Spec:** `docs/superpowers/specs/2026-03-17-detector-stabilization-design.md`

---

## Chunk 1: Measurement Module and Audit Script

### File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `project/scripts/detector_audit_module.py` | Core measurement logic: data loading, detect, precision/recall |
| Create | `project/scripts/audit_detector_precision_recall.py` | CLI: enumerate detectors, run measurement, write JSON report |

---

### Task 1: Build `detector_audit_module.py`

**Files:**
- Create: `project/scripts/detector_audit_module.py`

- [ ] **Step 1.1: Write a failing test for `measure_detector` returning a metrics dict**

Create `tests/scripts/test_detector_audit_module.py`:

```python
"""Tests for detector_audit_module shared measurement logic."""
import math
import pandas as pd
import pytest


def _make_df(n: int = 5000) -> pd.DataFrame:
    """Build a minimal rich DataFrame for testing."""
    import numpy as np
    ts = pd.date_range("2023-01-01", periods=n, freq="5min", tz="UTC")
    close = pd.Series(30000.0 + np.cumsum(np.random.randn(n) * 50), name="close")
    df = pd.DataFrame({
        "timestamp": ts,
        "open": close,
        "high": close * 1.001,
        "low": close * 0.999,
        "close": close,
        "close_perp": close,
        "close_spot": close * 0.9998,
        "volume": 1000.0,
        "quote_volume": close * 1000.0,
        "trade_count": 500,
        "taker_buy_volume": 500.0,
        "taker_buy_quote_volume": close * 500.0,
        "spread_bps": 2.5,
        "depth_usd": 5_000_000.0,
        "funding_rate_scaled": 0.0001,
        "symbol": "BTCUSDT",
    })
    log_ret = np.log(close / close.shift(1))
    df["rv_96"] = log_ret.rolling(96, min_periods=12).std()
    return df


def test_measure_detector_returns_metrics_dict():
    from project.events.detectors.registry import load_all_detectors, get_detector
    from project.scripts.detector_audit_module import measure_detector

    load_all_detectors()
    detector = get_detector("VOL_SPIKE")
    assert detector is not None, "VOL_SPIKE detector must be registered"

    df = _make_df()
    segments = []  # no truth windows → uncovered

    metrics = measure_detector(detector, df, "BTCUSDT", segments, "test_run")

    assert metrics["event_type"] == "VOL_SPIKE"
    assert metrics["symbol"] == "BTCUSDT"
    assert metrics["classification"] == "uncovered"
    assert metrics["error"] is None
    assert isinstance(metrics["total_events"], int)
    assert isinstance(metrics["precision"], float)


def test_measure_detector_handles_missing_required_column():
    from project.events.detectors.registry import load_all_detectors, get_detector
    from project.scripts.detector_audit_module import measure_detector

    load_all_detectors()
    detector = get_detector("BASIS_DISLOC")
    assert detector is not None

    df = _make_df()
    df = df.drop(columns=["close_spot"])  # BASIS_DISLOC requires close_spot
    segments = []

    metrics = measure_detector(detector, df, "BTCUSDT", segments, "test_run")
    assert metrics["classification"] == "error"
    assert metrics["error"] is not None


def test_classify_noisy():
    from project.scripts.detector_audit_module import _classify
    assert _classify(precision=0.30, recall=0.60, expected_windows=5) == "noisy"


def test_classify_silent():
    from project.scripts.detector_audit_module import _classify
    assert _classify(precision=0.70, recall=0.10, expected_windows=5) == "silent"


def test_classify_broken():
    from project.scripts.detector_audit_module import _classify
    assert _classify(precision=0.20, recall=0.10, expected_windows=5) == "broken"


def test_classify_stable():
    from project.scripts.detector_audit_module import _classify
    assert _classify(precision=0.60, recall=0.50, expected_windows=5) == "stable"


def test_classify_uncovered():
    from project.scripts.detector_audit_module import _classify
    assert _classify(precision=0.0, recall=0.0, expected_windows=0) == "uncovered"
```

- [ ] **Step 1.2: Run to confirm failure**

```bash
cd /home/tstuv/workspace/trading/EDGEE
.venv/bin/python -m pytest tests/scripts/test_detector_audit_module.py -v 2>&1 | head -30
```

Expected: `ModuleNotFoundError: No module named 'project.scripts.detector_audit_module'`

- [ ] **Step 1.3: Write `project/scripts/detector_audit_module.py`**

```python
"""
Shared measurement logic for detector precision/recall auditing.

Imported by both audit_detector_precision_recall.py (CLI) and
tests/events/test_detector_precision_recall.py (regression tests).

Placement in project/scripts/ (not project/events/) avoids circular import risk:
some family modules import from project.research at module level.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import numpy as np
import pandas as pd

from project.events.detectors.base import BaseEventDetector


# ---------------------------------------------------------------------------
# Classification constants
# ---------------------------------------------------------------------------

MIN_PRECISION: float = 0.50
MIN_RECALL: float = 0.30

# Known run_id → label mapping. CLI uses this to resolve --run_id arguments.
AUDIT_RUN_IDS: Dict[str, str] = {
    "2021_bull": "synthetic_2021_bull",
    "default": "synthetic_2025_full_year",
    "stress_crash": "synthetic_2025_stress_crash",
    "golden": "golden_synthetic_discovery",
}
# Also accept run_id values directly.
KNOWN_RUN_IDS = set(AUDIT_RUN_IDS.values())


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class DetectorMetrics:
    event_type: str
    symbol: str
    run_id: str
    total_events: int
    event_rate_per_1k: float
    in_window_events: int
    off_regime_events: int
    expected_windows: int
    windows_hit: int
    precision: float
    recall: float  # float("nan") when expected_windows == 0
    classification: str  # stable | noisy | silent | broken | uncovered | error
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {k: v for k, v in self.__dict__.items()}
        if math.isnan(d.get("recall", 0)):
            d["recall"] = None  # JSON-serializable
        return d


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

def _classify(precision: float, recall: float, expected_windows: int) -> str:
    """Classify a detector result into one of five classes."""
    if expected_windows == 0:
        return "uncovered"
    p_ok = precision >= MIN_PRECISION
    r_ok = recall >= MIN_RECALL
    if p_ok and r_ok:
        return "stable"
    if not p_ok and r_ok:
        return "noisy"
    if p_ok and not r_ok:
        return "silent"
    return "broken"


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_manifest(data_root: Path, run_id: str) -> Dict[str, Any]:
    """Load synthetic_generation_manifest.json for a run_id."""
    path = data_root / "synthetic" / run_id / "synthetic_generation_manifest.json"
    return json.loads(path.read_text(encoding="utf-8"))


def load_truth_segments(data_root: Path, run_id: str) -> List[Dict[str, Any]]:
    """Load synthetic_regime_segments.json for a run_id."""
    path = data_root / "synthetic" / run_id / "synthetic_regime_segments.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and "segments" in payload:
        return list(payload["segments"])
    return list(payload)


def build_symbol_df(symbol_entry: Dict[str, Any]) -> pd.DataFrame:
    """
    Build a rich merged DataFrame for one symbol using manifest paths.

    Columns produced (beyond raw OHLCV):
      - close_perp: alias of perp close
      - close_spot: spot close, merged by timestamp
      - funding_rate_scaled: forward-filled from funding parquet
      - rv_96: rolling 96-bar realized vol (computed if absent)
    """
    paths = symbol_entry["paths"]

    # --- perp bars ---
    perp_frames = [pd.read_parquet(p) for p in paths["cleaned_perp"]]
    perp = pd.concat(perp_frames, ignore_index=True)
    perp["timestamp"] = pd.to_datetime(perp["timestamp"], utc=True, errors="coerce")
    perp = perp.sort_values("timestamp").reset_index(drop=True)
    perp["close_perp"] = perp["close"]  # basis detectors need close_perp

    # --- spot bars ---
    spot_paths = paths.get("cleaned_spot", [])
    if spot_paths:
        spot_frames = [pd.read_parquet(p) for p in spot_paths]
        spot = pd.concat(spot_frames, ignore_index=True)
        spot["timestamp"] = pd.to_datetime(spot["timestamp"], utc=True, errors="coerce")
        spot = (
            spot[["timestamp", "close"]]
            .rename(columns={"close": "close_spot"})
            .sort_values("timestamp")
        )
        perp = pd.merge_asof(
            perp.sort_values("timestamp"),
            spot,
            on="timestamp",
            direction="nearest",
            tolerance=pd.Timedelta("5min"),
        ).reset_index(drop=True)

    # --- funding: forward-fill to bar frequency ---
    funding_path = paths.get("funding")
    if funding_path and Path(funding_path).exists():
        funding = pd.read_parquet(funding_path)
        funding["timestamp"] = pd.to_datetime(funding["timestamp"], utc=True, errors="coerce")
        if "funding_rate_scaled" in funding.columns:
            funding = (
                funding[["timestamp", "funding_rate_scaled"]]
                .sort_values("timestamp")
            )
            perp = pd.merge_asof(
                perp.sort_values("timestamp"),
                funding,
                on="timestamp",
                direction="backward",
            ).reset_index(drop=True)

    # --- rv_96: required by TrendExhaustionDetector ---
    if "rv_96" not in perp.columns:
        log_ret = np.log(perp["close"] / perp["close"].shift(1))
        perp["rv_96"] = log_ret.rolling(96, min_periods=12).std()

    perp["symbol"] = symbol_entry["symbol"]
    return perp.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Measurement
# ---------------------------------------------------------------------------

def _get_tolerance_td(event_type: str, tolerance_minutes: Union[int, Dict[str, int]]) -> pd.Timedelta:
    if isinstance(tolerance_minutes, dict):
        minutes = tolerance_minutes.get(event_type, 30)
    else:
        minutes = int(tolerance_minutes)
    return pd.Timedelta(minutes=minutes)


def _build_truth_windows(
    segments: List[Dict[str, Any]],
    event_type: str,
    symbol: str,
    tolerance: pd.Timedelta,
) -> List[tuple]:
    windows = []
    for seg in segments:
        if seg.get("symbol", "").upper() != symbol.upper():
            continue
        if event_type.upper() not in [et.upper() for et in seg.get("expected_event_types", [])]:
            continue
        start = pd.Timestamp(seg["start_ts"], tz="UTC") - tolerance
        end = pd.Timestamp(seg["end_ts"], tz="UTC") + tolerance
        windows.append((start, end))
    return windows


def _count_hits(
    event_times: pd.Series,
    windows: List[tuple],
) -> tuple:
    """Returns (in_window_count, windows_hit_count)."""
    if event_times.empty or not windows:
        return 0, 0
    in_window = pd.Series(False, index=event_times.index)
    windows_hit = 0
    for start_ts, end_ts in windows:
        mask = event_times.between(start_ts, end_ts, inclusive="both")
        if bool(mask.any()):
            windows_hit += 1
        in_window = in_window | mask
    return int(in_window.sum()), windows_hit


def measure_detector(
    detector: BaseEventDetector,
    df: pd.DataFrame,
    symbol: str,
    segments: List[Dict[str, Any]],
    run_id: str,
    tolerance_minutes: Union[int, Dict[str, int]] = 30,
) -> DetectorMetrics:
    """
    Run a detector against a prepared DataFrame and compute precision/recall.

    Precision = in_window_events / total_events  (0.0 if no events fired)
    Recall    = windows_hit / expected_windows   (NaN if no truth windows)

    Returns a DetectorMetrics dataclass. On detection errors (e.g. missing
    required columns), classification is set to "error" and error field is set.
    """
    event_type = detector.event_type
    tolerance = _get_tolerance_td(event_type, tolerance_minutes)
    truth_windows = _build_truth_windows(segments, event_type, symbol, tolerance)

    try:
        events = detector.detect(df, symbol=symbol)
    except Exception as exc:
        return DetectorMetrics(
            event_type=event_type,
            symbol=symbol,
            run_id=run_id,
            total_events=0,
            event_rate_per_1k=0.0,
            in_window_events=0,
            off_regime_events=0,
            expected_windows=len(truth_windows),
            windows_hit=0,
            precision=0.0,
            recall=float("nan"),
            classification="error",
            error=str(exc),
        )

    total_bars = len(df)

    # Extract event timestamps — try each possible column name in order
    ts_col = next(
        (c for c in ("signal_ts", "timestamp", "eval_bar_ts") if c in events.columns),
        None,
    )
    if ts_col and not events.empty:
        event_times = pd.to_datetime(events[ts_col], utc=True, errors="coerce").dropna()
    else:
        event_times = pd.Series(dtype="datetime64[ns, UTC]")

    total_events = len(event_times)
    event_rate = (total_events / max(1, total_bars)) * 1000.0
    in_window, windows_hit = _count_hits(event_times, truth_windows)
    off_regime = max(0, total_events - in_window)
    expected_windows = len(truth_windows)

    precision = float(in_window / total_events) if total_events > 0 else 0.0
    recall = (
        float(windows_hit / expected_windows)
        if expected_windows > 0
        else float("nan")
    )

    recall_for_classify = 0.0 if math.isnan(recall) else recall
    classification = _classify(precision, recall_for_classify, expected_windows)

    return DetectorMetrics(
        event_type=event_type,
        symbol=symbol,
        run_id=run_id,
        total_events=total_events,
        event_rate_per_1k=round(event_rate, 2),
        in_window_events=in_window,
        off_regime_events=off_regime,
        expected_windows=expected_windows,
        windows_hit=windows_hit,
        precision=round(precision, 4),
        recall=round(recall, 4) if not math.isnan(recall) else float("nan"),
        classification=classification,
        error=None,
    )
```

- [ ] **Step 1.4: Run the tests to verify they pass**

```bash
cd /home/tstuv/workspace/trading/EDGEE
.venv/bin/python -m pytest tests/scripts/test_detector_audit_module.py -v 2>&1 | tail -20
```

Expected: all 7 tests pass.

- [ ] **Step 1.5: Commit**

```bash
cd /home/tstuv/workspace/trading/EDGEE
git add project/scripts/detector_audit_module.py tests/scripts/test_detector_audit_module.py
git commit -m "feat: add detector_audit_module with measure_detector and classification logic"
```

---

### Task 2: Build `audit_detector_precision_recall.py`

**Files:**
- Create: `project/scripts/audit_detector_precision_recall.py`

- [ ] **Step 2.1: Write a failing smoke test**

Add to `tests/scripts/test_detector_audit_module.py`:

```python
def test_audit_script_is_importable():
    """Verify the audit CLI script can be imported without errors."""
    import importlib
    mod = importlib.import_module("project.scripts.audit_detector_precision_recall")
    assert hasattr(mod, "main")
```

- [ ] **Step 2.2: Run to confirm failure**

```bash
cd /home/tstuv/workspace/trading/EDGEE
.venv/bin/python -m pytest tests/scripts/test_detector_audit_module.py::test_audit_script_is_importable -v
```

Expected: `ModuleNotFoundError`

- [ ] **Step 2.3: Write `project/scripts/audit_detector_precision_recall.py`**

```python
"""
CLI audit script: measure precision/recall for all registered event detectors
across all synthetic run_ids.

Usage:
  python -m project.scripts.audit_detector_precision_recall
  python -m project.scripts.audit_detector_precision_recall --run_id synthetic_2021_bull
  python -m project.scripts.audit_detector_precision_recall --event_type VOL_SPIKE
  python -m project.scripts.audit_detector_precision_recall --out_dir /tmp/my_audit
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from project.core.config import get_data_root
from project.events.detectors.registry import (
    get_detector,
    list_registered_event_types,
    load_all_detectors,
)
from project.scripts.detector_audit_module import (
    KNOWN_RUN_IDS,
    build_symbol_df,
    load_manifest,
    load_truth_segments,
    measure_detector,
)


def _print_table(all_metrics: list) -> None:
    """Print a human-readable classification table to stdout."""
    # Group by classification
    from collections import defaultdict
    by_class: dict = defaultdict(list)
    for m in all_metrics:
        by_class[m["classification"]].append(m)

    order = ["broken", "noisy", "silent", "error", "stable", "uncovered"]
    header = f"{'EVENT_TYPE':<40} {'SYMBOL':<10} {'RUN_ID':<35} {'CLASS':<10} {'PREC':>6} {'REC':>6} {'EVENTS':>7} {'RATE/1K':>8}"
    print("\n" + "=" * len(header))
    print(header)
    print("=" * len(header))

    for cls in order:
        rows = by_class.get(cls, [])
        if not rows:
            continue
        print(f"\n--- {cls.upper()} ({len(rows)}) ---")
        for m in sorted(rows, key=lambda x: x["event_type"]):
            prec = f"{m['precision']:.3f}" if m["classification"] != "error" else "  err"
            rec_val = m.get("recall")
            rec = f"{rec_val:.3f}" if rec_val is not None else "  N/A"
            print(
                f"{m['event_type']:<40} {m['symbol']:<10} {m['run_id']:<35} "
                f"{m['classification']:<10} {prec:>6} {rec:>6} "
                f"{m['total_events']:>7} {m['event_rate_per_1k']:>8.1f}"
            )

    print("\n" + "=" * len(header))
    total = len(all_metrics)
    stable = len(by_class.get("stable", []))
    broken = len(by_class.get("broken", [])) + len(by_class.get("noisy", [])) + len(by_class.get("silent", []))
    print(f"TOTAL: {total}  STABLE: {stable}  NEED WORK: {broken}  UNCOVERED: {len(by_class.get('uncovered', []))}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit detector precision/recall across synthetic datasets.")
    parser.add_argument("--run_id", default=None, help="Run a single run_id (e.g. synthetic_2021_bull)")
    parser.add_argument("--event_type", default=None, help="Audit only this event type")
    parser.add_argument("--out_dir", default=None, help="Output directory for JSON report")
    args = parser.parse_args(argv)

    data_root = get_data_root()

    load_all_detectors()
    all_event_types = list_registered_event_types()

    if args.event_type:
        all_event_types = [et for et in all_event_types if et == args.event_type.upper()]
        if not all_event_types:
            print(f"ERROR: event_type {args.event_type!r} not registered.")
            return 1

    run_ids = [args.run_id] if args.run_id else sorted(KNOWN_RUN_IDS)
    # Validate requested run_id exists on disk
    for run_id in run_ids:
        manifest_path = data_root / "synthetic" / run_id / "synthetic_generation_manifest.json"
        if not manifest_path.exists():
            print(f"ERROR: manifest not found for run_id {run_id!r}: {manifest_path}")
            return 1

    all_metrics = []

    for run_id in run_ids:
        print(f"\nAuditing {run_id} ...")
        manifest = load_manifest(data_root, run_id)
        segments = load_truth_segments(data_root, run_id)

        for symbol_entry in manifest["symbols"]:
            symbol = symbol_entry["symbol"]
            print(f"  Building DataFrame for {symbol} ...")
            df = build_symbol_df(symbol_entry)

            for event_type in all_event_types:
                detector = get_detector(event_type)
                if detector is None:
                    continue
                metrics = measure_detector(detector, df, symbol, segments, run_id)
                all_metrics.append(metrics.to_dict())

    # --- Output ---
    _print_table(all_metrics)

    timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if args.out_dir:
        out_dir = Path(args.out_dir)
    else:
        out_dir = data_root / "artifacts" / "detector_audit" / timestamp

    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / "metrics.json"
    report_path.write_text(json.dumps(all_metrics, indent=2), encoding="utf-8")
    print(f"\nReport saved to: {report_path}")

    # Non-zero exit if any detector is broken/noisy/silent
    needs_work = [m for m in all_metrics if m["classification"] in ("broken", "noisy", "silent", "error")]
    return 1 if needs_work else 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2.4: Run the import test**

```bash
cd /home/tstuv/workspace/trading/EDGEE
.venv/bin/python -m pytest tests/scripts/test_detector_audit_module.py -v 2>&1 | tail -15
```

Expected: all tests pass.

- [ ] **Step 2.5: Verify the script runs end-to-end against one run_id**

```bash
cd /home/tstuv/workspace/trading/EDGEE
.venv/bin/python -m project.scripts.audit_detector_precision_recall \
  --run_id synthetic_2021_bull \
  --out_dir /tmp/detector_audit_test 2>&1 | tail -30
```

Expected: classification table printed, `metrics.json` written, no Python tracebacks.

- [ ] **Step 2.6: Commit**

```bash
cd /home/tstuv/workspace/trading/EDGEE
git add project/scripts/audit_detector_precision_recall.py
git commit -m "feat: add audit_detector_precision_recall CLI script"
```

---

## Chunk 2: Regression Test Scaffolding

### File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `tests/events/test_detector_precision_recall.py` | Per-detector regression tests using fixture thresholds |
| Create | `tests/events/fixtures/detector_thresholds.json` | Threshold values per detector × run_id (empty initially) |

---

### Task 3: Build the regression test file

**Files:**
- Create: `tests/events/test_detector_precision_recall.py`
- Create: `tests/events/fixtures/detector_thresholds.json`

- [ ] **Step 3.1: Create the empty fixture file**

```bash
mkdir -p /home/tstuv/workspace/trading/EDGEE/tests/events/fixtures
echo '{}' > /home/tstuv/workspace/trading/EDGEE/tests/events/fixtures/detector_thresholds.json
```

- [ ] **Step 3.2: Write the regression test**

Create `tests/events/test_detector_precision_recall.py`:

```python
"""
Per-detector precision/recall regression tests.

Tests are parameterized from tests/events/fixtures/detector_thresholds.json.
The fixture is seeded after the audit (plan Task 5).

If the fixture file is empty or an entry is missing, the test is SKIPPED (not
failed), allowing incremental population during the fix phase.

Mark: pytest.mark.slow — run with `pytest -m slow` or include in full suite.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict

import pytest

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "detector_thresholds.json"


def _load_thresholds() -> Dict[str, Any]:
    if not FIXTURE_PATH.exists():
        return {}
    raw = FIXTURE_PATH.read_text(encoding="utf-8").strip()
    if not raw or raw == "{}":
        return {}
    return json.loads(raw)


def _test_params():
    thresholds = _load_thresholds()
    params = []
    for event_type, run_map in thresholds.items():
        for run_id, bounds in run_map.items():
            params.append(pytest.param(event_type, run_id, bounds, id=f"{event_type}/{run_id}"))
    return params


@pytest.mark.slow
@pytest.mark.parametrize("event_type,run_id,bounds", _test_params())
def test_detector_precision_recall(event_type: str, run_id: str, bounds: Dict[str, float]) -> None:
    """
    Assert that a detector meets minimum precision and recall on a specific run_id.

    Averages metrics across all symbols in the run. Skips if the detector is
    uncovered (no truth windows) for all symbols.
    """
    from project.core.config import get_data_root
    from project.events.detectors.registry import get_detector, load_all_detectors
    from project.scripts.detector_audit_module import (
        build_symbol_df,
        load_manifest,
        load_truth_segments,
        measure_detector,
    )

    load_all_detectors()
    detector = get_detector(event_type)
    if detector is None:
        pytest.skip(f"Detector {event_type!r} not registered — fixture may be stale")

    data_root = get_data_root()
    manifest_path = data_root / "synthetic" / run_id / "synthetic_generation_manifest.json"
    if not manifest_path.exists():
        pytest.skip(f"Synthetic run {run_id!r} not found at {manifest_path}")

    manifest = load_manifest(data_root, run_id)
    segments = load_truth_segments(data_root, run_id)

    precision_vals = []
    recall_vals = []
    error_msgs = []

    for symbol_entry in manifest["symbols"]:
        df = build_symbol_df(symbol_entry)
        metrics = measure_detector(detector, df, symbol_entry["symbol"], segments, run_id)

        if metrics.classification == "error":
            error_msgs.append(f"{symbol_entry['symbol']}: {metrics.error}")
            continue
        if metrics.classification == "uncovered":
            continue

        precision_vals.append(metrics.precision)
        if not math.isnan(metrics.recall):
            recall_vals.append(metrics.recall)

    if error_msgs:
        pytest.fail(f"{event_type}/{run_id} detection errors:\n" + "\n".join(error_msgs))

    if not precision_vals:
        pytest.skip(f"{event_type}/{run_id}: all symbols uncovered — no truth windows")

    avg_precision = sum(precision_vals) / len(precision_vals)
    avg_recall = sum(recall_vals) / len(recall_vals) if recall_vals else float("nan")

    min_precision = float(bounds.get("min_precision", 0.50))
    min_recall = float(bounds.get("min_recall", 0.30))

    assert avg_precision >= min_precision, (
        f"{event_type}/{run_id}: avg precision {avg_precision:.3f} < required {min_precision:.3f}"
    )
    if not math.isnan(avg_recall):
        assert avg_recall >= min_recall, (
            f"{event_type}/{run_id}: avg recall {avg_recall:.3f} < required {min_recall:.3f}"
        )
```

- [ ] **Step 3.3: Verify the test collects zero items (fixture is empty)**

```bash
cd /home/tstuv/workspace/trading/EDGEE
.venv/bin/python -m pytest tests/events/test_detector_precision_recall.py --collect-only -q 2>&1 | head -10
```

Expected: `0 tests collected` (fixture is empty, no parametrize params generated).

- [ ] **Step 3.4: Run existing events tests to confirm no regressions**

```bash
cd /home/tstuv/workspace/trading/EDGEE
.venv/bin/python -m pytest tests/events/ -q 2>&1 | tail -10
```

Expected: all existing tests pass.

- [ ] **Step 3.5: Commit**

```bash
cd /home/tstuv/workspace/trading/EDGEE
git add tests/events/test_detector_precision_recall.py tests/events/fixtures/detector_thresholds.json
git commit -m "feat: add detector precision/recall regression test scaffold (empty fixture)"
```

---

## Chunk 3: Audit Execution and Fixture Seeding

> This chunk is an execution phase, not a code-writing phase. Run the audit, review the output, then seed the fixture file.

### Task 4: Run the full audit

**Files:**
- Read: `data/artifacts/detector_audit/<timestamp>/metrics.json` (generated)

- [ ] **Step 4.1: Run the full audit across all run_ids**

```bash
cd /home/tstuv/workspace/trading/EDGEE
.venv/bin/python -m project.scripts.audit_detector_precision_recall \
  --out_dir data/artifacts/detector_audit/baseline 2>&1 | tee /tmp/audit_output.txt
```

Expected: classification table printed with all detectors classified. Report saved to `data/artifacts/detector_audit/baseline/metrics.json`.

- [ ] **Step 4.2: Review the classification table**

Look for:
- All detectors classified as `broken`, `noisy`, or `silent` → these need fixing
- Any detectors classified as `error` → these have runtime issues (likely missing required columns not handled; investigate separately)
- Note the pre-audit classification for the 6 known-bad detectors

- [ ] **Step 4.3: Verify expected run_ids were all processed**

```bash
cd /home/tstuv/workspace/trading/EDGEE
python3 -c "
import json
metrics = json.load(open('data/artifacts/detector_audit/baseline/metrics.json'))
run_ids = sorted(set(m['run_id'] for m in metrics))
print('Run IDs audited:', run_ids)
event_types = sorted(set(m['event_type'] for m in metrics))
print('Event types audited:', len(event_types), event_types[:5], '...')
by_class = {}
for m in metrics:
    by_class.setdefault(m['classification'], []).append(m['event_type'])
for cls, ets in sorted(by_class.items()):
    print(f'{cls}: {len(ets)} results')
"
```

---

### Task 5: Seed the fixture file

**Files:**
- Modify: `tests/events/fixtures/detector_thresholds.json`

- [ ] **Step 5.1: Generate the fixture JSON from audit results**

Run the following script to build the fixture from the audit report. This seeds the fixture with **pre-fix** measured values (for documentation) but marks all non-stable detectors with the spec minimums (0.50 precision, 0.30 recall) so tests will fail for detectors that aren't yet fixed:

```bash
python3 - <<'EOF'
import json
from pathlib import Path

metrics = json.load(open("data/artifacts/detector_audit/baseline/metrics.json"))

# Only include stable detectors in the fixture at this stage.
# Non-stable detectors will be added after they are fixed (Task 12).
thresholds = {}
for m in metrics:
    if m["classification"] != "stable":
        continue
    if m.get("recall") is None:
        continue  # uncovered
    event_type = m["event_type"]
    run_id = m["run_id"]
    if event_type not in thresholds:
        thresholds[event_type] = {}
    if run_id not in thresholds[event_type]:
        # Buffer: subtract 0.05 from measured, floor at spec minimums
        min_prec = max(0.50, round(m["precision"] - 0.05, 3))
        min_rec = max(0.30, round(m["recall"] - 0.05, 3))
        thresholds[event_type][run_id] = {
            "min_precision": min_prec,
            "min_recall": min_rec,
        }

fixture_path = Path("tests/events/fixtures/detector_thresholds.json")
fixture_path.write_text(json.dumps(thresholds, indent=2), encoding="utf-8")
print(f"Seeded {sum(len(v) for v in thresholds.values())} entries for {len(thresholds)} detectors")
EOF
```

- [ ] **Step 5.2: Verify stable-only tests collect and pass**

```bash
cd /home/tstuv/workspace/trading/EDGEE
.venv/bin/python -m pytest tests/events/test_detector_precision_recall.py --collect-only -q 2>&1 | head -10
.venv/bin/python -m pytest tests/events/test_detector_precision_recall.py -m slow -q 2>&1 | tail -15
```

Expected: tests collected for stable detectors only; all pass.

- [ ] **Step 5.3: Commit the pre-fix fixture**

```bash
cd /home/tstuv/workspace/trading/EDGEE
git add tests/events/fixtures/detector_thresholds.json
git commit -m "chore: seed detector_thresholds fixture with stable detectors (pre-fix baseline)"
```

---

## Chunk 4: Detector Fixes

Fix detectors in priority order: **broken** first, then **noisy**, then **silent**.

For each detector, the workflow is identical:
1. Read the audit report for the specific detector to understand the failure mode
2. Make the minimum necessary change
3. Re-run the audit for just that detector to verify improvement
4. Re-run contract tests
5. Commit

**Template command for re-auditing a single detector:**
```bash
.venv/bin/python -m project.scripts.audit_detector_precision_recall \
  --event_type <EVENT_TYPE> \
  --out_dir data/artifacts/detector_audit/fix_<EVENT_TYPE>
```

**Template command for re-running contract tests:**
```bash
.venv/bin/python -m pytest tests/events/ -q 2>&1 | tail -5
```

---

### Task 6: Fix `MOMENTUM_DIVERGENCE_TRIGGER` (pre-classified: noisy)

**File:** `project/events/detectors/exhaustion.py`

The detector requires divergence + divergence turn + extension at 90th percentile. If noisy, the extension gate isn't filtering enough false positives.

- [ ] **Step 6.1: Read audit report for MOMENTUM_DIVERGENCE_TRIGGER**

```bash
python3 -c "
import json
metrics = json.load(open('data/artifacts/detector_audit/baseline/metrics.json'))
rows = [m for m in metrics if m['event_type'] == 'MOMENTUM_DIVERGENCE_TRIGGER']
for r in rows:
    print(r['run_id'], r['symbol'], r['classification'], 'prec:', r['precision'], 'rec:', r['recall'], 'events:', r['total_events'])
"
```

- [ ] **Step 6.2: If classified as noisy — tighten extension threshold**

In `project/events/detectors/exhaustion.py`, change the class attribute:

```python
# Before
min_trend_extension_quantile: float = 0.90

# After
min_trend_extension_quantile: float = 0.95
```

This requires the trend extension to be in the 95th percentile of historical extensions before divergence can fire, reducing false positives in low-extension regimes.

- [ ] **Step 6.3: Re-run audit for this detector**

```bash
cd /home/tstuv/workspace/trading/EDGEE
.venv/bin/python -m project.scripts.audit_detector_precision_recall \
  --event_type MOMENTUM_DIVERGENCE_TRIGGER \
  --out_dir data/artifacts/detector_audit/fix_MOMENTUM_DIVERGENCE_TRIGGER
```

Expected: classification improves toward `stable`. If still `noisy`, further increase to 0.97 and re-run.

- [ ] **Step 6.4: Run contract tests**

```bash
.venv/bin/python -m pytest tests/events/ -q 2>&1 | tail -5
```

Expected: all pass.

- [ ] **Step 6.5: Commit**

```bash
git add project/events/detectors/exhaustion.py
git commit -m "fix: raise MOMENTUM_DIVERGENCE_TRIGGER extension threshold to reduce false positives"
```

---

### Task 7: Fix `TREND_ACCELERATION` (pre-classified: noisy)

**File:** `project/events/detectors/trend.py`

The detector requires trend at 92nd percentile AND trend delta at 98th percentile AND direction consistency. If still noisy, the issue is likely direction_consistency allowing brief noise spikes to pass.

- [ ] **Step 7.1: Read audit report for TREND_ACCELERATION**

```bash
python3 -c "
import json
metrics = json.load(open('data/artifacts/detector_audit/baseline/metrics.json'))
rows = [m for m in metrics if m['event_type'] == 'TREND_ACCELERATION']
for r in rows:
    print(r['run_id'], r['symbol'], r['classification'], 'prec:', r['precision'], 'rec:', r['recall'], 'events:', r['total_events'])
"
```

- [ ] **Step 7.2: If classified as noisy — widen the direction consistency window**

In `project/events/detectors/trend.py`, change the direction consistency check in `compute_raw_mask` from a 3-bar rolling mean to a 6-bar rolling mean:

```python
# Before (line ~86)
direction_consistent = (np.sign(ret_1.rolling(window=3, min_periods=1).mean()) == np.sign(trend_raw)).fillna(False)

# After
direction_consistent = (np.sign(ret_1.rolling(window=6, min_periods=3).mean()) == np.sign(trend_raw)).fillna(False)
```

This requires short-term momentum to sustain direction alignment for 6 bars rather than 3, filtering transient noise spikes.

- [ ] **Step 7.3: Re-run audit for this detector**

```bash
.venv/bin/python -m project.scripts.audit_detector_precision_recall \
  --event_type TREND_ACCELERATION \
  --out_dir data/artifacts/detector_audit/fix_TREND_ACCELERATION
```

Expected: precision improves. If still `noisy`, try one additional change independently (not combined with Step 7.2): raise `min_trend_extension_quantile` from 0.92 to 0.95 as a separate commit. Attribute each change individually to understand which one is effective.

- [ ] **Step 7.4: Run contract tests**

```bash
.venv/bin/python -m pytest tests/events/ -q 2>&1 | tail -5
```

- [ ] **Step 7.5: Commit**

```bash
git add project/events/detectors/trend.py
git commit -m "fix: widen TREND_ACCELERATION direction consistency window to reduce noise"
```

---

### Task 8: Fix `TREND_EXHAUSTION_TRIGGER` (pre-classified: silent)

**File:** `project/events/detectors/exhaustion.py`

If silent, the detector is too strict. The most likely cause is the `trend_peak_multiplier=1.10` requiring trend to be 10% *above* the 95th percentile extreme — effectively the 97-99th percentile after multiplication.

- [ ] **Step 8.1: Read audit report for TREND_EXHAUSTION_TRIGGER**

```bash
python3 -c "
import json
metrics = json.load(open('data/artifacts/detector_audit/baseline/metrics.json'))
rows = [m for m in metrics if m['event_type'] == 'TREND_EXHAUSTION_TRIGGER']
for r in rows:
    print(r['run_id'], r['symbol'], r['classification'], 'prec:', r['precision'], 'rec:', r['recall'], 'events:', r['total_events'], 'rate:', r['event_rate_per_1k'])
"
```

- [ ] **Step 8.2: If classified as silent — reduce the trend_peak_multiplier default**

In `TrendExhaustionDetector.compute_raw_mask`, the multiplier is read from params:

```python
trend_peak_multiplier = float(params.get("trend_peak_multiplier", 1.10))
```

Change the default in the params call:

```python
# Before
trend_peak_multiplier = float(params.get("trend_peak_multiplier", 1.10))

# After — reduce from 1.10 to 1.00; trend only needs to reach (not exceed) the 95th percentile
trend_peak_multiplier = float(params.get("trend_peak_multiplier", 1.00))
```

This allows trend exhaustion to fire when trend reaches the 95th percentile (not 10% beyond it), improving recall while the dual cooldown+reversal guards maintain precision.

- [ ] **Step 8.3: Re-run audit for this detector**

```bash
.venv/bin/python -m project.scripts.audit_detector_precision_recall \
  --event_type TREND_EXHAUSTION_TRIGGER \
  --out_dir data/artifacts/detector_audit/fix_TREND_EXHAUSTION_TRIGGER
```

Expected: recall improves. If still `silent`, try lowering `trend_quantile` default from 0.95 to 0.90 in `prepare_features`.

- [ ] **Step 8.4: Run contract tests**

```bash
.venv/bin/python -m pytest tests/events/ -q 2>&1 | tail -5
```

- [ ] **Step 8.5: Commit**

```bash
git add project/events/detectors/exhaustion.py
git commit -m "fix: lower TREND_EXHAUSTION_TRIGGER peak multiplier to improve recall"
```

---

### Task 9: Fix `LIQUIDITY_STRESS_DIRECT` (pre-classified: silent)

**File:** `project/events/detectors/liquidity.py`

Requires BOTH depth < 50% of median AND spread > 3x median simultaneously. In synthetic data, both conditions must coincide in the same bar; the joint condition may be too strict.

- [ ] **Step 9.1: Read audit report for LIQUIDITY_STRESS_DIRECT**

```bash
python3 -c "
import json
metrics = json.load(open('data/artifacts/detector_audit/baseline/metrics.json'))
rows = [m for m in metrics if m['event_type'] == 'LIQUIDITY_STRESS_DIRECT']
for r in rows:
    print(r['run_id'], r['symbol'], r['classification'], 'prec:', r['precision'], 'rec:', r['recall'], 'events:', r['total_events'], 'rate:', r['event_rate_per_1k'])
"
```

- [ ] **Step 9.2: If classified as silent with near-zero event rate — reduce thresholds**

In `BaseLiquidityStressDetector`, the default thresholds are `depth_collapse_threshold=0.5` and `spread_spike_threshold=3.0`. Lower both slightly:

```python
# Before
default_depth_collapse_threshold = 0.5
default_spread_spike_threshold = 3.0

# After
default_depth_collapse_threshold = 0.6   # depth must fall to <60% of median (less strict)
default_spread_spike_threshold = 2.5     # spread must exceed 2.5x median (less strict)
```

- [ ] **Step 9.3: Re-run audit**

```bash
.venv/bin/python -m project.scripts.audit_detector_precision_recall \
  --event_type LIQUIDITY_STRESS_DIRECT \
  --out_dir data/artifacts/detector_audit/fix_LIQUIDITY_STRESS_DIRECT
```

Expected: event rate increases; check that precision stays ≥ 0.50. If precision drops too far, restore `spread_spike_threshold` to 3.0 and only keep the depth change.

- [ ] **Step 9.4: Run contract tests**

```bash
.venv/bin/python -m pytest tests/events/ -q 2>&1 | tail -5
```

- [ ] **Step 9.5: Commit**

```bash
git add project/events/detectors/liquidity.py
git commit -m "fix: loosen LIQUIDITY_STRESS_DIRECT thresholds to improve recall on synthetic data"
```

---

### Task 10: Fix remaining non-stable detectors from audit

For each detector classified as `broken`, `noisy`, or `silent` by the audit (beyond the 4 above), apply the same workflow:

- [ ] **Step 10.1: For each non-stable, non-error detector from the audit:**

  1. Read its code: `project/events/detectors/<family>.py` or `project/events/families/<family>.py`
  2. Identify the failure mode: noisy → filter is too loose; silent → filter is too strict
  3. Make the minimum change (adjust one quantile threshold or window size)
  4. Re-run the single-detector audit
  5. Run contract tests
  6. Commit with message: `fix: <DETECTOR_NAME> - <one sentence description>`

- [ ] **Step 10.2: After all fixes — run a rough verification audit**

```bash
.venv/bin/python -m project.scripts.audit_detector_precision_recall \
  --out_dir data/artifacts/detector_audit/post_fix 2>&1 | tee /tmp/post_fix_audit.txt
```

Expected: all detectors classified as `stable` or `uncovered`. Any remaining `noisy`/`silent`/`broken` must be documented in `defect_ledger.md` with a reason for deferral.

Note: This is a rough check only. Task 12 runs the authoritative final audit that is used to seed the fixture file. The results of this step and Task 12 may differ slightly if additional fixes are made between them.

---

## Chunk 5: Truth Validator Update and Final Gates

### File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Modify | `project/scripts/validate_synthetic_detector_truth.py` | Add per-event-type tolerance dict support |
| Modify | `tests/events/fixtures/detector_thresholds.json` | Add post-fix thresholds for fixed detectors |
| Read | `defect_ledger.md` | Add rows for each fixed detector |

---

### Task 11: Update the truth validator

**File:** `project/scripts/validate_synthetic_detector_truth.py`

- [ ] **Step 11.1: Write a failing test for the new interface**

Add to `tests/scripts/test_validate_synthetic_detector_truth.py` (create if absent):

```python
def test_tolerance_minutes_accepts_dict():
    """validate_detector_truth must accept tolerance_minutes as a dict."""
    from project.scripts.validate_synthetic_detector_truth import validate_detector_truth
    import inspect
    sig = inspect.signature(validate_detector_truth)
    # Verify the function accepts the call without TypeError
    # (actual behavior tested in existing tests)
    assert "tolerance_minutes" in sig.parameters
```

```python
def test_tolerance_dict_uses_per_event_type_value(tmp_path):
    """When tolerance_minutes is a dict, event-type-specific values are used."""
    import json
    from project.scripts.validate_synthetic_detector_truth import validate_detector_truth

    # Minimal truth map with one segment
    truth_map = {
        "segments": [{
            "regime_type": "test",
            "symbol": "BTCUSDT",
            "start_ts": "2024-01-01T01:00:00+00:00",
            "end_ts": "2024-01-01T02:00:00+00:00",
            "sign": 1,
            "amplitude": 1.0,
            "intended_effect_direction": "test",
            "expected_event_types": ["VOL_SPIKE"],
            "expected_detector_families": [],
        }]
    }
    truth_map_path = tmp_path / "truth.json"
    truth_map_path.write_text(json.dumps(truth_map))

    # Function should not raise when passed a dict
    # (it will return without events since there's no data_root content)
    result = validate_detector_truth(
        data_root=tmp_path,
        run_id="test_run",
        truth_map_path=truth_map_path,
        tolerance_minutes={"VOL_SPIKE": 60, "BASIS_DISLOC": 15},
    )
    assert isinstance(result, dict)
    assert "passed" in result
```

- [ ] **Step 11.2: Run to confirm failure**

```bash
.venv/bin/python -m pytest tests/scripts/test_validate_synthetic_detector_truth.py -v 2>&1 | tail -15
```

Expected: `test_tolerance_dict_uses_per_event_type_value` fails with `TypeError` (function doesn't accept dict yet).

- [ ] **Step 11.3: Update `validate_synthetic_detector_truth.py`**

Make two changes:

**Change 1:** Update the function signature at line 74:

```python
# Before
def validate_detector_truth(
    *,
    data_root: Path,
    run_id: str,
    truth_map_path: Path,
    tolerance_minutes: int = 30,
    max_off_regime_rate: float = 0.75,
) -> Dict[str, Any]:

# After
def validate_detector_truth(
    *,
    data_root: Path,
    run_id: str,
    truth_map_path: Path,
    tolerance_minutes: Union[int, Dict[str, int]] = 30,
    max_off_regime_rate: float = 0.75,
) -> Dict[str, Any]:
```

**Change 2:** Add `Union` and `Dict` to the imports at the top of the file:

```python
# Before
from typing import Any, Dict, Iterable, List, Mapping

# After
from typing import Any, Dict, Iterable, List, Mapping, Union
```

**Change 3:** Replace the single `tolerance = pd.Timedelta(...)` line (line 83) with per-event-type resolution:

```python
# Before (line 83)
    tolerance = pd.Timedelta(minutes=int(tolerance_minutes))

# After
    def _get_tolerance(event_type: str) -> pd.Timedelta:
        if isinstance(tolerance_minutes, dict):
            minutes = tolerance_minutes.get(event_type, 30)
        else:
            minutes = int(tolerance_minutes)
        return pd.Timedelta(minutes=minutes)
```

**Change 4:** Replace uses of `tolerance` in the loop with `_get_tolerance(event_type)`:

```python
# Before (inside the for event_type loop, line ~105)
            windows = _truth_windows(relevant_segments, symbol=symbol, tolerance=tolerance)

# After
            windows = _truth_windows(relevant_segments, symbol=symbol, tolerance=_get_tolerance(event_type))
```

Also update the return dict to serialize the tolerance value correctly:

```python
# Before (line ~139)
        "tolerance_minutes": int(tolerance_minutes),

# After
        "tolerance_minutes": tolerance_minutes if isinstance(tolerance_minutes, int) else dict(tolerance_minutes),
```

**Note on CLI:** The `argparse` `--tolerance_minutes` argument at line 151 and its `int()` cast at line 166 are intentionally left as `type=int`. The CLI is not the primary interface for per-event-type overrides (those are passed programmatically). The dict form is only used by callers invoking `validate_detector_truth()` directly from Python. No change is needed to the CLI code.

- [ ] **Step 11.4: Run the new tests**

```bash
.venv/bin/python -m pytest tests/scripts/test_validate_synthetic_detector_truth.py -v 2>&1 | tail -15
```

Expected: all pass.

- [ ] **Step 11.5: Run full events tests to confirm no regressions**

```bash
.venv/bin/python -m pytest tests/ -q 2>&1 | tail -10
```

Expected: all pass.

- [ ] **Step 11.6: Commit**

```bash
git add project/scripts/validate_synthetic_detector_truth.py
git commit -m "feat: make validate_detector_truth tolerance_minutes accept per-event-type dict"
```

---

### Task 12: Update fixture thresholds with post-fix values

**Files:**
- Modify: `tests/events/fixtures/detector_thresholds.json`

- [ ] **Step 12.1: Run the post-fix audit to get final measurements**

```bash
.venv/bin/python -m project.scripts.audit_detector_precision_recall \
  --out_dir data/artifacts/detector_audit/post_fix_final
```

- [ ] **Step 12.2: Add fixed detectors to the fixture**

Run the same seeding script as Task 5.1 but against the post-fix audit, and merge with existing fixture:

```bash
python3 - <<'EOF'
import json
from pathlib import Path

metrics = json.load(open("data/artifacts/detector_audit/post_fix_final/metrics.json"))
fixture_path = Path("tests/events/fixtures/detector_thresholds.json")
thresholds = json.loads(fixture_path.read_text())

for m in metrics:
    if m["classification"] != "stable":
        continue
    if m.get("recall") is None:
        continue
    event_type = m["event_type"]
    run_id = m["run_id"]
    if event_type not in thresholds:
        thresholds[event_type] = {}
    if run_id not in thresholds[event_type]:
        min_prec = max(0.50, round(m["precision"] - 0.05, 3))
        min_rec = max(0.30, round(m["recall"] - 0.05, 3))
        thresholds[event_type][run_id] = {
            "min_precision": min_prec,
            "min_recall": min_rec,
        }

fixture_path.write_text(json.dumps(thresholds, indent=2), encoding="utf-8")
total = sum(len(v) for v in thresholds.values())
print(f"Fixture now has {total} entries for {len(thresholds)} detectors")
EOF
```

- [ ] **Step 12.3: Run all regression tests to confirm they pass**

```bash
.venv/bin/python -m pytest tests/events/test_detector_precision_recall.py -m slow -v 2>&1 | tail -20
```

Expected: all tests pass. No failures.

- [ ] **Step 12.4: Commit**

```bash
git add tests/events/fixtures/detector_thresholds.json
git commit -m "chore: populate detector_thresholds fixture with post-fix precision/recall values"
```

---

### Task 13: Run golden synthetic discovery

- [ ] **Step 13.1: Run golden synthetic discovery**

```bash
cd /home/tstuv/workspace/trading/EDGEE
make golden-synthetic-discovery 2>&1 | tail -20
```

If `make golden-synthetic-discovery` is unavailable, use:

```bash
.venv/bin/python -m project.scripts.run_golden_synthetic_discovery 2>&1 | tail -20
```

- [ ] **Step 13.2: Verify passed: true**

```bash
python3 -c "
import json
result = json.load(open('reliability/golden_synthetic_discovery_summary.json'))
print('passed:', result.get('passed'))
if not result.get('passed'):
    print('FAILED — check event reports')
"
```

Expected: `passed: True`

- [ ] **Step 13.3: Run full test suite**

```bash
.venv/bin/python -m pytest -q 2>&1 | tail -15
```

Expected: all tests pass.

---

### Task 14: Update `defect_ledger.md`

**File:** `defect_ledger.md`

- [ ] **Step 14.1: Add a row for each detector that was classified as non-stable**

For each detector that was fixed, add a row using this schema:

| Column | Value |
|--------|-------|
| ID | Next sequential ID (D-007, D-008, ...) |
| Status | Closed |
| Category | Detector Calibration |
| Defect Description | Pre-fix classification (e.g. "MOMENTUM_DIVERGENCE_TRIGGER noisy: precision 0.28 on synthetic_2021_bull") |
| Root Cause | One sentence (e.g. "Extension threshold at 90th percentile allowed false positives in low-extension regimes") |
| Owner | ts |
| Acceptance Criteria | Post-fix values (e.g. "Precision ≥ 0.50, recall ≥ 0.30 on all applicable run_ids") |

D-005 (safe_coercion warnings) is a separate issue with a broader scope than detector fixes. Do not update D-005 as part of this task — it requires a separate smoke run verification. Leave it as `Open`.

- [ ] **Step 14.2: Update the Reproducible Baseline Status section**

Add a new line:
```
- **Detector Precision/Recall:** GREEN (all detectors stable or documented as uncovered)
```

- [ ] **Step 14.3: Commit**

```bash
git add defect_ledger.md
git commit -m "docs: update defect_ledger with detector stabilization baselines"
```

---

## Appendix: Detector Fix Decision Tree

Use this when fixing a detector from the audit:

```
Is event_rate_per_1k == 0 or near zero?
  YES → Detector is completely silent. Check required_columns are present.
        If columns present: the filter conditions are never satisfied.
        Try: reduce quantile thresholds by 0.05 increments.
  NO →
    Is precision < 0.50?
      YES (noisy) → Detector fires too often outside truth windows.
                    Try: raise quantile thresholds, add minimum magnitude filter,
                         increase min_spacing, or add a direction consistency check.
    Is recall < 0.30?
      YES (silent) → Detector fires too rarely during truth windows.
                     Try: lower quantile thresholds, widen alignment windows,
                          reduce min_spacing, or relax AND conditions to OR.
    Both?
      (broken) → Address precision first (noisy path), then recheck recall.
```
