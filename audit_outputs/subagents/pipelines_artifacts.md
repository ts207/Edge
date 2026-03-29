# pipelines_artifacts

## Scope
- project/pipelines/
- project/artifacts/
- project/reliability/
- project/contracts/pipeline_registry.py
- project/tests/pipelines/
- project/tests/contracts/
- project/tests/artifacts/
- project/tests/smoke/

## Summary
run_all builds a pipeline plan, validates the static registry, bootstraps a run manifest, then executes stages through pipeline_execution and execution_engine. Success is largely subprocess-exit and stage-manifest-schema based; declared artifact contracts are not reconciled against actual produced files before run success is granted.

## Findings
### Certification mode records strict artifact-safety flags but never enables the environment gates that enforce them
- Severity: high
- Confidence: verified
- Category: contract_integrity
- Affected: project/pipelines/run_all_bootstrap.py, project/io/utils.py, project/pipelines/execution_engine.py, project/pipelines/run_all.py
- Evidence: run_all_bootstrap writes strict_run_scoped_reads and require_stage_manifests into the run manifest, but execution gates in project/io/utils.py and project/pipelines/execution_engine.py only read BACKTEST_STRICT_RUN_SCOPED_READS and BACKTEST_REQUIRE_STAGE_MANIFEST, which run_all never exports.
- Why it matters: Certification mode advertises fail-closed artifact isolation while still allowing the default fallback behavior.
- Validation: Run project.pipelines.run_all in certification mode and inspect both run_manifest.json and the run_all environment-handling code.
- Remediation: Export the enforcement env vars from run_all in certification mode and add an execution-path test that proves the stricter behavior is active.

### build_features can exit success with no inputs, no outputs, and no per-symbol results
- Severity: high
- Confidence: verified
- Category: artifact_integrity
- Affected: project/pipelines/features/build_features.py, project/pipelines/execution_engine.py, project/specs/manifest.py
- Evidence: build_features initializes empty inputs/outputs, continues when cleaned bars are absent, never appends written outputs to the manifest, and still finalizes success. The manifest schema only checks that outputs is a list, not that success manifests declare artifacts.
- Why it matters: A green feature stage can represent zero produced artifacts, which is a false-green path and breaks cache/reconciliation logic.
- Validation: Run project.pipelines.features.build_features against an empty temporary BACKTEST_DATA_ROOT and inspect the emitted stage manifest.
- Remediation: Make zero-produced-symbol runs fail or warn, and require successful manifests to declare existing outputs.

### ingest_binance_um_ohlcv converts total fetch failure into a green stage with only missing-archive stats
- Severity: critical
- Confidence: verified
- Category: correctness
- Affected: project/pipelines/ingest/ingest_binance_um_ohlcv.py, project/pipelines/execution_engine.py
- Evidence: async_main() classifies failed/not_found monthly fetches as missing_archives, raises nothing when all months fail, and main() still finalizes success with empty outputs.
- Why it matters: The root raw-data producer can go green when no requested market data was actually ingested.
- Validation: Monkeypatch _process_month to always return failed/not_found and inspect async_main() and main() behavior.
- Remediation: Treat coverage failure as terminal when required partitions are missing and record actual written partitions into manifest outputs.

### Funding ingestion records missing coverage but still returns success, allowing partial or empty funding artifacts to masquerade as complete
- Severity: high
- Confidence: verified
- Category: artifact_integrity
- Affected: project/pipelines/ingest/ingest_binance_um_funding.py, project/pipelines/features/build_features.py, project/contracts/pipeline_registry.py
- Evidence: ingest_binance_um_funding computes missing_after_all and missing_count, but finalizes success regardless; build_features treats funding as optional, and the registry models funding as optional input for build_features_*.
- Why it matters: A run can appear funding-aware while silently dropping funding-derived signal content.
- Validation: Trace missing_after_all handling in ingest_binance_um_funding.py and build_features funding-read behavior.
- Remediation: Differentiate complete success from partial coverage and add configurable enforcement when funding-derived features are expected.

### Run-manifest reconciliation upgrades failed runs to success without checking declared outputs or artifact existence
- Severity: high
- Confidence: verified
- Category: artifact_integrity
- Affected: project/pipelines/pipeline_provenance.py, project/tests/pipelines/test_run_manifest_reconciliation.py
- Evidence: reconcile_run_manifest_from_stage_manifests() promotes the run to success when all planned stage manifests are terminal, without validating outputs, hashes, or on-disk existence. The tests explicitly encode warning/success-only reconciliation.
- Why it matters: Manual or stale manifests can flip a failed run to success even when artifacts are missing or empty.
- Validation: Create terminal stage manifests with empty/missing outputs for a failed run and call reconcile_run_manifest_from_stage_manifests().
- Remediation: Require reconciliation to validate declared outputs against disk and, ideally, against the artifact contract before promoting the run.
