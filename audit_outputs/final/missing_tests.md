# Missing Tests

## Missing deterministic canaries
- A monitor-only live-runtime canary that proves no venue order can be emitted on kill-switch or startup paths.
- A certification-mode pipeline canary that proves strict run-scoped reads and required stage-manifest enforcement are actually enabled.
- A synthetic-truth end-to-end detector canary that runs the real detector path and validates the real emitted report without monkeypatching.
- A search-boundary canary that proves horizon-crossing events do not count as validation rows.
- A benchmark discoverability canary that proves default matrix output is visible to review/readiness tools.

## Weak fixtures
- `project/configs/experiments/e2e_synth_small.yaml` currently encodes zero-lag search values that the core search validator rejects.
- Synthetic-truth smoke tests use fake pipeline runners and monkeypatched validators, so the fixture proves summary wiring more than inference.
- Live-engine CLI/default-config fixtures do not encode the real `EDGE_*` environment contract.

## Misleading tests
- `project/tests/pipelines/test_stage_registry_contract.py` treats missing strategy-wrapper scripts as valid contract surfaces.
- `project/tests/pipelines/test_run_manifest_reconciliation.py` encodes success promotion from terminal manifests without output-existence checks.
- `project/tests/smoke/test_golden_synthetic_discovery.py` passes with a fake pipeline and monkeypatched truth validator.
- `project/tests/eval/*` still protect legacy eval modules more strongly than the active `project/research/validation/*` path.
- `project/tests/smoke/test_promotion_smoke.py` still carries stale commentary about a defect that appears fixed in current runtime behavior.

## CI blind spots
- Pull requests only run tier1; tier2 smoke/replay coverage is main-only and tier3 full-suite coverage is nightly/manual.
- PR CI does not run a PIT canary, a real synthetic-truth inference canary, or the public CLI smoke surface with non-default flags.
- Docs/generated inventory and artifact-compatibility checks are weaker than the docs imply.

## Minimum tests needed to close the highest-risk gaps
- `project/tests/live/test_runner_monitor_only_no_orders.py`: monitor_only kill-switch and startup must never hit the exchange client.
- `project/tests/pipelines/test_successful_stage_outputs_required.py`: any successful stage manifest must declare non-empty existing outputs.
- `project/tests/research/test_horizon_boundary_split_integrity.py`: boundary-crossing horizons must not count as validation-safe observations.
- `project/tests/research/test_placebo_shift_semantics.py`: placebo timestamps must shift by bar duration or bar index, not previous-row timestamp reuse.
- `project/tests/specs/test_zero_lag_rejected_everywhere.py`: proposal defaults, experiment configs, and search validators must all reject lag 0.
- `project/tests/strategy_dsl/test_blueprint_lineage_round_trip.py`: all lineage fields survive Blueprint serialization/rebuild.
- `project/tests/eval/test_cost_semantics_alignment.py`: one fee config yields one agreed after-cost value across core/search/eval paths.
- `project/tests/smoke/test_real_synthetic_truth_detector_canary.py`: real detector inference on a narrow synthetic scenario.
