# Research Calibration Baseline

## Phase 2 Defaults

```
max_phase2_candidate_count_delta_abs = 10
max_phase2_survivor_count_delta_abs = 2.0
max_promotion_promoted_count_delta_abs = 2
max_edge_candidate_count_delta_abs = 2.0
max_edge_median_resolved_cost_bps_delta_abs = 0.25
max_edge_median_expectancy_bps_delta_abs = 0.25
min_total_n_obs = 30
min_total_n_obs = 4
```

## Test Profiles

- synthetic_2025_full_year_v4_promo_relaxed_dsr0
- failed_gate_promo_dsr
- e2e_synth_medium_candidate
- e2e_synth_medium_continuation_only

## Run Examples

edge candidate_count delta=-3
e2e_synth_medium_continuation_only_runall_searchfix_live
e2e_synth_medium_continuation_only_runall_fanout_fix

--templates continuation
--run_phase2_conditional 1
PYTHONPATH=. python3 project/pipelines/run_all.py
--skip_ingest_ohlcv 1
--funding_scale decimal
phase2 candidate_count delta=3400
phase2 survivor_count delta=3400
edge candidate_count delta=-6
edge median_resolved_cost_bps delta=-6.0
edge median_expectancy_bps delta=6.0

tradable_count