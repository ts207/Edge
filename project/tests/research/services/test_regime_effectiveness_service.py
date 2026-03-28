from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from project.research.services.regime_effectiveness_service import (
    compute_regime_effectiveness,
    write_regime_effectiveness_reports,
)


def test_regime_effectiveness_computes_metrics_and_excludes_non_canonical_layers():
    frame = pd.DataFrame(
        [
            {
                "event_type": "LIQUIDITY_STRESS_DIRECT",
                "symbol": "BTCUSDT",
                "timestamp": "2024-01-01T00:00:00Z",
                "duration_bars": 3,
                "horizon": "12b",
                "after_cost_expectancy": 0.0010,
                "resolved_cost_bps": 1.0,
            },
            {
                "event_type": "LIQUIDITY_STRESS_PROXY",
                "symbol": "BTCUSDT",
                "timestamp": "2024-01-01T00:05:00Z",
                "duration_bars": 2,
                "horizon": "12b",
                "after_cost_expectancy": 0.0005,
                "resolved_cost_bps": 1.5,
            },
            {
                "event_type": "SEQ_LIQ_VACUUM_THEN_DEPTH_RECOVERY",
                "symbol": "BTCUSDT",
                "timestamp": "2024-01-01T00:10:00Z",
                "duration_bars": 1,
                "horizon": "12b",
                "after_cost_expectancy": 0.0050,
            },
            {
                "event_type": "SESSION_OPEN_EVENT",
                "symbol": "BTCUSDT",
                "timestamp": "2024-01-01T00:15:00Z",
                "duration_bars": 1,
                "horizon": "12b",
                "after_cost_expectancy": 0.0001,
            },
        ]
    )

    artifacts = compute_regime_effectiveness(frame)

    assert set(artifacts.main_scorecard["canonical_regime"]) == {"LIQUIDITY_STRESS"}
    assert artifacts.summary["episodes_total"] == 2
    assert artifacts.summary["recommended_bucket_counts"]["trade_generating"] == 2
    stability = artifacts.direct_proxy_stability.set_index("canonical_regime").loc["LIQUIDITY_STRESS"]
    assert stability["direct_count"] == 1
    assert stability["proxy_count"] == 1
    main = artifacts.main_scorecard.sort_values(["evidence_mode"]).reset_index(drop=True)
    assert json.loads(main.loc[0, "forward_return_profile"]) != {}
    assert "resolved_cost_bps" in json.loads(main.loc[0, "execution_impact_profile"])


def test_regime_effectiveness_writer_emits_run_scoped_artifacts(tmp_path):
    frame = pd.DataFrame(
        [
            {
                "event_type": "CROSS_ASSET_DESYNC_EVENT",
                "symbol": "BTCUSDT",
                "timestamp": "2024-01-01T00:00:00Z",
                "duration_bars": 4,
                "horizon": "24b",
                "after_cost_expectancy": 0.0015,
            }
        ]
    )

    artifacts = write_regime_effectiveness_reports(
        run_id="demo_run",
        data_root=tmp_path,
        episodes=frame,
    )

    expected = {
        "regime_effectiveness.parquet",
        "regime_effectiveness_summary.json",
        "regime_overlap_matrix.parquet",
        "regime_subtype_breakdown.parquet",
        "regime_direct_proxy_stability.parquet",
    }
    written = {path.name for path in Path(artifacts.output_dir).iterdir()}
    assert expected.issubset(written)
