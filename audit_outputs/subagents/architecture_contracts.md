# architecture_contracts

## Scope
- README.md
- docs/
- docs/generated/
- project/contracts/
- project/pipelines/run_all.py
- project/* package boundaries

## Summary
Executable orchestration is centered on project/pipelines/run_all.py, with stage planning in project/pipelines/planner.py and family builders in project/pipelines/stages/*. Real execution uses wrapper and CLI modules under project/pipelines/research/* and project/research/cli/* more than the service-owner map declared in project/contracts/stage_dag.py and project/contracts/system_map.py.

## Findings
### Phase-2 contract registry still describes legacy conditional and bridge stages that the planner no longer schedules
- Severity: high
- Confidence: verified
- Category: contract_integrity
- Affected: project/contracts/pipeline_registry.py, project/pipelines/stages/research.py, project/pipelines/research/README.md, project/tests/pipelines/test_pipeline_discovery_mode.py
- Evidence: project/contracts/pipeline_registry.py maps phase2_discovery to phase2_conditional_hypotheses* and bridge_evaluate_phase2*, but project/pipelines/stages/research.py appends phase2_search_engine instead, and project/tests/pipelines/test_pipeline_discovery_mode.py asserts the legacy stages are absent.
- Why it matters: Governance/docs describe a discovery chain that does not actually execute, so operator expectations and contract audits can be wrong before runtime starts.
- Validation: Inspect build_research_stages in project/pipelines/stages/research.py and compare its emitted names to STAGE_FAMILY_REGISTRY in project/contracts/pipeline_registry.py.
- Remediation: Either remove legacy conditional/bridge stages from the registry/docs or restore explicit scheduling paths and end-to-end planner tests.

### Strategy packaging stages point at nonexistent wrapper scripts while contract validation still reports the plan valid
- Severity: critical
- Confidence: verified
- Category: correctness
- Affected: project/pipelines/stages/evaluation.py, project/contracts/pipeline_registry.py, project/tests/pipelines/test_stage_registry_contract.py
- Evidence: project/pipelines/stages/evaluation.py schedules project/pipelines/research/compile_strategy_blueprints.py and select_profitable_strategies.py, but those wrapper files do not exist. validate_stage_plan_contract() in project/contracts/pipeline_registry.py only checks glob patterns, and the corresponding test treats those missing paths as valid.
- Why it matters: A plan can pass the contract layer and then fail only at execution time when Python cannot open the stage script.
- Validation: Build evaluation stages with run_strategy_blueprint_compiler=1 and run_profitable_selector=1, then check Path.exists() for the emitted script paths and compare with validate_stage_plan_contract().
- Remediation: Point the planner and registry at real implementations under project/research/* or restore the missing wrappers, then make the registry validator reject nonexistent scripts.

### README declares docs/generated authoritative, but required generated artifacts are missing and build_system_map --check fails
- Severity: high
- Confidence: verified
- Category: artifact_integrity
- Affected: README.md, docs/generated/, project/scripts/build_system_map.py, project/scripts/regenerate_artifacts.sh
- Evidence: README lists docs/generated/system_map.* and event ontology artifacts as authoritative. The audited tree lacks several of them, and project/scripts/build_system_map.py --check fails because docs/generated/system_map.{md,json} are absent.
- Why it matters: Governance-facing generated artifacts are incomplete and not reproducible from the checked-in regeneration path, so artifact trust is lower than the docs claim.
- Validation: List docs/generated/* and compare with README.md, then run project/scripts/build_system_map.py --format both --check.
- Remediation: Narrow the documented generated surface or commit and continuously check the full declared set in CI.

### System-map ownership points to services, but run_all actually executes wrappers and CLI modules
- Severity: medium
- Confidence: verified
- Category: architecture
- Affected: project/contracts/stage_dag.py, project/contracts/system_map.py, project/pipelines/run_all.py, project/pipelines/research/phase2_search_engine.py, project/research/cli/promotion_cli.py
- Evidence: project/contracts/stage_dag.py says phase2_discovery and promotion belong to candidate_discovery_service and promotion_service, but run_all traverses wrapper modules under project/pipelines/research/* and CLI adapters before or instead of those services.
- Why it matters: The declared boundary map is not the real orchestration graph, which hides ownership and upgrade risk.
- Validation: Trace imports from project/pipelines/run_all.py through stage wrappers and compare them with owner modules in project/contracts/stage_dag.py.
- Remediation: Either make wrappers call services directly as the canonical surface or update the stage_dag/system_map to reflect the actual wrapper chain.

### Stage contracts are enforced by naming and glob patterns rather than executable or artifact proof
- Severity: medium
- Confidence: verified
- Category: maintainability
- Affected: project/contracts/pipeline_registry.py, project/tests/pipelines/test_stage_registry_contract.py
- Evidence: validate_stage_plan_contract() only verifies stage names and path globs. It does not check file existence, importability, or declared outputs, and tests reinforce that weak contract.
- Why it matters: High-leverage failures survive planning and contract checks until runtime or later artifact review.
- Validation: Feed validate_stage_plan_contract() a stage tuple whose path matches the allowed glob but points to no real file.
- Remediation: Add existence/import checks and at least one artifact-level smoke assertion per stage family.
