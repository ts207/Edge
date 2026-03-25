from __future__ import annotations

from types import SimpleNamespace

from pathlib import Path

import pandas as pd
import project.research.helpers.shrinkage as shrinkage
import project.specs.manifest as manifest_spec

PROJECT_ROOT = Path(__file__).resolve().parents[3] / "project"

import project.research.export_edge_candidates as export_edge_candidates


def test_export_chain_includes_declared_subtype_families():
    expected_scripts = {
        "FUNDING_EXTREME_ONSET": "analyze_events.py",
        "FUNDING_PERSISTENCE_TRIGGER": "analyze_events.py",
        "FUNDING_NORMALIZATION_TRIGGER": "analyze_events.py",
        "OI_SPIKE_POSITIVE": "analyze_events.py",
        "OI_SPIKE_NEGATIVE": "analyze_events.py",
        "OI_FLUSH": "analyze_events.py",
        "LIQUIDITY_STRESS_DIRECT": "analyze_events.py",
        "LIQUIDITY_STRESS_PROXY": "analyze_events.py",
        "DEPTH_COLLAPSE": "analyze_events.py",
        "DEPTH_STRESS_PROXY": "analyze_events.py",
        "SPREAD_BLOWOUT": "analyze_events.py",
        "ORDERFLOW_IMBALANCE_SHOCK": "analyze_events.py",
        "PRICE_VOL_IMBALANCE_PROXY": "analyze_events.py",
        "SWEEP_STOPRUN": "analyze_events.py",
        "WICK_REVERSAL_PROXY": "analyze_events.py",
        "ABSORPTION_EVENT": "analyze_events.py",
        "ABSORPTION_PROXY": "analyze_events.py",
        "LIQUIDITY_GAP_PRINT": "analyze_events.py",
        "VOL_SPIKE": "analyze_events.py",
        "VOL_RELAXATION_START": "analyze_events.py",
        "VOL_CLUSTER_SHIFT": "analyze_events.py",
        "RANGE_COMPRESSION_END": "analyze_events.py",
        "BREAKOUT_TRIGGER": "analyze_events.py",
        "FUNDING_FLIP": "analyze_events.py",
        "DELEVERAGING_WAVE": "analyze_events.py",
        "TREND_EXHAUSTION_TRIGGER": "analyze_events.py",
        "MOMENTUM_DIVERGENCE_TRIGGER": "analyze_events.py",
        "CLIMAX_VOLUME_BAR": "analyze_events.py",
        "FAILED_CONTINUATION": "analyze_events.py",
        "POST_DELEVERAGING_REBOUND": "analyze_events.py",
        "FLOW_EXHAUSTION_PROXY": "analyze_events.py",
        "RANGE_BREAKOUT": "analyze_events.py",
        "FALSE_BREAKOUT": "analyze_events.py",
        "TREND_ACCELERATION": "analyze_events.py",
        "TREND_DECELERATION": "analyze_events.py",
        "PULLBACK_PIVOT": "analyze_events.py",
        "SUPPORT_RESISTANCE_BREAK": "analyze_events.py",
        "ZSCORE_STRETCH": "analyze_events.py",
        "BAND_BREAK": "analyze_events.py",
        "OVERSHOOT_AFTER_SHOCK": "analyze_events.py",
        "GAP_OVERSHOOT": "analyze_events.py",
        "VOL_REGIME_SHIFT_EVENT": "analyze_events.py",
        "TREND_TO_CHOP_SHIFT": "analyze_events.py",
        "CHOP_TO_TREND_SHIFT": "analyze_events.py",
        "CORRELATION_BREAKDOWN_EVENT": "analyze_events.py",
        "BETA_SPIKE_EVENT": "analyze_events.py",
        "INDEX_COMPONENT_DIVERGENCE": "analyze_events.py",
        "SPOT_PERP_BASIS_SHOCK": "analyze_events.py",
        "LEAD_LAG_BREAK": "analyze_events.py",
        "SESSION_OPEN_EVENT": "analyze_events.py",
        "SESSION_CLOSE_EVENT": "analyze_events.py",
        "FUNDING_TIMESTAMP_EVENT": "analyze_events.py",
        "SCHEDULED_NEWS_WINDOW_EVENT": "analyze_events.py",
        "SPREAD_REGIME_WIDENING_EVENT": "analyze_events.py",
        "SLIPPAGE_SPIKE_EVENT": "analyze_events.py",
        "FEE_REGIME_CHANGE_EVENT": "analyze_events.py",
    }
    chain_map = {event: script for event, script, _ in export_edge_candidates.PHASE2_EVENT_CHAIN}
    for event_type, expected_script in expected_scripts.items():
        assert chain_map.get(event_type) == expected_script


def test_export_chain_has_no_canonical_analyzer_routes():
    assert all(
        script != "analyze_canonical_events.py"
        for _, script, _ in export_edge_candidates.PHASE2_EVENT_CHAIN
    )


def test_export_execute_chain_uses_phase2_candidate_discovery(monkeypatch, tmp_path):
    fake_root = tmp_path / "project"
    research_dir = fake_root / "pipelines" / "research"
    research_dir.mkdir(parents=True, exist_ok=True)
    for name in (
        "analyze_liquidity_vacuum.py",
        "build_event_registry.py",
        "phase2_candidate_discovery.py",
        "bridge_evaluate_phase2.py",
    ):
        (research_dir / name).write_text("#!/usr/bin/env python3\n", encoding="utf-8")

    captured: list[list[str]] = []

    def fake_run(cmd, *args, **kwargs):
        captured.append([str(x) for x in cmd])
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(export_edge_candidates, "PROJECT_ROOT", fake_root)
    monkeypatch.setattr(
        export_edge_candidates,
        "PHASE2_EVENT_CHAIN",
        [("LIQUIDITY_VACUUM", "analyze_liquidity_vacuum.py", [])],
    )
    monkeypatch.setattr(export_edge_candidates.subprocess, "run", fake_run)

    export_edge_candidates._run_research_chain(
        run_id="r_test",
        symbols="BTCUSDT",
    )

    phase2_cmds = [
        cmd for cmd in captured if any("phase2_candidate_discovery.py" in token for token in cmd)
    ]
    legacy_cmds = [
        cmd for cmd in captured if any("phase2_conditional_hypotheses.py" in token for token in cmd)
    ]
    assert phase2_cmds
    assert not legacy_cmds


def test_export_edge_candidates_stamps_confirmatory_metadata(monkeypatch, tmp_path):
    monkeypatch.setattr(export_edge_candidates, "get_data_root", lambda: tmp_path)
    monkeypatch.setattr(
        export_edge_candidates,
        "_collect_phase2_candidates",
        lambda run_id, run_symbols: [
            {
                "candidate_id": "cand_1",
                "event": "VOL_SHOCK",
                "status": "PROMOTED_RESEARCH",
                "selection_score_executed": 1.0,
                "profit_density_score": 1.0,
                "edge_score": 1.0,
                "stability_proxy": 1.0,
                "p_value": 0.01,
                "q_value": 0.02,
                "train_n_obs": 10,
                "validation_n_obs": 3,
                "test_n_obs": 2,
                "validation_samples": 3,
                "test_samples": 2,
                "sample_size": 5,
            }
        ],
    )
    monkeypatch.setattr(
        manifest_spec, "load_run_manifest", lambda run_id: {"run_mode": "production"}
    )
    monkeypatch.setattr(export_edge_candidates, "ontology_spec_hash", lambda root: "hash123")
    monkeypatch.setattr(shrinkage, "_apply_hierarchical_shrinkage", lambda df, **kwargs: df)

    captured = {}

    def fake_write_parquet(df, path):
        captured["df"] = df.copy()
        captured["path"] = path

    monkeypatch.setattr(export_edge_candidates, "write_parquet", fake_write_parquet)
    monkeypatch.setattr(
        export_edge_candidates.Path,
        "write_text",
        lambda self, content, encoding=None: captured.setdefault("json_path", self),
    )
    monkeypatch.setattr(
        export_edge_candidates.sys,
        "argv",
        ["export_edge_candidates.py", "--run_id", "r1", "--symbols", "BTCUSDT"],
    )

    assert export_edge_candidates.main() == 0
    assert (
        captured["path"]
        == tmp_path / "reports" / "edge_candidates" / "r1" / "edge_candidates_normalized.parquet"
    )
    out = captured["df"]
    assert list(out["confirmatory_locked"]) == [True]
    assert list(out["frozen_spec_hash"]) == ["hash123"]
    assert list(out["run_mode"]) == ["production"]
    assert list(out["q_value"]) == [0.02]
    assert list(out["validation_n_obs"]) == [3]
    assert list(out["test_n_obs"]) == [2]
    assert list(out["validation_samples"]) == [3]
    assert list(out["test_samples"]) == [2]
    assert list(out["sample_size"]) == [5]


def test_export_edge_candidates_stamps_adjacent_survivorship_metadata(monkeypatch, tmp_path):
    monkeypatch.setattr(export_edge_candidates, "get_data_root", lambda: tmp_path)
    monkeypatch.setattr(
        export_edge_candidates,
        "_collect_phase2_candidates",
        lambda run_id, run_symbols: [
            {
                "candidate_id": "cand_1",
                "candidate_symbol": "BTCUSDT",
                "event_type": "STATE_CHOP_STATE",
                "event": "STATE_CHOP_STATE",
                "direction": "long",
                "horizon": "60m",
                "status": "PROMOTED_RESEARCH",
                "selection_score_executed": 1.0,
                "profit_density_score": 1.0,
                "edge_score": 1.0,
                "stability_proxy": 1.0,
                "p_value": 0.01,
                "q_value": 0.02,
            }
        ],
    )
    monkeypatch.setattr(manifest_spec, "load_run_manifest", lambda run_id: {"run_mode": "research"})
    monkeypatch.setattr(export_edge_candidates, "ontology_spec_hash", lambda root: "hash123")
    monkeypatch.setattr(shrinkage, "_apply_hierarchical_shrinkage", lambda df, **kwargs: df)

    adjacent_dir = tmp_path / "reports" / "adjacent_survivorship" / "target_run" / "vs_r1"
    adjacent_dir.mkdir(parents=True, exist_ok=True)
    (adjacent_dir / "adjacent_survivorship.json").write_text(
        """
        {
          "candidate_rows": [
            {
              "symbol": "BTCUSDT",
              "event_type": "STATE_CHOP_STATE",
              "direction": "long",
              "horizon": "60m",
              "survived_adjacent_window": false,
              "failure_reasons": ["after_cost_negative", "bridge_fail"],
              "target_after_cost_expectancy_per_trade": -0.0015
            }
          ]
        }
        """,
        encoding="utf-8",
    )

    captured = {}

    def fake_write_parquet(df, path):
        captured["df"] = df.copy()
        captured["path"] = path

    monkeypatch.setattr(export_edge_candidates, "write_parquet", fake_write_parquet)
    monkeypatch.setattr(
        export_edge_candidates.Path,
        "write_text",
        lambda self, content, encoding=None: captured.setdefault("json_path", self),
    )
    monkeypatch.setattr(
        export_edge_candidates.sys,
        "argv",
        ["export_edge_candidates.py", "--run_id", "r1", "--symbols", "BTCUSDT"],
    )

    assert export_edge_candidates.main() == 0
    out = captured["df"]
    assert list(out["adjacent_window_survived"]) == [False]
    assert list(out["adjacent_window_target_run_id"]) == ["target_run"]
    assert list(out["adjacent_window_failure_reasons"]) == ["after_cost_negative|bridge_fail"]
    assert list(out["adjacent_window_target_after_cost_expectancy_per_trade"]) == [-0.0015]


def test_collect_phase2_candidates_includes_search_engine_rows(monkeypatch, tmp_path):
    monkeypatch.setattr(export_edge_candidates, "get_data_root", lambda: tmp_path)
    search_dir = tmp_path / "reports" / "phase2" / "r_search" / "search_engine"
    search_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {
                "candidate_id": "search_1",
                "event_type": "STATE_AFTERSHOCK_STATE",
                "symbol": "BTCUSDT",
                "q_value": 0.01,
                "p_value": 0.005,
                "sample_size": 42,
                "validation_n_obs": 12,
                "test_n_obs": 8,
                "train_n_obs": 22,
                "gate_bridge_tradable": True,
            }
        ]
    ).to_parquet(search_dir / "phase2_candidates.parquet", index=False)

    rows = export_edge_candidates._collect_phase2_candidates("r_search", ["BTCUSDT"])

    assert len(rows) == 1
    assert rows[0]["candidate_id"] == "search_1"
    assert rows[0]["event"] == "STATE_AFTERSHOCK_STATE"
    assert rows[0]["q_value"] == 0.01
    assert rows[0]["sample_size"] == 42


def test_phase2_row_to_candidate_skips_warning_spam_for_missing_optional_fields(caplog):
    row = {
        "candidate_id": "cand_1",
        "event_type": "VOL_SHOCK",
        "q_value": 0.01,
    }

    with caplog.at_level("WARNING"):
        candidate = export_edge_candidates._phase2_row_to_candidate(
            run_id="r1",
            event="VOL_SHOCK",
            row=row,
            idx=0,
            source_path=Path("/tmp/source.parquet"),
            default_status="CANDIDATE",
            run_symbols=["BTCUSDT"],
        )

    assert candidate["candidate_id"] == "cand_1"
    assert candidate["event"] == "VOL_SHOCK"
    assert "safe_float: failed to convert None" not in caplog.text
    assert "safe_int: failed to convert None" not in caplog.text


def test_phase2_row_to_candidate_uses_expectancy_fallback_fields():
    row = {
        "candidate_id": "cand_2",
        "event_type": "VOL_SHOCK",
        "expectancy": -0.00005,
        "expectancy_bps": -0.5,
    }

    candidate = export_edge_candidates._phase2_row_to_candidate(
        run_id="r1",
        event="VOL_SHOCK",
        row=row,
        idx=0,
        source_path=Path("/tmp/source.parquet"),
        default_status="CANDIDATE",
        run_symbols=["BTCUSDT"],
    )

    assert candidate["expectancy_per_trade"] == -0.00005
    assert candidate["after_cost_expectancy_per_trade"] == -0.00005


def test_phase2_row_to_candidate_normalizes_numeric_direction():
    row = {
        "candidate_id": "cand_3",
        "event_type": "VOL_SPIKE",
        "direction": 1.0,
    }

    candidate = export_edge_candidates._phase2_row_to_candidate(
        run_id="r1",
        event="VOL_SPIKE",
        row=row,
        idx=0,
        source_path=Path("/tmp/source.parquet"),
        default_status="CANDIDATE",
        run_symbols=["BTCUSDT"],
    )

    assert candidate["direction"] == "long"


def test_normalize_edge_candidates_df_coerces_mixed_direction_types():
    df = pd.DataFrame(
        [
            {"candidate_id": "search_1", "direction": "short"},
            {"candidate_id": "event_1", "direction": 1.0},
            {"candidate_id": "event_2", "direction": -1.0},
            {"candidate_id": "event_3", "direction": 0.0},
        ]
    )

    normalized = export_edge_candidates._normalize_edge_candidates_df(
        df,
        run_mode="research",
        is_confirmatory=False,
        current_spec_hash="hash123",
    )

    assert list(normalized["direction"]) == ["short", "long", "short", "flat"]
