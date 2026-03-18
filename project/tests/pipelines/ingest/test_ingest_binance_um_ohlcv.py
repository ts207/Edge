from __future__ import annotations

from pathlib import Path

from project import PROJECT_ROOT
from project.pipelines.stages.ingest import build_ingest_stages


def test_generic_um_ohlcv_ingest_owns_timeframe_specific_manifest_naming() -> None:
    script_path = PROJECT_ROOT / "pipelines" / "ingest" / "ingest_binance_um_ohlcv.py"
    content = script_path.read_text(encoding="utf-8")

    assert 'def _expected_bars(start: datetime, end_exclusive: datetime, timeframe: str)' in content
    assert 'f"ingest_binance_um_ohlcv_{args.timeframe}"' in content


def test_build_ingest_stages_uses_generic_um_ohlcv_entrypoint_for_all_timeframes() -> None:
    class _Args:
        timeframes = "1m,5m,15m"
        skip_ingest_ohlcv = 0
        skip_ingest_funding = 1
        skip_ingest_spot_ohlcv = 1
        run_ingest_liquidation_snapshot = 0
        run_ingest_open_interest_hist = 0
        open_interest_period = "5m"

    stages = build_ingest_stages(
        args=_Args(),
        run_id="r1",
        symbols="BTCUSDT",
        start="2026-01-01",
        end="2026-01-02",
        force_flag="0",
        run_spot_pipeline=False,
        project_root=PROJECT_ROOT,
    )

    assert [stage_name for stage_name, _script, _args in stages] == [
        "ingest_binance_um_ohlcv_1m",
        "ingest_binance_um_ohlcv_5m",
        "ingest_binance_um_ohlcv_15m",
    ]
    for stage_name, script_path, stage_args in stages:
        assert script_path == PROJECT_ROOT / "pipelines" / "ingest" / "ingest_binance_um_ohlcv.py"
        assert "--timeframe" in stage_args
        assert stage_args[stage_args.index("--timeframe") + 1] == stage_name.rsplit("_", 1)[1]
