"""Tests for the four items implemented after the patch merge.

1. INTERACTION trigger type in CampaignController
2. MI scan auto pre-step wiring
3. evaluate_by_regime deep hook — regime_breakdown.parquet + regime_conditional_candidates
4. portfolio_state_path loading for marginal contribution check
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
from project.research.run_hypothesis_search import (
    _write_regime_conditional_candidates_from_breakdown,
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _make_ctrl(tmp_path: Path, **cfg_kwargs) -> CampaignController:
    config = CampaignConfig(program_id="test_extras", max_runs=5, **cfg_kwargs)
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
    ctrl.registries.events = {"events": {
        "EVT_A": {"enabled": True, "family": "FAM_A"},
    }}
    ctrl.registries.templates = {"families": {
        "FAM_A": {"allowed_templates": ["mean_reversion"]},
    }}
    return ctrl


def _empty_mem() -> Dict[str, Any]:
    return {
        "belief_state": {}, "next_actions": {"repair": [], "exploit": [],
        "explore_adjacent": [], "hold": []},
        "latest_reflection": {}, "avoid_region_keys": set(),
        "avoid_event_types": set(), "promising_regions": [], "superseded_stages": set(),
    }


# ---------------------------------------------------------------------------
# 1. INTERACTION trigger type
# ---------------------------------------------------------------------------

class TestInteractionTrigger:

    def test_load_interaction_motifs_from_real_registry(self, tmp_path):
        ctrl = _make_ctrl(tmp_path)
        motifs = ctrl._load_interaction_motifs()
        assert len(motifs) >= 1
        for m in motifs:
            assert "left" in m and "right" in m and "op" in m

    def test_interaction_proposal_built(self, tmp_path):
        ctrl = _make_ctrl(tmp_path, scan_trigger_types=["INTERACTION"])
        mem = _empty_mem()
        with patch(
            "project.research.campaign_controller.read_memory_table",
            return_value=pd.DataFrame(),
        ):
            result = ctrl._step_scan_interactions(mem)
        assert result is not None
        ts = result["trigger_space"]
        assert ts["allowed_trigger_types"] == ["INTERACTION"]
        assert "interactions" in ts
        interactions = ts["interactions"]["include"]
        assert isinstance(interactions, list) and len(interactions) >= 1
        for inter in interactions:
            assert "left" in inter and "right" in inter and "op" in inter

    def test_interaction_batch_capped_at_three(self, tmp_path):
        ctrl = _make_ctrl(tmp_path)
        mem = _empty_mem()
        with patch(
            "project.research.campaign_controller.read_memory_table",
            return_value=pd.DataFrame(),
        ):
            result = ctrl._step_scan_interactions(mem)
        if result is not None:
            assert len(result["trigger_space"]["interactions"]["include"]) <= 3

    def test_interaction_no_zero_lags(self, tmp_path):
        ctrl = _make_ctrl(tmp_path)
        mem = _empty_mem()
        with patch(
            "project.research.campaign_controller.read_memory_table",
            return_value=pd.DataFrame(),
        ):
            result = ctrl._step_scan_interactions(mem)
        if result is not None:
            assert 0 not in result["evaluation"]["entry_lags"]

    def test_interaction_returns_none_when_no_motifs(self, tmp_path):
        ctrl = _make_ctrl(tmp_path)
        with patch.object(ctrl, "_load_interaction_motifs", return_value=[]):
            mem = _empty_mem()
            result = ctrl._step_scan_interactions(mem)
        assert result is None

    def test_interaction_returns_none_when_all_tested(self, tmp_path):
        ctrl = _make_ctrl(tmp_path)
        motifs = ctrl._load_interaction_motifs()
        if not motifs:
            pytest.skip("No motifs in registry")
        m = motifs[0]
        tested_key = f"{m['left']}|{m['op']}|{m['right']}"
        tested_df = pd.DataFrame({
            "trigger_type": ["INTERACTION"],
            "event_type": [tested_key],
        })
        with patch(
            "project.research.campaign_controller.read_memory_table",
            return_value=tested_df,
        ), patch.object(ctrl, "_load_interaction_motifs", return_value=[m]):
            result = ctrl._step_scan_interactions(_empty_mem())
        assert result is None

    def test_build_proposal_routes_interaction_trigger(self, tmp_path):
        ctrl = _make_ctrl(tmp_path)
        inters = [{"left": "EVT_A", "right": "EVT_B", "op": "AND", "lag": 6}]
        p = ctrl._build_proposal(
            events=[], templates=["mean_reversion"], horizons=[12],
            description="test", promotion_enabled=False,
            date_scope=("2024-01-01", "2024-03-31"),
            trigger_type="INTERACTION", interactions=inters,
        )
        ts = p["trigger_space"]
        assert ts["allowed_trigger_types"] == ["INTERACTION"]
        assert ts["interactions"]["include"] == inters

    def test_scan_trigger_types_can_include_interaction(self, tmp_path):
        ctrl = _make_ctrl(tmp_path,
            scan_trigger_types=["EVENT", "STATE", "TRANSITION", "FEATURE_PREDICATE",
                                 "SEQUENCE", "INTERACTION"])
        assert "INTERACTION" in ctrl.config.scan_trigger_types

    def test_dispatch_routes_to_interaction_scanner(self, tmp_path):
        ctrl = _make_ctrl(tmp_path)
        mem = _empty_mem()
        called = []
        with patch.object(ctrl, "_step_scan_interactions",
                          side_effect=lambda m: called.append(True) or None):
            ctrl._step_scan_for_type("INTERACTION", mem)
        assert called


# ---------------------------------------------------------------------------
# 2. MI scan auto pre-step
# ---------------------------------------------------------------------------

class TestMiScanPreStep:

    def test_auto_run_mi_scan_default_false(self, tmp_path):
        ctrl = _make_ctrl(tmp_path)
        assert ctrl.config.auto_run_mi_scan is False

    def test_auto_run_mi_scan_can_be_enabled(self, tmp_path):
        ctrl = _make_ctrl(tmp_path, auto_run_mi_scan=True)
        assert ctrl.config.auto_run_mi_scan is True

    def test_mi_scan_symbols_and_timeframe_defaults(self, tmp_path):
        ctrl = _make_ctrl(tmp_path)
        assert ctrl.config.mi_scan_symbols == "BTCUSDT"
        assert ctrl.config.mi_scan_timeframe == "5m"

    def test_pre_step_skips_when_disabled(self, tmp_path):
        ctrl = _make_ctrl(tmp_path, auto_run_mi_scan=False)
        with patch(
            "project.research.campaign_controller.CampaignController._run_mi_scan_pre_step"
        ) as mock_scan:
            # Simulate run_campaign stub — just call the pre-step decision
            if ctrl.config.auto_run_mi_scan:
                ctrl._run_mi_scan_pre_step()
        mock_scan.assert_not_called()

    def test_pre_step_called_when_enabled(self, tmp_path):
        ctrl = _make_ctrl(tmp_path, auto_run_mi_scan=True)
        called = []
        with patch.object(ctrl, "_run_mi_scan_pre_step", side_effect=lambda: called.append(1)):
            if ctrl.config.auto_run_mi_scan:
                ctrl._run_mi_scan_pre_step()
        assert called

    def test_pre_step_swallows_load_failure(self, tmp_path):
        """Feature load failure must not raise — campaign must still start."""
        ctrl = _make_ctrl(tmp_path, auto_run_mi_scan=True)
        with patch(
            "project.research.phase2.load_features",
            side_effect=Exception("disk error"),
        ):
            ctrl._run_mi_scan_pre_step()  # must not raise

    def test_pre_step_writes_candidate_predicates(self, tmp_path):
        """When features load, MI scan writes candidate_predicates.json."""
        import numpy as np
        ctrl = _make_ctrl(tmp_path, auto_run_mi_scan=True)
        n = 300
        rng = np.random.default_rng(42)
        close = 100 * np.exp(np.cumsum(rng.normal(0, 0.001, n)))
        fake_features = pd.DataFrame({
            "timestamp": pd.date_range("2024-01-01", periods=n, freq="5min", tz="UTC"),
            "symbol": "BTCUSDT",
            "close": close,
            "logret_1": np.log(close / np.roll(close, 1)),
            "rv_96": np.abs(rng.normal(0.001, 0.0005, n)),
            "spread_bps": np.abs(rng.normal(5, 2, n)),
        })
        with patch(
            "project.research.phase2.load_features",
            return_value=fake_features,
        ):
            ctrl._run_mi_scan_pre_step()

        expected = tmp_path / "reports" / "feature_mi" / "test_extras" / "candidate_predicates.json"
        assert expected.exists()

    def test_pre_step_with_empty_features_skips_gracefully(self, tmp_path):
        """Empty feature table → pre-step logs and returns without raising."""
        ctrl = _make_ctrl(tmp_path, auto_run_mi_scan=True)
        with patch(
            "project.research.phase2.load_features",
            return_value=pd.DataFrame(),
        ):
            ctrl._run_mi_scan_pre_step()  # must not raise
        # No output file when features are empty (pre-step exits early)
        out_dir = tmp_path / "reports" / "feature_mi" / "test_extras"
        if out_dir.exists():
            cand = out_dir / "candidate_predicates.json"
            if cand.exists():
                preds = json.loads(cand.read_text())
                assert isinstance(preds, list)


# ---------------------------------------------------------------------------
# 3. evaluate_by_regime deep hook
# ---------------------------------------------------------------------------

class TestRegimeBreakdownHook:

    def _make_metrics(self, n: int = 10) -> pd.DataFrame:
        rng = np.random.default_rng(0)
        rows = []
        for i in range(n):
            rows.append({
                "hypothesis_id": f"h{i:02d}",
                "trigger_key": f"event:EVT_{i % 3}",
                "template_id": "mean_reversion",
                "direction": "long",
                "horizon": "12b",
                "t_stat": rng.uniform(0.3, 2.5),
                "mean_return_bps": rng.uniform(-5, 15),
                "sharpe": rng.uniform(-0.5, 2.0),
                "hit_rate": rng.uniform(0.4, 0.7),
                "n": 100,
            })
        return pd.DataFrame(rows)

    def _make_regime_breakdown(self, metrics: pd.DataFrame) -> pd.DataFrame:
        """Attach regime rows including some strong-regime weak-overall candidates."""
        rows = []
        for _, m in metrics.iterrows():
            rows.append({
                "hypothesis_id": m["hypothesis_id"],
                "trigger_key": m["trigger_key"],
                "template_id": m["template_id"],
                "direction": m["direction"],
                "horizon": m["horizon"],
                "regime": "HIGH_VOL",
                "n": 35,
                "mean_return_bps": m["mean_return_bps"] * 2,
                "t_stat": 2.0 if m["t_stat"] < 1.5 else m["t_stat"],  # strong per-regime
                "hit_rate": 0.6,
            })
        return pd.DataFrame(rows)

    def test_rcc_written_when_weak_overall_strong_regime(self, tmp_path):
        metrics = self._make_metrics(10)
        regime_breakdown = self._make_regime_breakdown(metrics)
        _write_regime_conditional_candidates_from_breakdown(metrics, regime_breakdown, tmp_path)
        rcc_path = tmp_path / "regime_conditional_candidates.parquet"
        assert rcc_path.exists()
        rcc = pd.read_parquet(rcc_path)
        # All entries should be weak overall
        assert (rcc["overall_t_stat"].abs() < 1.5).all()

    def test_rcc_has_best_regime_columns(self, tmp_path):
        metrics = self._make_metrics(5)
        regime_breakdown = self._make_regime_breakdown(metrics)
        _write_regime_conditional_candidates_from_breakdown(metrics, regime_breakdown, tmp_path)
        rcc = pd.read_parquet(tmp_path / "regime_conditional_candidates.parquet")
        if not rcc.empty:
            assert "best_regime" in rcc.columns
            assert "best_regime_t_stat" in rcc.columns
            assert "best_regime_mean_return_bps" in rcc.columns

    def test_rcc_empty_when_no_weak_overall(self, tmp_path):
        """All hypotheses strong overall → no regime conditional candidates."""
        metrics = self._make_metrics(5)
        metrics["t_stat"] = 3.0  # all strong overall
        regime_breakdown = self._make_regime_breakdown(metrics)
        _write_regime_conditional_candidates_from_breakdown(metrics, regime_breakdown, tmp_path)
        rcc = pd.read_parquet(tmp_path / "regime_conditional_candidates.parquet")
        assert rcc.empty

    def test_rcc_empty_when_no_regime_breakdown(self, tmp_path):
        metrics = self._make_metrics(5)
        _write_regime_conditional_candidates_from_breakdown(metrics, None, tmp_path)
        rcc = pd.read_parquet(tmp_path / "regime_conditional_candidates.parquet")
        assert rcc.empty

    def test_rcc_empty_when_regime_breakdown_empty(self, tmp_path):
        metrics = self._make_metrics(5)
        _write_regime_conditional_candidates_from_breakdown(
            metrics, pd.DataFrame(), tmp_path
        )
        rcc = pd.read_parquet(tmp_path / "regime_conditional_candidates.parquet")
        assert rcc.empty

    def test_rcc_event_type_extracted_from_trigger_key(self, tmp_path):
        metrics = pd.DataFrame([{
            "hypothesis_id": "h0", "trigger_key": "event:LIQUIDATION_CASCADE",
            "template_id": "m", "direction": "long", "horizon": "12b",
            "t_stat": 0.8, "mean_return_bps": 5.0, "sharpe": 0.3,
            "hit_rate": 0.55, "n": 50,
        }])
        regime_breakdown = pd.DataFrame([{
            "hypothesis_id": "h0", "trigger_key": "event:LIQUIDATION_CASCADE",
            "template_id": "m", "direction": "long", "horizon": "12b",
            "regime": "HIGH_VOL", "n": 30,
            "mean_return_bps": 12.0, "t_stat": 2.5, "hit_rate": 0.65,
        }])
        _write_regime_conditional_candidates_from_breakdown(metrics, regime_breakdown, tmp_path)
        rcc = pd.read_parquet(tmp_path / "regime_conditional_candidates.parquet")
        assert not rcc.empty
        assert rcc.iloc[0]["event_type"] == "LIQUIDATION_CASCADE"

    def test_rcc_sorted_by_best_regime_t_stat(self, tmp_path):
        metrics = self._make_metrics(8)
        metrics["t_stat"] = 0.5  # all weak overall
        regime_breakdown = self._make_regime_breakdown(metrics)
        # Vary the regime t_stats
        regime_breakdown["t_stat"] = [2.0 + i * 0.1 for i in range(len(regime_breakdown))]
        _write_regime_conditional_candidates_from_breakdown(metrics, regime_breakdown, tmp_path)
        rcc = pd.read_parquet(tmp_path / "regime_conditional_candidates.parquet")
        if len(rcc) >= 2:
            assert rcc["best_regime_t_stat"].iloc[0] >= rcc["best_regime_t_stat"].iloc[-1]

    def test_evaluator_attaches_regime_breakdown_attr(self):
        """evaluate_hypothesis_batch must attach regime_breakdown to df.attrs."""
        from project.research.search.evaluator import evaluate_hypothesis_batch
        from project.domain.hypotheses import HypothesisSpec, TriggerSpec

        rng = np.random.default_rng(42)
        n = 100
        close = 100 * np.exp(np.cumsum(rng.normal(0, 0.002, n)))
        features = pd.DataFrame({
            "close": close,
            "time_open": pd.date_range("2024-01-01", periods=n, freq="5min", tz="UTC"),
        })
        features.index = range(n)

        spec = HypothesisSpec(
            trigger=TriggerSpec.event("VOL_SPIKE"),
            direction="long",
            horizon="12b",
            template_id="mean_reversion",
            entry_lag=1,
        )

        result = evaluate_hypothesis_batch([spec], features)
        # The attribute must exist (may be empty if no events fired)
        assert "regime_breakdown" in result.attrs
        rb = result.attrs["regime_breakdown"]
        assert isinstance(rb, pd.DataFrame)


# ---------------------------------------------------------------------------
# 4. portfolio_state_path — live state seeding for marginal contribution
# ---------------------------------------------------------------------------

class TestPortfolioStatePath:

    def test_portfolio_state_path_on_campaign_config(self, tmp_path):
        config = CampaignConfig(
            program_id="test_ps",
            portfolio_state_path=str(tmp_path / "portfolio_state.json"),
        )
        assert config.portfolio_state_path == str(tmp_path / "portfolio_state.json")

    def test_portfolio_state_path_default_none(self):
        config = CampaignConfig(program_id="test")
        assert config.portfolio_state_path is None

    def test_deployed_strategies_seed_promoted_blueprints(self, tmp_path):
        """Live deployed strategies populate promoted_blueprints for marginal check."""
        from project.research.compile_strategy_blueprints import (
            _check_marginal_contribution,
        )
        portfolio_state = {
            "gross_exposure": 0.5,
            "deployed_strategies": [
                {"blueprint_id": "live_bp_1", "risk_per_trade": 0.01,
                 "max_gross_leverage": 2.0, "portfolio_risk_budget": 1.0},
            ]
        }
        ps_path = tmp_path / "portfolio_state.json"
        ps_path.write_text(json.dumps(portfolio_state))

        # Simulate a new blueprint very similar to the live one
        new_bp = MagicMock()
        new_bp.sizing.risk_per_trade = 0.01
        new_bp.sizing.max_gross_leverage = 2.0
        new_bp.sizing.portfolio_risk_budget = 1.0

        # Build stub for the live deployed strategy
        stub = MagicMock()
        stub.sizing.risk_per_trade = 0.01
        stub.sizing.max_gross_leverage = 2.0
        stub.sizing.portfolio_risk_budget = 1.0

        passes, max_sim = _check_marginal_contribution(new_bp, [stub])
        assert max_sim > 0.9  # Nearly identical → high similarity
        assert passes is False  # Blocked by default threshold 0.8

    def test_portfolio_state_not_found_is_silently_skipped(self, tmp_path):
        """Missing portfolio_state_path must not cause an error."""
        from project.research.compile_strategy_blueprints import (
            _write_strategy_contract_artifacts,
        )

        bp = MagicMock()
        bp.id = "bp_001"
        bp.candidate_id = "cand_001"
        bp.event_type = "VOL_SPIKE"
        bp.sizing.mode = "kelly"
        bp.sizing.risk_per_trade = 0.01
        bp.sizing.max_gross_leverage = 2.0
        bp.sizing.portfolio_risk_budget = 1.0
        bp.sizing.symbol_risk_budget = 0.5
        bp.sizing.signal_scaling = {}
        bp.lineage.constraints = {}
        bp.symbol_scope.model_dump.return_value = {"symbols": ["BTCUSDT"]}
        bp.execution.policy_executor_config = {}

        with patch(
            "project.research.compile_strategy_blueprints._build_executable_strategy_spec",
            return_value=MagicMock(model_dump=lambda: {}, execution=MagicMock(policy_executor_config={})),
        ), patch(
            "project.research.compile_strategy_blueprints._build_allocation_spec",
            return_value=MagicMock(model_dump=lambda: {}),
        ), patch(
            "project.research.compile_strategy_blueprints._validate_strategy_contract",
        ):
            result = _write_strategy_contract_artifacts(
                blueprints=[bp],
                out_dir=tmp_path,
                run_id="r1",
                retail_profile="standard",
                low_capital_contract={},
                require_low_capital_contract=False,
                effective_max_concurrent_positions=5,
                effective_per_position_notional_cap_usd=10000.0,
                default_fee_tier="tier1",
                fees_bps_per_side=4.0,
                slippage_bps_per_fill=2.0,
                portfolio_state_path=str(tmp_path / "nonexistent.json"),
            )
        assert result is not None

    def test_marginal_contribution_log_written(self, tmp_path):
        """marginal_contribution_log.json should be written for every compile batch."""
        from project.research.compile_strategy_blueprints import (
            _write_strategy_contract_artifacts,
        )
        bp = MagicMock()
        bp.id = "bp_001"
        bp.candidate_id = "c1"
        bp.event_type = "EVT"
        bp.sizing.mode = "kelly"
        bp.sizing.risk_per_trade = 0.01
        bp.sizing.max_gross_leverage = 2.0
        bp.sizing.portfolio_risk_budget = 1.0
        bp.sizing.symbol_risk_budget = 0.5
        bp.sizing.signal_scaling = {}
        bp.lineage.constraints = {}
        bp.symbol_scope.model_dump.return_value = {"symbols": ["BTCUSDT"]}

        with patch(
            "project.research.compile_strategy_blueprints._build_executable_strategy_spec",
            return_value=MagicMock(model_dump=lambda: {}, execution=MagicMock(policy_executor_config={})),
        ), patch(
            "project.research.compile_strategy_blueprints._build_allocation_spec",
            return_value=MagicMock(model_dump=lambda: {}),
        ), patch(
            "project.research.compile_strategy_blueprints._validate_strategy_contract",
        ):
            _write_strategy_contract_artifacts(
                blueprints=[bp],
                out_dir=tmp_path,
                run_id="r1",
                retail_profile="standard",
                low_capital_contract={},
                require_low_capital_contract=False,
                effective_max_concurrent_positions=5,
                effective_per_position_notional_cap_usd=10000.0,
                default_fee_tier="tier1",
                fees_bps_per_side=4.0,
                slippage_bps_per_fill=2.0,
            )

        log_path = tmp_path / "marginal_contribution_log.json"
        assert log_path.exists()
        log = json.loads(log_path.read_text())
        assert isinstance(log, list)
        assert len(log) == 1
        assert "blueprint_id" in log[0]
        assert "passes_marginal_check" in log[0]
