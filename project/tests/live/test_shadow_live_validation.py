from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from project.live import shadow_live_validation as svc
from project.live.contracts import PromotedThesis, ThesisEvidence, ThesisGovernance, ThesisLineage, ThesisRequirements, ThesisSource
from project.research.thesis_evidence_runner import FoundingThesisSpec


def _write_raw_partition(root: Path, symbol: str, dataset: str, frame: pd.DataFrame, *, year: int, month: int, stem: str) -> None:
    out_dir = root / "lake" / "raw" / "perp" / symbol / dataset / f"year={year}" / f"month={month:02d}"
    out_dir.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(out_dir / f"{stem}.parquet", index=False)


def _synthetic_bars(symbol: str) -> pd.DataFrame:
    timestamps = list(pd.date_range("2021-12-20", periods=900, freq="5min", tz="UTC"))
    timestamps += list(pd.date_range("2022-12-20", periods=900, freq="5min", tz="UTC"))
    close = []
    price = 100.0 if symbol == "BTCUSDT" else 50.0
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
            "symbol": symbol,
            "source": "synthetic",
        }
    )


def _write_store(path: Path) -> None:
    theses = [
        PromotedThesis(
            thesis_id="THESIS_VOL_SHOCK",
            promotion_class="paper_promoted",
            deployment_state="paper_only",
            evidence_gaps=[],
            status="active",
            symbol_scope={"mode": "symbol_set", "symbols": ["BTCUSDT"], "candidate_symbol": "BTCUSDT"},
            timeframe="5m",
            event_family="VOL_SHOCK",
            event_side="both",
            required_context={},
            supportive_context={"has_realized_oos_path": True},
            expected_response={},
            invalidation={},
            risk_notes=[],
            evidence=ThesisEvidence(sample_size=100, validation_samples=50, test_samples=50, estimate_bps=100.0, net_expectancy_bps=94.0, q_value=0.01, stability_score=0.9, rank_score=37.0),
            lineage=ThesisLineage(run_id="test", candidate_id="THESIS_VOL_SHOCK"),
            governance=ThesisGovernance(tier="A", operational_role="trigger", deployment_disposition="primary_trigger_candidate", evidence_mode="direct", overlap_group_id="VOL_SHOCK::NO_EPISODE::ANY::trigger", trade_trigger_eligible=True),
            requirements=ThesisRequirements(trigger_events=["VOL_SHOCK"], confirmation_events=[]),
            source=ThesisSource(event_contract_ids=["VOL_SHOCK"]),
        ),
        PromotedThesis(
            thesis_id="THESIS_LIQUIDITY_VACUUM",
            promotion_class="paper_promoted",
            deployment_state="paper_only",
            evidence_gaps=[],
            status="active",
            symbol_scope={"mode": "symbol_set", "symbols": ["BTCUSDT"], "candidate_symbol": "BTCUSDT"},
            timeframe="5m",
            event_family="LIQUIDITY_VACUUM",
            event_side="both",
            required_context={},
            supportive_context={"has_realized_oos_path": True},
            expected_response={},
            invalidation={},
            risk_notes=[],
            evidence=ThesisEvidence(sample_size=80, validation_samples=40, test_samples=40, estimate_bps=90.0, net_expectancy_bps=84.0, q_value=0.02, stability_score=0.8, rank_score=35.0),
            lineage=ThesisLineage(run_id="test", candidate_id="THESIS_LIQUIDITY_VACUUM"),
            governance=ThesisGovernance(tier="A", operational_role="trigger", deployment_disposition="primary_trigger_candidate", evidence_mode="direct", overlap_group_id="LIQUIDITY_VACUUM::NO_EPISODE::ANY::trigger", trade_trigger_eligible=True),
            requirements=ThesisRequirements(trigger_events=["LIQUIDITY_VACUUM"], confirmation_events=[]),
            source=ThesisSource(event_contract_ids=["LIQUIDITY_VACUUM"]),
        ),
        PromotedThesis(
            thesis_id="THESIS_VOL_SHOCK_LIQUIDITY_CONFIRM",
            promotion_class="paper_promoted",
            deployment_state="paper_only",
            evidence_gaps=[],
            status="active",
            symbol_scope={"mode": "symbol_set", "symbols": ["BTCUSDT"], "candidate_symbol": "BTCUSDT"},
            timeframe="5m",
            event_family="VOL_SHOCK",
            event_side="both",
            required_context={},
            supportive_context={"has_realized_oos_path": True},
            expected_response={},
            invalidation={},
            risk_notes=[],
            evidence=ThesisEvidence(sample_size=40, validation_samples=20, test_samples=20, estimate_bps=95.0, net_expectancy_bps=89.0, q_value=0.03, stability_score=0.7, rank_score=34.0),
            lineage=ThesisLineage(run_id="test", candidate_id="THESIS_VOL_SHOCK_LIQUIDITY_CONFIRM"),
            governance=ThesisGovernance(tier="A", operational_role="confirm", deployment_disposition="seed_review_required", evidence_mode="direct", overlap_group_id="VOL_SHOCK::NO_EPISODE::ANY::confirm", trade_trigger_eligible=True),
            requirements=ThesisRequirements(trigger_events=["VOL_SHOCK"], confirmation_events=["LIQUIDITY_VACUUM"]),
            source=ThesisSource(event_contract_ids=["VOL_SHOCK", "LIQUIDITY_VACUUM"]),
        ),
    ]
    payload = {
        "schema_version": "promoted_thesis_store_v1",
        "run_id": "shadow_test",
        "generated_at_utc": "2026-01-01T00:00:00Z",
        "thesis_count": len(theses),
        "active_thesis_count": len(theses),
        "pending_thesis_count": 0,
        "theses": [thesis.model_dump() for thesis in theses],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def test_run_shadow_live_thesis_validation_tracks_confirmation_only_when_window_has_both(tmp_path: Path, monkeypatch) -> None:
    data_root = tmp_path / "data"
    docs_dir = tmp_path / "docs"
    monkeypatch.setenv("BACKTEST_DATA_ROOT", str(data_root))

    bars = _synthetic_bars("BTCUSDT")
    for year in (2021, 2022):
        subset = bars[bars["timestamp"].dt.year == year]
        _write_raw_partition(data_root, "BTCUSDT", "ohlcv_5m", subset, year=year, month=12, stem=f"ohlcv_BTCUSDT_5m_{year}-12")

    specs = (
        FoundingThesisSpec(
            candidate_id="THESIS_VOL_SHOCK",
            event_type="VOL_SHOCK",
            detector_kind="vol_shock",
            symbols=("BTCUSDT",),
            horizons=(2, 4),
            payoff_mode="absolute_return",
            fees_bps=1.0,
            params={"rv_window": 3, "baseline_window": 12, "shock_quantile": 0.8},
        ),
        FoundingThesisSpec(
            candidate_id="THESIS_LIQUIDITY_VACUUM",
            event_type="LIQUIDITY_VACUUM",
            detector_kind="liquidity_vacuum",
            symbols=("BTCUSDT",),
            horizons=(2, 4),
            payoff_mode="absolute_return",
            fees_bps=1.0,
            params={
                "shock_quantile": 0.8,
                "shock_window": 12,
                "volume_window": 6,
                "vol_ratio_floor": 0.95,
                "range_multiplier": 1.0,
                "lookahead_bars": 3,
                "min_vacuum_bars": 1,
            },
        ),
        FoundingThesisSpec(
            candidate_id="THESIS_LIQUIDATION_CASCADE",
            event_type="LIQUIDATION_CASCADE",
            detector_kind="liquidation_cascade",
            symbols=("BTCUSDT",),
            horizons=(2, 4),
            payoff_mode="absolute_return",
            fees_bps=1.0,
            params={"shock_quantile": 0.99, "shock_window": 24, "oi_window": 2, "oi_drop_quantile": 0.01, "funding_window": 24, "funding_z": 9.0},
        ),
    )
    monkeypatch.setattr(svc, "_policy_specs", lambda _path=None: specs)

    def _vol_mask(frame: pd.DataFrame, _params: dict[str, object]) -> pd.Series:
        mask = pd.Series(False, index=frame.index, dtype=bool)
        mask.iloc[::12] = True
        return mask

    def _liq_mask(frame: pd.DataFrame, _params: dict[str, object]) -> pd.Series:
        mask = pd.Series(False, index=frame.index, dtype=bool)
        mask.iloc[1::12] = True
        return mask

    monkeypatch.setattr(svc, "_vol_shock_events", _vol_mask)
    monkeypatch.setattr(svc, "_liquidity_vacuum_events", _liq_mask)

    thesis_store = tmp_path / "promoted_theses.json"
    _write_store(thesis_store)

    out = svc.run_shadow_live_thesis_validation(
        thesis_store_path=thesis_store,
        data_root=data_root,
        docs_dir=docs_dir,
        out_dir=tmp_path / "shadow",
        window_days=400,
        context_window_bars=3,
        symbols=["BTCUSDT"],
        run_id="shadow_test",
    )

    summary = json.loads(out["summary_json"].read_text(encoding="utf-8"))
    stats = summary["confirmation_thesis_stats"]
    assert summary["contexts_evaluated"] > 0
    assert stats["retrieved_cycles"] > 0
    assert stats["confirmation_match_cycles"] > 0
    assert summary["confirmation_thesis_stats_by_id"]["THESIS_VOL_SHOCK_LIQUIDITY_CONFIRM"]["confirmation_match_cycles"] > 0
    assert summary["quality_checks"]["overlap_metadata_visible_consistently"] is True
    assert summary["invalid_artifact_refs"] == []
    assert summary["artifact_refs"]["trace"]["path"].startswith("shadow/")
    assert "/home/irene/" not in out["summary_md"].read_text(encoding="utf-8")
