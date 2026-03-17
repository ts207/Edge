from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from project.core.feature_schema import feature_dataset_dir_name

from project.pipelines.clean import validate_feature_integrity as integrity

def _write_csv(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)

def test_validate_symbol_prefers_run_scoped_artifacts(tmp_path):
    data_root = tmp_path / "data"
    symbol = "BTCUSDT"
    run_id = "r1"

    global_features = pd.DataFrame({"x": [1.0, 2.0, 3.0]})
    run_features = pd.DataFrame({"x": [1.0, None, None]})

    _write_csv(
        data_root / "lake" / "features" / "perp" / symbol / "5m" / feature_dataset_dir_name() / "global.csv",
        global_features,
    )
    _write_csv(
        data_root
        / "lake"
        / "runs"
        / run_id
        / "features"
        / "perp"
        / symbol
        / "5m"
        / feature_dataset_dir_name()
        / "run.csv",
        run_features,
    )

    issues = integrity.validate_symbol(
        data_root,
        run_id,
        symbol,
        timeframe="5m",
        nan_threshold=0.5,
        z_threshold=10.0,
    )
    assert "features" in issues
    assert any("Column 'x'" in msg for msg in issues["features"])

def test_main_fails_when_issues_found_and_fail_on_issues_enabled(monkeypatch, tmp_path):
    data_root = tmp_path / "data"
    symbol = "BTCUSDT"
    run_id = "r1"
    _write_csv(
        data_root
        / "lake"
        / "runs"
        / run_id
        / "features"
        / "perp"
        / symbol
        / "5m"
        / feature_dataset_dir_name()
        / "run.csv",
        pd.DataFrame({"x": [None, None, 1.0]}),
    )
    monkeypatch.setenv("BACKTEST_DATA_ROOT", str(data_root))
    monkeypatch.setattr(
        sys,
        "argv",
        ["validate_feature_integrity.py", "--run_id", run_id, "--symbols", symbol, "--nan_threshold", "0.5"],
    )
    assert integrity.main() == 1

def test_main_warns_only_when_fail_on_issues_disabled(monkeypatch, tmp_path):
    data_root = tmp_path / "data"
    symbol = "BTCUSDT"
    run_id = "r2"
    _write_csv(
        data_root
        / "lake"
        / "runs"
        / run_id
        / "features"
        / "perp"
        / symbol
        / "5m"
        / feature_dataset_dir_name()
        / "run.csv",
        pd.DataFrame({"x": [None, None, 1.0]}),
    )
    monkeypatch.setenv("BACKTEST_DATA_ROOT", str(data_root))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "validate_feature_integrity.py",
            "--run_id",
            run_id,
            "--symbols",
            symbol,
            "--nan_threshold",
            "0.5",
            "--fail_on_issues",
            "0",
        ],
    )
    assert integrity.main() == 0


def test_validate_symbol_logs_single_drift_summary(monkeypatch, tmp_path, caplog):
    data_root = tmp_path / "data"
    symbol = "BTCUSDT"
    run_id = "r3"
    feature_dir = (
        data_root
        / "lake"
        / "runs"
        / run_id
        / "features"
        / "perp"
        / symbol
        / "5m"
        / feature_dataset_dir_name()
    )
    _write_csv(
        feature_dir / "run.csv",
        pd.DataFrame({"x": list(range(10)), "y": list(range(10, 20))}),
    )
    monkeypatch.setattr(
        integrity,
        "detect_feature_drift",
        lambda *_args, **_kwargs: [
            {"feature": "x", "p_value": 0.01},
            {"feature": "y", "p_value": 0.02},
        ],
    )

    with caplog.at_level("WARNING"):
        issues = integrity.validate_symbol(data_root, run_id, symbol, timeframe="5m")

    assert issues["features"] == [
        "Drift detected in 'x': KS p-value = 0.0100",
        "Drift detected in 'y': KS p-value = 0.0200",
    ]
    assert "BTCUSDT feature drift summary: 2 flagged columns (x, y)" in caplog.text
