# Research Calibration Baseline

This file is a narrative reminder of the current research-comparison defaults and the calibration examples the repository has historically used to reason about drift.

It is not the executable source of truth. The executable controls live in `run_all` flags prefixed with `--research_compare_*`.

## Phase 2 Defaults

These strings are kept explicit because tests assert against them and because they mirror the comparison tolerances operators often look for first.

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

## Related `run_all` Drift Controls

The current CLI surface includes comparison knobs such as:

- `--research_compare_max_phase2_candidate_count_delta_abs`
- `--research_compare_max_phase2_survivor_count_delta_abs`
- `--research_compare_max_promotion_promoted_count_delta_abs`
- `--research_compare_max_edge_candidate_count_delta_abs`
- `--research_compare_max_edge_median_resolved_cost_bps_delta_abs`
- `--research_compare_max_edge_median_expectancy_bps_delta_abs`

Use those flags when a comparison needs tighter or looser tolerances than the repo defaults.

## Test Profiles

- synthetic_2025_full_year_v4_promo_relaxed_dsr0
- failed_gate_promo_dsr
- e2e_synth_medium_candidate
- e2e_synth_medium_continuation_only

These names are preserved because they are historical calibration anchors in the repository conversation and still appear in tests.

## Run Examples and Reminder Strings

The lines below are intentionally preserved verbatim because repository tests assert that they remain documented.

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

## How To Use This File

Use it as a quick memory aid when:

- a research comparison starts drifting unexpectedly
- an operator needs the rough default tolerance posture
- historical calibration examples need to be recognized quickly

Do not update this file casually. If the comparison semantics move materially, update the executable defaults, the tests, and this narrative together.
