from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from project.research.seed_bootstrap import build_promotion_seed_inventory
from project.research.seed_empirical import run_empirical_seed_pass
from project.research import thesis_evidence_runner
from project.research.thesis_evidence_runner import build_founding_thesis_evidence


def _write_raw_partition(root: Path, symbol: str, dataset: str, frame: pd.DataFrame, *, year: int, month: int, stem: str) -> None:
    out_dir = root / "lake" / "raw" / "perp" / symbol / dataset / f"year={year}" / f"month={month:02d}"
    out_dir.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(out_dir / f"{stem}.parquet", index=False)


def _write_feature_partition(root: Path, run_id: str, symbol: str, frame: pd.DataFrame, *, year: int, month: int, stem: str) -> None:
    out_dir = (
        root
        / "lake"
        / "runs"
        / run_id
        / "features"
        / "perp"
        / symbol
        / "5m"
        / "features_feature_schema_v2"
        / f"year={year}"
        / f"month={month:02d}"
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(out_dir / f"{stem}.parquet", index=False)


def _synthetic_bars() -> pd.DataFrame:
    timestamps = list(pd.date_range("2021-01-01", periods=240, freq="5min", tz="UTC"))
    timestamps += list(pd.date_range("2022-01-01", periods=240, freq="5min", tz="UTC"))
    close = []
    price = 100.0
    for idx, _ts in enumerate(timestamps):
        cycle = idx % 12
        if cycle == 0:
            price *= 1.08
        elif cycle in {1, 2, 3}:
            price *= 1.01
        else:
            price *= 1.0005
        close.append(price)
    close = np.asarray(close)
    open_ = np.concatenate([[close[0] / 1.001], close[:-1]])
    high = np.maximum(open_, close) * 1.002
    low = np.minimum(open_, close) * 0.998
    volume = np.where(np.arange(len(close)) % 12 == 0, 2000.0, 500.0)
    return pd.DataFrame(
        {
            "timestamp": pd.to_datetime(timestamps, utc=True),
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
            "quote_volume": volume * close,
            "taker_base_volume": volume * 0.55,
            "symbol": "BTCUSDT",
            "source": "synthetic",
        }
    )


def _synthetic_basis_features() -> pd.DataFrame:
    timestamps = list(pd.date_range("2021-01-01", periods=240, freq="5min", tz="UTC"))
    timestamps += list(pd.date_range("2022-01-01", periods=240, freq="5min", tz="UTC"))
    close = []
    price = 100.0
    for idx, _ts in enumerate(timestamps):
        cycle = idx % 12
        if cycle == 0:
            price *= 1.03
        elif cycle in {1, 2}:
            price *= 1.004
        else:
            price *= 1.0005
        close.append(price)
    close = np.asarray(close)
    open_ = np.concatenate([[close[0] / 1.001], close[:-1]])
    high = np.maximum(open_, close) * 1.002
    low = np.minimum(open_, close) * 0.998
    event_mask = (np.arange(len(close)) % 12 == 0)
    basis_bps = np.where(event_mask, 30.0, 1.0)
    basis_zscore = np.where(event_mask, 6.0, 0.2)
    funding_rate_scaled = np.where(event_mask, 0.0008, 0.00002)
    return pd.DataFrame(
        {
            "timestamp": pd.to_datetime(timestamps, utc=True),
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": np.where(event_mask, 1800.0, 500.0),
            "quote_volume": np.where(event_mask, 1800.0, 500.0) * close,
            "taker_base_volume": np.where(event_mask, 900.0, 250.0),
            "symbol": "BTCUSDT",
            "source": "synthetic_feature_schema",
            "basis_bps": basis_bps,
            "basis_zscore": basis_zscore,
            "spot_close": close / (1.0 + basis_bps / 10_000.0),
            "basis_spot_coverage": np.ones(len(close)),
            "funding_rate_scaled": funding_rate_scaled,
        }
    )


def _synthetic_liquidation_proxy_features() -> pd.DataFrame:
    timestamps = list(pd.date_range("2021-01-01", periods=240, freq="5min", tz="UTC"))
    timestamps += list(pd.date_range("2022-01-01", periods=240, freq="5min", tz="UTC"))
    close = []
    price = 100.0
    event_mask = []
    for idx, _ts in enumerate(timestamps):
        is_event = idx % 12 == 0 and idx > 24
        event_mask.append(is_event)
        if is_event:
            price *= 0.965
        elif idx % 12 in {1, 2}:
            price *= 0.997
        else:
            price *= 1.0004
        close.append(price)
    close = np.asarray(close)
    open_ = np.concatenate([[close[0] / 1.001], close[:-1]])
    high = np.maximum(open_, close) * 1.001
    low = np.minimum(open_, close) * 0.997
    event_mask_np = np.asarray(event_mask, dtype=bool)
    return pd.DataFrame(
        {
            "timestamp": pd.to_datetime(timestamps, utc=True),
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": np.where(event_mask_np, 2400.0, 600.0),
            "quote_volume": np.where(event_mask_np, 2400.0, 600.0) * close,
            "taker_base_volume": np.where(event_mask_np, 1200.0, 300.0),
            "symbol": "BTCUSDT",
            "source": "synthetic_feature_schema",
            "funding_rate_scaled": np.where(event_mask_np, 0.0014, 0.0001),
            "micro_depth_depletion": np.where(event_mask_np, 0.92, 0.15),
            "spread_zscore": np.where(event_mask_np, 8.0, 0.5),
        }
    )


def test_load_raw_dataset_uses_shared_parquet_reader(monkeypatch, tmp_path) -> None:
    dataset_dir = tmp_path / "lake" / "raw" / "perp" / "BTCUSDT" / "ohlcv_5m"
    dataset_dir.mkdir(parents=True, exist_ok=True)
    files = [dataset_dir / "year=2026" / "month=01" / "part-000.parquet"]
    frame = pd.DataFrame({"timestamp": pd.to_datetime(["2026-01-01T00:00:00Z"], utc=True)})
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        thesis_evidence_runner,
        "resolve_raw_dataset_dir",
        lambda *_args, **_kwargs: dataset_dir,
    )
    monkeypatch.setattr(thesis_evidence_runner, "list_parquet_files", lambda _path: files)

    def _fake_read_parquet(arg):
        captured["arg"] = arg
        return frame.copy()

    monkeypatch.setattr(thesis_evidence_runner, "read_parquet", _fake_read_parquet)

    out = thesis_evidence_runner._load_raw_dataset("BTCUSDT", "ohlcv_5m", data_root=tmp_path)

    assert not out.empty
    assert captured["arg"] == files


def test_build_founding_thesis_evidence_writes_bundle(tmp_path: Path, monkeypatch) -> None:
    data_root = tmp_path / "data"
    docs = tmp_path / "docs"
    monkeypatch.setenv("BACKTEST_DATA_ROOT", str(data_root))

    bars = _synthetic_bars()
    _write_raw_partition(data_root, "BTCUSDT", "ohlcv_5m", bars[bars["timestamp"].dt.year == 2021], year=2021, month=1, stem="ohlcv_BTCUSDT_5m_2021-01")
    _write_raw_partition(data_root, "BTCUSDT", "ohlcv_5m", bars[bars["timestamp"].dt.year == 2022], year=2022, month=1, stem="ohlcv_BTCUSDT_5m_2022-01")

    policy_path = tmp_path / "founding_policy.yaml"
    policy_path.write_text(
        yaml.safe_dump(
            {
                "founding_theses": [
                    {
                        "candidate_id": "THESIS_VOL_TEST",
                        "event_type": "VOL_SHOCK",
                        "detector_kind": "vol_shock",
                        "symbols": ["BTCUSDT"],
                        "horizons": [2, 4],
                        "payoff_mode": "absolute_return",
                        "fees_bps": 1.0,
                        "params": {"rv_window": 3, "baseline_window": 12, "shock_quantile": 0.8},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    out = build_founding_thesis_evidence(policy_path=policy_path, docs_dir=docs, data_root=data_root)
    bundle_path = data_root / "reports" / "promotions" / "THESIS_VOL_TEST" / "evidence_bundles.jsonl"
    assert bundle_path.exists()
    rows = [json.loads(line) for line in bundle_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert rows
    row = rows[0]
    assert row["candidate_id"] == "THESIS_VOL_TEST"
    assert row["sample_definition"]["test_samples"] > 0
    assert row["metadata"]["has_realized_oos_path"] is True
    payload = json.loads(out["json"].read_text(encoding="utf-8"))
    assert payload["schema_version"] == "founding_thesis_evidence_summary_v1"
    assert payload["workspace_root"] == "."
    assert payload["artifact_root"] == "docs"
    assert payload["source_run_id"] == "founding_thesis_evidence"
    assert payload["all_referenced_files_exist"] is True
    assert payload["invalid_artifact_refs"] == []
    assert any(key.startswith("bundle::THESIS_VOL_TEST") for key in payload["artifact_refs"])
    summary_md = out["md"].read_text(encoding="utf-8")
    assert "## Artifact metadata" in summary_md
    assert "THESIS_VOL_TEST" in summary_md


def test_empirical_confirm_candidate_requires_explicit_bundle(tmp_path: Path, monkeypatch) -> None:
    docs = tmp_path / "docs"
    data_root = tmp_path / "data"
    monkeypatch.setenv("BACKTEST_DATA_ROOT", str(data_root))
    build_promotion_seed_inventory(docs_dir=docs)

    for run_id, event_type in (("run-vol", "VOL_SHOCK"), ("run-liq", "LIQUIDITY_VACUUM")):
        out_dir = data_root / "reports" / "promotions" / run_id
        out_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "candidate_id": f"THESIS_{event_type}",
            "event_family": event_type,
            "event_type": event_type,
            "sample_definition": {"n_events": 120, "validation_samples": 40, "test_samples": 40},
            "effect_estimates": {"estimate_bps": 20.0},
            "uncertainty_estimates": {"q_value": 0.03},
            "stability_tests": {"stability_score": 0.10},
            "falsification_results": {"negative_control_pass_rate": 0.01, "session_transition": {"passed": True}},
            "cost_robustness": {"net_expectancy_bps": 10.0},
            "metadata": {"has_realized_oos_path": True},
        }
        (out_dir / "evidence_bundles.jsonl").write_text(json.dumps(payload) + "\n", encoding="utf-8")

    out = run_empirical_seed_pass(docs_dir=docs, inventory_path=docs / "promotion_seed_inventory.csv", data_root=data_root)
    rows = json.loads(out["json"].read_text(encoding="utf-8"))
    confirm = next(row for row in rows if row["candidate_id"] == "THESIS_VOL_SHOCK_LIQUIDITY_CONFIRM")
    assert int(confirm["matched_bundle_count"]) == 0
    assert confirm["empirical_decision"] == "needs_more_evidence"


def test_build_founding_thesis_evidence_supports_basis_and_funding_from_feature_schema(tmp_path: Path, monkeypatch) -> None:
    data_root = tmp_path / "data"
    docs = tmp_path / "docs"
    monkeypatch.setenv("BACKTEST_DATA_ROOT", str(data_root))

    features = _synthetic_basis_features()
    _write_feature_partition(
        data_root,
        "run_feature_test",
        "BTCUSDT",
        features[features["timestamp"].dt.year == 2021],
        year=2021,
        month=1,
        stem="features_BTCUSDT_feature_schema_v2_2021-01",
    )
    _write_feature_partition(
        data_root,
        "run_feature_test",
        "BTCUSDT",
        features[features["timestamp"].dt.year == 2022],
        year=2022,
        month=1,
        stem="features_BTCUSDT_feature_schema_v2_2022-01",
    )

    policy_path = tmp_path / "founding_policy.yaml"
    policy_path.write_text(
        yaml.safe_dump(
            {
                "founding_theses": [
                    {
                        "candidate_id": "THESIS_BASIS_DISLOC",
                        "event_type": "BASIS_DISLOC",
                        "detector_kind": "basis_disloc",
                        "symbols": ["BTCUSDT"],
                        "horizons": [2, 4],
                        "payoff_mode": "absolute_return",
                        "fees_bps": 1.0,
                        "params": {"z_threshold": 5.0, "min_basis_bps": 10.0, "cooldown_bars": 4},
                    },
                    {
                        "candidate_id": "THESIS_FND_DISLOC",
                        "event_type": "FND_DISLOC",
                        "detector_kind": "fnd_disloc",
                        "symbols": ["BTCUSDT"],
                        "horizons": [2, 4],
                        "payoff_mode": "absolute_return",
                        "fees_bps": 1.0,
                        "params": {
                            "z_threshold": 5.0,
                            "min_basis_bps": 10.0,
                            "threshold_bps": 2.0,
                            "funding_quantile": 0.95,
                            "alignment_window": 3,
                            "cooldown_bars": 4,
                        },
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    out = build_founding_thesis_evidence(policy_path=policy_path, docs_dir=docs, data_root=data_root)

    basis_bundle = data_root / "reports" / "promotions" / "THESIS_BASIS_DISLOC" / "evidence_bundles.jsonl"
    funding_bundle = data_root / "reports" / "promotions" / "THESIS_FND_DISLOC" / "evidence_bundles.jsonl"
    assert basis_bundle.exists()
    assert funding_bundle.exists()
    basis_rows = [json.loads(line) for line in basis_bundle.read_text(encoding="utf-8").splitlines() if line.strip()]
    funding_rows = [json.loads(line) for line in funding_bundle.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert basis_rows
    assert funding_rows
    assert basis_rows[0]["event_type"] == "BASIS_DISLOC"
    assert funding_rows[0]["event_type"] == "FND_DISLOC"
    assert "THESIS_BASIS_DISLOC" in out["json"].read_text(encoding="utf-8")
    assert "THESIS_FND_DISLOC" in out["json"].read_text(encoding="utf-8")


def test_build_founding_thesis_evidence_uses_chronological_holdout_when_single_split_side_exists(
    tmp_path: Path, monkeypatch
) -> None:
    data_root = tmp_path / "data"
    docs = tmp_path / "docs"
    monkeypatch.setenv("BACKTEST_DATA_ROOT", str(data_root))

    features = _synthetic_basis_features()
    features = features[features["timestamp"].dt.year == 2022].reset_index(drop=True)
    _write_feature_partition(
        data_root,
        "run_feature_test",
        "BTCUSDT",
        features[features["timestamp"].dt.year == 2021],
        year=2021,
        month=1,
        stem="features_BTCUSDT_feature_schema_v2_2021-01",
    )
    _write_feature_partition(
        data_root,
        "run_feature_test",
        "BTCUSDT",
        features[features["timestamp"].dt.year == 2022],
        year=2022,
        month=1,
        stem="features_BTCUSDT_feature_schema_v2_2022-01",
    )

    policy_path = tmp_path / "founding_policy.yaml"
    policy_path.write_text(
        yaml.safe_dump(
            {
                "founding_theses": [
                    {
                        "candidate_id": "THESIS_BASIS_DISLOC",
                        "event_type": "BASIS_DISLOC",
                        "detector_kind": "basis_disloc",
                        "symbols": ["BTCUSDT"],
                        "horizons": [2, 4],
                        "payoff_mode": "absolute_return",
                        "fees_bps": 1.0,
                        "params": {"z_threshold": 5.0, "min_basis_bps": 10.0, "cooldown_bars": 4},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    build_founding_thesis_evidence(policy_path=policy_path, docs_dir=docs, data_root=data_root)
    basis_bundle = data_root / "reports" / "promotions" / "THESIS_BASIS_DISLOC" / "evidence_bundles.jsonl"
    rows = [json.loads(line) for line in basis_bundle.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert rows
    assert rows[0]["split_definition"]["split_scheme_id"] == "chronological_holdout_70_30"
    assert rows[0]["sample_definition"]["validation_samples"] >= 10
    assert rows[0]["sample_definition"]["test_samples"] >= 10


def test_build_founding_thesis_evidence_supports_liquidation_proxy_from_feature_schema(
    tmp_path: Path, monkeypatch
) -> None:
    data_root = tmp_path / "data"
    docs = tmp_path / "docs"
    monkeypatch.setenv("BACKTEST_DATA_ROOT", str(data_root))

    features = _synthetic_liquidation_proxy_features()
    _write_feature_partition(
        data_root,
        "run_feature_test",
        "BTCUSDT",
        features[features["timestamp"].dt.year == 2021],
        year=2021,
        month=1,
        stem="features_BTCUSDT_feature_schema_v2_2021-01",
    )
    _write_feature_partition(
        data_root,
        "run_feature_test",
        "BTCUSDT",
        features[features["timestamp"].dt.year == 2022],
        year=2022,
        month=1,
        stem="features_BTCUSDT_feature_schema_v2_2022-01",
    )

    policy_path = tmp_path / "founding_policy.yaml"
    policy_path.write_text(
        yaml.safe_dump(
            {
                "founding_theses": [
                    {
                        "candidate_id": "THESIS_LIQUIDATION_CASCADE",
                        "event_type": "LIQUIDATION_CASCADE",
                        "detector_kind": "liquidation_cascade",
                        "symbols": ["BTCUSDT"],
                        "horizons": [2, 4],
                        "payoff_mode": "absolute_return",
                        "fees_bps": 1.0,
                        "params": {
                            "shock_quantile": 0.9,
                            "shock_window": 24,
                            "funding_quantile": 0.8,
                            "depth_quantile": 0.8,
                            "spread_quantile": 0.8,
                            "cooldown_bars": 4,
                            "min_funding_abs": 0.0005,
                            "min_depth_depletion": 0.6,
                            "min_spread_z": 3.0,
                        },
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    build_founding_thesis_evidence(policy_path=policy_path, docs_dir=docs, data_root=data_root)
    bundle_path = data_root / "reports" / "promotions" / "THESIS_LIQUIDATION_CASCADE" / "evidence_bundles.jsonl"
    assert bundle_path.exists()
    rows = [json.loads(line) for line in bundle_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert rows
    assert rows[0]["metadata"]["input_mode"] == "feature_schema_proxy"
    assert rows[0]["event_type"] == "LIQUIDATION_CASCADE"
