from __future__ import annotations

import pandas as pd
import pytest

from project.engine.exchange_constraints import SymbolConstraints
from project.engine.strategy_executor import build_live_order_metadata, calculate_strategy_returns


class _DummyStrategy:
    def generate_positions(
        self, bars: pd.DataFrame, features: pd.DataFrame, params: dict
    ) -> pd.Series:
        out = pd.Series([0.0, 1.0, 1.0], index=pd.DatetimeIndex(bars["timestamp"]), dtype=float)
        out.attrs["strategy_metadata"] = {"family": "test"}
        return out


def _bars() -> pd.DataFrame:
    idx = pd.date_range("2024-01-01", periods=3, freq="5min", tz="UTC")
    return pd.DataFrame(
        {
            "timestamp": idx,
            "open": [100.0, 100.0, 100.0],
            "high": [100.2, 100.2, 100.2],
            "low": [99.8, 99.8, 99.8],
            "close": [100.0, 100.0, 100.0],
        }
    )


def _features() -> pd.DataFrame:
    idx = pd.date_range("2024-01-01", periods=3, freq="5min", tz="UTC")
    return pd.DataFrame(
        {
            "timestamp": idx,
            "spread_bps": [4.0, 4.0, 4.0],
            "quote_volume": [250000.0, 250000.0, 250000.0],
            "depth_usd": [50000.0, 50000.0, 50000.0],
            "tob_coverage": [1.0, 1.0, 1.0],
            "atr_14": [0.2, 0.2, 0.2],
        }
    )


def test_calculate_strategy_returns_applies_execution_aware_sizing(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("project.engine.strategy_executor.get_strategy", lambda _: _DummyStrategy())
    monkeypatch.setattr(
        "project.engine.strategy_executor.load_symbol_constraints",
        lambda symbol, meta_dir: SymbolConstraints(
            tick_size=None, step_size=None, min_notional=None
        ),
    )

    bars = _bars()
    features = _features()
    base_params = {
        "position_scale": 1000.0,
        "execution_lag_bars": 0,
        "execution_model": {
            "cost_model": "dynamic",
            "base_fee_bps": 2.0,
            "base_slippage_bps": 1.0,
            "spread_weight": 0.5,
            "volatility_weight": 0.0,
            "liquidity_weight": 0.0,
            "impact_weight": 1.0,
            "min_tob_coverage": 0.8,
        },
        "event_score": 0.008,
        "expected_return_bps": 20.0,
        "expected_adverse_bps": 20.0,
        "target_vol": 0.1,
        "current_vol": 0.1,
    }

    legacy = calculate_strategy_returns(
        "BTCUSDT",
        bars,
        features,
        "dummy_strategy",
        dict(base_params),
        0.0,
        tmp_path,
    )
    aware = calculate_strategy_returns(
        "BTCUSDT",
        bars,
        features,
        "dummy_strategy",
        {**base_params, "execution_aware_sizing": 1},
        0.0,
        tmp_path,
    )

    legacy_scale = float(legacy.data["requested_position_scale"].iloc[0])
    aware_scale = float(aware.data["requested_position_scale"].iloc[0])

    assert legacy_scale == pytest.approx(1000.0)
    assert aware_scale < legacy_scale
    assert float(aware.data["target_position"].iloc[-1]) < float(
        legacy.data["target_position"].iloc[-1]
    )
    assert aware.strategy_metadata["execution_aware_scale"] == pytest.approx(aware_scale)
    assert aware.strategy_metadata["execution_aware_estimated_cost_bps"] > 0.0
    assert aware.strategy_metadata["live_order_metadata_template"][
        "expected_return_bps"
    ] == pytest.approx(20.0)
    assert aware.strategy_metadata["live_order_metadata_template"][
        "expected_adverse_bps"
    ] == pytest.approx(20.0)
    assert aware.strategy_metadata["live_order_metadata_template"]["expected_cost_bps"] > 0.0
    assert (
        aware.strategy_metadata["live_order_metadata_template"]["volatility_regime"] == "elevated"
    )
    assert (
        aware.strategy_metadata["live_order_metadata_template"]["microstructure_regime"]
        == "healthy"
    )


def test_build_live_order_metadata_uses_latest_strategy_row(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("project.engine.strategy_executor.get_strategy", lambda _: _DummyStrategy())
    monkeypatch.setattr(
        "project.engine.strategy_executor.load_symbol_constraints",
        lambda symbol, meta_dir: SymbolConstraints(
            tick_size=None, step_size=None, min_notional=None
        ),
    )

    result = calculate_strategy_returns(
        "BTCUSDT",
        _bars(),
        _features(),
        "dummy_strategy",
        {
            "position_scale": 1000.0,
            "execution_lag_bars": 0,
            "expected_return_bps": 30.0,
            "expected_adverse_bps": 5.0,
            "execution_model": {
                "cost_model": "static",
                "base_fee_bps": 2.0,
                "base_slippage_bps": 1.0,
            },
        },
        0.0,
        tmp_path,
    )

    metadata = build_live_order_metadata(result, realized_fee_bps=1.5)

    assert metadata["strategy"] == "dummy_strategy"
    assert metadata["signal_timestamp"].startswith("2024-01-01T00:10:00")
    assert metadata["volatility_regime"] == "elevated"
    assert metadata["microstructure_regime"] == "healthy"
    assert metadata["expected_entry_price"] == pytest.approx(100.0)
    assert metadata["expected_return_bps"] == pytest.approx(30.0)
    assert metadata["expected_adverse_bps"] == pytest.approx(5.0)
    assert metadata["expected_cost_bps"] == pytest.approx(3.0)
    assert metadata["expected_net_edge_bps"] == pytest.approx(22.0)
    assert metadata["realized_fee_bps"] == pytest.approx(1.5)
