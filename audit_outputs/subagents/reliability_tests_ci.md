# reliability_tests_ci

## Scope
- project/reliability/
- project/synthetic_truth/
- project/tests/
- .github/workflows/
- Makefile
- pyproject.toml

## Summary
Reliability centers on CLI smoke generation, artifact/schema validators, manifest checks, and smoke data builders. Synthetic-truth detector scoring in CI is mostly posthoc report-window validation, while the heavier detector-execution harness lives under project/tests/synthetic_truth/* and is not strongly represented in PR CI.

## Findings
### CLI smoke entrypoint silently ignores --seed and --storage_mode
- Severity: medium
- Confidence: verified
- Category: correctness
- Affected: project/reliability/cli_smoke.py, project/tests/reliability/test_cli_smoke_entrypoint.py, project/tests/reliability/test_storage_modes.py, .github/workflows/tier2.yml
- Evidence: cli_smoke.main() parses seed and storage_mode, but calls run_smoke_cli() without passing either argument. Direct execution leaves environment.storage_mode at parquet even when csv-fallback is requested.
- Why it matters: The maintained smoke CLI does not honor its own operator-facing contract, and tier2 only exercises defaults.
- Validation: Run project.reliability.cli_smoke.main(["--mode","engine","--storage_mode","csv-fallback",...]) and inspect smoke_summary.json.
- Remediation: Pass the parsed args into run_smoke_cli() and add a CLI-level contract test.

### Synthetic-truth validation in CI is mostly artifact-plumbing validation, not full inference-chain validation
- Severity: high
- Confidence: verified
- Category: test_gap
- Affected: project/scripts/validate_synthetic_detector_truth.py, project/scripts/run_golden_synthetic_discovery.py, project/tests/smoke/test_golden_synthetic_discovery.py, project/tests/synthetic_truth/assertions/engine.py
- Evidence: validate_synthetic_detector_truth.py reads precomputed reports and scores them; it never invokes detector code. The golden workflow smoke test fakes the pipeline runner and monkeypatches the validator itself.
- Why it matters: A stale or fabricated report can satisfy CI without proving detector inference worked on the synthetic input.
- Validation: Inspect validate_synthetic_detector_truth.py and test_golden_synthetic_discovery.py side by side.
- Remediation: Add one deterministic end-to-end canary that runs the real detector path and validates the real emitted report without monkeypatching.

### PR CI tiers do not gate several high-risk deterministic surfaces before merge
- Severity: high
- Confidence: verified
- Category: operator_hazard
- Affected: .github/workflows/tier1.yml, .github/workflows/tier2.yml, .github/workflows/tier3.yml, Makefile
- Evidence: Only tier1 runs on pull_request, and it does not include smoke workflows, synthetic-truth canaries, or broad PIT coverage. tier2 is main-only and tier3 is nightly/release/manual.
- Why it matters: Breakage in smoke orchestration, synthetic-truth wiring, and PIT invariants can merge without PR-time detection.
- Validation: Compare workflow triggers and invoked tests across tier1/tier2/tier3 plus Makefile minimum-green-gate.
- Remediation: Promote a minimal subset of tier2 into PR gating: CLI smoke, one synthetic-truth canary, and one PIT canary.

### PIT and promotion safety helper modules exist but are entirely outside test and CI coverage
- Severity: medium
- Confidence: verified
- Category: test_gap
- Affected: project/reliability/promotion_gate.py, project/reliability/temporal_lint.py, .github/workflows/tier1.yml, .github/workflows/tier2.yml, .github/workflows/tier3.yml
- Evidence: repo search finds definitions for promotion_gate / verify_pit_integrity / temporal_lint, but no tests or workflow invocations.
- Why it matters: Either critical PIT/promotion safety guards are unverified, or dead code creates a false sense of protection.
- Validation: Search project/tests and .github/workflows for promotion_gate and temporal_lint references.
- Remediation: Add narrow deterministic unit tests or remove/deprecate the unused safety-helper surfaces.

### Promotion smoke test contains stale defect commentary that contradicts current runtime behavior
- Severity: low
- Confidence: verified
- Category: docs_drift
- Affected: project/tests/smoke/test_promotion_smoke.py, project/reliability/cli_smoke.py
- Evidence: The test comment still claims run_smoke_cli("promotion") is broken, but runtime full-mode smoke now validates promotion artifacts successfully.
- Why it matters: Stale defect commentary distorts audit and maintenance work even when runtime behavior has improved.
- Validation: Run run_smoke_cli("full") and compare the resulting promotion summary with the stale comment.
- Remediation: Remove/update the stale comment and add an explicit promotion-mode smoke test.
