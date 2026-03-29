# strategy_compilation

## Scope
- project/strategy/
- project/compilers/
- project/research/compile_strategy_blueprints.py
- project/research/build_strategy_candidates.py
- spec/strategies/
- project/tests/strategy*/
- project/tests/strategies/

## Summary
The executable path is promoted candidate rows -> compile_blueprint() -> DSL Blueprint JSONL -> ExecutableStrategySpec.from_blueprint() -> engine.run_engine_for_specs() -> DslInterpreterV1.generate_positions(). spec/strategies/*.yaml and project/compilers/spec_transformer.py are side surfaces rather than the active runtime contract.

## Findings
### Serialized blueprint lineage is silently reset when runtime rebuilds a blueprint
- Severity: high
- Confidence: verified
- Category: contract_integrity
- Affected: project/strategy/dsl/normalize.py, project/strategy/dsl/schema.py, project/strategy/models/executable_strategy_spec.py, project/strategy/runtime/dsl_runtime/interpreter.py
- Evidence: build_blueprint() only maps a subset of LineageSpec fields, so fields such as proposal_id, wf_status, cost_config_digest, promotion_track, ontology_spec_hash, template_verb, and constraints revert to defaults during rebuild.
- Why it matters: Artifact identity and provenance are lost exactly at the blueprint/spec -> runtime boundary.
- Validation: Serialize a Blueprint with populated lineage fields, rebuild it with build_blueprint(), and compare lineage before/after.
- Remediation: Round-trip the full LineageSpec payload or validate the entire lineage dict directly instead of cherry-picking fields.

### Runtime hard-requires funding_rate_scaled even for strategies that never reference funding
- Severity: high
- Confidence: verified
- Category: runtime_safety
- Affected: project/strategy/runtime/dsl_runtime/execution_context.py, project/strategy/runtime/dsl_runtime/interpreter.py, project/tests/strategy_dsl/test_dsl_runtime_contracts.py
- Evidence: build_signal_frame() raises if funding_rate_scaled is absent, and DslInterpreterV1.generate_positions() calls it before interpreting the blueprint, even for non-funding strategies.
- Why it matters: Legal strategies can fail at runtime because the runtime contract is broader than the declared trigger/condition set.
- Validation: Execute a non-funding blueprint with spread-only features and no funding columns.
- Remediation: Make funding fields lazy or defaultable for strategies that do not use funding conditions.

### Post-compile clustering is nondeterministic because it uses Python hash()
- Severity: high
- Confidence: verified
- Category: artifact_integrity
- Affected: project/research/compile_strategy_blueprints.py
- Evidence: compile_strategy_blueprints.py computes cluster_key = hash((event_type, template_verb)) % 1000, and Python salts hash() per process.
- Why it matters: The same inputs can keep or drop different blueprints across separate runs.
- Validation: Run hash((event_type, template_verb)) % 1000 in separate interpreters and compare outputs.
- Remediation: Use a stable digest or the explicit tuple as the clustering key.

### Main blueprint compiler bypasses its own selection helper and ignores several exposed gating arguments
- Severity: medium
- Confidence: verified
- Category: maintainability
- Affected: project/research/compile_strategy_blueprints.py, project/tests/pipelines/research/test_compile_blueprint_module_wiring.py
- Evidence: _choose_event_rows() exists and understands max_per_event and fallback/quality gates, but main() iterates every promoted row directly and never calls it.
- Why it matters: Operator-facing CLI knobs appear to control compilation but do not change the output set.
- Validation: Trace main() from argparse through the loop over edge_df.to_dict("records") and compare output counts across different --max_per_event values.
- Remediation: Route main() through _choose_event_rows() or delete the dead CLI knobs.

### spec/strategies YAML files are not part of the executable pipeline and have drifted from runtime reality
- Severity: low
- Confidence: verified
- Category: docs_drift
- Affected: spec/strategies/liquidity_dislocation_mr.yaml, spec/strategies/context_state_smoke.yaml, project/compilers/spec_transformer.py, project/research/compile_strategy_blueprints.py
- Evidence: No executable path in scope loads spec/strategies/*.yaml; the engine consumes ExecutableStrategySpec objects built from DSL blueprints instead.
- Why it matters: These YAML files look authoritative but do not govern runtime behavior.
- Validation: Search the repo for spec/strategies references and compare with compile_strategy_blueprints.py and engine/runner.py.
- Remediation: Either wire these YAMLs into an enforced compile path or demote them to examples/tests and point operators at Blueprint/ExecutableStrategySpec as the source of truth.
