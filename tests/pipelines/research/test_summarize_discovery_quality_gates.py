from __future__ import annotations

import pandas as pd

import project.pipelines.research.summarize_discovery_quality as summarize_discovery_quality

def test_gate_pass_series_prefers_gate_phase2_final_when_present():
    frame = pd.DataFrame(
        {
            "gate_all": [1, 1, 0],
            "gate_phase2_final": [0, 1, 0],
        }
    )

    observed = summarize_discovery_quality._gate_pass_series(frame)

    assert observed.tolist() == [False, True, False]

def test_build_summary_uses_phase2_final_for_family_and_global_pass_counts(tmp_path, monkeypatch):
    run_id = "test_run"
    phase2_root = tmp_path / "reports" / "phase2" / run_id
    event_dir = phase2_root / "LIQUIDITY_VACUUM"
    event_dir.mkdir(parents=True, exist_ok=True)

    frame = pd.DataFrame(
        [
            {"candidate_id": "c1", "gate_all": 1, "gate_phase2_final": 1, "fail_reasons": ""},
            {"candidate_id": "c2", "gate_all": 1, "gate_phase2_final": 0, "fail_reasons": "bridge_cost"},
            {"candidate_id": "c3", "gate_all": 1, "gate_phase2_final": 0, "fail_reasons": "stability"},
        ]
    )
    frame.to_csv(event_dir / "phase2_candidates.csv", index=False)

    monkeypatch.setattr(summarize_discovery_quality, "get_data_root", lambda: tmp_path)
    payload = summarize_discovery_quality.build_summary(
        run_id=run_id,
        phase2_root=phase2_root,
        top_fail_reasons=5,
    )

    family = payload["by_event_family"]["LIQUIDITY_VACUUM"]
    assert family["phase2_candidates"] == 3
    assert family["gate_pass_count"] == 1
    assert family["phase2_gate_all_pass"] == 1
    assert payload["gate_pass_count"] == 1


def test_build_summary_reads_nested_timeframe_phase2_outputs(tmp_path, monkeypatch):
    run_id = "test_run_nested"
    phase2_root = tmp_path / "reports" / "phase2" / run_id
    event_dir = phase2_root / "LIQUIDITY_VACUUM" / "15m"
    event_dir.mkdir(parents=True, exist_ok=True)

    frame = pd.DataFrame(
        [
            {"candidate_id": "c1", "gate_phase2_final": 1, "fail_reasons": ""},
            {"candidate_id": "c2", "gate_phase2_final": 0, "fail_reasons": "bridge_cost"},
        ]
    )
    frame.to_csv(event_dir / "phase2_candidates.csv", index=False)

    monkeypatch.setattr(summarize_discovery_quality, "get_data_root", lambda: tmp_path)
    payload = summarize_discovery_quality.build_summary(
        run_id=run_id,
        phase2_root=phase2_root,
        top_fail_reasons=5,
    )

    family = payload["by_event_family"]["LIQUIDITY_VACUUM"]
    assert family["phase2_candidates"] == 2
    assert family["gate_pass_count"] == 1


def test_build_summary_includes_search_engine_event_types(tmp_path, monkeypatch):
    run_id = "test_run_search_engine"
    phase2_root = tmp_path / "reports" / "phase2" / run_id
    search_dir = phase2_root / "search_engine"
    search_dir.mkdir(parents=True, exist_ok=True)

    frame = pd.DataFrame(
        [
            {"candidate_id": "s1", "event_type": "STATE_AFTERSHOCK_STATE", "gate_pass": 1, "fail_reasons": ""},
            {"candidate_id": "s2", "event_type": "STATE_AFTERSHOCK_STATE", "gate_pass": 0, "fail_reasons": "bridge_cost"},
            {"candidate_id": "s3", "event_type": "STATE_CROWDING_STATE", "gate_pass": 1, "fail_reasons": ""},
        ]
    )
    frame.to_parquet(search_dir / "phase2_candidates.parquet", index=False)

    monkeypatch.setattr(summarize_discovery_quality, "get_data_root", lambda: tmp_path)
    payload = summarize_discovery_quality.build_summary(
        run_id=run_id,
        phase2_root=phase2_root,
        top_fail_reasons=5,
    )

    assert payload["by_event_family"]["STATE_AFTERSHOCK_STATE"]["phase2_candidates"] == 2
    assert payload["by_event_family"]["STATE_AFTERSHOCK_STATE"]["gate_pass_count"] == 1
    assert payload["by_event_family"]["STATE_CROWDING_STATE"]["phase2_candidates"] == 1
    assert payload["total_candidates"] == 3


def test_build_summary_counts_embedded_search_engine_bridge_results(tmp_path, monkeypatch):
    run_id = "test_run_search_engine_bridge"
    phase2_root = tmp_path / "reports" / "phase2" / run_id
    search_dir = phase2_root / "search_engine"
    search_dir.mkdir(parents=True, exist_ok=True)

    frame = pd.DataFrame(
        [
            {
                "candidate_id": "s1",
                "event_type": "STATE_AFTERSHOCK_STATE",
                "gate_pass": 0,
                "gate_bridge_tradable": False,
                "bridge_eval_status": "rejected",
            },
            {
                "candidate_id": "s2",
                "event_type": "STATE_AFTERSHOCK_STATE",
                "gate_pass": 1,
                "gate_bridge_tradable": True,
                "bridge_eval_status": "accepted",
            },
        ]
    )
    frame.to_parquet(search_dir / "phase2_candidates.parquet", index=False)

    monkeypatch.setattr(summarize_discovery_quality, "get_data_root", lambda: tmp_path)
    payload = summarize_discovery_quality.build_summary(
        run_id=run_id,
        phase2_root=phase2_root,
        top_fail_reasons=5,
    )

    family = payload["by_event_family"]["STATE_AFTERSHOCK_STATE"]
    assert family["phase2_candidates"] == 2
    assert family["bridge_evaluable"] == 2
    assert family["bridge_pass_val"] == 1
    assert family["gate_pass_count"] == 1
