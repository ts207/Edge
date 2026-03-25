from __future__ import annotations

import logging

from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

import project.research.phase2 as svc


def test_prepare_events_dataframe_unknown_event_raises():
    with pytest.raises(KeyError):
        svc.prepare_events_dataframe(
            data_root=Path("/tmp/unknown"),
            run_id="r1",
            event_type="UNKNOWN_EVENT",
            symbols=["BTCUSDT"],
            event_registry_specs={},
            horizons=["5m"],
            entry_lag_bars=1,
            fam_config={},
            logger=logging.getLogger("p2svc"),
        )


def test_prepare_events_dataframe_fallback_filters_symbols(monkeypatch, tmp_path):
    monkeypatch.setattr(svc, "load_registry_episode_anchors", lambda **_kwargs: pd.DataFrame())
    monkeypatch.setattr(
        svc,
        "_read_csv_or_parquet",
        lambda _path: pd.DataFrame(
            {
                "symbol": ["BTCUSDT", "ETHUSDT"],
                "timestamp": ["2024-01-01T00:00:00Z", "2024-01-01T00:05:00Z"],
            }
        ),
    )
    events = svc.prepare_events_dataframe(
        data_root=tmp_path,
        run_id="r2",
        event_type="VOL_SHOCK",
        symbols=["BTCUSDT"],
        event_registry_specs={
            "VOL_SHOCK": SimpleNamespace(reports_dir="vol", events_file="events.csv")
        },
        horizons=["5m"],
        entry_lag_bars=1,
        fam_config={},
        logger=logging.getLogger("p2svc"),
    )
    assert not events.empty
    assert set(events["symbol"].astype(str)) == {"BTCUSDT"}


def test_populate_fail_reasons_considers_retail_gates():
    df = pd.DataFrame(
        [
            {
                "gate_phase2_final": False,
                "gate_economic": True,
                "gate_economic_conservative": True,
                "gate_stability": True,
                "gate_state_information": True,
                "gate_cost_model_valid": True,
                "gate_cost_ratio": True,
                "gate_retail_net_expectancy": False,
                "gate_retail_cost_budget": True,
                "gate_retail_turnover": True,
                "gate_retail_viability": False,
            }
        ]
    )
    out = svc.populate_fail_reasons(df)
    assert out.loc[0, "fail_gate_primary"] == "gate_retail_net_expectancy"
    assert out.loc[0, "fail_reason_primary"] == "failed_gate_retail_net_expectancy"


def test_populate_fail_reasons_considers_oos_gates():
    df = pd.DataFrame(
        [
            {
                "gate_phase2_final": False,
                "gate_economic": True,
                "gate_economic_conservative": True,
                "gate_stability": True,
                "gate_oos_min_samples": False,
                "gate_oos_validation": False,
                "gate_oos_validation_test": False,
                "gate_oos_consistency_strict": False,
                "gate_state_information": True,
                "gate_cost_model_valid": True,
                "gate_cost_ratio": True,
                "gate_retail_net_expectancy": True,
                "gate_retail_cost_budget": True,
                "gate_retail_turnover": True,
                "gate_retail_viability": True,
            }
        ]
    )
    out = svc.populate_fail_reasons(df)
    assert out.loc[0, "fail_gate_primary"] == "gate_oos_min_samples"
    assert out.loc[0, "fail_reason_primary"] == "failed_gate_oos_min_samples"


def test_populate_fail_reasons_falls_back_to_fail_reasons_tokens():
    df = pd.DataFrame(
        [
            {
                "gate_phase2_final": False,
                "gate_economic": True,
                "gate_economic_conservative": True,
                "gate_stability": True,
                "gate_state_information": True,
                "gate_cost_model_valid": True,
                "gate_cost_ratio": True,
                "gate_retail_net_expectancy": True,
                "gate_retail_cost_budget": True,
                "gate_retail_turnover": True,
                "gate_retail_viability": True,
                "fail_reasons": "MIN_SAMPLE_SIZE_GATE",
            }
        ]
    )
    out = svc.populate_fail_reasons(df)
    assert out.loc[0, "fail_gate_primary"] == "MIN_SAMPLE_SIZE_GATE"
    assert out.loc[0, "fail_reason_primary"] == "failed_MIN_SAMPLE_SIZE_GATE"
