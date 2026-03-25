"""Phase 2.3 & 2.4 — Tests for research_mode routing and supersession tracking.

Phase 2.3 — research_mode flag on CampaignConfig
  - scan mode:    Step 4 selects events from a single family (best-quality first)
  - explore mode: Step 4 selects across all families (cross-family batch, up to 5)
  - exploit mode: Step 4 never reached; returns None when promising_regions empty

Phase 2.4 — Supersession tracking for resolved failures
  - mark_failures_superseded() populates superseded_by_run_id on matching rows
  - _step_repair() skips entries whose stage is already superseded
  - _read_memory() exposes superseded_stages drawn from the failures table
  - update_campaign_memory() calls mark_failures_superseded on recovered stages
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from project.research.campaign_controller import (
    CampaignConfig,
    CampaignController,
    _DEFAULT_QUALITY,
)
from project.research.update_campaign_memory import mark_failures_superseded


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


def _make_controller(tmp_path: Path, research_mode: str = "scan") -> CampaignController:
    config = CampaignConfig(
        program_id="test_prog",
        max_runs=5,
        research_mode=research_mode,
    )
    ctrl = CampaignController.__new__(CampaignController)
    ctrl.config = config
    ctrl.data_root = tmp_path
    ctrl.registry_root = tmp_path / "reg"
    ctrl.campaign_dir = tmp_path / "artifacts" / "experiments" / config.program_id
    ctrl.campaign_dir.mkdir(parents=True)
    ctrl.ledger_path = ctrl.campaign_dir / "tested_ledger.parquet"
    ctrl.summary_path = ctrl.campaign_dir / "campaign_summary.json"
    ctrl._search_space_path = Path("spec/search_space.yaml")
    ctrl._quality_weights = {}

    ctrl.registries = MagicMock()
    ctrl.registries.events = {
        "events": {
            # Family A — two events
            "EVT_A1": {"enabled": True, "family": "FAMILY_A"},
            "EVT_A2": {"enabled": True, "family": "FAMILY_A"},
            # Family B — two events
            "EVT_B1": {"enabled": True, "family": "FAMILY_B"},
            "EVT_B2": {"enabled": True, "family": "FAMILY_B"},
            # Family C — one event (HIGH quality)
            "EVT_C1": {"enabled": True, "family": "FAMILY_C"},
        }
    }
    ctrl.registries.templates = {
        "families": {
            "FAMILY_A": {"allowed_templates": ["mean_reversion", "continuation"]},
            "FAMILY_B": {"allowed_templates": ["mean_reversion"]},
            "FAMILY_C": {"allowed_templates": ["exhaustion_reversal"]},
        }
    }
    return ctrl


def _empty_memory() -> Dict[str, Any]:
    return {
        "belief_state": {},
        "next_actions": {"repair": [], "exploit": [], "explore_adjacent": [], "hold": []},
        "latest_reflection": {},
        "avoid_region_keys": set(),
        "avoid_event_types": set(),
        "promising_regions": [],
        "superseded_stages": set(),
    }


# ---------------------------------------------------------------------------
# Phase 2.3 — research_mode = "scan" (single-family constraint)
# ---------------------------------------------------------------------------


class TestScanModeSingleFamily:
    def test_scan_picks_single_family(self, tmp_path):
        ctrl = _make_controller(tmp_path, research_mode="scan")
        # Give FAMILY_C the highest weight via its single event
        ctrl._quality_weights = {
            "EVT_C1": 3.467,   # HIGH tier
            "EVT_A1": 1.5,
            "EVT_A2": 1.5,
            "EVT_B1": 1.0,
            "EVT_B2": 1.0,
        }
        mem = _empty_memory()

        with patch(
            "project.research.campaign_controller.read_memory_table",
            return_value=pd.DataFrame(),
        ):
            result = ctrl._step_scan_frontier(mem)

        assert result is not None
        events = result["trigger_space"]["events"]["include"]
        # All events must be from the same family
        families = {
            str(ctrl.registries.events["events"].get(e, {}).get("family", "?"))
            for e in events
        }
        assert len(families) == 1, f"Expected 1 family, got {families}"

    def test_scan_best_family_chosen_by_max_member_weight(self, tmp_path):
        ctrl = _make_controller(tmp_path, research_mode="scan")
        ctrl._quality_weights = {
            "EVT_A1": 3.0,   # FAMILY_A has a HIGH member
            "EVT_A2": 1.5,
            "EVT_B1": 2.0,   # FAMILY_B best member is MODERATE
            "EVT_B2": 2.0,
            "EVT_C1": 1.0,   # FAMILY_C is LOW
        }
        mem = _empty_memory()

        with patch(
            "project.research.campaign_controller.read_memory_table",
            return_value=pd.DataFrame(),
        ):
            result = ctrl._step_scan_frontier(mem)

        events = result["trigger_space"]["events"]["include"]
        families = {
            str(ctrl.registries.events["events"].get(e, {}).get("family", "?"))
            for e in events
        }
        assert families == {"FAMILY_A"}, f"FAMILY_A should win; got {families}"

    def test_scan_respects_avoid_list(self, tmp_path):
        ctrl = _make_controller(tmp_path, research_mode="scan")
        ctrl._quality_weights = {"EVT_C1": 3.0}
        mem = _empty_memory()
        mem["avoid_event_types"] = {"EVT_C1"}  # The only HIGH event is avoided

        with patch(
            "project.research.campaign_controller.read_memory_table",
            return_value=pd.DataFrame(),
        ):
            result = ctrl._step_scan_frontier(mem)

        # EVT_C1 avoided → should fall back to A or B family
        if result is not None:
            events = result["trigger_space"]["events"]["include"]
            assert "EVT_C1" not in events

    def test_scan_returns_none_when_all_tested(self, tmp_path):
        ctrl = _make_controller(tmp_path, research_mode="scan")
        mem = _empty_memory()
        all_events_df = pd.DataFrame({
            "event_type": ["EVT_A1", "EVT_A2", "EVT_B1", "EVT_B2", "EVT_C1"]
        })

        with patch(
            "project.research.campaign_controller.read_memory_table",
            return_value=all_events_df,
        ):
            result = ctrl._step_scan_frontier(mem)

        assert result is None

    def test_scan_batch_capped_at_three(self, tmp_path):
        ctrl = _make_controller(tmp_path, research_mode="scan")
        # Add many events to FAMILY_A so the cap matters
        ctrl.registries.events["events"].update({
            f"EVT_A{i}": {"enabled": True, "family": "FAMILY_A"} for i in range(3, 10)
        })
        ctrl._quality_weights = {f"EVT_A{i}": 3.0 for i in range(1, 10)}
        mem = _empty_memory()

        with patch(
            "project.research.campaign_controller.read_memory_table",
            return_value=pd.DataFrame(),
        ):
            result = ctrl._step_scan_frontier(mem)

        assert result is not None
        assert len(result["trigger_space"]["events"]["include"]) <= 3

    def test_scan_no_zero_entry_lags(self, tmp_path):
        ctrl = _make_controller(tmp_path, research_mode="scan")
        mem = _empty_memory()
        with patch(
            "project.research.campaign_controller.read_memory_table",
            return_value=pd.DataFrame(),
        ):
            result = ctrl._step_scan_frontier(mem)
        assert result is not None
        assert 0 not in result["evaluation"]["entry_lags"]


# ---------------------------------------------------------------------------
# Phase 2.3 — research_mode = "explore" (cross-family batches)
# ---------------------------------------------------------------------------


class TestExploreModeCrossFamily:
    def test_explore_pulls_from_multiple_families(self, tmp_path):
        ctrl = _make_controller(tmp_path, research_mode="explore")
        ctrl._quality_weights = {
            "EVT_A1": 3.0,
            "EVT_B1": 2.5,
            "EVT_C1": 2.0,
            "EVT_A2": 1.5,
            "EVT_B2": 1.0,
        }
        mem = _empty_memory()

        with patch(
            "project.research.campaign_controller.read_memory_table",
            return_value=pd.DataFrame(),
        ):
            result = ctrl._step_scan_frontier_cross_family(mem)

        assert result is not None
        events = result["trigger_space"]["events"]["include"]
        families = {
            str(ctrl.registries.events["events"].get(e, {}).get("family", "?"))
            for e in events
        }
        assert len(families) > 1, f"Explore mode should span families; got {families}"

    def test_explore_batch_capped_at_five(self, tmp_path):
        ctrl = _make_controller(tmp_path, research_mode="explore")
        # Add enough events that 5-cap matters
        for i in range(10):
            ctrl.registries.events["events"][f"EVT_X{i}"] = {
                "enabled": True, "family": f"FAM_{i}"
            }
        mem = _empty_memory()

        with patch(
            "project.research.campaign_controller.read_memory_table",
            return_value=pd.DataFrame(),
        ):
            result = ctrl._step_scan_frontier_cross_family(mem)

        assert result is not None
        assert len(result["trigger_space"]["events"]["include"]) <= 5

    def test_explore_uses_wider_date_scope(self, tmp_path):
        ctrl = _make_controller(tmp_path, research_mode="explore")
        mem = _empty_memory()

        with patch(
            "project.research.campaign_controller.read_memory_table",
            return_value=pd.DataFrame(),
        ):
            result = ctrl._step_scan_frontier_cross_family(mem)

        assert result is not None
        # Explore uses 3-month window vs scan's 1-month
        assert result["instrument_scope"]["end"] == "2024-03-31"

    def test_explore_returns_none_when_exhausted(self, tmp_path):
        ctrl = _make_controller(tmp_path, research_mode="explore")
        mem = _empty_memory()
        all_events = list(ctrl.registries.events["events"].keys())
        tested_df = pd.DataFrame({"event_type": all_events})

        with patch(
            "project.research.campaign_controller.read_memory_table",
            return_value=tested_df,
        ):
            result = ctrl._step_scan_frontier_cross_family(mem)

        assert result is None

    def test_explore_mode_routes_step4_to_cross_family(self, tmp_path):
        """End-to-end: explore mode's Step 4 produces cross-family results."""
        ctrl = _make_controller(tmp_path, research_mode="explore")
        ctrl._quality_weights = {
            "EVT_A1": 3.0, "EVT_B1": 2.5, "EVT_C1": 2.0,
        }
        mem = _empty_memory()

        with patch.object(ctrl, "_read_memory", return_value=mem), \
             patch(
                 "project.research.campaign_controller.read_memory_table",
                 return_value=pd.DataFrame(),
             ):
            result = ctrl._propose_next_request()

        assert result is not None
        # Cross-family explore uses 3-month window, scan uses 1-month
        assert result["instrument_scope"]["end"] == "2024-03-31"

    def test_scan_mode_routes_step4_to_single_family(self, tmp_path):
        """End-to-end: scan mode's Step 4 produces single-family results."""
        ctrl = _make_controller(tmp_path, research_mode="scan")
        ctrl._quality_weights = {
            "EVT_A1": 3.0, "EVT_A2": 2.8,
            "EVT_B1": 2.0, "EVT_C1": 1.0,
        }
        mem = _empty_memory()

        with patch.object(ctrl, "_read_memory", return_value=mem), \
             patch(
                 "project.research.campaign_controller.read_memory_table",
                 return_value=pd.DataFrame(),
             ):
            result = ctrl._propose_next_request()

        assert result is not None
        events = result["trigger_space"]["events"]["include"]
        families = {
            str(ctrl.registries.events["events"].get(e, {}).get("family", "?"))
            for e in events
        }
        assert len(families) == 1

    def test_explore_mode_still_runs_repair_first(self, tmp_path):
        """research_mode=explore does not bypass Step 1 REPAIR."""
        ctrl = _make_controller(tmp_path, research_mode="explore")
        mem = _empty_memory()
        mem["next_actions"]["repair"] = [{"proposed_scope": {"stage": "feature_pipeline"}}]

        with patch.object(ctrl, "_read_memory", return_value=mem), \
             patch(
                 "project.research.campaign_controller.read_memory_table",
                 return_value=pd.DataFrame(),
             ):
            result = ctrl._propose_next_request()

        # Repair takes priority — short 7-day window
        assert result is not None
        assert result["instrument_scope"]["end"] == "2024-01-07"


# ---------------------------------------------------------------------------
# Phase 2.4 — mark_failures_superseded
# ---------------------------------------------------------------------------


class TestMarkFailuresSuperseded:
    def _make_failures(self) -> pd.DataFrame:
        return pd.DataFrame({
            "run_id": ["run_1", "run_1", "run_2"],
            "program_id": ["prog_a", "prog_a", "prog_a"],
            "stage": ["phase2_search_engine", "feature_pipeline", "phase2_search_engine"],
            "failure_class": ["stage_failed", "stage_failed", "stage_failed"],
            "failure_detail": ["err", "err", "err"],
            "artifact_path": ["a", "b", "c"],
            "is_mechanical": [True, True, True],
            "is_repeated": [False, False, False],
            "superseded_by_run_id": ["", "", ""],
        })

    def test_marks_matching_stage_and_program(self):
        df = self._make_failures()
        result = mark_failures_superseded(
            df, current_run_id="run_3", stage="phase2_search_engine", program_id="prog_a"
        )
        superseded = result[result["stage"] == "phase2_search_engine"]
        assert all(superseded["superseded_by_run_id"] == "run_3")

    def test_does_not_touch_other_stages(self):
        df = self._make_failures()
        result = mark_failures_superseded(
            df, current_run_id="run_3", stage="phase2_search_engine", program_id="prog_a"
        )
        pipeline_rows = result[result["stage"] == "feature_pipeline"]
        assert all(pipeline_rows["superseded_by_run_id"] == "")

    def test_does_not_touch_already_superseded_rows(self):
        df = self._make_failures()
        df.loc[0, "superseded_by_run_id"] = "run_earlier"
        result = mark_failures_superseded(
            df, current_run_id="run_3", stage="phase2_search_engine", program_id="prog_a"
        )
        # Row 0 already superseded — must not be overwritten
        assert result.loc[0, "superseded_by_run_id"] == "run_earlier"
        # Row 2 was open — must be superseded now
        assert result.loc[2, "superseded_by_run_id"] == "run_3"

    def test_empty_dataframe_returns_empty(self):
        result = mark_failures_superseded(
            pd.DataFrame(),
            current_run_id="run_3",
            stage="any_stage",
            program_id="prog_a",
        )
        assert result.empty

    def test_no_matching_rows_no_change(self):
        df = self._make_failures()
        result = mark_failures_superseded(
            df, current_run_id="run_3", stage="NONEXISTENT_STAGE", program_id="prog_a"
        )
        assert all(result["superseded_by_run_id"] == "")

    def test_scoped_to_program_id(self):
        df = self._make_failures()
        # Change one row to a different program
        df.loc[0, "program_id"] = "prog_b"
        result = mark_failures_superseded(
            df, current_run_id="run_3", stage="phase2_search_engine", program_id="prog_a"
        )
        # prog_b row must not be superseded
        assert result.loc[0, "superseded_by_run_id"] == ""
        # prog_a row must be superseded
        assert result.loc[2, "superseded_by_run_id"] == "run_3"

    def test_adds_column_if_missing(self):
        df = self._make_failures().drop(columns=["superseded_by_run_id"])
        result = mark_failures_superseded(
            df, current_run_id="run_x", stage="phase2_search_engine", program_id="prog_a"
        )
        assert "superseded_by_run_id" in result.columns


# ---------------------------------------------------------------------------
# Phase 2.4 — _step_repair skips superseded stages
# ---------------------------------------------------------------------------


class TestRepairSkipsSuperseded:
    def test_repair_skips_superseded_stage(self, tmp_path):
        ctrl = _make_controller(tmp_path)
        mem = _empty_memory()
        mem["next_actions"]["repair"] = [
            {"proposed_scope": {"stage": "phase2_search_engine"}}
        ]
        # Mark that stage as already superseded
        mem["superseded_stages"] = {"phase2_search_engine"}

        result = ctrl._step_repair(mem)
        assert result is None  # Superseded → nothing to repair

    def test_repair_acts_on_non_superseded_stage(self, tmp_path):
        ctrl = _make_controller(tmp_path)
        mem = _empty_memory()
        mem["next_actions"]["repair"] = [
            {"proposed_scope": {"stage": "feature_pipeline"}}
        ]
        mem["superseded_stages"] = {"phase2_search_engine"}  # different stage

        result = ctrl._step_repair(mem)
        assert result is not None  # feature_pipeline not superseded → propose repair

    def test_repair_acts_when_superseded_stages_empty(self, tmp_path):
        ctrl = _make_controller(tmp_path)
        mem = _empty_memory()
        mem["next_actions"]["repair"] = [
            {"proposed_scope": {"stage": "feature_pipeline"}}
        ]
        # No superseded stages at all

        result = ctrl._step_repair(mem)
        assert result is not None

    def test_repair_skips_all_when_all_superseded(self, tmp_path):
        ctrl = _make_controller(tmp_path)
        mem = _empty_memory()
        mem["next_actions"]["repair"] = [
            {"proposed_scope": {"stage": "stage_a"}},
            {"proposed_scope": {"stage": "stage_b"}},
        ]
        mem["superseded_stages"] = {"stage_a", "stage_b"}

        result = ctrl._step_repair(mem)
        assert result is None

    def test_repair_acts_on_first_non_superseded_in_queue(self, tmp_path):
        ctrl = _make_controller(tmp_path)
        mem = _empty_memory()
        mem["next_actions"]["repair"] = [
            {"proposed_scope": {"stage": "stage_a"}},   # superseded
            {"proposed_scope": {"stage": "stage_b"}},   # open
        ]
        mem["superseded_stages"] = {"stage_a"}

        result = ctrl._step_repair(mem)
        assert result is not None
        assert "stage_b" in result["description"]


# ---------------------------------------------------------------------------
# Phase 2.4 — _read_memory exposes superseded_stages
# ---------------------------------------------------------------------------


class TestReadMemorySupersededStages:
    def test_superseded_stages_populated_from_failures_table(self, tmp_path):
        ctrl = _make_controller(tmp_path)

        failures_df = pd.DataFrame({
            "stage": ["phase2_search_engine", "feature_pipeline"],
            "superseded_by_run_id": ["run_fix", ""],
        })

        with patch(
            "project.research.campaign_controller.read_memory_table",
            return_value=failures_df,
        ), patch(
            "project.research.campaign_controller.memory_paths",
        ) as mock_paths:
            mock_paths.return_value = MagicMock(
                belief_state=tmp_path / "belief_state.json",
                next_actions=tmp_path / "next_actions.json",
                reflections=tmp_path / "reflections.parquet",
            )
            mem = ctrl._read_memory()

        assert "phase2_search_engine" in mem["superseded_stages"]
        assert "feature_pipeline" not in mem["superseded_stages"]

    def test_superseded_stages_empty_when_none_superseded(self, tmp_path):
        ctrl = _make_controller(tmp_path)

        failures_df = pd.DataFrame({
            "stage": ["phase2_search_engine"],
            "superseded_by_run_id": [""],
        })

        with patch(
            "project.research.campaign_controller.read_memory_table",
            return_value=failures_df,
        ), patch(
            "project.research.campaign_controller.memory_paths",
        ) as mock_paths:
            mock_paths.return_value = MagicMock(
                belief_state=tmp_path / "belief_state.json",
                next_actions=tmp_path / "next_actions.json",
                reflections=tmp_path / "reflections.parquet",
            )
            mem = ctrl._read_memory()

        assert mem["superseded_stages"] == set()

    def test_superseded_stages_empty_on_exception(self, tmp_path):
        ctrl = _make_controller(tmp_path)

        with patch(
            "project.research.campaign_controller.read_memory_table",
            side_effect=Exception("disk error"),
        ), patch(
            "project.research.campaign_controller.memory_paths",
        ) as mock_paths:
            mock_paths.return_value = MagicMock(
                belief_state=tmp_path / "belief_state.json",
                next_actions=tmp_path / "next_actions.json",
                reflections=tmp_path / "reflections.parquet",
            )
            mem = ctrl._read_memory()

        assert mem["superseded_stages"] == set()
