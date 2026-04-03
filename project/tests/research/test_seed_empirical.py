from __future__ import annotations

import json
from pathlib import Path

from project.research.seed_bootstrap import build_promotion_seed_inventory
from project.research.seed_empirical import run_empirical_seed_pass


def _write_bundle(root: Path, run_id: str, payload: dict) -> None:
    out = root / 'reports' / 'promotions' / run_id
    out.mkdir(parents=True, exist_ok=True)
    (out / 'evidence_bundles.jsonl').write_text(json.dumps(payload) + '\n', encoding='utf-8')


def test_empirical_seed_pass_fails_closed_without_bundle_matches(tmp_path: Path, monkeypatch) -> None:
    docs = tmp_path / 'docs'
    data_root = tmp_path / 'data'
    monkeypatch.setenv('BACKTEST_DATA_ROOT', str(data_root))
    build_promotion_seed_inventory(docs_dir=docs)

    out = run_empirical_seed_pass(docs_dir=docs, inventory_path=docs / 'promotion_seed_inventory.csv')

    rows = json.loads(out['json'].read_text(encoding='utf-8'))
    assert rows
    vol = next(row for row in rows if row['candidate_id'] == 'THESIS_VOL_SHOCK')
    assert vol['matched_bundle_count'] == 0
    assert vol['empirical_decision'] == 'needs_more_evidence'
    assert 'No empirical evidence bundles matched' in out['md'].read_text(encoding='utf-8')


def test_empirical_seed_pass_promotes_candidate_with_valid_bundle(tmp_path: Path, monkeypatch) -> None:
    docs = tmp_path / 'docs'
    data_root = tmp_path / 'data'
    monkeypatch.setenv('BACKTEST_DATA_ROOT', str(data_root))
    build_promotion_seed_inventory(docs_dir=docs)
    _write_bundle(
        data_root,
        'run-volshock',
        {
            'candidate_id': 'cand-volshock-1',
            'event_family': 'VOL_SHOCK',
            'event_type': 'VOL_SHOCK',
            'sample_definition': {'n_events': 150, 'validation_samples': 40, 'test_samples': 35, 'symbol': 'BTCUSDT'},
            'split_definition': {'split_scheme_id': 'chronological'},
            'effect_estimates': {'estimate_bps': 24.5},
            'uncertainty_estimates': {'q_value': 0.04},
            'stability_tests': {'stability_score': 0.11},
            'falsification_results': {
                'negative_control_pass_rate': 0.005,
                'session_transition': {'passed': True},
                'scheduled_window': {'passed': True},
            },
            'cost_robustness': {'net_expectancy_bps': 12.2},
            'multiplicity_adjustment': {'correction_method': 'bh'},
            'metadata': {'has_realized_oos_path': True},
        },
    )

    out = run_empirical_seed_pass(docs_dir=docs, inventory_path=docs / 'promotion_seed_inventory.csv')

    rows = json.loads(out['json'].read_text(encoding='utf-8'))
    vol = next(row for row in rows if row['candidate_id'] == 'THESIS_VOL_SHOCK')
    assert vol['primary_event_id'] == 'VOL_SHOCK'
    assert vol['compat_event_family'] == 'VOL_SHOCK'
    assert vol['matched_bundle_count'] == 1
    assert vol['empirical_decision'] in {'seed_promote', 'paper_candidate'}
    assert int(vol['holdout_quality']) >= 4
    assert int(vol['confounder_handling']) >= 4


def test_empirical_seed_pass_caps_derived_confirmation_to_seed_promote(tmp_path: Path, monkeypatch) -> None:
    docs = tmp_path / 'docs'
    data_root = tmp_path / 'data'
    monkeypatch.setenv('BACKTEST_DATA_ROOT', str(data_root))
    build_promotion_seed_inventory(docs_dir=docs)
    _write_bundle(
        data_root,
        'THESIS_VOL_SHOCK_LIQUIDITY_CONFIRM',
        {
            'candidate_id': 'THESIS_VOL_SHOCK_LIQUIDITY_CONFIRM',
            'event_family': 'VOL_SHOCK',
            'event_type': 'VOL_SHOCK_LIQUIDITY_CONFIRM',
            'sample_definition': {'n_events': 120, 'validation_samples': 60, 'test_samples': 40, 'symbol': 'BTCUSDT'},
            'split_definition': {'split_scheme_id': 'derived_bridge'},
            'effect_estimates': {'estimate_bps': 20.0},
            'uncertainty_estimates': {'q_value': 0.01},
            'stability_tests': {'stability_score': 0.20},
            'falsification_results': {
                'negative_control_pass_rate': 0.0,
                'session_transition': {'passed': True},
                'realized_vol_regime': {'passed': True},
            },
            'cost_robustness': {'net_expectancy_bps': 15.0},
            'metadata': {
                'has_realized_oos_path': True,
                'derived_from_component_evidence': True,
                'thesis_contract_id': 'THESIS_VOL_SHOCK_LIQUIDITY_CONFIRM',
                'thesis_contract_ids': ['THESIS_VOL_SHOCK_LIQUIDITY_CONFIRM'],
            },
        },
    )

    out = run_empirical_seed_pass(docs_dir=docs, inventory_path=docs / 'promotion_seed_inventory.csv', data_root=data_root)
    rows = json.loads(out['json'].read_text(encoding='utf-8'))
    confirm = next(row for row in rows if row['candidate_id'] == 'THESIS_VOL_SHOCK_LIQUIDITY_CONFIRM')
    assert confirm['primary_event_id'] == 'VOL_SHOCK_LIQUIDITY_CONFIRM'
    assert confirm['compat_event_family'] == 'VOL_SHOCK'
    assert confirm['matched_bundle_count'] == 1
    assert confirm['empirical_decision'] == 'seed_promote'
    assert 'direct_pair_event_study_missing' in confirm['evidence_gap_summary']
