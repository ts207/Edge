# scripts_operator_surface

## Scope
- project/scripts/
- project/apps/
- docs/03_OPERATOR_WORKFLOW.md
- docs/04_COMMANDS_AND_ENTRY_POINTS.md
- docs/08_TESTING_AND_MAINTENANCE.md

## Summary
The maintained surface is proposal wrappers -> run_all, plus smoke/certification scripts and benchmark tooling. In practice, project/scripts also exposes many undocumented standalone CLIs and one-off mutators that bypass proposal issuance, artifact compatibility helpers, or consistent output roots. project/apps/ is only a compatibility facade.

## Findings
### Benchmark tools write to two different artifact roots, making direct matrix runs invisible to review tooling
- Severity: high
- Confidence: verified
- Category: contract_integrity
- Affected: project/scripts/run_benchmark_matrix.py, project/scripts/run_benchmark_maintenance_cycle.py, project/scripts/show_benchmark_review.py, project/scripts/show_promotion_readiness.py, docs/04_COMMANDS_AND_ENTRY_POINTS.md, docs/08_TESTING_AND_MAINTENANCE.md
- Evidence: run_benchmark_matrix.py defaults to data/reports/perf_benchmarks/* while maintenance, review, and readiness readers look under data/reports/benchmarks/latest or history.
- Why it matters: An operator can run the documented benchmark path successfully and then fail to discover or compare the result using maintained review tooling.
- Validation: Run run_benchmark_matrix with defaults, then run show_benchmark_review without --path and compare the searched roots.
- Remediation: Unify benchmark roots through one shared path helper and add a default-discoverability regression test.

### edge-live-engine has undocumented environment contracts and a dead-end default config
- Severity: high
- Confidence: verified
- Category: operator_hazard
- Affected: project/scripts/run_live_engine.py, project/configs/golden_certification.yaml, docs/04_COMMANDS_AND_ENTRY_POINTS.md, project/tests/contracts/test_live_environment_service_contract.py
- Evidence: run_live_engine help text does not mention required EDGE_* env vars. Its default config is project/configs/golden_certification.yaml, which does not resolve to paper or production, so startup falls through to unsupported venue preflight.
- Why it matters: A documented maintained entry point is not operable from its own visible CLI contract.
- Validation: Compare run_live_engine --help with validate_live_runtime_environment() and _resolve_runtime_environment() behavior on golden_certification.yaml.
- Remediation: Fail fast when no runtime environment resolves, document the full env contract, and remove or replace the dead-end default config.

### run_researcher_verification hardcodes direct phase-2 paths and rejects supported nested search_engine artifact layouts
- Severity: high
- Confidence: verified
- Category: artifact_integrity
- Affected: project/scripts/run_researcher_verification.py, project/scripts/run_golden_synthetic_discovery.py, project/artifacts/catalog.py, project/tests/smoke/test_golden_synthetic_discovery.py
- Evidence: _verify_experiment_artifacts() only checks direct reports/phase2/<run_id>/phase2_candidates.parquet and phase2_diagnostics.json, while golden synthetic discovery and catalog compatibility helpers already support nested search_engine layouts.
- Why it matters: A verification tool rejects valid outputs because it bypasses the repo’s shared artifact resolver.
- Validation: Use a run whose phase-2 artifacts live under reports/phase2/<run_id>/search_engine and call run_researcher_verification.
- Remediation: Use project.artifacts.catalog helpers in _verify_experiment_artifacts() and add tests for both direct and nested layouts.

### Two cleanup entry points with the same purpose have materially different destructive behavior
- Severity: medium
- Confidence: verified
- Category: operator_hazard
- Affected: project/scripts/clean_data.py, project/scripts/clean_data.sh
- Evidence: clean_data.py respects get_data_root() and defaults to age-based cleanup, while clean_data.sh wipes fixed repo-relative trees, can delete data/synthetic, and can wipe top-level artifacts/ in all mode.
- Why it matters: Two similarly named cleaners can preserve history in one invocation and destructively wipe broader trees in another.
- Validation: Read both implementations and compare clean_data.py --full with clean_data.sh all/runtime behavior.
- Remediation: Collapse to one maintained cleaner or document/rename the destructive differences prominently.

### One-off mutation scripts bypass proposal/governance contracts and edit tracked code or config directly
- Severity: medium
- Confidence: verified
- Category: contract_integrity
- Affected: project/scripts/fix_regime.py, project/scripts/fix_detector_registry.py, project/scripts/pipeline_governance.py, docs/03_OPERATOR_WORKFLOW.md, docs/04_COMMANDS_AND_ENTRY_POINTS.md
- Evidence: fix_regime.py and fix_detector_registry.py mutate tracked files at import time with no parser, no dry-run, no validation, and no handoff to pipeline_governance.py.
- Why it matters: These scripts circumvent the disciplined operator surfaces the docs tell users to trust and can silently desynchronize registries/specs/generated artifacts.
- Validation: Open the files and observe top-level mutation logic with no CLI or check/apply split.
- Remediation: Remove them from the maintained tree or fold them into a governed tool that supports --check/--apply and post-mutation validation.

### strategy_workbench.py is an undocumented bypass path that writes temp specs and launches run_all directly
- Severity: medium
- Confidence: verified
- Category: docs_drift
- Affected: project/scripts/strategy_workbench.py, docs/03_OPERATOR_WORKFLOW.md, docs/04_COMMANDS_AND_ENTRY_POINTS.md
- Evidence: strategy_workbench.py writes spec/concepts/workbench_temp.yaml and calls run_all with hardcoded direct CLI flags, without proposal issuance, bookkeeping, or checked subprocess semantics.
- Why it matters: Operators can discover a plausible-looking script that bypasses the repo’s claimed planning and memory/accountability flow.
- Validation: Inspect strategy_workbench.py and note the temp spec write plus unchecked subprocess.run().
- Remediation: Retire it or convert it into a proposal generator that delegates through issue_proposal/execute_proposal.

### Legacy memory rebuild scripts are hardcoded to one synthetic run and mutate persistent memory tables with no controls
- Severity: low
- Confidence: verified
- Category: maintainability
- Affected: project/scripts/rebuild_memory.py, project/scripts/rebuild_memory_v2.py, docs/04_COMMANDS_AND_ENTRY_POINTS.md
- Evidence: Both scripts hardcode synthetic_2025_full_year identifiers, execute at import time, and write directly into memory tables with no parser or dry-run.
- Why it matters: They are operator-confusing legacy surfaces that can overwrite persistent memory state for one hardcoded program.
- Validation: Inspect the top-level execution and hardcoded ids in both scripts.
- Remediation: Delete them if obsolete or replace them with parameterized CLIs requiring explicit ids and apply confirmation.

### Artifact regeneration script hardcodes python3 instead of the project interpreter
- Severity: low
- Confidence: likely
- Category: operator_hazard
- Affected: project/scripts/regenerate_artifacts.sh, docs/08_TESTING_AND_MAINTENANCE.md
- Evidence: regenerate_artifacts.sh shells out to python3 directly instead of resolving the repo interpreter the way pre_commit.sh does.
- Why it matters: Artifact regeneration can fail or drift on hosts where python3 is not the project environment.
- Validation: Compare regenerate_artifacts.sh with pre_commit.sh and run the script on a machine where python3 lacks repo deps.
- Remediation: Resolve the project interpreter explicitly or move artifact regeneration behind a make target/Python entry point that uses the configured env.
