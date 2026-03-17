import numpy as np
from project.research.promotion.core import evaluate_row

def base_kwargs():
    return {
        'hypothesis_index': {},
        'negative_control_summary': {},
        'max_q_value': 0.10,
        'min_events': 20,
        'min_stability_score': 0.1,
        'min_sign_consistency': 0.5,
        'min_cost_survival_ratio': 0.5,
        'max_negative_control_pass_rate': 0.2,
        'min_tob_coverage': 0.5,
        'require_hypothesis_audit': False,
        'allow_missing_negative_controls': True,
        'min_net_expectancy_bps': 0.0,
        'require_retail_viability': False,
        'require_low_capital_viability': False,
    }

def passing_row():
    return {
        'event_type': 'VOL_SHOCK',
        'n_events': 50,
        'q_value': 0.01,
        'event_is_descriptive': False,
        'event_is_trade_trigger': True,
        'gate_tob_coverage': True,
        'gate_net_expectancy': True,
        'gate_cost_budget': True,
        'gate_turnover': True,
        'tob_coverage': 0.8,
        'net_expectancy_bps': 12.0,
        'sharpe_ratio': 2.0,
        'effective_cost_bps': 2.0,
        'turnover_proxy_mean': 0.5,
        'gate_after_cost_positive': True,
        'gate_after_cost_stressed_positive': True,
        'baseline_expectancy_bps': 5.0,
        'pass_shift_placebo': True,
        'pass_random_entry_placebo': True,
        'pass_direction_reversal_placebo': True,
        'gate_stability': True,
        'gate_delay_robustness': True,
        'effect_shrunk_state': 1.0,
        'std_return': 1.0,
        'val_t_stat': 1.0,
        'oos1_t_stat': 1.0,
        'test_t_stat': 1.0,
        'gate_bridge_microstructure': True,
        'gate_delayed_entry_stress': True,
        'control_pass_rate': 0.05,
        'q_value_by': 0.05,
        'q_value_cluster': 0.05,
        'run_mode': 'research',
        'gate_bridge_low_capital_viability': True,
        'low_capital_viability_score': 0.9,
    }

res = evaluate_row(row=passing_row(), **base_kwargs())
print(f"Decision: {res.get('promotion_decision')}")
print(f"Reject Reason: {res.get('reject_reason')}")
print(f"Promotion Fail Gate Primary: {res.get('promotion_fail_gate_primary')}")
