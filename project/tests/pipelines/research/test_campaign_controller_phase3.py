"""Phase 3 — Discovery Surface tests.

3.1  STATE and TRANSITION trigger activation
3.2  Context conditioning via vol_regime wildcard
3.3  Within-run alpha clustering deduplication
3.4  SEQUENCE trigger seeding from weak-signal event pairs
3.5  FEATURE_PREDICATE trigger activation from search_space.yaml
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from project.research.campaign_controller import (
    CampaignConfig,
    CampaignController,
    _DEFAULT_QUALITY,
)
from project.research.run_hypothesis_search import _cluster_deduplicate


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _make_ctrl(tmp_path: Path, **cfg_kwargs) -> CampaignController:
    config = CampaignConfig(program_id="ph3_test", max_runs=10, **cfg_kwargs)
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
            "EVT_A1": {"enabled": True, "family": "FAM_A"},
            "EVT_A2": {"enabled": True, "family": "FAM_A"},
            "EVT_B1": {"enabled": True, "family": "FAM_B"},
        }
    }
    ctrl.registries.templates = {
        "families": {
            "FAM_A": {"allowed_templates": ["mean_reversion", "continuation"]},
            "FAM_B": {"allowed_templates": ["mean_reversion"]},
        }
    }
    return ctrl


def _empty_mem() -> Dict[str, Any]:
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
# 3.1 — scan_trigger_types sequences through trigger types
# ---------------------------------------------------------------------------


class TestScanTriggerTypeSequencing:
    """Phase 3.1: controller sequences through scan_trigger_types."""

    def test_default_config_event_only(self, tmp_path):
        ctrl = _make_ctrl(tmp_path)
        assert ctrl.config.scan_trigger_types == ["EVENT"]

    def test_scan_trigger_types_custom(self, tmp_path):
        ctrl = _make_ctrl(tmp_path, scan_trigger_types=["EVENT", "STATE", "TRANSITION"])
        assert ctrl.config.scan_trigger_types == ["EVENT", "STATE", "TRANSITION"]

    def test_event_scan_returns_when_events_remain(self, tmp_path):
        ctrl = _make_ctrl(tmp_path, scan_trigger_types=["EVENT", "STATE"])
        mem = _empty_mem()
        with patch(
            "project.research.campaign_controller.read_memory_table",
            return_value=pd.DataFrame(),
        ):
            result = ctrl._step_scan_frontier(mem)
        assert result is not None
        assert result["trigger_space"]["allowed_trigger_types"] == ["EVENT"]

    def test_falls_through_to_state_when_events_exhausted(self, tmp_path):
        ctrl = _make_ctrl(tmp_path, scan_trigger_types=["EVENT", "STATE"])
        mem = _empty_mem()
        all_events = pd.DataFrame({"event_type": ["EVT_A1", "EVT_A2", "EVT_B1"]})
        with patch(
            "project.research.campaign_controller.read_memory_table",
            return_value=all_events,
        ):
            result = ctrl._step_scan_frontier(mem)
        # Events exhausted → should propose STATE if search_space.yaml has states
        if result is not None:
            # Could be STATE or None if states also exhausted/unavailable
            ttype = result["trigger_space"]["allowed_trigger_types"][0]
            assert ttype in ("STATE", "TRANSITION", "FEATURE_PREDICATE", "SEQUENCE")

    def test_returns_none_when_all_tiers_exhausted(self, tmp_path):
        ctrl = _make_ctrl(tmp_path, scan_trigger_types=["EVENT"])
        mem = _empty_mem()
        all_events = pd.DataFrame({"event_type": ["EVT_A1", "EVT_A2", "EVT_B1"]})
        with patch(
            "project.research.campaign_controller.read_memory_table",
            return_value=all_events,
        ):
            result = ctrl._step_scan_frontier(mem)
        # EVENT-only config, all events tested → exhausted
        assert result is None

    def test_state_proposal_built_correctly(self, tmp_path):
        ctrl = _make_ctrl(tmp_path, scan_trigger_types=["STATE"])
        mem = _empty_mem()
        with patch(
            "project.research.campaign_controller.read_memory_table",
            return_value=pd.DataFrame(),
        ):
            result = ctrl._step_scan_states(mem)
        if result is not None:
            assert result["trigger_space"]["allowed_trigger_types"] == ["STATE"]
            assert "states" in result["trigger_space"]
            assert isinstance(result["trigger_space"]["states"]["include"], list)
            assert len(result["trigger_space"]["states"]["include"]) > 0

    def test_transition_proposal_built_correctly(self, tmp_path):
        ctrl = _make_ctrl(tmp_path, scan_trigger_types=["TRANSITION"])
        mem = _empty_mem()
        with patch(
            "project.research.campaign_controller.read_memory_table",
            return_value=pd.DataFrame(),
        ):
            result = ctrl._step_scan_transitions(mem)
        if result is not None:
            assert result["trigger_space"]["allowed_trigger_types"] == ["TRANSITION"]
            assert "transitions" in result["trigger_space"]
            transitions = result["trigger_space"]["transitions"]["include"]
            assert isinstance(transitions, list)
            for t in transitions:
                assert "from_state" in t and "to_state" in t

    def test_state_batch_capped_at_four(self, tmp_path):
        ctrl = _make_ctrl(tmp_path)
        mem = _empty_mem()
        with patch(
            "project.research.campaign_controller.read_memory_table",
            return_value=pd.DataFrame(),
        ):
            result = ctrl._step_scan_states(mem)
        if result is not None:
            assert len(result["trigger_space"]["states"]["include"]) <= 4

    def test_state_scan_treats_prefixed_memory_event_type_as_already_tested(self, tmp_path):
        ctrl = _make_ctrl(tmp_path, scan_trigger_types=["STATE"])
        mem = _empty_mem()
        tested = pd.DataFrame(
            [{"event_type": "STATE_HIGH_VOL_REGIME", "trigger_type": "STATE"}]
        )
        with patch(
            "project.research.campaign_controller.read_memory_table",
            return_value=tested,
        ):
            result = ctrl._step_scan_states(mem)
        if result is not None:
            assert "HIGH_VOL_REGIME" not in result["trigger_space"]["states"]["include"]

    def test_transition_batch_capped_at_three(self, tmp_path):
        ctrl = _make_ctrl(tmp_path)
        mem = _empty_mem()
        with patch(
            "project.research.campaign_controller.read_memory_table",
            return_value=pd.DataFrame(),
        ):
            result = ctrl._step_scan_transitions(mem)
        if result is not None:
            assert len(result["trigger_space"]["transitions"]["include"]) <= 3

    def test_transition_scan_treats_prefixed_memory_event_type_as_already_tested(self, tmp_path):
        ctrl = _make_ctrl(tmp_path, scan_trigger_types=["TRANSITION"])
        mem = _empty_mem()
        tested = pd.DataFrame(
            [
                {
                    "event_type": "TRANSITION_LOW_VOL_REGIME_HIGH_VOL_REGIME",
                    "trigger_type": "TRANSITION",
                }
            ]
        )
        with patch(
            "project.research.campaign_controller.read_memory_table",
            return_value=tested,
        ):
            result = ctrl._step_scan_transitions(mem)
        if result is not None:
            transitions = result["trigger_space"]["transitions"]["include"]
            assert {"from_state": "LOW_VOL_REGIME", "to_state": "HIGH_VOL_REGIME"} not in transitions

    def test_state_no_zero_entry_lags(self, tmp_path):
        ctrl = _make_ctrl(tmp_path)
        mem = _empty_mem()
        with patch(
            "project.research.campaign_controller.read_memory_table",
            return_value=pd.DataFrame(),
        ):
            result = ctrl._step_scan_states(mem)
        if result is not None:
            assert 0 not in result["evaluation"]["entry_lags"]


# ---------------------------------------------------------------------------
# 3.2 — Context conditioning
# ---------------------------------------------------------------------------


class TestContextConditioning:
    """Phase 3.2: vol_regime context applied when enable_context_conditioning=True."""

    def test_context_disabled_by_default(self, tmp_path):
        ctrl = _make_ctrl(tmp_path)
        assert ctrl.config.enable_context_conditioning is False
        assert ctrl._context_for_proposal() == {}

    def test_context_enabled_returns_vol_regime(self, tmp_path):
        ctrl = _make_ctrl(tmp_path, enable_context_conditioning=True)
        ctx = ctrl._context_for_proposal()
        assert "vol_regime" in ctx
        assert "low" in ctx["vol_regime"]
        assert "high" in ctx["vol_regime"]

    def test_event_proposal_has_context_when_enabled(self, tmp_path):
        ctrl = _make_ctrl(tmp_path, enable_context_conditioning=True)
        mem = _empty_mem()
        with patch(
            "project.research.campaign_controller.read_memory_table",
            return_value=pd.DataFrame(),
        ):
            result = ctrl._step_scan_events(mem)
        assert result is not None
        assert result["contexts"]["include"].get("vol_regime") == ["low", "high"]

    def test_event_proposal_no_context_when_disabled(self, tmp_path):
        ctrl = _make_ctrl(tmp_path, enable_context_conditioning=False)
        mem = _empty_mem()
        with patch(
            "project.research.campaign_controller.read_memory_table",
            return_value=pd.DataFrame(),
        ):
            result = ctrl._step_scan_events(mem)
        assert result is not None
        assert result["contexts"]["include"] == {}

    def test_event_scan_uses_configured_date_scope(self, tmp_path):
        ctrl = _make_ctrl(tmp_path, scan_event_date_scope=("2025-03-01", "2025-03-15"))
        mem = _empty_mem()
        with patch(
            "project.research.campaign_controller.read_memory_table",
            return_value=pd.DataFrame(),
        ):
            result = ctrl._step_scan_events(mem)
        assert result is not None
        assert result["instrument_scope"]["start"] == "2025-03-01"
        assert result["instrument_scope"]["end"] == "2025-03-15"

    def test_state_proposal_inherits_context(self, tmp_path):
        ctrl = _make_ctrl(tmp_path, enable_context_conditioning=True)
        mem = _empty_mem()
        with patch(
            "project.research.campaign_controller.read_memory_table",
            return_value=pd.DataFrame(),
        ):
            result = ctrl._step_scan_states(mem)
        if result is not None:
            assert "vol_regime" in result["contexts"]["include"]

    def test_build_proposal_passes_context(self, tmp_path):
        ctrl = _make_ctrl(tmp_path)
        proposal = ctrl._build_proposal(
            events=["EVT_A1"],
            templates=["mean_reversion"],
            horizons=[12],
            description="test",
            promotion_enabled=False,
            date_scope=("2024-01-01", "2024-01-31"),
            contexts={"vol_regime": ["low", "high"]},
        )
        assert proposal["contexts"]["include"] == {"vol_regime": ["low", "high"]}

    def test_build_proposal_empty_context_by_default(self, tmp_path):
        ctrl = _make_ctrl(tmp_path)
        proposal = ctrl._build_proposal(
            events=["EVT_A1"],
            templates=["mean_reversion"],
            horizons=[12],
            description="test",
            promotion_enabled=False,
            date_scope=("2024-01-01", "2024-01-31"),
        )
        assert proposal["contexts"]["include"] == {}


# ---------------------------------------------------------------------------
# 3.3 — Alpha clustering deduplication
# ---------------------------------------------------------------------------


class TestAlphaClustering:
    """Phase 3.3: within-run alpha clustering marks redundant hypotheses."""

    def _make_metrics(self, n: int, vary: bool = True) -> pd.DataFrame:
        """Build a minimal metrics DataFrame."""
        rng = np.random.default_rng(42)
        rows = []
        for i in range(n):
            base = rng.normal(5.0, 10.0) if vary else 5.0
            rows.append({
                "hypothesis_id": f"hyp_{i:03d}",
                "mean_return_bps": base,
                "t_stat": base / 3.0,
                "sharpe": base / 20.0,
                "hit_rate": 0.5 + base / 1000.0,
                "trigger_type": "EVENT",
                "template_id": "mean_reversion",
                "n": 100,
            })
        return pd.DataFrame(rows)

    def test_empty_metrics_returned_unchanged(self):
        result = _cluster_deduplicate(pd.DataFrame())
        assert result.empty

    def test_single_hypothesis_not_redundant(self):
        metrics = self._make_metrics(1)
        result = _cluster_deduplicate(metrics)
        assert not result["is_cluster_redundant"].any()

    def test_column_added_to_output(self):
        metrics = self._make_metrics(5)
        result = _cluster_deduplicate(metrics)
        assert "is_cluster_redundant" in result.columns

    def test_identical_hypotheses_deduped(self):
        """Near-identical metric vectors → all but one marked redundant."""
        rows = [
            {"hypothesis_id": f"hyp_{i}", "mean_return_bps": 5.0,
             "t_stat": 1.67, "sharpe": 0.25, "hit_rate": 0.505}
            for i in range(5)
        ]
        metrics = pd.DataFrame(rows)
        result = _cluster_deduplicate(metrics, eps=0.01)
        # At least some should be marked redundant
        assert result["is_cluster_redundant"].sum() >= 1

    def test_diverse_hypotheses_not_all_redundant(self):
        """Very different profiles → each in its own cluster."""
        rows = [
            {"hypothesis_id": "hyp_0", "mean_return_bps": 50.0, "t_stat": 3.0, "sharpe": 1.5, "hit_rate": 0.65},
            {"hypothesis_id": "hyp_1", "mean_return_bps": -20.0, "t_stat": -1.5, "sharpe": -0.5, "hit_rate": 0.35},
            {"hypothesis_id": "hyp_2", "mean_return_bps": 0.1, "t_stat": 0.05, "sharpe": 0.01, "hit_rate": 0.50},
        ]
        metrics = pd.DataFrame(rows)
        result = _cluster_deduplicate(metrics, eps=0.5)
        # Diverse hypotheses: representatives should remain
        non_redundant = (~result["is_cluster_redundant"]).sum()
        assert non_redundant >= 2

    def test_best_sharpe_kept_in_cluster(self):
        """Within a cluster, the hypothesis with highest Sharpe is the representative."""
        rows = [
            {"hypothesis_id": "good", "mean_return_bps": 5.1, "t_stat": 1.68, "sharpe": 1.0, "hit_rate": 0.505},
            {"hypothesis_id": "bad",  "mean_return_bps": 4.9, "t_stat": 1.65, "sharpe": 0.3, "hit_rate": 0.503},
        ]
        metrics = pd.DataFrame(rows)
        result = _cluster_deduplicate(metrics, eps=0.5)
        # If they cluster together, "good" should survive
        good_row = result[result["hypothesis_id"] == "good"].iloc[0]
        bad_row  = result[result["hypothesis_id"] == "bad"].iloc[0]
        if good_row["is_cluster_redundant"] or bad_row["is_cluster_redundant"]:
            # They were clustered — good must be the representative
            assert not good_row["is_cluster_redundant"], "High-Sharpe hypothesis wrongly marked redundant"

    def test_missing_proxy_columns_skips_clustering(self):
        """If metric columns are absent, return unchanged (no crash)."""
        metrics = pd.DataFrame({"hypothesis_id": ["h1", "h2"], "n": [100, 100]})
        result = _cluster_deduplicate(metrics)
        assert "is_cluster_redundant" in result.columns

    def test_output_length_unchanged(self):
        """Clustering must not drop rows — only marks them."""
        metrics = self._make_metrics(20)
        result = _cluster_deduplicate(metrics)
        assert len(result) == 20

    def test_cluster_eps_parameter_respected(self):
        """Tighter eps → smaller clusters → fewer redundant marks."""
        rows = [
            {"hypothesis_id": f"h{i}", "mean_return_bps": 5.0 + i * 0.1,
             "t_stat": 1.67, "sharpe": 0.25, "hit_rate": 0.505}
            for i in range(10)
        ]
        metrics = pd.DataFrame(rows)
        result_tight = _cluster_deduplicate(metrics, eps=0.01)
        result_loose = _cluster_deduplicate(metrics, eps=2.0)
        assert result_loose["is_cluster_redundant"].sum() >= result_tight["is_cluster_redundant"].sum()


# ---------------------------------------------------------------------------
# 3.4 — SEQUENCE trigger seeding from weak-signal pairs
# ---------------------------------------------------------------------------


class TestSequenceSeeding:
    """Phase 3.4: SEQUENCE proposals generated from weak-signal event pairs."""

    def _make_tested_regions(self, events_data) -> pd.DataFrame:
        rows = []
        for evt, mean_bps in events_data:
            rows.append({
                "event_type": evt,
                "mean_return_bps": mean_bps,
                "gate_promo_statistical": "false",
                "trigger_type": "EVENT",
                "run_id": "run_1",
            })
        return pd.DataFrame(rows)

    def test_weak_signal_pairs_found(self, tmp_path):
        ctrl = _make_ctrl(tmp_path)
        tested = self._make_tested_regions([
            ("EVT_A", 3.5), ("EVT_B", 2.1), ("EVT_C", 1.8),
        ])
        with patch(
            "project.research.campaign_controller.read_memory_table",
            return_value=tested,
        ):
            pairs = ctrl._find_weak_signal_event_pairs()
        assert len(pairs) > 0

    def test_negative_return_events_excluded(self, tmp_path):
        ctrl = _make_ctrl(tmp_path)
        tested = self._make_tested_regions([
            ("EVT_POS", 3.5), ("EVT_NEG", -2.0),
        ])
        with patch(
            "project.research.campaign_controller.read_memory_table",
            return_value=tested,
        ):
            pairs = ctrl._find_weak_signal_event_pairs()
        # Only EVT_POS qualifies — need at least 2 events to pair
        assert len(pairs) == 0

    def test_promoted_events_excluded(self, tmp_path):
        ctrl = _make_ctrl(tmp_path)
        # Promoted events should NOT seed sequences (they already passed)
        tested = pd.DataFrame([
            {"event_type": "PROMOTED", "mean_return_bps": 10.0,
             "gate_promo_statistical": "true", "trigger_type": "EVENT", "run_id": "r1"},
            {"event_type": "WEAK", "mean_return_bps": 2.0,
             "gate_promo_statistical": "false", "trigger_type": "EVENT", "run_id": "r1"},
        ])
        with patch(
            "project.research.campaign_controller.read_memory_table",
            return_value=tested,
        ):
            pairs = ctrl._find_weak_signal_event_pairs()
        # Only WEAK qualifies — need 2 events, so no pairs
        assert len(pairs) == 0

    def test_pairs_capped_at_five(self, tmp_path):
        ctrl = _make_ctrl(tmp_path)
        # 6 events → up to 15 pairs, but capped at 5
        tested = self._make_tested_regions([
            (f"EVT_{i}", float(i + 1)) for i in range(6)
        ])
        with patch(
            "project.research.campaign_controller.read_memory_table",
            return_value=tested,
        ):
            pairs = ctrl._find_weak_signal_event_pairs()
        assert len(pairs) <= 5

    def test_sequence_proposal_structure(self, tmp_path):
        ctrl = _make_ctrl(tmp_path, scan_trigger_types=["SEQUENCE"])
        mem = _empty_mem()
        tested = self._make_tested_regions([
            ("EVT_A", 3.5), ("EVT_B", 2.1),
        ])
        with patch(
            "project.research.campaign_controller.read_memory_table",
            return_value=tested,
        ):
            result = ctrl._step_scan_sequences(mem)
        if result is not None:
            assert result["trigger_space"]["allowed_trigger_types"] == ["SEQUENCE"]
            seq = result["trigger_space"]["sequences"]
            assert "include" in seq
            assert "max_gaps_bars" in seq
            assert 6 in seq["max_gaps_bars"]

    def test_no_sequences_when_no_weak_signals(self, tmp_path):
        ctrl = _make_ctrl(tmp_path)
        mem = _empty_mem()
        with patch(
            "project.research.campaign_controller.read_memory_table",
            return_value=pd.DataFrame(),
        ):
            result = ctrl._step_scan_sequences(mem)
        assert result is None


# ---------------------------------------------------------------------------
# 3.5 — FEATURE_PREDICATE trigger activation
# ---------------------------------------------------------------------------


class TestFeaturePredicateActivation:
    """Phase 3.5: FEATURE_PREDICATE proposals from search_space.yaml."""

    def test_predicates_loaded_from_search_space(self, tmp_path):
        ctrl = _make_ctrl(tmp_path)
        preds = ctrl._load_search_space_predicates()
        # Real spec/search_space.yaml has 8+ predicates
        assert len(preds) >= 8

    def test_predicates_have_required_keys(self, tmp_path):
        ctrl = _make_ctrl(tmp_path)
        preds = ctrl._load_search_space_predicates()
        for p in preds:
            assert "feature" in p, f"Predicate missing 'feature': {p}"
            assert "operator" in p, f"Predicate missing 'operator': {p}"
            assert "threshold" in p, f"Predicate missing 'threshold': {p}"

    def test_feature_predicate_proposal_built(self, tmp_path):
        ctrl = _make_ctrl(tmp_path, scan_trigger_types=["FEATURE_PREDICATE"])
        mem = _empty_mem()
        with patch(
            "project.research.campaign_controller.read_memory_table",
            return_value=pd.DataFrame(),
        ):
            result = ctrl._step_scan_feature_predicates(mem)
        assert result is not None
        assert result["trigger_space"]["allowed_trigger_types"] == ["FEATURE_PREDICATE"]
        preds = result["trigger_space"]["feature_predicates"]["include"]
        assert isinstance(preds, list)
        assert len(preds) >= 1

    def test_feature_predicate_batch_capped_at_eight(self, tmp_path):
        ctrl = _make_ctrl(tmp_path)
        mem = _empty_mem()
        with patch(
            "project.research.campaign_controller.read_memory_table",
            return_value=pd.DataFrame(),
        ):
            result = ctrl._step_scan_feature_predicates(mem)
        if result is not None:
            preds = result["trigger_space"]["feature_predicates"]["include"]
            assert len(preds) <= 8

    def test_feature_predicate_no_zero_lags(self, tmp_path):
        ctrl = _make_ctrl(tmp_path)
        mem = _empty_mem()
        with patch(
            "project.research.campaign_controller.read_memory_table",
            return_value=pd.DataFrame(),
        ):
            result = ctrl._step_scan_feature_predicates(mem)
        if result is not None:
            assert 0 not in result["evaluation"]["entry_lags"]

    def test_feature_predicate_scan_treats_memory_key_as_already_tested(self, tmp_path):
        ctrl = _make_ctrl(tmp_path, scan_trigger_types=["FEATURE_PREDICATE"])
        mem = _empty_mem()
        tested = pd.DataFrame(
            [
                {
                    "event_type": "FEATURE_IMBALANCE_ZSCORE_2_0",
                    "trigger_type": "FEATURE_PREDICATE",
                }
            ]
        )
        with patch(
            "project.research.campaign_controller.read_memory_table",
            return_value=tested,
        ):
            result = ctrl._step_scan_feature_predicates(mem)
        if result is not None:
            preds = result["trigger_space"]["feature_predicates"]["include"]
            assert {"feature": "imbalance_zscore", "operator": ">", "threshold": 2.0} not in preds

    def test_scan_trigger_types_includes_feature_predicate(self, tmp_path):
        ctrl = _make_ctrl(
            tmp_path,
            scan_trigger_types=["EVENT", "STATE", "TRANSITION", "FEATURE_PREDICATE"],
        )
        assert "FEATURE_PREDICATE" in ctrl.config.scan_trigger_types

    def test_missing_search_space_returns_empty(self, tmp_path):
        ctrl = _make_ctrl(tmp_path)
        ctrl._search_space_path = tmp_path / "nonexistent.yaml"
        preds = ctrl._load_search_space_predicates()
        assert preds == []


# ---------------------------------------------------------------------------
# _build_proposal trigger_type routing
# ---------------------------------------------------------------------------


class TestBuildProposalTriggerTypes:
    """Verify _build_proposal routes each trigger type correctly."""

    def test_event_trigger_structure(self, tmp_path):
        ctrl = _make_ctrl(tmp_path)
        p = ctrl._build_proposal(
            events=["EVT_A1"],
            templates=["mean_reversion"],
            horizons=[12],
            description="test",
            promotion_enabled=False,
            date_scope=("2024-01-01", "2024-01-31"),
            trigger_type="EVENT",
        )
        ts = p["trigger_space"]
        assert ts["allowed_trigger_types"] == ["EVENT"]
        assert "events" in ts
        assert "EVT_A1" in ts["events"]["include"]

    def test_state_trigger_structure(self, tmp_path):
        ctrl = _make_ctrl(tmp_path)
        p = ctrl._build_proposal(
            events=[],
            templates=["mean_reversion"],
            horizons=[12],
            description="test",
            promotion_enabled=False,
            date_scope=("2024-01-01", "2024-03-31"),
            trigger_type="STATE",
            states=["HIGH_VOL_REGIME", "LOW_VOL_REGIME"],
        )
        ts = p["trigger_space"]
        assert ts["allowed_trigger_types"] == ["STATE"]
        assert ts["states"]["include"] == ["HIGH_VOL_REGIME", "LOW_VOL_REGIME"]

    def test_transition_trigger_structure(self, tmp_path):
        ctrl = _make_ctrl(tmp_path)
        p = ctrl._build_proposal(
            events=[],
            templates=["mean_reversion"],
            horizons=[12],
            description="test",
            promotion_enabled=False,
            date_scope=("2024-01-01", "2024-03-31"),
            trigger_type="TRANSITION",
            transitions=[{"from_state": "LOW_VOL_REGIME", "to_state": "HIGH_VOL_REGIME"}],
        )
        ts = p["trigger_space"]
        assert ts["allowed_trigger_types"] == ["TRANSITION"]
        assert ts["transitions"]["include"][0]["from_state"] == "LOW_VOL_REGIME"

    def test_feature_predicate_trigger_structure(self, tmp_path):
        ctrl = _make_ctrl(tmp_path)
        pred = {"feature": "imbalance_zscore", "operator": ">", "threshold": 2.0}
        p = ctrl._build_proposal(
            events=[],
            templates=["mean_reversion"],
            horizons=[12],
            description="test",
            promotion_enabled=False,
            date_scope=("2024-01-01", "2024-03-31"),
            trigger_type="FEATURE_PREDICATE",
            feature_predicates=[pred],
        )
        ts = p["trigger_space"]
        assert ts["allowed_trigger_types"] == ["FEATURE_PREDICATE"]
        assert ts["feature_predicates"]["include"][0] == pred

    def test_sequence_trigger_structure(self, tmp_path):
        ctrl = _make_ctrl(tmp_path)
        p = ctrl._build_proposal(
            events=[],
            templates=["mean_reversion"],
            horizons=[12],
            description="test",
            promotion_enabled=False,
            date_scope=("2024-01-01", "2024-03-31"),
            trigger_type="SEQUENCE",
            sequences={"include": [["EVT_A", "EVT_B"]], "max_gaps_bars": [6, 12]},
        )
        ts = p["trigger_space"]
        assert ts["allowed_trigger_types"] == ["SEQUENCE"]
        assert ts["sequences"]["max_gaps_bars"] == [6, 12]
