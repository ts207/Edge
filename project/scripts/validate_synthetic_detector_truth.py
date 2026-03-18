from __future__ import annotations

import argparse
import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any, Dict, List, Union

import pandas as pd

from project.core.config import get_data_root
from project.events.registry import EVENT_REGISTRY_SPECS
from project.io.utils import read_parquet


TIME_COLUMNS = ("enter_ts", "timestamp", "signal_ts", "event_ts", "anchor_ts")


def load_truth_map(path: Path) -> List[Dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and isinstance(payload.get("segments"), list):
        return [dict(item) for item in payload["segments"] if isinstance(item, Mapping)]
    raise ValueError(f"Invalid truth-map payload: {path}")


def _event_time_series(frame: pd.DataFrame) -> pd.Series:
    for column in TIME_COLUMNS:
        if column in frame.columns:
            return pd.to_datetime(frame[column], utc=True, errors="coerce")
    return pd.Series(dtype="datetime64[ns, UTC]")


def load_event_frame(*, data_root: Path, run_id: str, event_type: str) -> pd.DataFrame:
    spec = EVENT_REGISTRY_SPECS.get(str(event_type).strip().upper())
    if spec is None:
        return pd.DataFrame()
    report_dir = Path(data_root) / "reports" / spec.reports_dir / run_id
    report_path = report_dir / spec.events_file
    csv_path = report_path.with_suffix(".csv")
    source_path = report_path if report_path.exists() else csv_path
    if not source_path.exists():
        return pd.DataFrame()
    frame = read_parquet(source_path)
    if frame.empty:
        return frame
    if "event_type" in frame.columns:
        frame = frame[frame["event_type"].astype(str).str.upper() == str(event_type).strip().upper()].copy()
    return frame.reset_index(drop=True)


def _truth_windows(
    segments: Iterable[Mapping[str, Any]],
    *,
    symbol: str,
    event_type: str,
    tolerance: pd.Timedelta,
) -> List[tuple[pd.Timestamp, pd.Timestamp]]:
    windows: List[tuple[pd.Timestamp, pd.Timestamp]] = []
    for segment in segments:
        if str(segment.get("symbol", "")).upper() != str(symbol).upper():
            continue
        event_truth_windows = segment.get("event_truth_windows", {})
        event_specific = event_truth_windows.get(str(event_type).strip().upper(), [])
        if event_specific:
            for window in event_specific:
                start_ts = pd.Timestamp(window["start_ts"], tz="UTC") - tolerance
                end_ts = pd.Timestamp(window["end_ts"], tz="UTC") + tolerance
                windows.append((start_ts, end_ts))
            continue
        start_ts = pd.Timestamp(segment["start_ts"], tz="UTC") - tolerance
        end_ts = pd.Timestamp(segment["end_ts"], tz="UTC") + tolerance
        windows.append((start_ts, end_ts))
    return windows


def _count_hits(times: pd.Series, windows: List[tuple[pd.Timestamp, pd.Timestamp]]) -> tuple[int, int]:
    if times.empty or not windows:
        return 0, 0
    in_window = pd.Series(False, index=times.index)
    hit_windows = 0
    for start_ts, end_ts in windows:
        mask = times.between(start_ts, end_ts, inclusive="both")
        if bool(mask.any()):
            hit_windows += 1
        in_window = in_window | mask
    return int(in_window.sum()), int(hit_windows)


def _collect_truth_event_types(
    segments: Iterable[Mapping[str, Any]],
    *,
    field_name: str,
    selected_event_types: set[str],
) -> list[str]:
    return sorted(
        {
            str(event_type).strip().upper()
            for segment in segments
            for event_type in segment.get(field_name, [])
            if str(event_type).strip()
            and (not selected_event_types or str(event_type).strip().upper() in selected_event_types)
        }
    )


def _build_event_reports(
    *,
    segments: list[dict[str, Any]],
    event_types: list[str],
    field_name: str,
    data_root: Path,
    run_id: str,
    max_off_regime_rate: float,
    get_tolerance,
    min_precision_fraction: float | None = None,
) -> list[dict[str, Any]]:
    event_reports: List[Dict[str, Any]] = []
    for event_type in event_types:
        frame = load_event_frame(data_root=data_root, run_id=run_id, event_type=event_type)
        times = _event_time_series(frame)
        total_events = int(times.notna().sum())
        per_symbol: List[Dict[str, Any]] = []
        relevant_segments = [segment for segment in segments if event_type in segment.get(field_name, [])]
        for symbol in sorted({str(segment.get("symbol", "")).upper() for segment in relevant_segments if str(segment.get("symbol", "")).strip()}):
            if not frame.empty and "symbol" in frame.columns:
                symbol_frame = frame[frame["symbol"].astype(str).str.upper() == symbol].copy()
            else:
                symbol_frame = frame.iloc[0:0].copy()
            symbol_times = _event_time_series(symbol_frame)
            windows = _truth_windows(
                relevant_segments,
                symbol=symbol,
                event_type=event_type,
                tolerance=get_tolerance(event_type),
            )
            in_window_events, hit_windows = _count_hits(symbol_times, windows)
            off_regime_events = max(0, int(symbol_times.notna().sum()) - in_window_events)
            expected_windows = len(windows)
            off_regime_rate = float(off_regime_events / max(1, int(symbol_times.notna().sum())))
            precision = float(in_window_events / max(1, int(symbol_times.notna().sum())))
            passed_precision = (
                bool(precision >= float(min_precision_fraction))
                if min_precision_fraction is not None else None
            )
            per_symbol.append(
                {
                    "symbol": symbol,
                    "expected_windows": expected_windows,
                    "windows_hit": int(hit_windows),
                    "in_window_events": int(in_window_events),
                    "off_regime_events": int(off_regime_events),
                    "off_regime_rate": off_regime_rate,
                    "precision": precision,
                    "passed_hit_requirement": bool(hit_windows > 0 if expected_windows > 0 else True),
                    "passed_off_regime_bound": bool(off_regime_rate <= float(max_off_regime_rate)),
                    "passed_precision_bound": passed_precision,
                }
            )
        event_reports.append(
            {
                "event_type": event_type,
                "truth_role": "supporting" if field_name == "supporting_event_types" else "expected",
                "reports_dir": EVENT_REGISTRY_SPECS[event_type].reports_dir if event_type in EVENT_REGISTRY_SPECS else None,
                "total_events": total_events,
                "per_symbol": per_symbol,
            }
        )
    return event_reports


def validate_detector_truth(
    *,
    data_root: Path,
    run_id: str,
    truth_map_path: Path,
    tolerance_minutes: Union[int, Dict[str, int]] = 30,
    max_off_regime_rate: float = 0.35,
    min_precision_fraction: float | None = None,
    event_types: Iterable[str] | None = None,
    include_supporting_events: bool = False,
) -> Dict[str, Any]:
    segments = load_truth_map(truth_map_path)
    selected_event_types = {
        str(event_type).strip().upper()
        for event_type in (event_types or [])
        if str(event_type).strip()
    }

    def _get_tolerance(event_type: str) -> pd.Timedelta:
        if isinstance(tolerance_minutes, dict):
            minutes = tolerance_minutes.get(event_type, 30)
        else:
            minutes = int(tolerance_minutes)
        return pd.Timedelta(minutes=minutes)
    expected_event_types = _collect_truth_event_types(
        segments,
        field_name="expected_event_types",
        selected_event_types=selected_event_types,
    )
    event_reports = _build_event_reports(
        segments=segments,
        event_types=expected_event_types,
        field_name="expected_event_types",
        data_root=data_root,
        run_id=run_id,
        max_off_regime_rate=float(max_off_regime_rate),
        get_tolerance=_get_tolerance,
        min_precision_fraction=min_precision_fraction,
    )
    supporting_event_reports = (
        _build_event_reports(
            segments=segments,
            event_types=_collect_truth_event_types(
                segments,
                field_name="supporting_event_types",
                selected_event_types=selected_event_types,
            ),
            field_name="supporting_event_types",
            data_root=data_root,
            run_id=run_id,
            max_off_regime_rate=float(max_off_regime_rate),
            get_tolerance=_get_tolerance,
            min_precision_fraction=min_precision_fraction,
        )
        if include_supporting_events
        else []
    )

    overall_pass = all(
        all(symbol_row["passed_hit_requirement"] and symbol_row["passed_off_regime_bound"] for symbol_row in event_row["per_symbol"])
        for event_row in event_reports
    )
    return {
        "schema_version": "synthetic_detector_truth_validation_v2",
        "run_id": run_id,
        "truth_map_path": str(truth_map_path),
        "tolerance_minutes": tolerance_minutes if isinstance(tolerance_minutes, int) else dict(tolerance_minutes),
        "max_off_regime_rate": float(max_off_regime_rate),
        "selected_event_types": sorted(selected_event_types),
        "event_reports": event_reports,
        "supporting_event_reports": supporting_event_reports,
        "include_supporting_events": bool(include_supporting_events),
        "passed": bool(overall_pass),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate detector outputs against a synthetic truth map.")
    parser.add_argument("--run_id", required=True)
    parser.add_argument("--truth_map_path", default=None)
    parser.add_argument("--data_root", default=None)
    parser.add_argument("--tolerance_minutes", type=int, default=30)
    parser.add_argument("--max_off_regime_rate", type=float, default=0.35)
    parser.add_argument("--min_precision_fraction", type=float, default=None,
                        help="Minimum fraction of events that must fall inside regime windows")
    parser.add_argument("--event_types", nargs="+", default=None)
    parser.add_argument("--include_supporting_events", type=int, default=0)
    parser.add_argument("--json_out", default=None)
    args = parser.parse_args(argv)

    data_root = Path(args.data_root) if args.data_root else get_data_root()
    truth_map_path = (
        Path(args.truth_map_path)
        if args.truth_map_path
        else data_root / "synthetic" / args.run_id / "synthetic_regime_segments.json"
    )
    result = validate_detector_truth(
        data_root=data_root,
        run_id=str(args.run_id),
        truth_map_path=truth_map_path,
        tolerance_minutes=int(args.tolerance_minutes),
        max_off_regime_rate=float(args.max_off_regime_rate),
        min_precision_fraction=args.min_precision_fraction,
        event_types=args.event_types,
        include_supporting_events=bool(args.include_supporting_events),
    )
    if args.json_out:
        out_path = Path(args.json_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
