# Research Calibration Baseline

This file records the current default research-quality calibration after the architecture and service-boundary cleanup.

## Current Defaults

### Drift Thresholds

- `max_phase2_candidate_count_delta_abs = 10`
- `max_phase2_survivor_count_delta_abs = 2.0`
- `max_phase2_zero_eval_rows_increase = 0`
- `max_phase2_survivor_q_value_increase = 0.05`
- `max_phase2_survivor_estimate_bps_drop = 3.0`
- `max_promotion_promoted_count_delta_abs = 2`
- `max_reject_reason_shift_abs = 3`
- `max_edge_tradable_count_delta_abs = 2.0`
- `max_edge_candidate_count_delta_abs = 2.0`
- `max_edge_after_cost_positive_validation_count_delta_abs = 2.0`
- `max_edge_median_resolved_cost_bps_delta_abs = 0.25`
- `max_edge_median_expectancy_bps_delta_abs = 0.25`

### Sample-Quality Policy

- `standard`
  - `min_validation_n_obs = 2`
  - `min_test_n_obs = 2`
  - `min_total_n_obs = 10`
- `synthetic`
  - `min_validation_n_obs = 1`
  - `min_test_n_obs = 1`
  - `min_total_n_obs = 4`

## Rationale

- Candidate and promotion drift limits are now tuned for small-to-medium research runs rather than broad architectural smoke tests.
- `zero_eval_rows` remains strict because any increase usually indicates a split-quality regression rather than a harmless fluctuation.
- `standard` discovery is stricter than `synthetic` because synthetic truth workflows intentionally tolerate smaller sample sizes while still requiring both validation and test coverage.
- The defaults are intentionally conservative enough to catch silent policy drift, but not so tight that every minor run-to-run fluctuation becomes an enforced failure.

## Empirical Note

This workspace currently has usable synthetic `phase2_diagnostics.json` artifacts but not matching `promotion_diagnostics.json` artifacts for the same run families, so the empirical calibration basis is phase-2 heavy.

Observed local synthetic search-engine runs include:

- `synthetic_2025_full_year_v3` / `v4` / `v5` / `v6` / `v7` / `v8` / `v9`
- `synthetic_2025_stress_crash`
- `synthetic_2025_stress_crash_v4`
- `synthetic_2021_bull_v10`

On those older search-engine diagnostics, `bridge_candidates_rows` ranged from `0` to `34`, with the biggest jumps occurring when the discovery profile moved from `standard` to `synthetic` and the search space widened. Because of that, candidate-count drift should only be enforced for like-for-like comparisons. The comparison service now suppresses candidate-count threshold enforcement when the baseline and candidate differ in `discovery_profile` or `search_spec`.

One real promotion comparison pair is now available locally:

- baseline: `synthetic_2025_full_year_v4`
- candidate: `synthetic_2025_full_year_v6`
- promotion command: relaxed research-mode promotion on existing exported edge candidates with `allow_discovery_promotion=1`, `min_events=8`, `require_hypothesis_audit=0`, and `allow_missing_negative_controls=1`

Observed result for that pair:

- promotion candidates: `12` vs `12`
- promoted count: `0` vs `0`
- rejected count: `12` vs `12`
- primary fail gate: `gate_promo_cost_survival` for all candidates in both runs
- comparison assessment: `pass`

That pair is useful as a smoke calibration point for the promotion comparison path, but it is not yet a discriminating threshold-tuning sample because both runs collapse to the same rejection pattern.

Two additional local derived promotion runs now provide a discriminating policy-change sample:

- baseline: `synthetic_2025_full_year_v4_promo_relaxed`
- candidate: `synthetic_2025_full_year_v4_promo_relaxed_dsr0`
- promotion change: identical exported edge candidates, but the candidate run relaxed `min_dsr` from the normal research floor to `0`

Observed result for that pair:

- promotion candidates: `12` vs `12`
- promoted count: `0` vs `12`
- rejected count: `12` vs `0`
- baseline primary reject reason: `failed_gate_promo_dsr`
- comparison assessment: `warn`
- dominant violations:
  - promoted-count delta exceeded the default threshold
  - reject-reason shift for `failed_gate_promo_dsr` exceeded the default threshold

That pair is now the canonical empirical warning-case for promotion-policy drift. It demonstrates that the current thresholds stay quiet on like-for-like runs, but fire when a DSR policy relaxation turns an all-reject set into an all-promoted set.

The previously documented medium `run_all` edge-drift warning-case is no longer valid after the zero-direction discovery fix. The corrected like-for-like pair now passes:

- baseline: `e2e_synth_medium_base`
- candidate: `e2e_synth_medium_candidate`
- pipeline change: like-for-like medium synthetic runs after the event-level direction-policy fix

Observed result for that pair:

- edge candidate count: `6` vs `6`
- tradable count: `0` vs `0`
- comparison assessment: `pass`

That corrected pass case is important because it shows the old warning was being driven by stale or invalid event-level artifacts rather than legitimate run drift.

One real corrected-artifact pair now provides the canonical natural warning-case:

- baseline: `e2e_synth_medium_base`
- candidate: `e2e_synth_medium_continuation_only`
- policy change: event-level Phase 2 rerun on the same medium synthetic data, but restricted to `--templates continuation`

Observed result for that pair:

- edge candidate count: `6` vs `3`
- tradable count: `0` vs `0`
- comparison assessment: `warn`
- dominant violation:
  - `edge candidate_count delta=-3` exceeded the default edge threshold `2.0`

That pair is now the canonical empirical warning-case for corrected event-level policy drift. It is useful because the warning is generated from a legitimate discovery-policy change on top of trustworthy artifacts, not from the removed zero-direction fallback bug.

Reproduction through the standard pipeline entrypoint is now straightforward because `run_all` forwards `--templates` to the event-level Phase 2 stages. Template-only runs now fan out across the canonical event chain when `--run_phase2_conditional 1` is enabled, rather than silently collapsing to the parser default `VOL_SHOCK`. A live verification run in this workspace confirmed that the planned stages include `analyze_events__VOL_SPIKE_5m` and `phase2_conditional_hypotheses__VOL_SPIKE_5m`.

In this workspace, the fixed fanout behavior was verified with:

```bash
PYTHONPATH=. python3 project/pipelines/run_all.py \
  --run_id e2e_synth_medium_continuation_only_runall_fanout_fix \
  --symbols BTCUSDT,ETHUSDT,SOLUSDT \
  --start 2026-01-01 \
  --end 2026-01-31 \
  --templates continuation \
  --run_phase2_conditional 1 \
  --skip_ingest_ohlcv 1 \
  --skip_ingest_funding 1 \
  --skip_ingest_spot_ohlcv 1 \
  --run_bridge_eval_phase2 0 \
  --run_edge_candidate_universe 0 \
  --run_candidate_promotion 0 \
  --run_expectancy_analysis 0 \
  --run_expectancy_robustness 0 \
  --run_recommendations_checklist 0 \
  --run_strategy_blueprint_compiler 0 \
  --run_strategy_builder 0 \
  --run_profitable_selector 0 \
  --run_interaction_lift 0 \
  --run_promotion_audit 0 \
  --run_edge_registry_update 0 \
  --run_campaign_memory_update 0 \
  --run_naive_entry_eval 0 \
  --run_discovery_quality_summary 0 \
  --funding_scale decimal
```

The canonical live comparison recipe now uses the corrected planner, search, and edge-export path:

```bash
PYTHONPATH=. python3 project/pipelines/run_all.py \
  --run_id e2e_synth_medium_continuation_only_runall_searchfix_live \
  --symbols BTCUSDT,ETHUSDT,SOLUSDT \
  --start 2026-01-01 \
  --end 2026-01-31 \
  --templates continuation \
  --run_phase2_conditional 1 \
  --skip_ingest_ohlcv 1 \
  --skip_ingest_funding 1 \
  --skip_ingest_spot_ohlcv 1 \
  --run_expectancy_analysis 0 \
  --funding_scale decimal \
  --research_compare_baseline_run_id e2e_synth_medium_base \
  --research_compare_drift_mode warn
```

Observed result for that live `run_all` pair:

- run status: `success`
- comparison assessment: `warn`
- comparison report: `data/reports/research_comparison/e2e_synth_medium_continuation_only_runall_searchfix_live/vs_e2e_synth_medium_base/research_run_comparison.json`
- dominant violations:
  - `phase2 candidate_count delta=3400` exceeded the default threshold `10.0`
  - `phase2 survivor_count delta=3400` exceeded the default threshold `2.0`
  - `edge candidate_count delta=-6` exceeded the default threshold `2.0`
  - `edge median_resolved_cost_bps delta=-6.0` exceeded the default threshold `0.25`
  - `edge median_expectancy_bps delta=6.0` exceeded the default threshold `0.25`

That live pair is now the canonical operational warning-case because it proves the postflight comparison path works on a full `run_all` execution, not just on manually rerun derived stages. The thresholds remain unchanged after this check because the local evidence is internally consistent:

- corrected like-for-like runs still pass
- meaningful promotion-policy changes still warn
- meaningful edge-policy changes still warn

Direction policy is now explicit for registry-style event discovery:

- directional events can resolve sign from event-type defaults or event-data tokens such as `up` / `down`
- unresolved non-directional event families fail closed and emit no registry candidates
- research-mode fallback event files can still be returned as non-promotable training-only data, but that path is logged as informational and carried in diagnostics rather than treated as a warning-level surprise

## Retuning Rule

Retune these defaults only after reviewing at least a few baseline-vs-candidate comparisons from real runs. If you change them:

1. Update the constants in [`project/research/services/run_comparison_service.py`](/home/tstuv/workspace/trading/EDGEE/project/research/services/run_comparison_service.py) and [`project/research/services/candidate_discovery_service.py`](/home/tstuv/workspace/trading/EDGEE/project/research/services/candidate_discovery_service.py).
2. Keep the parser defaults in [`project/pipelines/pipeline_planning.py`](/home/tstuv/workspace/trading/EDGEE/project/pipelines/pipeline_planning.py) in sync.
3. Refresh the tests that pin the default calibration behavior.
