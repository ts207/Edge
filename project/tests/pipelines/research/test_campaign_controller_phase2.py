"""Phase 2.1 — Tests for the memory-driven campaign controller.

Verifies that _propose_next_request() follows the four-step priority order:
  1. Repair   — open mechanical failures take absolute priority
  2. Exploit  — reflection-recommended exploit run
  3. Explore  — explore_adjacent queue entry
  4. Scan     — quality-weighted untested frontier

Also tests:
  - Quality-weight parsing from search_space.yaml annotations
  - Avoid-list filtering in frontier scan
  - _templates_for_event fallback behaviour
  - research_mode="exploit" short-circuits to promising_regions only
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from project.research.campaign_controller import (
    CampaignConfig,
    CampaignController,
    CampaignSummary,
    _load_event_quality_weights,
    _DEFAULT_QUALITY,
    _QUALITY_SCORES,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_controller(
    tmp_path: Path, research_mode: str = "scan", **config_kwargs: Any
) -> CampaignController:
    """Build a controller with a stubbed RegistryBundle so no real files needed."""
    config = CampaignConfig(
        program_id="test_program",
        max_runs=5,
        research_mode=research_mode,
        **config_kwargs,
    )
    registry_root = tmp_path / "registries"
    registry_root.mkdir()

    ctrl = CampaignController.__new__(CampaignController)
    ctrl.config = config
    ctrl.data_root = tmp_path
    ctrl.registry_root = registry_root
    ctrl.campaign_dir = tmp_path / "artifacts" / "experiments" / config.program_id
    ctrl.campaign_dir.mkdir(parents=True)
    ctrl.ledger_path = ctrl.campaign_dir / "tested_ledger.parquet"
    ctrl.summary_path = ctrl.campaign_dir / "campaign_summary.json"
    ctrl._search_space_path = Path("spec/search_space.yaml")
    ctrl._quality_weights = {}

    # Minimal registries stub
    ctrl.registries = MagicMock()
    ctrl.registries.events = {
        "events": {
            "ZSCORE_STRETCH": {"enabled": True, "family": "STATISTICAL_DISLOCATION"},
            "FND_DISLOC": {"enabled": True, "family": "POSITIONING_EXTREMES"},
            "VOL_SHOCK": {"enabled": True, "family": "VOLATILITY_TRANSITION"},
            "LIQUIDATION_CASCADE": {"enabled": True, "family": "FORCED_FLOW_AND_EXHAUSTION"},
        }
    }
    ctrl.registries.templates = {
        "families": {
            "STATISTICAL_DISLOCATION": {"allowed_templates": ["mean_reversion", "overshoot_repair"]},
            "POSITIONING_EXTREMES": {"allowed_templates": ["reversal_or_squeeze", "mean_reversion"]},
            "VOLATILITY_TRANSITION": {"allowed_templates": ["mean_reversion", "continuation"]},
            "FORCED_FLOW_AND_EXHAUSTION": {"allowed_templates": ["exhaustion_reversal", "momentum_fade"]},
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
    }


# ---------------------------------------------------------------------------
# Quality weight tests
# ---------------------------------------------------------------------------


class TestQualityWeightParsing:
    def test_parses_high(self, tmp_path):
        f = tmp_path / "search_space.yaml"
        f.write_text("    - LIQUIDATION_CASCADE # [QUALITY: HIGH] - High IG (0.000467)\n")
        weights = _load_event_quality_weights(f)
        # Phase 2.2: weight = tier base + IG bonus; must be >= tier base and in HIGH tier range
        assert "LIQUIDATION_CASCADE" in weights
        assert weights["LIQUIDATION_CASCADE"] >= _QUALITY_SCORES["HIGH"]
        assert weights["LIQUIDATION_CASCADE"] < _QUALITY_SCORES["HIGH"] + 1.0  # still HIGH tier

    def test_parses_moderate(self, tmp_path):
        f = tmp_path / "search_space.yaml"
        f.write_text("    - OVERSHOOT_AFTER_SHOCK # [QUALITY: MODERATE] - Moderate IG\n")
        weights = _load_event_quality_weights(f)
        assert weights["OVERSHOOT_AFTER_SHOCK"] == _QUALITY_SCORES["MODERATE"]

    def test_parses_low(self, tmp_path):
        f = tmp_path / "search_space.yaml"
        f.write_text("    - LIQUIDITY_VACUUM # [QUALITY: LOW] - Marginal IG (0.000134)\n")
        weights = _load_event_quality_weights(f)
        # Phase 2.2: weight = tier base + IG bonus
        assert "LIQUIDITY_VACUUM" in weights
        assert weights["LIQUIDITY_VACUUM"] >= _QUALITY_SCORES["LOW"]
        assert weights["LIQUIDITY_VACUUM"] < _QUALITY_SCORES["LOW"] + 1.0  # still LOW tier

    def test_unannotated_events_absent(self, tmp_path):
        f = tmp_path / "search_space.yaml"
        f.write_text("    - VOL_SPIKE\n")
        weights = _load_event_quality_weights(f)
        assert "VOL_SPIKE" not in weights

    def test_missing_file_returns_empty(self, tmp_path):
        weights = _load_event_quality_weights(tmp_path / "nonexistent.yaml")
        assert weights == {}

    def test_structured_entries_skipped(self, tmp_path):
        f = tmp_path / "search_space.yaml"
        f.write_text("    - { from: LOW_VOL_REGIME, to: HIGH_VOL_REGIME }\n")
        weights = _load_event_quality_weights(f)
        assert weights == {}


# ---------------------------------------------------------------------------
# Step 1 — Repair priority
# ---------------------------------------------------------------------------


class TestStep1Repair:
    def test_repair_takes_priority_over_all(self, tmp_path):
        ctrl = _make_controller(tmp_path)
        mem = _empty_memory()
        mem["next_actions"]["repair"] = [
            {"reason": "mechanical failure detected",
             "proposed_scope": {"stage": "phase2_search_engine"}}
        ]
        # Even with a reflection saying exploit, repair wins
        mem["latest_reflection"]["recommended_next_action"] = "exploit_promising_region"
        mem["latest_reflection"]["recommended_next_experiment"] = json.dumps(
            {"event_type": "FND_DISLOC"}
        )

        result = ctrl._step_repair(mem)
        assert result is not None
        assert result["promotion"]["enabled"] is False
        # Repair proposals use a short date window
        assert result["instrument_scope"]["start"] == "2024-01-01"
        assert result["instrument_scope"]["end"] == "2024-01-07"

    def test_no_repair_when_queue_empty(self, tmp_path):
        ctrl = _make_controller(tmp_path)
        mem = _empty_memory()
        result = ctrl._step_repair(mem)
        assert result is None

    def test_repair_proposal_has_valid_entry_lags(self, tmp_path):
        ctrl = _make_controller(tmp_path)
        mem = _empty_memory()
        mem["next_actions"]["repair"] = [
            {"proposed_scope": {"stage": "feature_pipeline"}}
        ]
        result = ctrl._step_repair(mem)
        assert result is not None
        assert 0 not in result["evaluation"]["entry_lags"]
        assert all(lag >= 1 for lag in result["evaluation"]["entry_lags"])

    def test_repair_uses_configured_date_scope(self, tmp_path):
        ctrl = _make_controller(
            tmp_path,
            repair_date_scope=("2025-02-01", "2025-02-05"),
        )
        mem = _empty_memory()
        mem["next_actions"]["repair"] = [{"proposed_scope": {"stage": "feature_pipeline"}}]

        result = ctrl._step_repair(mem)

        assert result is not None
        assert result["instrument_scope"]["start"] == "2025-02-01"
        assert result["instrument_scope"]["end"] == "2025-02-05"


# ---------------------------------------------------------------------------
# Step 2 — Exploit from reflection
# ---------------------------------------------------------------------------


class TestStep2ExploitFromReflection:
    def test_exploit_when_reflection_says_exploit(self, tmp_path):
        ctrl = _make_controller(tmp_path)
        mem = _empty_memory()
        mem["latest_reflection"] = {
            "recommended_next_action": "exploit_promising_region",
            "recommended_next_experiment": json.dumps({"event_type": "ZSCORE_STRETCH"}),
        }

        result = ctrl._step_exploit_from_reflection(mem)
        assert result is not None
        assert result["promotion"]["enabled"] is True
        assert "ZSCORE_STRETCH" in result["trigger_space"]["events"]["include"]

    def test_no_exploit_when_action_is_explore(self, tmp_path):
        ctrl = _make_controller(tmp_path)
        mem = _empty_memory()
        mem["latest_reflection"] = {
            "recommended_next_action": "explore_adjacent_region",
            "recommended_next_experiment": json.dumps({"event_type": "ZSCORE_STRETCH"}),
        }

        result = ctrl._step_exploit_from_reflection(mem)
        assert result is None

    def test_no_exploit_when_event_type_missing(self, tmp_path):
        ctrl = _make_controller(tmp_path)
        mem = _empty_memory()
        mem["latest_reflection"] = {
            "recommended_next_action": "exploit_promising_region",
            "recommended_next_experiment": json.dumps({"event_type": ""}),
        }

        result = ctrl._step_exploit_from_reflection(mem)
        assert result is None

    def test_exploit_uses_broader_date_scope(self, tmp_path):
        ctrl = _make_controller(tmp_path)
        mem = _empty_memory()
        mem["latest_reflection"] = {
            "recommended_next_action": "exploit_promising_region",
            "recommended_next_experiment": json.dumps({"event_type": "FND_DISLOC"}),
        }
        result = ctrl._step_exploit_from_reflection(mem)
        assert result is not None
        # Exploit uses wider date window than scan
        assert result["instrument_scope"]["start"] == "2023-10-01"

    def test_exploit_uses_family_templates(self, tmp_path):
        ctrl = _make_controller(tmp_path)
        mem = _empty_memory()
        mem["latest_reflection"] = {
            "recommended_next_action": "exploit_promising_region",
            "recommended_next_experiment": json.dumps({"event_type": "ZSCORE_STRETCH"}),
        }
        result = ctrl._step_exploit_from_reflection(mem)
        # ZSCORE_STRETCH → STATISTICAL_DISLOCATION → [mean_reversion, overshoot_repair]
        assert "mean_reversion" in result["templates"]["include"]
        assert "overshoot_repair" in result["templates"]["include"]


# ---------------------------------------------------------------------------
# Step 3 — Explore adjacent
# ---------------------------------------------------------------------------


class TestStep3ExploreAdjacent:
    def test_explore_when_queue_has_entry(self, tmp_path):
        ctrl = _make_controller(tmp_path)
        mem = _empty_memory()
        mem["next_actions"]["explore_adjacent"] = [
            {
                "reason": "explore_adjacent_region",
                "proposed_scope": {"event_type": "FND_DISLOC"},
            }
        ]

        result = ctrl._step_explore_adjacent(mem)
        assert result is not None
        assert "FND_DISLOC" in result["trigger_space"]["events"]["include"]
        assert result["promotion"]["enabled"] is False

    def test_explore_uses_wider_horizons(self, tmp_path):
        ctrl = _make_controller(tmp_path)
        mem = _empty_memory()
        mem["next_actions"]["explore_adjacent"] = [
            {"proposed_scope": {"event_type": "VOL_SHOCK"}}
        ]
        result = ctrl._step_explore_adjacent(mem)
        assert result is not None
        # Explore uses [6, 12, 24, 48] vs scan's [12, 24]
        assert 6 in result["evaluation"]["horizons_bars"]
        assert 48 in result["evaluation"]["horizons_bars"]

    def test_no_explore_when_queue_empty(self, tmp_path):
        ctrl = _make_controller(tmp_path)
        mem = _empty_memory()
        result = ctrl._step_explore_adjacent(mem)
        assert result is None

    def test_explore_skips_empty_event_type(self, tmp_path):
        ctrl = _make_controller(tmp_path)
        mem = _empty_memory()
        mem["next_actions"]["explore_adjacent"] = [
            {"proposed_scope": {"event_type": ""}}
        ]
        result = ctrl._step_explore_adjacent(mem)
        assert result is None

    def test_explore_reconstructs_state_trigger_from_memory_scope(self, tmp_path):
        ctrl = _make_controller(tmp_path)
        mem = _empty_memory()
        mem["next_actions"]["explore_adjacent"] = [
            {
                "proposed_scope": {
                    "event_type": "STATE_HIGH_VOL_STATE",
                    "trigger_type": "STATE",
                }
            }
        ]

        result = ctrl._step_explore_adjacent(mem)

        assert result is not None
        assert result["trigger_space"]["allowed_trigger_types"] == ["STATE"]
        assert result["trigger_space"]["states"]["include"] == ["HIGH_VOL_STATE"]

    def test_explore_reconstructs_sequence_trigger_from_memory_payload(self, tmp_path):
        ctrl = _make_controller(tmp_path)
        mem = _empty_memory()
        mem["next_actions"]["explore_adjacent"] = [
            {
                "proposed_scope": {
                    "event_type": "SEQUENCE_SEQ_ABC",
                    "trigger_type": "SEQUENCE",
                    "trigger_payload_json": json.dumps(
                        {
                            "trigger_type": "sequence",
                            "sequence_id": "SEQ_ABC",
                            "events": ["VOL_SHOCK", "LIQUIDATION_CASCADE"],
                            "max_gap": [6],
                        }
                    ),
                }
            }
        ]

        result = ctrl._step_explore_adjacent(mem)

        assert result is not None
        assert result["trigger_space"]["allowed_trigger_types"] == ["SEQUENCE"]
        assert result["trigger_space"]["sequences"]["include"] == [
            ["VOL_SHOCK", "LIQUIDATION_CASCADE"]
        ]
        assert result["trigger_space"]["sequences"]["max_gaps_bars"] == [6]


# ---------------------------------------------------------------------------
# Step 4 — Frontier scan
# ---------------------------------------------------------------------------


class TestStep4FrontierScan:
    def test_scan_returns_untested_events(self, tmp_path):
        ctrl = _make_controller(tmp_path)
        mem = _empty_memory()

        with patch.object(ctrl, "_read_memory", return_value=mem), \
             patch("project.research.campaign_controller.read_memory_table",
                   return_value=__import__("pandas").DataFrame()):
            result = ctrl._step_scan_frontier(mem)

        assert result is not None
        assert len(result["trigger_space"]["events"]["include"]) <= 3

    def test_scan_respects_avoid_list(self, tmp_path):
        ctrl = _make_controller(tmp_path)
        mem = _empty_memory()
        mem["avoid_event_types"] = {"ZSCORE_STRETCH", "FND_DISLOC", "VOL_SHOCK", "LIQUIDATION_CASCADE"}

        with patch("project.research.campaign_controller.read_memory_table",
                   return_value=__import__("pandas").DataFrame()):
            result = ctrl._step_scan_frontier(mem)

        assert result is None  # All 4 events avoided → nothing to propose

    def test_scan_quality_weights_applied(self, tmp_path):
        ctrl = _make_controller(tmp_path)
        # Assign HIGH to LIQUIDATION_CASCADE, LOW to others
        ctrl._quality_weights = {
            "LIQUIDATION_CASCADE": 3.0,
            "ZSCORE_STRETCH": 1.0,
            "FND_DISLOC": 1.0,
            "VOL_SHOCK": 1.0,
        }
        mem = _empty_memory()

        with patch("project.research.campaign_controller.read_memory_table",
                   return_value=__import__("pandas").DataFrame()):
            result = ctrl._step_scan_frontier(mem)

        assert result is not None
        events = result["trigger_space"]["events"]["include"]
        # LIQUIDATION_CASCADE should be first (highest quality)
        assert events[0] == "LIQUIDATION_CASCADE"

    def test_scan_skips_already_tested(self, tmp_path):
        import pandas as pd
        ctrl = _make_controller(tmp_path)
        mem = _empty_memory()
        # Fake tested_regions with ZSCORE_STRETCH already tested
        tested_df = pd.DataFrame({"event_type": ["ZSCORE_STRETCH"]})

        with patch("project.research.campaign_controller.read_memory_table",
                   return_value=tested_df):
            result = ctrl._step_scan_frontier(mem)

        assert result is not None
        events = result["trigger_space"]["events"]["include"]
        assert "ZSCORE_STRETCH" not in events

    def test_scan_entry_lags_no_zero(self, tmp_path):
        ctrl = _make_controller(tmp_path)
        mem = _empty_memory()

        with patch("project.research.campaign_controller.read_memory_table",
                   return_value=__import__("pandas").DataFrame()):
            result = ctrl._step_scan_frontier(mem)

        assert result is not None
        assert 0 not in result["evaluation"]["entry_lags"]


# ---------------------------------------------------------------------------
# Priority order — end-to-end
# ---------------------------------------------------------------------------


class TestPriorityOrder:
    def _patch_mem(self, ctrl, mem):
        ctrl._read_memory = lambda: mem

    def test_repair_beats_exploit(self, tmp_path):
        ctrl = _make_controller(tmp_path)
        mem = _empty_memory()
        mem["next_actions"]["repair"] = [{"proposed_scope": {"stage": "s1"}}]
        mem["latest_reflection"] = {
            "recommended_next_action": "exploit_promising_region",
            "recommended_next_experiment": json.dumps({"event_type": "ZSCORE_STRETCH"}),
        }
        self._patch_mem(ctrl, mem)

        with patch("project.research.campaign_controller.read_memory_table",
                   return_value=__import__("pandas").DataFrame()):
            result = ctrl._propose_next_request()

        # Repair proposals use 7-day window
        assert result["instrument_scope"]["end"] == "2024-01-07"

    def test_exploit_beats_explore(self, tmp_path):
        ctrl = _make_controller(tmp_path)
        mem = _empty_memory()
        mem["latest_reflection"] = {
            "recommended_next_action": "exploit_promising_region",
            "recommended_next_experiment": json.dumps({"event_type": "FND_DISLOC"}),
        }
        mem["next_actions"]["explore_adjacent"] = [
            {"proposed_scope": {"event_type": "VOL_SHOCK"}}
        ]
        self._patch_mem(ctrl, mem)

        with patch("project.research.campaign_controller.read_memory_table",
                   return_value=__import__("pandas").DataFrame()):
            result = ctrl._propose_next_request()

        # Exploit → FND_DISLOC, not explore → VOL_SHOCK
        assert "FND_DISLOC" in result["trigger_space"]["events"]["include"]
        assert result["promotion"]["enabled"] is True

    def test_explore_beats_scan(self, tmp_path):
        ctrl = _make_controller(tmp_path)
        mem = _empty_memory()
        mem["next_actions"]["explore_adjacent"] = [
            {"proposed_scope": {"event_type": "VOL_SHOCK"}}
        ]
        self._patch_mem(ctrl, mem)

        with patch("project.research.campaign_controller.read_memory_table",
                   return_value=__import__("pandas").DataFrame()):
            result = ctrl._propose_next_request()

        assert "VOL_SHOCK" in result["trigger_space"]["events"]["include"]
        # Explore uses 6-month window, scan uses 1-month
        assert result["instrument_scope"]["end"] == "2024-06-30"

    def test_scan_when_all_higher_priority_empty(self, tmp_path):
        ctrl = _make_controller(tmp_path)
        mem = _empty_memory()
        self._patch_mem(ctrl, mem)

        with patch("project.research.campaign_controller.read_memory_table",
                   return_value=__import__("pandas").DataFrame()):
            result = ctrl._propose_next_request()

        assert result is not None
        assert result["promotion"]["enabled"] is False
        assert result["instrument_scope"]["end"] == "2024-01-31"


# ---------------------------------------------------------------------------
# Exploit mode
# ---------------------------------------------------------------------------


class TestExploitMode:
    def test_exploit_mode_uses_promising_regions(self, tmp_path):
        ctrl = _make_controller(tmp_path, research_mode="exploit")
        mem = _empty_memory()
        mem["promising_regions"] = [
            {"event_type": "LIQUIDATION_CASCADE", "template_id": "exhaustion_reversal"}
        ]

        with patch.object(ctrl, "_read_memory", return_value=mem):
            result = ctrl._propose_next_request()

        assert result is not None
        assert "LIQUIDATION_CASCADE" in result["trigger_space"]["events"]["include"]
        assert result["promotion"]["enabled"] is True

    def test_exploit_mode_returns_none_when_promising_empty(self, tmp_path):
        ctrl = _make_controller(tmp_path, research_mode="exploit")
        mem = _empty_memory()
        # No repair either
        with patch.object(ctrl, "_read_memory", return_value=mem):
            result = ctrl._propose_next_request()
        assert result is None

    def test_exploit_mode_reconstructs_state_trigger_from_promising_region(self, tmp_path):
        ctrl = _make_controller(tmp_path, research_mode="exploit")
        mem = _empty_memory()
        mem["promising_regions"] = [
            {
                "event_type": "STATE_HIGH_VOL_STATE",
                "trigger_type": "STATE",
                "template_id": "mean_reversion",
            }
        ]

        with patch.object(ctrl, "_read_memory", return_value=mem):
            result = ctrl._propose_next_request()

        assert result is not None
        assert result["trigger_space"]["allowed_trigger_types"] == ["STATE"]
        assert result["trigger_space"]["states"]["include"] == ["HIGH_VOL_STATE"]

    def test_exploit_mode_reconstructs_interaction_trigger_from_promising_region(self, tmp_path):
        ctrl = _make_controller(tmp_path, research_mode="exploit")
        mem = _empty_memory()
        mem["promising_regions"] = [
            {
                "event_type": "INTERACTION_INT_ABC_AND_",
                "trigger_type": "INTERACTION",
                "template_id": "mean_reversion",
                "trigger_payload_json": json.dumps(
                    {
                        "trigger_type": "interaction",
                        "interaction_id": "INT_ABC",
                        "left": "VOL_SHOCK",
                        "right": "HIGH_VOL_STATE",
                        "op": "and",
                        "lag": 6,
                    }
                ),
            }
        ]

        with patch.object(ctrl, "_read_memory", return_value=mem):
            result = ctrl._propose_next_request()

        assert result is not None
        assert result["trigger_space"]["allowed_trigger_types"] == ["INTERACTION"]
        assert result["trigger_space"]["interactions"]["include"] == [
            {
                "left": "VOL_SHOCK",
                "right": "HIGH_VOL_STATE",
                "op": "AND",
                "lag": 6,
            }
        ]


def test_run_campaign_continues_after_pipeline_failure(tmp_path):
    ctrl = _make_controller(tmp_path)
    proposals = iter(
        [
            {
                "program_id": ctrl.config.program_id,
                "run_mode": "research",
                "instrument_scope": {
                    "instrument_classes": ["crypto"],
                    "symbols": ["BTCUSDT"],
                    "timeframe": "5m",
                    "start": "2024-01-01",
                    "end": "2024-01-31",
                },
                "trigger_space": {
                    "allowed_trigger_types": ["EVENT"],
                    "events": {"include": ["ZSCORE_STRETCH"]},
                },
                "templates": {"include": ["mean_reversion"]},
                "evaluation": {
                    "horizons_bars": [12],
                    "directions": ["long"],
                    "entry_lags": [1],
                },
                "contexts": {"include": {}},
                "search_control": {
                    "max_hypotheses_total": 10,
                    "max_hypotheses_per_template": 10,
                    "max_hypotheses_per_event_family": 10,
                },
                "promotion": {"enabled": False},
            },
            None,
        ]
    )
    counts = {"updated": 0}
    ctrl._propose_next_request = lambda: next(proposals)
    ctrl._execute_pipeline = lambda config_path, run_id: (_ for _ in ()).throw(RuntimeError("boom"))
    ctrl._update_campaign_stats = (
        lambda: counts.__setitem__("updated", counts["updated"] + 1)
        or CampaignSummary(ctrl.config.program_id)
    )
    ctrl._should_halt = lambda summary: False

    with patch("project.research.campaign_controller.build_experiment_plan", return_value=None):
        ctrl.run_campaign()

    assert counts["updated"] == 1


# ---------------------------------------------------------------------------
# _templates_for_event fallback
# ---------------------------------------------------------------------------


class TestTemplatesForEvent:
    def test_returns_family_templates(self, tmp_path):
        ctrl = _make_controller(tmp_path)
        templates = ctrl._templates_for_event("ZSCORE_STRETCH")
        assert "mean_reversion" in templates
        assert "overshoot_repair" in templates

    def test_fallback_for_unknown_event(self, tmp_path):
        ctrl = _make_controller(tmp_path)
        templates = ctrl._templates_for_event("UNKNOWN_EVENT_XYZ")
        assert templates == ["mean_reversion", "continuation"]

    def test_fallback_for_unmapped_family(self, tmp_path):
        ctrl = _make_controller(tmp_path)
        # Event exists in events registry but family has no templates
        ctrl.registries.events["events"]["ORPHAN_EVENT"] = {
            "enabled": True, "family": "NO_SUCH_FAMILY"
        }
        templates = ctrl._templates_for_event("ORPHAN_EVENT")
        assert templates == ["mean_reversion", "continuation"]
