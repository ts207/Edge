from __future__ import annotations

import json
from types import SimpleNamespace

import pandas as pd
import pytest

import project.research.services.promotion_service as svc


def _run_promotion(tmp_path, **overrides):
    config = svc.PromotionConfig(
        run_id='r1',
        symbols='',
        out_dir=tmp_path / 'promotions',
        max_q_value=0.10,
        min_events=100,
        min_stability_score=0.05,
        min_sign_consistency=0.67,
        min_cost_survival_ratio=0.75,
        max_negative_control_pass_rate=0.01,
        min_tob_coverage=0.60,
        require_hypothesis_audit=True,
        allow_missing_negative_controls=False,
        require_multiplicity_diagnostics=False,
        min_dsr=0.5,
        max_overlap_ratio=0.80,
        max_profile_correlation=0.90,
        allow_discovery_promotion=False,
        program_id='default_program',
        retail_profile='capital_constrained',
        objective_name='',
        objective_spec=None,
        retail_profiles_spec=None,
    )
    if overrides:
        config = svc.PromotionConfig(**(config.__dict__ | overrides))
    return svc.execute_promotion(config)


def test_run_promotion_service_smoke(monkeypatch, tmp_path):
    monkeypatch.setattr(svc, 'get_data_root', lambda: tmp_path)
    monkeypatch.setattr(svc, 'load_run_manifest', lambda run_id: {'run_mode': 'confirmatory', 'discovery_profile': 'standard'})
    monkeypatch.setattr(svc, 'resolve_objective_profile_contract', lambda **kwargs: SimpleNamespace(
        min_net_expectancy_bps=5.0,
        max_fee_plus_slippage_bps=10.0,
        max_daily_turnover_multiple=5.0,
        require_retail_viability=False,
        require_low_capital_contract=False,
    ))
    monkeypatch.setattr(svc, 'ontology_spec_hash', lambda root: 'hash')
    monkeypatch.setattr(svc, '_load_gates_spec', lambda root: {'promotion_confirmatory_gates': {}})
    monkeypatch.setattr(svc, '_load_negative_control_summary', lambda run_id: {})
    monkeypatch.setattr(svc, '_load_dynamic_min_events_by_event', lambda run_id: {})

    cand_path = tmp_path / 'reports' / 'edge_candidates' / 'r1'
    cand_path.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{
        'candidate_id': 'cand_1', 'event_type': 'VOL_SHOCK', 'q_value': 0.01, 'confirmatory_locked': True,
        'frozen_spec_hash': 'hash'
    }]).to_csv(cand_path / 'edge_candidates_normalized.csv', index=False)

    audit_df = pd.DataFrame([{
        'candidate_id': 'cand_1', 'event_type': 'VOL_SHOCK', 'promotion_decision': 'promoted',
        'promotion_track': 'standard', 'promotion_metrics_trace': '{}', 'evidence_bundle_json': json.dumps({'candidate_id': 'cand_1', 'event_type': 'VOL_SHOCK', 'promotion_decision': {'promotion_status': 'promoted', 'promotion_track': 'standard'}, 'sample_definition': {'n_events': 100}, 'effect_estimates': {}, 'uncertainty_estimates': {}, 'stability_tests': {}, 'falsification_results': {}, 'cost_robustness': {}, 'multiplicity_adjustment': {}})
    }])
    promoted_df = pd.DataFrame([{'candidate_id': 'cand_1', 'event_type': 'VOL_SHOCK', 'status': 'PROMOTED'}])
    monkeypatch.setattr(svc, 'promote_candidates', lambda **kwargs: (audit_df.copy(), promoted_df.copy(), {'promoted': 1}))
    monkeypatch.setattr(svc, 'build_promotion_statistical_audit', lambda **kwargs: audit_df.copy())
    monkeypatch.setattr(svc, 'stabilize_promoted_output_schema', lambda promoted_df, audit_df: promoted_df.copy())

    result = _run_promotion(tmp_path)
    assert result.exit_code == 0
    assert any((tmp_path / 'promotions').glob('promotion_statistical_audit.*'))
    assert any((tmp_path / 'promotions').glob('promoted_candidates.*'))
    assert (tmp_path / 'promotions' / 'evidence_bundles.jsonl').exists()
    assert "primary_reject_reason" in result.audit_df.columns
    assert "failed_gate_count" in result.audit_df.columns
    assert "decision_summary" in result.diagnostics


def test_annotate_promotion_audit_decisions_derives_failed_stage_summary():
    audit_df = pd.DataFrame(
        [
            {
                "candidate_id": "cand_1",
                "event_type": "VOL_SHOCK",
                "promotion_decision": "rejected",
                "promotion_fail_gate_primary": "gate_promo_stability",
                "promotion_fail_reason_primary": "",
                "reject_reason": "stability_score|negative_control_fail",
                "promotion_metrics_trace": json.dumps(
                    {
                        "statistical": {"passed": True},
                        "stability": {"passed": False},
                        "negative_control": {"passed": False},
                    }
                ),
            },
            {
                "candidate_id": "cand_2",
                "event_type": "VOL_SHOCK",
                "promotion_decision": "promoted",
                "promotion_fail_gate_primary": "",
                "promotion_fail_reason_primary": "",
                "reject_reason": "",
                "promotion_metrics_trace": json.dumps(
                    {
                        "statistical": {"passed": True},
                        "stability": {"passed": True},
                    }
                ),
            },
        ]
    )

    out = svc._annotate_promotion_audit_decisions(audit_df)
    row = out.loc[out["candidate_id"] == "cand_1"].iloc[0]

    assert row["primary_reject_reason"] == "stability_score"
    assert row["failed_gate_count"] == 2
    assert row["failed_gate_list"] == "stability|negative_control"
    assert row["weakest_fail_stage"] == "stability"
    assert row["rejection_classification"] == "scope_mismatch"
    assert row["recommended_next_action"] == "narrow_scope"

    diagnostics = svc._build_promotion_decision_diagnostics(out)
    assert diagnostics["rejected_count"] == 1
    assert diagnostics["primary_fail_gate_counts"]["gate_promo_stability"] == 1
    assert diagnostics["primary_reject_reason_counts"]["stability_score"] == 1
    assert diagnostics["failed_stage_counts"]["negative_control"] == 1
    assert diagnostics["rejection_classification_counts"]["scope_mismatch"] == 1
    assert diagnostics["recommended_next_action_counts"]["narrow_scope"] == 1


def test_classify_rejection_maps_holdout_and_contract_failures():
    holdout = svc._classify_rejection(
        {
            "promotion_fail_gate_primary": "gate_promo_oos_validation",
            "reject_reason": "oos_validation_fail",
        },
        ["oos_validation"],
    )
    contract = svc._classify_rejection(
        {
            "promotion_fail_gate_primary": "gate_promo_contract",
            "reject_reason": "missing_hypothesis_audit",
        },
        [],
    )

    assert holdout == "weak_holdout_support"
    assert svc._recommended_next_action_for_rejection(holdout) == "run_confirmatory"
    assert contract == "contract_failure"
    assert svc._recommended_next_action_for_rejection(contract) == "repair_pipeline"


def test_load_negative_control_summary_returns_empty_dict_on_invalid_json(monkeypatch, tmp_path):
    monkeypatch.setattr(svc, 'get_data_root', lambda: tmp_path)
    path = tmp_path / 'reports' / 'negative_control' / 'r1'
    path.mkdir(parents=True, exist_ok=True)
    (path / 'negative_control_summary.json').write_text('{bad json', encoding='utf-8')

    assert svc._load_negative_control_summary('r1') == {}


def test_read_csv_or_parquet_does_not_swallow_unexpected_runtime_errors(monkeypatch, tmp_path):
    path = tmp_path / 'edge_candidates_normalized.parquet'
    path.write_text('placeholder', encoding='utf-8')

    def _boom(_path):
        raise RuntimeError('parquet engine blew up')

    monkeypatch.setattr(pd, 'read_parquet', _boom)

    with pytest.raises(RuntimeError, match='parquet engine blew up'):
        svc._read_csv_or_parquet(path)


def test_confirmatory_run_missing_lock_column_fails_cleanly(monkeypatch, tmp_path):
    monkeypatch.setattr(svc, 'get_data_root', lambda: tmp_path)
    monkeypatch.setattr(svc, 'load_run_manifest', lambda run_id: {'run_mode': 'confirmatory', 'discovery_profile': 'standard'})
    monkeypatch.setattr(svc, 'resolve_objective_profile_contract', lambda **kwargs: SimpleNamespace(
        min_net_expectancy_bps=5.0,
        max_fee_plus_slippage_bps=10.0,
        max_daily_turnover_multiple=5.0,
        require_retail_viability=False,
        require_low_capital_contract=False,
    ))

    cand_path = tmp_path / 'reports' / 'edge_candidates' / 'r1'
    cand_path.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{
        'candidate_id': 'cand_1',
        'event_type': 'VOL_SHOCK',
        'q_value': 0.01,
        'frozen_spec_hash': 'hash',
    }]).to_csv(cand_path / 'edge_candidates_normalized.csv', index=False)

    result = _run_promotion(tmp_path)
    assert result.exit_code == 1
    assert result.audit_df.empty
    assert result.promoted_df.empty


def test_resolve_promotion_policy_research_relaxes_deploy_only_controls():
    contract = SimpleNamespace(
        min_trade_count=150,
        min_net_expectancy_bps=4.0,
        max_fee_plus_slippage_bps=10.0,
        max_daily_turnover_multiple=4.0,
        require_retail_viability=True,
        require_low_capital_contract=True,
    )
    config = svc.PromotionConfig(
        run_id='r1',
        symbols='',
        out_dir=None,
        max_q_value=0.10,
        min_events=20,
        min_stability_score=0.05,
        min_sign_consistency=0.67,
        min_cost_survival_ratio=0.75,
        max_negative_control_pass_rate=0.01,
        min_tob_coverage=0.60,
        require_hypothesis_audit=True,
        allow_missing_negative_controls=False,
        require_multiplicity_diagnostics=False,
        min_dsr=0.5,
        max_overlap_ratio=0.80,
        max_profile_correlation=0.90,
        allow_discovery_promotion=False,
        program_id='default_program',
        retail_profile='capital_constrained',
        objective_name='',
        objective_spec=None,
        retail_profiles_spec=None,
        promotion_profile='research',
    )

    policy = svc._resolve_promotion_policy(
        config=config,
        contract=contract,
        source_run_mode='production',
        project_root=svc.PROJECT_ROOT.parent,
    )

    assert policy.promotion_profile == 'research'
    assert policy.base_min_events == 20
    assert policy.dynamic_min_events == {}
    assert policy.min_net_expectancy_bps == 1.5
    assert policy.require_retail_viability is False
    assert policy.require_low_capital_viability is False
    assert policy.enforce_baseline_beats_complexity is False
    assert policy.enforce_placebo_controls is False
    assert policy.enforce_timeframe_consensus is False


def test_resolve_promotion_policy_deploy_preserves_contract_and_dynamic_floors(monkeypatch):
    contract = SimpleNamespace(
        min_trade_count=150,
        min_net_expectancy_bps=4.0,
        max_fee_plus_slippage_bps=10.0,
        max_daily_turnover_multiple=4.0,
        require_retail_viability=True,
        require_low_capital_contract=True,
    )
    config = svc.PromotionConfig(
        run_id='r1',
        symbols='',
        out_dir=None,
        max_q_value=0.10,
        min_events=20,
        min_stability_score=0.05,
        min_sign_consistency=0.67,
        min_cost_survival_ratio=0.75,
        max_negative_control_pass_rate=0.01,
        min_tob_coverage=0.60,
        require_hypothesis_audit=True,
        allow_missing_negative_controls=False,
        require_multiplicity_diagnostics=False,
        min_dsr=0.5,
        max_overlap_ratio=0.80,
        max_profile_correlation=0.90,
        allow_discovery_promotion=False,
        program_id='default_program',
        retail_profile='capital_constrained',
        objective_name='',
        objective_spec=None,
        retail_profiles_spec=None,
        promotion_profile='deploy',
    )
    monkeypatch.setattr(svc, '_load_dynamic_min_events_by_event', lambda _root: {'VOL_SHOCK': 300})

    policy = svc._resolve_promotion_policy(
        config=config,
        contract=contract,
        source_run_mode='production',
        project_root=svc.PROJECT_ROOT.parent,
    )

    assert policy.promotion_profile == 'deploy'
    assert policy.base_min_events == 150
    assert policy.dynamic_min_events == {'VOL_SHOCK': 300}
    assert policy.min_net_expectancy_bps == 4.0
    assert policy.require_retail_viability is True
    assert policy.require_low_capital_viability is True
    assert policy.enforce_baseline_beats_complexity is True
