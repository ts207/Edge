# Issue Ledger

## architecture_contracts:01 - Phase-2 contract registry still describes legacy conditional and bridge stages that the planner no longer schedules
- Agent: architecture_contracts
- Severity: high
- Confidence: verified
- Category: contract_integrity
- Affected: project/contracts/pipeline_registry.py, project/pipelines/stages/research.py, project/pipelines/research/README.md, project/tests/pipelines/test_pipeline_discovery_mode.py
- Evidence: project/contracts/pipeline_registry.py maps phase2_discovery to phase2_conditional_hypotheses* and bridge_evaluate_phase2*, but project/pipelines/stages/research.py appends phase2_search_engine instead, and project/tests/pipelines/test_pipeline_discovery_mode.py asserts the legacy stages are absent.
- Why it matters: Governance/docs describe a discovery chain that does not actually execute, so operator expectations and contract audits can be wrong before runtime starts.
- Validation: Inspect build_research_stages in project/pipelines/stages/research.py and compare its emitted names to STAGE_FAMILY_REGISTRY in project/contracts/pipeline_registry.py.
- Remediation: Either remove legacy conditional/bridge stages from the registry/docs or restore explicit scheduling paths and end-to-end planner tests.

## architecture_contracts:02 - Strategy packaging stages point at nonexistent wrapper scripts while contract validation still reports the plan valid
- Agent: architecture_contracts
- Severity: critical
- Confidence: verified
- Category: correctness
- Affected: project/pipelines/stages/evaluation.py, project/contracts/pipeline_registry.py, project/tests/pipelines/test_stage_registry_contract.py
- Evidence: project/pipelines/stages/evaluation.py schedules project/pipelines/research/compile_strategy_blueprints.py and select_profitable_strategies.py, but those wrapper files do not exist. validate_stage_plan_contract() in project/contracts/pipeline_registry.py only checks glob patterns, and the corresponding test treats those missing paths as valid.
- Why it matters: A plan can pass the contract layer and then fail only at execution time when Python cannot open the stage script.
- Validation: Build evaluation stages with run_strategy_blueprint_compiler=1 and run_profitable_selector=1, then check Path.exists() for the emitted script paths and compare with validate_stage_plan_contract().
- Remediation: Point the planner and registry at real implementations under project/research/* or restore the missing wrappers, then make the registry validator reject nonexistent scripts.

## architecture_contracts:03 - README declares docs/generated authoritative, but required generated artifacts are missing and build_system_map --check fails
- Agent: architecture_contracts
- Severity: high
- Confidence: verified
- Category: artifact_integrity
- Affected: README.md, docs/generated/, project/scripts/build_system_map.py, project/scripts/regenerate_artifacts.sh
- Evidence: README lists docs/generated/system_map.* and event ontology artifacts as authoritative. The audited tree lacks several of them, and project/scripts/build_system_map.py --check fails because docs/generated/system_map.{md,json} are absent.
- Why it matters: Governance-facing generated artifacts are incomplete and not reproducible from the checked-in regeneration path, so artifact trust is lower than the docs claim.
- Validation: List docs/generated/* and compare with README.md, then run project/scripts/build_system_map.py --format both --check.
- Remediation: Narrow the documented generated surface or commit and continuously check the full declared set in CI.

## architecture_contracts:04 - System-map ownership points to services, but run_all actually executes wrappers and CLI modules
- Agent: architecture_contracts
- Severity: medium
- Confidence: verified
- Category: architecture
- Affected: project/contracts/stage_dag.py, project/contracts/system_map.py, project/pipelines/run_all.py, project/pipelines/research/phase2_search_engine.py, project/research/cli/promotion_cli.py
- Evidence: project/contracts/stage_dag.py says phase2_discovery and promotion belong to candidate_discovery_service and promotion_service, but run_all traverses wrapper modules under project/pipelines/research/* and CLI adapters before or instead of those services.
- Why it matters: The declared boundary map is not the real orchestration graph, which hides ownership and upgrade risk.
- Validation: Trace imports from project/pipelines/run_all.py through stage wrappers and compare them with owner modules in project/contracts/stage_dag.py.
- Remediation: Either make wrappers call services directly as the canonical surface or update the stage_dag/system_map to reflect the actual wrapper chain.

## architecture_contracts:05 - Stage contracts are enforced by naming and glob patterns rather than executable or artifact proof
- Agent: architecture_contracts
- Severity: medium
- Confidence: verified
- Category: maintainability
- Affected: project/contracts/pipeline_registry.py, project/tests/pipelines/test_stage_registry_contract.py
- Evidence: validate_stage_plan_contract() only verifies stage names and path globs. It does not check file existence, importability, or declared outputs, and tests reinforce that weak contract.
- Why it matters: High-leverage failures survive planning and contract checks until runtime or later artifact review.
- Validation: Feed validate_stage_plan_contract() a stage tuple whose path matches the allowed glob but points to no real file.
- Remediation: Add existence/import checks and at least one artifact-level smoke assertion per stage family.

## research_inference:01 - Search evaluator counts validation events whose forward-return horizon exits in the test split
- Agent: research_inference
- Severity: high
- Confidence: verified
- Category: statistical_integrity
- Affected: project/research/search/search_feature_utils.py, project/research/search/evaluator.py
- Evidence: search_feature_utils assigns split_label by row timestamp only, and evaluate_hypothesis_batch() classifies observations from the entry bar label even when the realized forward-return window crosses into test bars.
- Why it matters: Holdout statistics can incorporate future test data while still being labeled as validation, biasing discovery and promotion evidence.
- Validation: Create a synthetic feature frame with an event near the validation/test boundary and a long horizon, then inspect validation_n_obs/test_n_obs from evaluate_hypothesis_batch().
- Remediation: Use event-window-aware split assignment or drop events whose realized horizon crosses a split boundary.

## research_inference:02 - Shift placebo construction uses the previous event timestamp instead of a true bar-offset timestamp
- Agent: research_inference
- Severity: high
- Confidence: verified
- Category: statistical_integrity
- Affected: project/research/validation/falsification.py, project/research/services/candidate_discovery_scoring.py
- Evidence: generate_placebo_events() uses ts.shift(shift_bars), which reuses earlier timestamps instead of adding a bar-duration offset.
- Why it matters: The placebo no longer represents a bar-shift null and can duplicate real event timing structure.
- Validation: Call generate_placebo_events() on a simple timestamp series and compare output timestamps to a true one-bar time offset.
- Remediation: Shift by bar-duration or bar index, not by previous-row timestamp reuse.

## research_inference:03 - Confirmatory placebo pass/fail can be driven by train rows because placebo frames are not restricted to evaluation splits
- Agent: research_inference
- Severity: high
- Confidence: verified
- Category: statistical_integrity
- Affected: project/research/services/candidate_discovery_scoring.py
- Evidence: _build_confirmatory_evidence() filters the observed frame to evaluation rows, but _placebo_pass() is fed full placebo frames and ignores their split labels.
- Why it matters: Discovery-vs-confirmatory separation collapses inside the falsification path.
- Validation: Construct an eval-only observed frame and a train-only placebo frame, then call _placebo_pass() or _build_confirmatory_evidence() and observe the train placebo drives the result.
- Remediation: Filter placebo frames to evaluation rows before placebo gating.

## research_inference:04 - Run comparison treats explicit zero-valued split knobs as unavailable instead of mismatches
- Agent: research_inference
- Severity: high
- Confidence: verified
- Category: contract_integrity
- Affected: project/research/services/run_comparison_service.py
- Evidence: _build_run_comparison_compatibility() only flags mismatch when compared values are both > 0, so 0 vs 1 or 0 vs 5 is treated as unavailable rather than incompatible.
- Why it matters: Runs with materially different purge/embargo/entry-lag contracts can compare as compatible.
- Validation: Pass manifests with purge_bars=0 vs 5 or entry_lag_bars=0 vs 1 into _build_run_comparison_compatibility().
- Remediation: Treat explicit zero as meaningful and compare presence separately from value.

## research_inference:05 - Promotion output assembly can silently drop malformed evidence bundles without failing closed
- Agent: research_inference
- Severity: medium
- Confidence: likely
- Category: artifact_integrity
- Affected: project/research/services/promotion_service.py
- Evidence: execute_promotion() skips blank or malformed evidence_bundle_json values and writes the surviving subset without a parity check against promoted rows.
- Why it matters: A promoted candidate can survive while its evidence bundle artifact is missing or malformed.
- Validation: Feed execute_promotion() a promoted row with malformed evidence_bundle_json and inspect whether it still exits successfully with an incomplete evidence_bundles.jsonl.
- Remediation: Make promotion assembly fail when promoted rows lack valid evidence bundles, or emit a blocking integrity error on count mismatch.

## research_inference:06 - Confirmatory candidate matching only preserves economic identity when optional fields happen to be present
- Agent: research_inference
- Severity: medium
- Confidence: likely
- Category: economic_realism
- Affected: project/research/services/confirmatory_candidate_service.py
- Evidence: Base structural matching omits cost_config_digest, after_cost_includes_funding_carry, and cost_model_source unless those columns are populated in both compared artifacts.
- Why it matters: Two runs can match as structurally continuous without proving they used the same cost contract.
- Validation: Compare origin and target candidate artifacts with identical base keys but missing cost identity fields.
- Remediation: Promote economic-identity fields from optional to required for confirmatory matching, or downgrade comparisons to non-confirmatory when they are absent.

## pipelines_artifacts:01 - Certification mode records strict artifact-safety flags but never enables the environment gates that enforce them
- Agent: pipelines_artifacts
- Severity: high
- Confidence: verified
- Category: contract_integrity
- Affected: project/pipelines/run_all_bootstrap.py, project/io/utils.py, project/pipelines/execution_engine.py, project/pipelines/run_all.py
- Evidence: run_all_bootstrap writes strict_run_scoped_reads and require_stage_manifests into the run manifest, but execution gates in project/io/utils.py and project/pipelines/execution_engine.py only read BACKTEST_STRICT_RUN_SCOPED_READS and BACKTEST_REQUIRE_STAGE_MANIFEST, which run_all never exports.
- Why it matters: Certification mode advertises fail-closed artifact isolation while still allowing the default fallback behavior.
- Validation: Run project.pipelines.run_all in certification mode and inspect both run_manifest.json and the run_all environment-handling code.
- Remediation: Export the enforcement env vars from run_all in certification mode and add an execution-path test that proves the stricter behavior is active.

## pipelines_artifacts:02 - build_features can exit success with no inputs, no outputs, and no per-symbol results
- Agent: pipelines_artifacts
- Severity: high
- Confidence: verified
- Category: artifact_integrity
- Affected: project/pipelines/features/build_features.py, project/pipelines/execution_engine.py, project/specs/manifest.py
- Evidence: build_features initializes empty inputs/outputs, continues when cleaned bars are absent, never appends written outputs to the manifest, and still finalizes success. The manifest schema only checks that outputs is a list, not that success manifests declare artifacts.
- Why it matters: A green feature stage can represent zero produced artifacts, which is a false-green path and breaks cache/reconciliation logic.
- Validation: Run project.pipelines.features.build_features against an empty temporary BACKTEST_DATA_ROOT and inspect the emitted stage manifest.
- Remediation: Make zero-produced-symbol runs fail or warn, and require successful manifests to declare existing outputs.

## pipelines_artifacts:03 - ingest_binance_um_ohlcv converts total fetch failure into a green stage with only missing-archive stats
- Agent: pipelines_artifacts
- Severity: critical
- Confidence: verified
- Category: correctness
- Affected: project/pipelines/ingest/ingest_binance_um_ohlcv.py, project/pipelines/execution_engine.py
- Evidence: async_main() classifies failed/not_found monthly fetches as missing_archives, raises nothing when all months fail, and main() still finalizes success with empty outputs.
- Why it matters: The root raw-data producer can go green when no requested market data was actually ingested.
- Validation: Monkeypatch _process_month to always return failed/not_found and inspect async_main() and main() behavior.
- Remediation: Treat coverage failure as terminal when required partitions are missing and record actual written partitions into manifest outputs.

## pipelines_artifacts:04 - Funding ingestion records missing coverage but still returns success, allowing partial or empty funding artifacts to masquerade as complete
- Agent: pipelines_artifacts
- Severity: high
- Confidence: verified
- Category: artifact_integrity
- Affected: project/pipelines/ingest/ingest_binance_um_funding.py, project/pipelines/features/build_features.py, project/contracts/pipeline_registry.py
- Evidence: ingest_binance_um_funding computes missing_after_all and missing_count, but finalizes success regardless; build_features treats funding as optional, and the registry models funding as optional input for build_features_*.
- Why it matters: A run can appear funding-aware while silently dropping funding-derived signal content.
- Validation: Trace missing_after_all handling in ingest_binance_um_funding.py and build_features funding-read behavior.
- Remediation: Differentiate complete success from partial coverage and add configurable enforcement when funding-derived features are expected.

## pipelines_artifacts:05 - Run-manifest reconciliation upgrades failed runs to success without checking declared outputs or artifact existence
- Agent: pipelines_artifacts
- Severity: high
- Confidence: verified
- Category: artifact_integrity
- Affected: project/pipelines/pipeline_provenance.py, project/tests/pipelines/test_run_manifest_reconciliation.py
- Evidence: reconcile_run_manifest_from_stage_manifests() promotes the run to success when all planned stage manifests are terminal, without validating outputs, hashes, or on-disk existence. The tests explicitly encode warning/success-only reconciliation.
- Why it matters: Manual or stale manifests can flip a failed run to success even when artifacts are missing or empty.
- Validation: Create terminal stage manifests with empty/missing outputs for a failed run and call reconcile_run_manifest_from_stage_manifests().
- Remediation: Require reconciliation to validate declared outputs against disk and, ideally, against the artifact contract before promoting the run.

## events_ontology:01 - Alias event ids bypass canonicalization in ontology deconfliction
- Agent: events_ontology
- Severity: high
- Confidence: verified
- Category: correctness
- Affected: project/events/ontology_deconfliction.py, project/events/event_aliases.py, project/research/services/regime_effectiveness_service.py, project/tests/events/test_ontology_deconfliction.py
- Evidence: attach_canonical_event_bundle() maps event_type directly into the bundle map and never calls resolve_event_alias(), so alias ids like VOL_REGIME_SHIFT or BASIS_DISLOCATION do not collapse with canonical ids.
- Why it matters: Equivalent events can survive as separate canonical episodes, corrupting regime routing and episode aggregation.
- Validation: Pass alias/canonical pairs through attach_canonical_event_bundle() and deconflict_event_episodes() and compare the output bundles.
- Remediation: Normalize through resolve_event_alias() before bundle lookup and add alias/canonical regression tests.

## events_ontology:02 - ontology_audit.json is false-green: it reports no failures while every state source event is missing relative to the checked registry
- Agent: events_ontology
- Severity: high
- Confidence: verified
- Category: artifact_integrity
- Affected: project/scripts/ontology_consistency_audit.py, spec/events/canonical_event_registry.yaml, docs/generated/ontology_audit.json
- Evidence: ontology_consistency_audit compares state source events to spec/events/canonical_event_registry.yaml, which is only a five-entry legacy stub. The audit emits 70 missing source events but leaves failures empty and --check still passes.
- Why it matters: Operators can see a passing ontology audit when the same artifact proves state-to-event linkage is invalid against its claimed canonical source.
- Validation: Run project.scripts.ontology_consistency_audit --check and inspect failures plus states_with_missing_source_event.
- Remediation: Validate against the unified/compiled registry instead, or escalate non-empty states_with_missing_source_event into failures.

## events_ontology:03 - Dead interaction-family specs are auto-registered as detectors outside the active ontology contract
- Agent: events_ontology
- Severity: medium
- Confidence: verified
- Category: contract_integrity
- Affected: project/events/families/interaction.py, project/spec_validation/loaders.py, spec/events/interaction/INT_LIQ_OI_CONFIRM.yaml, docs/generated/detector_coverage.md
- Evidence: interaction.py registers every ontology event whose id starts with INT_, even though those ids are absent from the active unified registry and ontology mapping. detector_coverage artifacts already report that drift.
- Why it matters: The detector registry exposes callable ids outside the authoritative ontology, creating inconsistent runtime universes depending on which registry surface code consults.
- Validation: Compare list_registered_event_types() with EVENT_REGISTRY_SPECS and the unified registry, paying attention to INT_* ids and CROSS_ASSET_INTERACTION.
- Remediation: Gate interaction registration on compiled-registry membership or promote the intended interaction ids into the authoritative registry/mapping.

## events_ontology:04 - Generated ontology audits disagree on active-event count because one still relies on top-level per-event YAML presence
- Agent: events_ontology
- Severity: medium
- Confidence: verified
- Category: docs_drift
- Affected: project/scripts/ontology_consistency_audit.py, docs/generated/ontology_audit.json, docs/generated/event_ontology_audit.json, spec/events/event_registry_unified.yaml
- Evidence: ontology_audit.json reports 69 active specs while event_ontology_audit.json and the compiled registry report 70, because ontology_consistency_audit only scans top-level spec/events/*.yaml and misses active events represented only in the unified registry.
- Why it matters: Repo inventory artifacts disagree about the live event universe, breaking audit comparability and governance trust.
- Validation: Compare both generated audits with len(get_domain_registry().event_ids) and inspect the missing top-level YAML for CROSS_ASSET_DESYNC_EVENT.
- Remediation: Derive both audits from the same unified runtime source or require a per-event YAML for every active event and fail when one is missing.

## strategy_compilation:01 - Serialized blueprint lineage is silently reset when runtime rebuilds a blueprint
- Agent: strategy_compilation
- Severity: high
- Confidence: verified
- Category: contract_integrity
- Affected: project/strategy/dsl/normalize.py, project/strategy/dsl/schema.py, project/strategy/models/executable_strategy_spec.py, project/strategy/runtime/dsl_runtime/interpreter.py
- Evidence: build_blueprint() only maps a subset of LineageSpec fields, so fields such as proposal_id, wf_status, cost_config_digest, promotion_track, ontology_spec_hash, template_verb, and constraints revert to defaults during rebuild.
- Why it matters: Artifact identity and provenance are lost exactly at the blueprint/spec -> runtime boundary.
- Validation: Serialize a Blueprint with populated lineage fields, rebuild it with build_blueprint(), and compare lineage before/after.
- Remediation: Round-trip the full LineageSpec payload or validate the entire lineage dict directly instead of cherry-picking fields.

## strategy_compilation:02 - Runtime hard-requires funding_rate_scaled even for strategies that never reference funding
- Agent: strategy_compilation
- Severity: high
- Confidence: verified
- Category: runtime_safety
- Affected: project/strategy/runtime/dsl_runtime/execution_context.py, project/strategy/runtime/dsl_runtime/interpreter.py, project/tests/strategy_dsl/test_dsl_runtime_contracts.py
- Evidence: build_signal_frame() raises if funding_rate_scaled is absent, and DslInterpreterV1.generate_positions() calls it before interpreting the blueprint, even for non-funding strategies.
- Why it matters: Legal strategies can fail at runtime because the runtime contract is broader than the declared trigger/condition set.
- Validation: Execute a non-funding blueprint with spread-only features and no funding columns.
- Remediation: Make funding fields lazy or defaultable for strategies that do not use funding conditions.

## strategy_compilation:03 - Post-compile clustering is nondeterministic because it uses Python hash()
- Agent: strategy_compilation
- Severity: high
- Confidence: verified
- Category: artifact_integrity
- Affected: project/research/compile_strategy_blueprints.py
- Evidence: compile_strategy_blueprints.py computes cluster_key = hash((event_type, template_verb)) % 1000, and Python salts hash() per process.
- Why it matters: The same inputs can keep or drop different blueprints across separate runs.
- Validation: Run hash((event_type, template_verb)) % 1000 in separate interpreters and compare outputs.
- Remediation: Use a stable digest or the explicit tuple as the clustering key.

## strategy_compilation:04 - Main blueprint compiler bypasses its own selection helper and ignores several exposed gating arguments
- Agent: strategy_compilation
- Severity: medium
- Confidence: verified
- Category: maintainability
- Affected: project/research/compile_strategy_blueprints.py, project/tests/pipelines/research/test_compile_blueprint_module_wiring.py
- Evidence: _choose_event_rows() exists and understands max_per_event and fallback/quality gates, but main() iterates every promoted row directly and never calls it.
- Why it matters: Operator-facing CLI knobs appear to control compilation but do not change the output set.
- Validation: Trace main() from argparse through the loop over edge_df.to_dict("records") and compare output counts across different --max_per_event values.
- Remediation: Route main() through _choose_event_rows() or delete the dead CLI knobs.

## strategy_compilation:05 - spec/strategies YAML files are not part of the executable pipeline and have drifted from runtime reality
- Agent: strategy_compilation
- Severity: low
- Confidence: verified
- Category: docs_drift
- Affected: spec/strategies/liquidity_dislocation_mr.yaml, spec/strategies/context_state_smoke.yaml, project/compilers/spec_transformer.py, project/research/compile_strategy_blueprints.py
- Evidence: No executable path in scope loads spec/strategies/*.yaml; the engine consumes ExecutableStrategySpec objects built from DSL blueprints instead.
- Why it matters: These YAML files look authoritative but do not govern runtime behavior.
- Validation: Search the repo for spec/strategies references and compare with compile_strategy_blueprints.py and engine/runner.py.
- Remediation: Either wire these YAMLs into an enforced compile path or demote them to examples/tests and point operators at Blueprint/ExecutableStrategySpec as the source of truth.

## engine_live_runtime:01 - Monitor-only runners can still send real flatten orders when the kill-switch fires
- Agent: engine_live_runtime
- Severity: critical
- Confidence: verified
- Category: runtime_safety
- Affected: project/scripts/run_live_engine.py, project/live/runner.py, project/live/oms.py, project/configs/live_paper.yaml, project/configs/live_production.yaml
- Evidence: build_live_runner() creates an exchange-backed OMS in monitor_only when credentials exist, and _handle_kill_switch_trigger() always calls cancel_all_orders() and flatten_all_positions(), which submit reduce_only market orders.
- Why it matters: A supposedly non-trading observer can place real venue orders during a stale-feed or health-triggered unwind.
- Validation: Instantiate LiveEngineRunner(runtime_mode="monitor_only") with an exchange-backed OrderManager and positions, then await _handle_kill_switch_trigger().
- Remediation: Hard-gate all venue mutation paths on runtime_mode, or rename/document the mode if protective order placement is intentional.

## engine_live_runtime:02 - Monitor-only startup still requires a tradable Binance account and trading credentials
- Agent: engine_live_runtime
- Severity: high
- Confidence: verified
- Category: contract_integrity
- Affected: project/scripts/run_live_engine.py, project/tests/scripts/test_run_live_engine.py, project/tests/contracts/test_live_environment_config_contract.py
- Evidence: main() always runs preflight_binance_venue_connectivity() and validate_binance_account_preflight() regardless of runtime_mode, while config contracts label live_paper/live_production as monitor_only.
- Why it matters: There is no safe read-only deployment tier despite the naming and config contract.
- Validation: Supply a non-tradable account preflight payload to validate_binance_account_preflight() while using a monitor_only config.
- Remediation: Branch startup requirements on runtime_mode and allow monitor_only to use read-only credentials/connectivity checks.

## engine_live_runtime:03 - Incubation or paper gating is ineffective and graduation status is inverted
- Agent: engine_live_runtime
- Severity: high
- Confidence: verified
- Category: correctness
- Affected: project/live/runner.py, project/portfolio/incubation.py, project/live/oms.py
- Evidence: _prepare_strategy_order() only writes order.metadata["is_paper"], submit_order_async() ignores it, and IncubationLedger.is_graduated() returns False even after graduate() sets status="live".
- Why it matters: Incubating strategies are not truly kept out of live trading, and explicit graduation status is misreported.
- Validation: Exercise IncubationLedger.graduate() and submit a non-graduated strategy order through a venue-backed OMS.
- Remediation: Fix is_graduated() semantics and enforce incubation at the OMS submission boundary.

## engine_live_runtime:04 - Any caller can forge a StrategyResult and reach live trading by flipping strategy_runtime.implemented
- Agent: engine_live_runtime
- Severity: high
- Confidence: verified
- Category: runtime_safety
- Affected: project/live/runner.py, project/live/oms.py, project/engine/strategy_executor.py
- Evidence: submit_strategy_result_async() accepts arbitrary StrategyResult-like payloads, and _ensure_trading_enabled() only checks runtime_mode and strategy_runtime["implemented"]. build_live_order_from_strategy_result() derives orders directly from result.data.
- Why it matters: Unsafe or fabricated runtime objects can bypass provenance checks and create venue orders.
- Validation: Pass a handcrafted StrategyResult with target_position and fill_price into submit_strategy_result_async() on a trading runner.
- Remediation: Bind live-trading eligibility to validated runtime object type or signed strategy provenance, not a free-form implemented flag.

## engine_live_runtime:05 - Runtime postflight audit can return pass for malformed event rows because normalization is skipped
- Agent: engine_live_runtime
- Severity: medium
- Confidence: verified
- Category: artifact_integrity
- Affected: project/runtime/invariants.py, project/runtime/normalized_event.py, project/pipelines/runtime/build_normalized_replay_stream.py
- Evidence: run_runtime_postflight_audit() never calls normalize_event_rows(); it counts raw rows, and run_watermark_audit() skips rows missing timestamps.
- Why it matters: Replay/postflight artifacts can go green on malformed runtime data that the real normalization stage would reject or truncate.
- Validation: Call run_runtime_postflight_audit() on an events_df missing timestamp fields and inspect the returned status and normalization counts.
- Remediation: Normalize first or consume the normalized replay artifact before performing postflight checks.

## engine_live_runtime:06 - OMS fills do not update LiveStateStore, so safety decisions run on stale account state until the next snapshot sync
- Agent: engine_live_runtime
- Severity: medium
- Confidence: verified
- Category: correctness
- Affected: project/live/runner.py, project/live/oms.py, project/live/state.py
- Evidence: on_order_fill() updates the OMS and execution-quality report, but it does not mutate LiveStateStore; account state only changes on periodic exchange snapshots.
- Why it matters: Sizing, drawdown checks, and kill-switch logic can act on stale balances and positions between exchange syncs.
- Validation: Call on_order_fill() on a runner with an in-memory order and inspect state_store.account before and after.
- Remediation: Apply provisional local state updates on fills or maintain a merged local execution ledger for safety-critical logic.

## core_features_costs:01 - Execution cost units diverge across core, eval, and research paths
- Agent: core_features_costs
- Severity: high
- Confidence: verified
- Category: correctness
- Affected: project/core/execution_costs.py, project/eval/cost_model.py, project/research/search/evaluator.py, project/research/phase2_cost_integration.py
- Evidence: project/core/execution_costs.py resolves a one-sided fee+slippage total, project/research/search/evaluator.py subtracts that once, while project/eval/cost_model.py applies 2 * (fee + slippage) as round-trip cost.
- Why it matters: The same fee config produces different after-cost returns depending on the path that computed them.
- Validation: Compare resolve_execution_costs(), estimate_transaction_cost_bps(), apply_cost_model(), and evaluate_hypothesis_batch() under the same fee/slippage config.
- Remediation: Adopt one repo-wide cost unit contract and rename fields/sites so per-side and round-trip values cannot be confused.

## core_features_costs:02 - Funding carry can make stressed-cost robustness improve as costs are stressed
- Agent: core_features_costs
- Severity: high
- Confidence: verified
- Category: economic_realism
- Affected: project/research/gating.py, project/research/services/candidate_discovery_scoring.py, project/eval/robustness.py
- Evidence: build_event_return_frame() records cost_return = per_trade_cost - funding_carry_return, which can go negative, and evaluate_structural_robustness() subtracts that negative cost again, making higher stress multipliers improve pnl retention.
- Why it matters: A cost-stress panel can certify fragile candidates as more robust when stressed harder.
- Validation: Generate a short-side return frame with positive funding_rate_scaled and feed the negative costs_bps into evaluate_structural_robustness().
- Remediation: Stress transaction costs separately from funding carry and clamp transaction-cost inputs to non-negative values.

## core_features_costs:03 - Funding carry is applied as a flat trade adjustment independent of holding horizon
- Agent: core_features_costs
- Severity: medium
- Confidence: verified
- Category: economic_realism
- Affected: project/research/gating.py
- Evidence: _funding_carry_return() reads one scalar funding rate and applies it once per trade regardless of horizon length or funding-interval count.
- Why it matters: A 5-minute hold and a 1-hour hold can receive identical funding carry, distorting horizon comparisons.
- Validation: Call build_event_return_frame() with the same event and constant funding rate but different horizons and compare funding_carry_return.
- Remediation: Accrue carry over the actual holding window using aligned funding timestamps and interval counts.

## core_features_costs:04 - Research helper integrate_execution_costs is broken and does not call the shared core utility correctly
- Agent: core_features_costs
- Severity: medium
- Confidence: verified
- Category: architecture
- Affected: project/research/cost_integration.py, project/core/execution_costs.py
- Evidence: integrate_execution_costs() calls resolve_execution_costs(symbol) positionally, but resolve_execution_costs is keyword-only and requires a full cost-config contract.
- Why it matters: A purported shared research integration path fails immediately and cannot share semantics with the maintained core path.
- Validation: Import integrate_execution_costs() and call it on a dummy DataFrame and symbol.
- Remediation: Delete the dead helper or rewrite it against the actual resolve_execution_costs() keyword contract.

## core_features_costs:05 - The repo marks after-cost outputs as including funding carry even when actual carry coverage can be zero
- Agent: core_features_costs
- Severity: medium
- Confidence: likely
- Category: contract_integrity
- Affected: project/research/services/candidate_discovery_service.py, project/research/services/candidate_discovery_scoring.py, project/research/gating.py
- Evidence: candidate_discovery_service hard-codes after_cost_includes_funding_carry=True, while candidate_discovery_scoring separately computes funding_carry_eval_coverage and gating only includes carry when funding fields are present.
- Why it matters: Consumers can assume net expectancy already includes carry economics when the observed coverage is actually zero.
- Validation: Trace the hard-coded flag in candidate_discovery_service.py and compare it with funding_carry_eval_coverage on candidate sets lacking funding columns.
- Remediation: Derive the flag from observed coverage or split formula capability from observed carry coverage.

## specs_configs_validation:01 - Compiled registry ignores the declared default entry-lag grid and falls back to (1, 2)
- Agent: specs_configs_validation
- Severity: medium
- Confidence: verified
- Category: correctness
- Affected: project/domain/models.py, spec/ontology/templates/template_registry.yaml
- Evidence: DomainRegistry.default_entry_lags() still looks for template_param_grid_defaults, while the template registry declares defaults.param_grids.common.entry_lag_bars = [1, 2, 3].
- Why it matters: Wildcard/default lag expansion under-enumerates the declared search space and drops lag 3.
- Validation: Compare get_domain_registry().default_entry_lags() with get_domain_registry().template_defaults() and the YAML in template_registry.yaml.
- Remediation: Read defaults.param_grids.common.entry_lag_bars (or support both keys during migration) and add a regression test for [1,2,3].

## specs_configs_validation:02 - Direct experiment-config path accepts zero-lag hypotheses that search validators classify as leakage
- Agent: specs_configs_validation
- Severity: high
- Confidence: verified
- Category: statistical_integrity
- Affected: project/research/experiment_engine_validators.py, project/research/experiment_engine.py, project/research/search/validation.py, project/configs/experiments/e2e_synth_small.yaml
- Evidence: validate_agent_request() only checks list size for entry_lags, not values, and build_experiment_plan() expands e2e_synth_small.yaml with entry_lag 0 even though validate_hypothesis_spec() rejects lag < 1.
- Why it matters: The experiment-engine entrypoint can generate same-bar-leakage hypotheses that the core search validator would reject.
- Validation: Load e2e_synth_small.yaml, call validate_agent_request(), then build_experiment_plan() and inspect the emitted entry_lag values.
- Remediation: Enforce entry_lag >= 1 in experiment_engine_validators and normalize existing configs away from zero.

## specs_configs_validation:03 - Authoritative search-limit defaults advertise invalid zero-lag values that the proposal pipeline rejects
- Agent: specs_configs_validation
- Severity: medium
- Confidence: verified
- Category: contract_integrity
- Affected: project/configs/registries/search_limits.yaml, project/research/agent_io/proposal_to_experiment.py, project/research/agent_io/proposal_schema.py
- Evidence: search_limits.yaml declares defaults.entry_lags: [0,1,2], but proposal normalization and proposal-schema validation reject lag < 1.
- Why it matters: The same registry file is presented as authoritative defaults but cannot survive the proposal path that consumes it.
- Validation: Run _load_search_limit_defaults() against project/configs/registries/search_limits.yaml or compare the YAML with _normalize_entry_lags().
- Remediation: Remove 0 from search_limits.yaml or change the downstream leakage contract; the mixed state is self-invalidating.

## specs_configs_validation:04 - carry_state=neutral is declared as allowed in one spec but rejected by the compiled runtime context map
- Agent: specs_configs_validation
- Severity: medium
- Confidence: verified
- Category: contract_integrity
- Affected: spec/states/state_families.yaml, spec/grammar/state_registry.yaml, project/domain/registry_loader.py, project/research/search/validation.py
- Evidence: state_families.yaml allows neutral, but the compiled context map only loads funding_pos and funding_neg from spec/grammar/state_registry.yaml, and validation rejects neutral as unknown_context_mapping.
- Why it matters: Proposal/search/runtime semantics for carry_state are internally contradictory.
- Validation: Validate a HypothesisSpec using context={"carry_state":"neutral"} and compare with both state spec files.
- Remediation: Add neutral to the compiled context map or remove it from the allowed-values surface.

## specs_configs_validation:05 - Experiment-engine registry consistency check is effectively unreachable because it reads the wrong registry shapes
- Agent: specs_configs_validation
- Severity: medium
- Confidence: verified
- Category: architecture
- Affected: project/research/experiment_engine.py, project/research/experiment_engine_schema.py, project/configs/registries/events.yaml, project/configs/registries/templates.yaml, project/tests/spec_validation/test_registry_consistency.py
- Evidence: validate_registry_consistency() expects families/event_families keys in RegistryBundle-loaded config files, but those keys are not present, so the function returns early and never performs the claimed check. CI tests use different authoritative files under spec/grammar and spec/ontology/templates.
- Why it matters: The runtime safeguard is a no-op, so drift can be caught in one test stack but never by the direct runtime path.
- Validation: Inspect RegistryBundle(Path("project/configs/registries")) and then trace validate_registry_consistency().
- Remediation: Point the runtime check at the same authoritative spec files as the CI consistency test, or remove the dead runtime check.

## specs_configs_validation:06 - cost_profiles and conditioning_intersections are declared in search specs but have no runtime consumers
- Agent: specs_configs_validation
- Severity: low
- Confidence: verified
- Category: maintainability
- Affected: spec/search_space.yaml, spec/search/search_full.yaml, spec/search/search_phase1.yaml, spec/search/search_phase2.yaml, spec/search/search_phase3.yaml, spec/search/search_synthetic_truth.yaml
- Evidence: The keys are present in search YAMLs, but repo search across project/research, project/spec_validation, project/spec_registry, and project/specs finds no runtime consumers.
- Why it matters: Operator-facing knobs appear authoritative but currently do nothing.
- Validation: Search the runtime code for cost_profiles and conditioning_intersections and compare with their YAML declarations.
- Remediation: Implement consumers or reject/deprecate these unsupported keys in schema validation.

## reliability_tests_ci:01 - CLI smoke entrypoint silently ignores --seed and --storage_mode
- Agent: reliability_tests_ci
- Severity: medium
- Confidence: verified
- Category: correctness
- Affected: project/reliability/cli_smoke.py, project/tests/reliability/test_cli_smoke_entrypoint.py, project/tests/reliability/test_storage_modes.py, .github/workflows/tier2.yml
- Evidence: cli_smoke.main() parses seed and storage_mode, but calls run_smoke_cli() without passing either argument. Direct execution leaves environment.storage_mode at parquet even when csv-fallback is requested.
- Why it matters: The maintained smoke CLI does not honor its own operator-facing contract, and tier2 only exercises defaults.
- Validation: Run project.reliability.cli_smoke.main(["--mode","engine","--storage_mode","csv-fallback",...]) and inspect smoke_summary.json.
- Remediation: Pass the parsed args into run_smoke_cli() and add a CLI-level contract test.

## reliability_tests_ci:02 - Synthetic-truth validation in CI is mostly artifact-plumbing validation, not full inference-chain validation
- Agent: reliability_tests_ci
- Severity: high
- Confidence: verified
- Category: test_gap
- Affected: project/scripts/validate_synthetic_detector_truth.py, project/scripts/run_golden_synthetic_discovery.py, project/tests/smoke/test_golden_synthetic_discovery.py, project/tests/synthetic_truth/assertions/engine.py
- Evidence: validate_synthetic_detector_truth.py reads precomputed reports and scores them; it never invokes detector code. The golden workflow smoke test fakes the pipeline runner and monkeypatches the validator itself.
- Why it matters: A stale or fabricated report can satisfy CI without proving detector inference worked on the synthetic input.
- Validation: Inspect validate_synthetic_detector_truth.py and test_golden_synthetic_discovery.py side by side.
- Remediation: Add one deterministic end-to-end canary that runs the real detector path and validates the real emitted report without monkeypatching.

## reliability_tests_ci:03 - PR CI tiers do not gate several high-risk deterministic surfaces before merge
- Agent: reliability_tests_ci
- Severity: high
- Confidence: verified
- Category: operator_hazard
- Affected: .github/workflows/tier1.yml, .github/workflows/tier2.yml, .github/workflows/tier3.yml, Makefile
- Evidence: Only tier1 runs on pull_request, and it does not include smoke workflows, synthetic-truth canaries, or broad PIT coverage. tier2 is main-only and tier3 is nightly/release/manual.
- Why it matters: Breakage in smoke orchestration, synthetic-truth wiring, and PIT invariants can merge without PR-time detection.
- Validation: Compare workflow triggers and invoked tests across tier1/tier2/tier3 plus Makefile minimum-green-gate.
- Remediation: Promote a minimal subset of tier2 into PR gating: CLI smoke, one synthetic-truth canary, and one PIT canary.

## reliability_tests_ci:04 - PIT and promotion safety helper modules exist but are entirely outside test and CI coverage
- Agent: reliability_tests_ci
- Severity: medium
- Confidence: verified
- Category: test_gap
- Affected: project/reliability/promotion_gate.py, project/reliability/temporal_lint.py, .github/workflows/tier1.yml, .github/workflows/tier2.yml, .github/workflows/tier3.yml
- Evidence: repo search finds definitions for promotion_gate / verify_pit_integrity / temporal_lint, but no tests or workflow invocations.
- Why it matters: Either critical PIT/promotion safety guards are unverified, or dead code creates a false sense of protection.
- Validation: Search project/tests and .github/workflows for promotion_gate and temporal_lint references.
- Remediation: Add narrow deterministic unit tests or remove/deprecate the unused safety-helper surfaces.

## reliability_tests_ci:05 - Promotion smoke test contains stale defect commentary that contradicts current runtime behavior
- Agent: reliability_tests_ci
- Severity: low
- Confidence: verified
- Category: docs_drift
- Affected: project/tests/smoke/test_promotion_smoke.py, project/reliability/cli_smoke.py
- Evidence: The test comment still claims run_smoke_cli("promotion") is broken, but runtime full-mode smoke now validates promotion artifacts successfully.
- Why it matters: Stale defect commentary distorts audit and maintenance work even when runtime behavior has improved.
- Validation: Run run_smoke_cli("full") and compare the resulting promotion summary with the stale comment.
- Remediation: Remove/update the stale comment and add an explicit promotion-mode smoke test.

## scripts_operator_surface:01 - Benchmark tools write to two different artifact roots, making direct matrix runs invisible to review tooling
- Agent: scripts_operator_surface
- Severity: high
- Confidence: verified
- Category: contract_integrity
- Affected: project/scripts/run_benchmark_matrix.py, project/scripts/run_benchmark_maintenance_cycle.py, project/scripts/show_benchmark_review.py, project/scripts/show_promotion_readiness.py, docs/04_COMMANDS_AND_ENTRY_POINTS.md, docs/08_TESTING_AND_MAINTENANCE.md
- Evidence: run_benchmark_matrix.py defaults to data/reports/perf_benchmarks/* while maintenance, review, and readiness readers look under data/reports/benchmarks/latest or history.
- Why it matters: An operator can run the documented benchmark path successfully and then fail to discover or compare the result using maintained review tooling.
- Validation: Run run_benchmark_matrix with defaults, then run show_benchmark_review without --path and compare the searched roots.
- Remediation: Unify benchmark roots through one shared path helper and add a default-discoverability regression test.

## scripts_operator_surface:02 - edge-live-engine has undocumented environment contracts and a dead-end default config
- Agent: scripts_operator_surface
- Severity: high
- Confidence: verified
- Category: operator_hazard
- Affected: project/scripts/run_live_engine.py, project/configs/golden_certification.yaml, docs/04_COMMANDS_AND_ENTRY_POINTS.md, project/tests/contracts/test_live_environment_service_contract.py
- Evidence: run_live_engine help text does not mention required EDGE_* env vars. Its default config is project/configs/golden_certification.yaml, which does not resolve to paper or production, so startup falls through to unsupported venue preflight.
- Why it matters: A documented maintained entry point is not operable from its own visible CLI contract.
- Validation: Compare run_live_engine --help with validate_live_runtime_environment() and _resolve_runtime_environment() behavior on golden_certification.yaml.
- Remediation: Fail fast when no runtime environment resolves, document the full env contract, and remove or replace the dead-end default config.

## scripts_operator_surface:03 - run_researcher_verification hardcodes direct phase-2 paths and rejects supported nested search_engine artifact layouts
- Agent: scripts_operator_surface
- Severity: high
- Confidence: verified
- Category: artifact_integrity
- Affected: project/scripts/run_researcher_verification.py, project/scripts/run_golden_synthetic_discovery.py, project/artifacts/catalog.py, project/tests/smoke/test_golden_synthetic_discovery.py
- Evidence: _verify_experiment_artifacts() only checks direct reports/phase2/<run_id>/phase2_candidates.parquet and phase2_diagnostics.json, while golden synthetic discovery and catalog compatibility helpers already support nested search_engine layouts.
- Why it matters: A verification tool rejects valid outputs because it bypasses the repo’s shared artifact resolver.
- Validation: Use a run whose phase-2 artifacts live under reports/phase2/<run_id>/search_engine and call run_researcher_verification.
- Remediation: Use project.artifacts.catalog helpers in _verify_experiment_artifacts() and add tests for both direct and nested layouts.

## scripts_operator_surface:04 - Two cleanup entry points with the same purpose have materially different destructive behavior
- Agent: scripts_operator_surface
- Severity: medium
- Confidence: verified
- Category: operator_hazard
- Affected: project/scripts/clean_data.py, project/scripts/clean_data.sh
- Evidence: clean_data.py respects get_data_root() and defaults to age-based cleanup, while clean_data.sh wipes fixed repo-relative trees, can delete data/synthetic, and can wipe top-level artifacts/ in all mode.
- Why it matters: Two similarly named cleaners can preserve history in one invocation and destructively wipe broader trees in another.
- Validation: Read both implementations and compare clean_data.py --full with clean_data.sh all/runtime behavior.
- Remediation: Collapse to one maintained cleaner or document/rename the destructive differences prominently.

## scripts_operator_surface:05 - One-off mutation scripts bypass proposal/governance contracts and edit tracked code or config directly
- Agent: scripts_operator_surface
- Severity: medium
- Confidence: verified
- Category: contract_integrity
- Affected: project/scripts/fix_regime.py, project/scripts/fix_detector_registry.py, project/scripts/pipeline_governance.py, docs/03_OPERATOR_WORKFLOW.md, docs/04_COMMANDS_AND_ENTRY_POINTS.md
- Evidence: fix_regime.py and fix_detector_registry.py mutate tracked files at import time with no parser, no dry-run, no validation, and no handoff to pipeline_governance.py.
- Why it matters: These scripts circumvent the disciplined operator surfaces the docs tell users to trust and can silently desynchronize registries/specs/generated artifacts.
- Validation: Open the files and observe top-level mutation logic with no CLI or check/apply split.
- Remediation: Remove them from the maintained tree or fold them into a governed tool that supports --check/--apply and post-mutation validation.

## scripts_operator_surface:06 - strategy_workbench.py is an undocumented bypass path that writes temp specs and launches run_all directly
- Agent: scripts_operator_surface
- Severity: medium
- Confidence: verified
- Category: docs_drift
- Affected: project/scripts/strategy_workbench.py, docs/03_OPERATOR_WORKFLOW.md, docs/04_COMMANDS_AND_ENTRY_POINTS.md
- Evidence: strategy_workbench.py writes spec/concepts/workbench_temp.yaml and calls run_all with hardcoded direct CLI flags, without proposal issuance, bookkeeping, or checked subprocess semantics.
- Why it matters: Operators can discover a plausible-looking script that bypasses the repo’s claimed planning and memory/accountability flow.
- Validation: Inspect strategy_workbench.py and note the temp spec write plus unchecked subprocess.run().
- Remediation: Retire it or convert it into a proposal generator that delegates through issue_proposal/execute_proposal.

## scripts_operator_surface:07 - Legacy memory rebuild scripts are hardcoded to one synthetic run and mutate persistent memory tables with no controls
- Agent: scripts_operator_surface
- Severity: low
- Confidence: verified
- Category: maintainability
- Affected: project/scripts/rebuild_memory.py, project/scripts/rebuild_memory_v2.py, docs/04_COMMANDS_AND_ENTRY_POINTS.md
- Evidence: Both scripts hardcode synthetic_2025_full_year identifiers, execute at import time, and write directly into memory tables with no parser or dry-run.
- Why it matters: They are operator-confusing legacy surfaces that can overwrite persistent memory state for one hardcoded program.
- Validation: Inspect the top-level execution and hardcoded ids in both scripts.
- Remediation: Delete them if obsolete or replace them with parameterized CLIs requiring explicit ids and apply confirmation.

## scripts_operator_surface:08 - Artifact regeneration script hardcodes python3 instead of the project interpreter
- Agent: scripts_operator_surface
- Severity: low
- Confidence: likely
- Category: operator_hazard
- Affected: project/scripts/regenerate_artifacts.sh, docs/08_TESTING_AND_MAINTENANCE.md
- Evidence: regenerate_artifacts.sh shells out to python3 directly instead of resolving the repo interpreter the way pre_commit.sh does.
- Why it matters: Artifact regeneration can fail or drift on hosts where python3 is not the project environment.
- Validation: Compare regenerate_artifacts.sh with pre_commit.sh and run the script on a machine where python3 lacks repo deps.
- Remediation: Resolve the project interpreter explicitly or move artifact regeneration behind a make target/Python entry point that uses the configured env.
