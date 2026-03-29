# Remediation Plan

## Stop-the-bleeding fixes
- Make `project/live/runner.py` and `project/live/oms.py` refuse all venue mutation in `monitor_only`, including kill-switch unwind paths.
- Make `project/contracts/pipeline_registry.py` reject missing stage scripts and fix `project/pipelines/stages/evaluation.py` to point at real strategy-packaging entrypoints.
- Make `project/pipelines/ingest/ingest_binance_um_ohlcv.py` and `project/pipelines/features/build_features.py` fail or warn on zero produced artifacts, and require non-empty successful outputs.
- Make `project/pipelines/pipeline_provenance.py` and `project/runtime/invariants.py` validate real output artifacts before returning success.
- Remove zero-lag defaults from `project/configs/registries/search_limits.yaml` and reject zero-lag experiment configs in `project/research/experiment_engine_validators.py`.

Validation after each fix:
- Re-run the targeted unit/regression tests plus one minimal end-to-end plan/run that exercises the touched surface.
- Add a negative test that reproduces the original false-green path and asserts it now fails closed.

## Inference integrity fixes
- Rework `project/research/search/evaluator.py` to classify/drop events by realized event window rather than entry bar only.
- Fix `project/research/validation/falsification.py` placebo timestamps to shift by bar duration or bar index.
- Restrict confirmatory placebo gating in `project/research/services/candidate_discovery_scoring.py` to evaluation rows only.
- Standardize entry-lag validation across proposal, experiment-engine, and search validator paths.

Validation after each fix:
- Add boundary-crossing horizon tests, placebo timestamp semantics tests, and train-vs-eval placebo isolation tests.
- Re-run `project/tests/research/*` plus a small search-plan canary with known split boundaries.

## Runtime safety fixes
- Require validated runtime provenance for `submit_strategy_result_async()` inputs in `project/live/runner.py`.
- Fix `project/portfolio/incubation.py` semantics and enforce incubation/paper routing at the OMS boundary.
- Update `project/live/runner.py::on_order_fill` / `project/live/state.py` so safety-critical logic sees local fill state before the next exchange snapshot.
- Normalize runtime events before `project/runtime/invariants.py::run_runtime_postflight_audit` evaluates them.

Validation after each fix:
- Add monitor-only no-order tests, forged-StrategyResult rejection tests, fill-to-state-store accounting tests, and malformed-row postflight tests.
- Re-run `project/tests/live/*`, `project/tests/runtime/*`, and a replay/postflight canary.

## Maintainability fixes
- Collapse spec/config loading onto one authoritative path for default lags, context labels, and family/template consistency.
- Remove or govern dead/legacy surfaces: `project/research/cost_integration.py`, undocumented mutator scripts, legacy memory rebuild scripts, and unsupported search-spec knobs.
- Replace nondeterministic `hash()` clustering in `project/research/compile_strategy_blueprints.py` with a stable key.
- Round-trip the full Blueprint lineage in `project/strategy/dsl/normalize.py`.

Validation after each fix:
- Add compiled-registry parity tests, unsupported-knob schema checks, multi-process determinism tests, and Blueprint lineage round-trip tests.

## Operator workflow fixes
- Unify benchmark writer/reader roots under one shared path resolver.
- Make `project/scripts/run_researcher_verification.py` use `project/artifacts/catalog.py` compatibility helpers.
- Document the full `edge-live-engine` env contract and remove the dead-end default config.
- Collapse or clearly separate `clean_data.py` and `clean_data.sh` semantics.
- Make `project/scripts/regenerate_artifacts.sh` use the repo interpreter rather than raw `python3`.

Validation after each fix:
- Add benchmark discoverability integration tests, nested phase-2 verification tests, live-engine fail-fast UX tests, and cleaner dry-run parity tests.

## Top 5 highest-leverage fixes
1. Enforce artifact truth before stage/run success (`build_features`, OHLCV ingest, reconciliation, postflight audit).
2. Remove runtime monitor-only/order-submission loopholes and provenance gaps in live trading.
3. Eliminate zero-lag and horizon-boundary leakage across proposal, experiment-engine, and evaluator paths.
4. Standardize cost/carry semantics across core, search, eval, bridge, and confirmatory paths.
5. Unify spec/config authority for entry lags, context labels, and registry consistency checks.
