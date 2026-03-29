# specs_configs_validation

## Scope
- spec/
- project/specs/
- project/spec_registry/
- project/spec_validation/
- project/configs/
- project/research/configs/
- project/tests/spec_validation/
- project/tests/spec_registry/
- project/tests/specs/

## Summary
Runtime registry consumers use project.spec_registry and project/domain/registry_loader.py against unified event/template/grammar specs. Search generation still uses older spec_validation facades for search YAMLs. Proposal, search, validation, promotion, blueprint/spec, and engine/live paths are split across different loaders and consistency checks.

## Findings
### Compiled registry ignores the declared default entry-lag grid and falls back to (1, 2)
- Severity: medium
- Confidence: verified
- Category: correctness
- Affected: project/domain/models.py, spec/ontology/templates/template_registry.yaml
- Evidence: DomainRegistry.default_entry_lags() still looks for template_param_grid_defaults, while the template registry declares defaults.param_grids.common.entry_lag_bars = [1, 2, 3].
- Why it matters: Wildcard/default lag expansion under-enumerates the declared search space and drops lag 3.
- Validation: Compare get_domain_registry().default_entry_lags() with get_domain_registry().template_defaults() and the YAML in template_registry.yaml.
- Remediation: Read defaults.param_grids.common.entry_lag_bars (or support both keys during migration) and add a regression test for [1,2,3].

### Direct experiment-config path accepts zero-lag hypotheses that search validators classify as leakage
- Severity: high
- Confidence: verified
- Category: statistical_integrity
- Affected: project/research/experiment_engine_validators.py, project/research/experiment_engine.py, project/research/search/validation.py, project/configs/experiments/e2e_synth_small.yaml
- Evidence: validate_agent_request() only checks list size for entry_lags, not values, and build_experiment_plan() expands e2e_synth_small.yaml with entry_lag 0 even though validate_hypothesis_spec() rejects lag < 1.
- Why it matters: The experiment-engine entrypoint can generate same-bar-leakage hypotheses that the core search validator would reject.
- Validation: Load e2e_synth_small.yaml, call validate_agent_request(), then build_experiment_plan() and inspect the emitted entry_lag values.
- Remediation: Enforce entry_lag >= 1 in experiment_engine_validators and normalize existing configs away from zero.

### Authoritative search-limit defaults advertise invalid zero-lag values that the proposal pipeline rejects
- Severity: medium
- Confidence: verified
- Category: contract_integrity
- Affected: project/configs/registries/search_limits.yaml, project/research/agent_io/proposal_to_experiment.py, project/research/agent_io/proposal_schema.py
- Evidence: search_limits.yaml declares defaults.entry_lags: [0,1,2], but proposal normalization and proposal-schema validation reject lag < 1.
- Why it matters: The same registry file is presented as authoritative defaults but cannot survive the proposal path that consumes it.
- Validation: Run _load_search_limit_defaults() against project/configs/registries/search_limits.yaml or compare the YAML with _normalize_entry_lags().
- Remediation: Remove 0 from search_limits.yaml or change the downstream leakage contract; the mixed state is self-invalidating.

### carry_state=neutral is declared as allowed in one spec but rejected by the compiled runtime context map
- Severity: medium
- Confidence: verified
- Category: contract_integrity
- Affected: spec/states/state_families.yaml, spec/grammar/state_registry.yaml, project/domain/registry_loader.py, project/research/search/validation.py
- Evidence: state_families.yaml allows neutral, but the compiled context map only loads funding_pos and funding_neg from spec/grammar/state_registry.yaml, and validation rejects neutral as unknown_context_mapping.
- Why it matters: Proposal/search/runtime semantics for carry_state are internally contradictory.
- Validation: Validate a HypothesisSpec using context={"carry_state":"neutral"} and compare with both state spec files.
- Remediation: Add neutral to the compiled context map or remove it from the allowed-values surface.

### Experiment-engine registry consistency check is effectively unreachable because it reads the wrong registry shapes
- Severity: medium
- Confidence: verified
- Category: architecture
- Affected: project/research/experiment_engine.py, project/research/experiment_engine_schema.py, project/configs/registries/events.yaml, project/configs/registries/templates.yaml, project/tests/spec_validation/test_registry_consistency.py
- Evidence: validate_registry_consistency() expects families/event_families keys in RegistryBundle-loaded config files, but those keys are not present, so the function returns early and never performs the claimed check. CI tests use different authoritative files under spec/grammar and spec/ontology/templates.
- Why it matters: The runtime safeguard is a no-op, so drift can be caught in one test stack but never by the direct runtime path.
- Validation: Inspect RegistryBundle(Path("project/configs/registries")) and then trace validate_registry_consistency().
- Remediation: Point the runtime check at the same authoritative spec files as the CI consistency test, or remove the dead runtime check.

### cost_profiles and conditioning_intersections are declared in search specs but have no runtime consumers
- Severity: low
- Confidence: verified
- Category: maintainability
- Affected: spec/search_space.yaml, spec/search/search_full.yaml, spec/search/search_phase1.yaml, spec/search/search_phase2.yaml, spec/search/search_phase3.yaml, spec/search/search_synthetic_truth.yaml
- Evidence: The keys are present in search YAMLs, but repo search across project/research, project/spec_validation, project/spec_registry, and project/specs finds no runtime consumers.
- Why it matters: Operator-facing knobs appear authoritative but currently do nothing.
- Validation: Search the runtime code for cost_profiles and conditioning_intersections and compare with their YAML declarations.
- Remediation: Implement consumers or reject/deprecate these unsupported keys in schema validation.
