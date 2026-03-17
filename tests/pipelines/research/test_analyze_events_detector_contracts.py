from __future__ import annotations

from types import SimpleNamespace

import pandas as pd

from project.pipelines.research import analyze_events


def test_analyze_events_uses_registry_event_stream_for_sequence_detectors(monkeypatch, tmp_path) -> None:
    load_calls: dict[str, int] = {"registry": 0, "features": 0}

    def _registry_events(*args, **kwargs):
        load_calls["registry"] += 1
        return pd.DataFrame(
            {
                "symbol": ["BTCUSDT", "BTCUSDT"],
                "event_type": ["OI_SPIKE_POSITIVE", "VOL_SPIKE"],
                "signal_ts": pd.to_datetime(
                    ["2024-01-01 10:00:00+00:00", "2024-01-01 10:20:00+00:00"],
                    utc=True,
                ),
            }
        )

    def _features(*args, **kwargs):
        load_calls["features"] += 1
        raise AssertionError("sequence detectors should not load feature bars")

    monkeypatch.setattr(analyze_events, "load_registry_events", _registry_events)
    monkeypatch.setattr(analyze_events, "load_features", _features)
    monkeypatch.setattr(analyze_events, "get_data_root", lambda: tmp_path)
    monkeypatch.setattr(analyze_events, "start_manifest", lambda *args, **kwargs: {})
    monkeypatch.setattr(analyze_events, "finalize_manifest", lambda *args, **kwargs: {})
    monkeypatch.setattr(analyze_events, "run_analyzer_suite", lambda *args, **kwargs: {})

    rc = analyze_events.main(
        [
            "--run_id",
            "r1",
            "--symbols",
            "BTCUSDT",
            "--event_type",
            "SEQ_OI_SPIKEPOS_THEN_VOL_SPIKE",
            "--out_dir",
            str(tmp_path / "out"),
        ]
    )

    assert rc == 0
    assert load_calls["registry"] == 1
    assert load_calls["features"] == 0


def test_analyze_events_runs_analyzers_per_symbol_market(monkeypatch, tmp_path) -> None:
    class FakeDetector:
        def detect(self, df: pd.DataFrame, *, symbol: str, **params):
            return pd.DataFrame(
                {
                    "event_type": ["VOL_SPIKE"],
                    "event_id": [f"id_{symbol}"],
                    "symbol": [symbol],
                    "eval_bar_ts": [df["timestamp"].iloc[0]],
                    "signal_ts": [df["timestamp"].iloc[0]],
                    "severity": [1.0],
                }
            )

    captured: list[tuple[str, float]] = []

    def _load_features(*, run_id: str, symbol: str, timeframe: str):
        base = 100.0 if symbol == "BTCUSDT" else 200.0
        return pd.DataFrame(
            {
                "timestamp": pd.date_range("2024-01-01", periods=3, freq="5min", tz="UTC"),
                "close": [base, base + 1.0, base + 2.0],
            }
        )

    def _run_analyzers(events: pd.DataFrame, *, market: pd.DataFrame | None = None, **kwargs):
        assert market is not None
        captured.append((str(events["symbol"].iloc[0]), float(market["close"].iloc[0])))
        return {}

    fake_cfg = SimpleNamespace(
        reports_dir="volatility_transition",
        events_file="volatility_transition_events.parquet",
        parameters={},
        signal_column="vol_spike_event",
    )

    monkeypatch.setattr(analyze_events, "compose_event_config", lambda event_type: fake_cfg)
    monkeypatch.setattr(analyze_events, "load_all_detectors", lambda: None)
    monkeypatch.setattr(analyze_events, "get_detector", lambda event_type: FakeDetector())
    monkeypatch.setattr(analyze_events, "load_features", _load_features)
    monkeypatch.setattr(analyze_events, "merge_event_csv", lambda out_path, event_type, new_df: new_df.copy())
    monkeypatch.setattr(analyze_events, "run_analyzer_suite", _run_analyzers)
    monkeypatch.setattr(analyze_events, "get_data_root", lambda: tmp_path)
    monkeypatch.setattr(analyze_events, "start_manifest", lambda *args, **kwargs: {})
    monkeypatch.setattr(analyze_events, "finalize_manifest", lambda *args, **kwargs: {})
    monkeypatch.setattr(analyze_events, "_save_analyzer_results", lambda *args, **kwargs: None)

    rc = analyze_events.main(
        [
            "--run_id",
            "r1",
            "--symbols",
            "BTCUSDT,ETHUSDT",
            "--event_type",
            "VOL_SPIKE",
            "--out_dir",
            str(tmp_path / "out"),
        ]
    )

    assert rc == 0
    assert sorted(captured) == [("BTCUSDT", 100.0), ("ETHUSDT", 200.0)]
