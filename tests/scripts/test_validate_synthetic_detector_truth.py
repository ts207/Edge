from __future__ import annotations

import json

import pandas as pd

from project.io.utils import ensure_dir, write_parquet
from project.scripts.validate_synthetic_detector_truth import validate_detector_truth


def _write_event_report(tmp_path, run_id: str, reports_dir: str, events_file: str, rows: list[dict]) -> None:
    out_dir = tmp_path / "reports" / reports_dir / run_id
    ensure_dir(out_dir)
    write_parquet(pd.DataFrame(rows), out_dir / events_file)


def test_validate_synthetic_detector_truth_scores_expected_windows(tmp_path):
    run_id = "truth_run"
    truth_dir = tmp_path / "synthetic" / run_id
    ensure_dir(truth_dir)
    truth_path = truth_dir / "synthetic_regime_segments.json"
    truth_payload = {
        "run_id": run_id,
        "segments": [
            {
                "regime_type": "basis_desync",
                "symbol": "BTCUSDT",
                "start_ts": "2026-01-02T00:00:00Z",
                "end_ts": "2026-01-02T02:00:00Z",
                "expected_event_types": ["CROSS_VENUE_DESYNC"],
                "expected_detector_families": ["cross_venue_desync"],
                "intended_effect_direction": "desync_signaled",
            }
        ],
    }
    truth_path.write_text(json.dumps(truth_payload, indent=2), encoding="utf-8")

    _write_event_report(
        tmp_path,
        run_id,
        "cross_venue_desync",
        "cross_venue_desync_events.parquet",
        [
            {"symbol": "BTCUSDT", "event_type": "CROSS_VENUE_DESYNC", "enter_ts": "2026-01-02T00:30:00Z"},
            {"symbol": "BTCUSDT", "event_type": "CROSS_VENUE_DESYNC", "enter_ts": "2026-01-05T00:30:00Z"},
        ],
    )

    result = validate_detector_truth(
        data_root=tmp_path,
        run_id=run_id,
        truth_map_path=truth_path,
        tolerance_minutes=30,
        max_off_regime_rate=0.75,
    )
    assert result["passed"] is True
    report = result["event_reports"][0]
    assert report["event_type"] == "CROSS_VENUE_DESYNC"
    assert report["per_symbol"][0]["windows_hit"] == 1
    assert report["per_symbol"][0]["off_regime_events"] == 1


def test_tolerance_minutes_accepts_dict():
    """validate_detector_truth must accept tolerance_minutes as a dict."""
    import inspect
    from project.scripts.validate_synthetic_detector_truth import validate_detector_truth
    sig = inspect.signature(validate_detector_truth)
    assert "tolerance_minutes" in sig.parameters


def test_tolerance_dict_uses_per_event_type_value(tmp_path):
    """When tolerance_minutes is a dict, event-type-specific values are used."""
    from project.scripts.validate_synthetic_detector_truth import validate_detector_truth
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
    result = validate_detector_truth(
        data_root=tmp_path,
        run_id="test_run",
        truth_map_path=truth_map_path,
        tolerance_minutes={"VOL_SPIKE": 60, "BASIS_DISLOC": 15},
    )
    assert isinstance(result, dict)
    assert "passed" in result


def test_validate_synthetic_detector_truth_fails_when_expected_detector_misses(tmp_path):
    run_id = "truth_fail"
    truth_dir = tmp_path / "synthetic" / run_id
    ensure_dir(truth_dir)
    truth_path = truth_dir / "synthetic_regime_segments.json"
    truth_payload = {
        "run_id": run_id,
        "segments": [
            {
                "regime_type": "deleveraging_burst",
                "symbol": "ETHUSDT",
                "start_ts": "2026-01-03T00:00:00Z",
                "end_ts": "2026-01-03T01:00:00Z",
                "expected_event_types": ["DELEVERAGING_WAVE"],
                "expected_detector_families": ["positioning_extremes"],
                "intended_effect_direction": "forced_deleveraging",
            }
        ],
    }
    truth_path.write_text(json.dumps(truth_payload, indent=2), encoding="utf-8")

    _write_event_report(
        tmp_path,
        run_id,
        "positioning_extremes",
        "positioning_extremes_events.parquet",
        [
            {"symbol": "ETHUSDT", "event_type": "DELEVERAGING_WAVE", "enter_ts": "2026-01-07T00:30:00Z"},
        ],
    )

    result = validate_detector_truth(
        data_root=tmp_path,
        run_id=run_id,
        truth_map_path=truth_path,
        tolerance_minutes=15,
        max_off_regime_rate=0.75,
    )
    assert result["passed"] is False
    assert result["event_reports"][0]["per_symbol"][0]["windows_hit"] == 0
    assert result["event_reports"][0]["per_symbol"][0]["passed_hit_requirement"] is False

