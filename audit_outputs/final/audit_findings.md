# Audit Findings

## Executive summary
The repo has real engineering depth, but the audit found repeated false-green patterns where manifests, generated audits, specs, docs, or CI signal success without proving runtime truth. The highest-risk failures cluster around artifact integrity, split/leakage integrity, runtime safety gating, and inconsistent cost/economic semantics. The strongest recurring pattern is contract drift: static registries, docs, and helper tooling often describe or validate a surface that is no longer the one the planner, runtime, or maintained scripts actually use.

## Top 15 verified defects
- Monitor-only runners can still send real flatten orders when the kill-switch fires [critical] (engine_live_runtime)
  Paths: project/scripts/run_live_engine.py, project/live/runner.py, project/live/oms.py, project/configs/live_paper.yaml
  Why: A supposedly non-trading observer can place real venue orders during a stale-feed or health-triggered unwind.
- Strategy packaging stages point at nonexistent wrapper scripts while contract validation still reports the plan valid [critical] (architecture_contracts)
  Paths: project/pipelines/stages/evaluation.py, project/contracts/pipeline_registry.py, project/tests/pipelines/test_stage_registry_contract.py
  Why: A plan can pass the contract layer and then fail only at execution time when Python cannot open the stage script.
- ingest_binance_um_ohlcv converts total fetch failure into a green stage with only missing-archive stats [critical] (pipelines_artifacts)
  Paths: project/pipelines/ingest/ingest_binance_um_ohlcv.py, project/pipelines/execution_engine.py
  Why: The root raw-data producer can go green when no requested market data was actually ingested.
- Alias event ids bypass canonicalization in ontology deconfliction [high] (events_ontology)
  Paths: project/events/ontology_deconfliction.py, project/events/event_aliases.py, project/research/services/regime_effectiveness_service.py, project/tests/events/test_ontology_deconfliction.py
  Why: Equivalent events can survive as separate canonical episodes, corrupting regime routing and episode aggregation.
- Any caller can forge a StrategyResult and reach live trading by flipping strategy_runtime.implemented [high] (engine_live_runtime)
  Paths: project/live/runner.py, project/live/oms.py, project/engine/strategy_executor.py
  Why: Unsafe or fabricated runtime objects can bypass provenance checks and create venue orders.
- Benchmark tools write to two different artifact roots, making direct matrix runs invisible to review tooling [high] (scripts_operator_surface)
  Paths: project/scripts/run_benchmark_matrix.py, project/scripts/run_benchmark_maintenance_cycle.py, project/scripts/show_benchmark_review.py, project/scripts/show_promotion_readiness.py
  Why: An operator can run the documented benchmark path successfully and then fail to discover or compare the result using maintained review tooling.
- Certification mode records strict artifact-safety flags but never enables the environment gates that enforce them [high] (pipelines_artifacts)
  Paths: project/pipelines/run_all_bootstrap.py, project/io/utils.py, project/pipelines/execution_engine.py, project/pipelines/run_all.py
  Why: Certification mode advertises fail-closed artifact isolation while still allowing the default fallback behavior.
- Confirmatory placebo pass/fail can be driven by train rows because placebo frames are not restricted to evaluation splits [high] (research_inference)
  Paths: project/research/services/candidate_discovery_scoring.py
  Why: Discovery-vs-confirmatory separation collapses inside the falsification path.
- Direct experiment-config path accepts zero-lag hypotheses that search validators classify as leakage [high] (specs_configs_validation)
  Paths: project/research/experiment_engine_validators.py, project/research/experiment_engine.py, project/research/search/validation.py, project/configs/experiments/e2e_synth_small.yaml
  Why: The experiment-engine entrypoint can generate same-bar-leakage hypotheses that the core search validator would reject.
- Execution cost units diverge across core, eval, and research paths [high] (core_features_costs)
  Paths: project/core/execution_costs.py, project/eval/cost_model.py, project/research/search/evaluator.py, project/research/phase2_cost_integration.py
  Why: The same fee config produces different after-cost returns depending on the path that computed them.
- Funding carry can make stressed-cost robustness improve as costs are stressed [high] (core_features_costs)
  Paths: project/research/gating.py, project/research/services/candidate_discovery_scoring.py, project/eval/robustness.py
  Why: A cost-stress panel can certify fragile candidates as more robust when stressed harder.
- Funding ingestion records missing coverage but still returns success, allowing partial or empty funding artifacts to masquerade as complete [high] (pipelines_artifacts)
  Paths: project/pipelines/ingest/ingest_binance_um_funding.py, project/pipelines/features/build_features.py, project/contracts/pipeline_registry.py
  Why: A run can appear funding-aware while silently dropping funding-derived signal content.
- Incubation or paper gating is ineffective and graduation status is inverted [high] (engine_live_runtime)
  Paths: project/live/runner.py, project/portfolio/incubation.py, project/live/oms.py
  Why: Incubating strategies are not truly kept out of live trading, and explicit graduation status is misreported.
- Monitor-only startup still requires a tradable Binance account and trading credentials [high] (engine_live_runtime)
  Paths: project/scripts/run_live_engine.py, project/tests/scripts/test_run_live_engine.py, project/tests/contracts/test_live_environment_config_contract.py
  Why: There is no safe read-only deployment tier despite the naming and config contract.
- PR CI tiers do not gate several high-risk deterministic surfaces before merge [high] (reliability_tests_ci)
  Paths: .github/workflows/tier1.yml, .github/workflows/tier2.yml, .github/workflows/tier3.yml, Makefile
  Why: Breakage in smoke orchestration, synthetic-truth wiring, and PIT invariants can merge without PR-time detection.

## Top likely defects
- Confirmatory candidate matching only preserves economic identity when optional fields happen to be present [medium] (research_inference)
  Paths: project/research/services/confirmatory_candidate_service.py
  Why: Two runs can match as structurally continuous without proving they used the same cost contract.
- Promotion output assembly can silently drop malformed evidence bundles without failing closed [medium] (research_inference)
  Paths: project/research/services/promotion_service.py
  Why: A promoted candidate can survive while its evidence bundle artifact is missing or malformed.
- The repo marks after-cost outputs as including funding carry even when actual carry coverage can be zero [medium] (core_features_costs)
  Paths: project/research/services/candidate_discovery_service.py, project/research/services/candidate_discovery_scoring.py, project/research/gating.py
  Why: Consumers can assume net expectancy already includes carry economics when the observed coverage is actually zero.
- Artifact regeneration script hardcodes python3 instead of the project interpreter [low] (scripts_operator_surface)
  Paths: project/scripts/regenerate_artifacts.sh, docs/08_TESTING_AND_MAINTENANCE.md
  Why: Artifact regeneration can fail or drift on hosts where python3 is not the project environment.

## Top architectural debt items
- Experiment-engine registry consistency check is effectively unreachable because it reads the wrong registry shapes [medium] (specs_configs_validation)
  Paths: project/research/experiment_engine.py, project/research/experiment_engine_schema.py, project/configs/registries/events.yaml, project/configs/registries/templates.yaml
  Why: The runtime safeguard is a no-op, so drift can be caught in one test stack but never by the direct runtime path.
- Main blueprint compiler bypasses its own selection helper and ignores several exposed gating arguments [medium] (strategy_compilation)
  Paths: project/research/compile_strategy_blueprints.py, project/tests/pipelines/research/test_compile_blueprint_module_wiring.py
  Why: Operator-facing CLI knobs appear to control compilation but do not change the output set.
- Research helper integrate_execution_costs is broken and does not call the shared core utility correctly [medium] (core_features_costs)
  Paths: project/research/cost_integration.py, project/core/execution_costs.py
  Why: A purported shared research integration path fails immediately and cannot share semantics with the maintained core path.
- Stage contracts are enforced by naming and glob patterns rather than executable or artifact proof [medium] (architecture_contracts)
  Paths: project/contracts/pipeline_registry.py, project/tests/pipelines/test_stage_registry_contract.py
  Why: High-leverage failures survive planning and contract checks until runtime or later artifact review.
- System-map ownership points to services, but run_all actually executes wrappers and CLI modules [medium] (architecture_contracts)
  Paths: project/contracts/stage_dag.py, project/contracts/system_map.py, project/pipelines/run_all.py, project/pipelines/research/phase2_search_engine.py
  Why: The declared boundary map is not the real orchestration graph, which hides ownership and upgrade risk.
- Legacy memory rebuild scripts are hardcoded to one synthetic run and mutate persistent memory tables with no controls [low] (scripts_operator_surface)
  Paths: project/scripts/rebuild_memory.py, project/scripts/rebuild_memory_v2.py, docs/04_COMMANDS_AND_ENTRY_POINTS.md
  Why: They are operator-confusing legacy surfaces that can overwrite persistent memory state for one hardcoded program.
- cost_profiles and conditioning_intersections are declared in search specs but have no runtime consumers [low] (specs_configs_validation)
  Paths: spec/search_space.yaml, spec/search/search_full.yaml, spec/search/search_phase1.yaml, spec/search/search_phase2.yaml
  Why: Operator-facing knobs appear authoritative but currently do nothing.

## Top missing tests
- Synthetic-truth validation in CI is mostly artifact-plumbing validation, not full inference-chain validation [high] (reliability_tests_ci)
  Paths: project/scripts/validate_synthetic_detector_truth.py, project/scripts/run_golden_synthetic_discovery.py, project/tests/smoke/test_golden_synthetic_discovery.py, project/tests/synthetic_truth/assertions/engine.py
  Why: A stale or fabricated report can satisfy CI without proving detector inference worked on the synthetic input.
- PIT and promotion safety helper modules exist but are entirely outside test and CI coverage [medium] (reliability_tests_ci)
  Paths: project/reliability/promotion_gate.py, project/reliability/temporal_lint.py, .github/workflows/tier1.yml, .github/workflows/tier2.yml
  Why: Either critical PIT/promotion safety guards are unverified, or dead code creates a false sense of protection.

## Docs/specs/code contradictions
- README says `docs/generated` is authoritative, but the checked-in set is incomplete and `project/scripts/build_system_map.py --check` fails.
- `project/contracts/pipeline_registry.py` still describes legacy phase-2 stages that `project/pipelines/stages/research.py` no longer schedules.
- `spec/events/canonical_event_registry.yaml` is still used by `project/scripts/ontology_consistency_audit.py`, while runtime uses `spec/events/event_registry_unified.yaml`.
- `project/configs/registries/search_limits.yaml` advertises zero-lag defaults while proposal and search validation code reject zero lag.
- `spec/states/state_families.yaml` allows `carry_state=neutral`, but the compiled runtime context map sourced from `spec/grammar/state_registry.yaml` rejects it.
- `spec/ontology/templates/template_registry.yaml` declares `[1,2,3]` default entry lags, but `project/domain/models.py` still falls back to `(1,2)`.
- `docs/04_COMMANDS_AND_ENTRY_POINTS.md` lists `edge-live-engine` without documenting the required `EDGE_*` environment contract.

## Stale artifact / false-green paths
- `project/pipelines/features/build_features.py` can finalize `success` with `outputs=[]` and no per-symbol results.
- `project/pipelines/ingest/ingest_binance_um_ohlcv.py` can finalize `success` even when all monthly fetches fail.
- `project/pipelines/pipeline_provenance.py` can upgrade a failed run to success by seeing terminal stage manifests, without checking output existence.
- `project/runtime/invariants.py::run_runtime_postflight_audit` can pass malformed event rows because it skips real normalization.
- `project/scripts/ontology_consistency_audit.py` leaves `failures=[]` while emitting 70 missing state source events.

## Three strongest "looks green but is unsafe" paths
- Certification mode writes strict flags into `run_manifest.json` but does not set the env vars that actually enforce strict run-scoped reads and required stage manifests.
- The live configs are labeled `monitor_only`, yet kill-switch unwind paths can still submit real reduce-only venue orders.
- Experiment configs and search defaults can admit `entry_lag=0` or misclassify horizon-crossing events while still flowing through green validation/planning paths.

## Three strongest "docs say X, code does Y" contradictions
- Docs/registry describe legacy `phase2_conditional_hypotheses` and `bridge_evaluate_phase2`; the planner actually emits `phase2_search_engine`.
- Docs present `docs/generated` as authoritative; code/tests tolerate missing generated inventory and failed `--check` generation.
- Docs list `edge-live-engine` as maintained without surfacing the real `EDGE_*` env and deploy-contract prerequisites that startup code requires.

## Maturity ranking
- architecture: 2/5
- statistical integrity: 1/5
- artifact discipline: 1/5
- runtime safety: 1/5
- economic realism: 2/5
- test adequacy: 2/5
- operator usability: 2/5
