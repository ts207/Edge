# Audit Run Schedule

This is the executable schedule for a full coding-agent audit of the repository.

Target depth:

- `8` runs: minimum credible audit
- `12` runs: strong full audit

This schedule is the `12`-run version.

## Rules

- Stop on the first unresolved mechanical failure.
- Record evidence after every run.
- Do not upgrade a unit to "clean" because a later run happened to pass.
- Separate mechanical, statistical, and deployment conclusions every time.

## Output Convention

Create an audit folder first:

```bash
mkdir -p data/audits/full_repo_audit_$(date +%Y%m%d)
```

For each run, save:

- command used
- stdout/stderr or key artifact path
- pass/fail decision
- next action

## A01: Operator Surface Audit

Purpose:

- verify entry points, docs, and command surfaces are discoverable

Commands:

```bash
make help
.venv/bin/python -m project.research.knowledge.query --help
.venv/bin/python -m project.research.agent_io.execute_proposal --help
.venv/bin/python -m project.research.agent_io.issue_proposal --help
.venv/bin/python -m project.pipelines.run_all --help
```

Evidence:

- [README.md](/home/irene/Edge/README.md)
- [docs/README.md](/home/irene/Edge/docs/README.md)

Pass if:

- all help commands render
- docs and top-level navigation do not point to dead paths

Stop if:

- maintained entry points fail to load

## A02: Architecture And Contract Inventory

Purpose:

- verify static structure and declared stage/artifact surfaces

Commands:

```bash
.venv/bin/python -m pytest project/tests/architecture
```

Evidence:

- [project/contracts/pipeline_registry.py](/home/irene/Edge/project/contracts/pipeline_registry.py)
- [project/contracts/](/home/irene/Edge/project/contracts)
- [project/pipelines/](/home/irene/Edge/project/pipelines)

Pass if:

- architecture tests pass
- no obvious stage-family import breakage

Stop if:

- architecture tests fail

## A03: Spec Governance Audit

Purpose:

- verify spec hygiene and generated inventory consistency

Commands:

```bash
.venv/bin/python project/scripts/spec_qa_linter.py
.venv/bin/python project/scripts/detector_coverage_audit.py --md-out docs/generated/detector_coverage.md --json-out docs/generated/detector_coverage.json --check
.venv/bin/python project/scripts/ontology_consistency_audit.py --output docs/generated/ontology_audit.json --check
```

Evidence:

- [spec/events/event_registry_unified.yaml](/home/irene/Edge/spec/events/event_registry_unified.yaml)
- [spec/gates.yaml](/home/irene/Edge/spec/gates.yaml)
- generated audit files under [docs/generated/](/home/irene/Edge/docs/generated)

Pass if:

- all governance checks pass

Stop if:

- ontology or detector coverage checks fail

## A04: Fast Regression Audit

Purpose:

- verify the maintained fast gate is green

Commands:

```bash
make test-fast
```

Pass if:

- the command completes without failures

Stop if:

- any fast test fails

## A05: Full Smoke Audit

Purpose:

- verify end-to-end orchestration, artifacts, and contract cleanliness

Commands:

```bash
.venv/bin/python -m project.reliability.cli_smoke --mode full --root /tmp/edge_full_audit_smoke
```

Key artifacts:

- `/tmp/edge_full_audit_smoke/reliability/smoke_summary.json`

Pass if:

- smoke summary is written
- engine, research, and promotion smoke all complete

Stop if:

- smoke fails or artifact validation fails

## A06: Synthetic Truth Audit

Purpose:

- verify detector and infrastructure behavior independent of live-market quality

Commands:

```bash
.venv/bin/python -m project.scripts.run_golden_synthetic_discovery
.venv/bin/python -m project.scripts.run_fast_synthetic_certification
.venv/bin/python -m project.scripts.validate_synthetic_detector_truth --run_id golden_synthetic_discovery
```

Pass if:

- synthetic discovery and certification complete
- truth validation does not report detector-truth breakage

Stop if:

- detector truth recovery fails

## A07: Historical Bad-Run Reconciliation

Purpose:

- verify that known historical failure is still diagnosable from artifacts

Target run:

- [codex_real_btc_vol_shock_20260328_4](/home/irene/Edge/data/runs/codex_real_btc_vol_shock_20260328_4)

Actions:

1. read [run_manifest.json](/home/irene/Edge/data/runs/codex_real_btc_vol_shock_20260328_4/run_manifest.json)
2. read [phase2_search_engine.log](/home/irene/Edge/data/runs/codex_real_btc_vol_shock_20260328_4/phase2_search_engine.log)
3. read [discovery_quality_summary.json](/home/irene/Edge/data/reports/phase2/codex_real_btc_vol_shock_20260328_4/discovery_quality_summary.json)
4. read [funnel_summary.json](/home/irene/Edge/data/reports/codex_real_btc_vol_shock_20260328_4/funnel_summary.json)

Pass if:

- you can prove from artifacts that:
  - runtime postflight failed
  - search scope leaked to the broad search surface
  - unrelated families polluted the outputs

Stop if:

- the failure cannot be reconstructed from artifacts alone

## A08: Historical Good-Run Reconciliation

Purpose:

- verify that a known repaired run is mechanically clean and narrowly attributable

Target run:

- [codex_real_btc_vol_shock_202211_202212_20260328_5](/home/irene/Edge/data/runs/codex_real_btc_vol_shock_202211_202212_20260328_5)

Actions:

1. read [run_manifest.json](/home/irene/Edge/data/runs/codex_real_btc_vol_shock_202211_202212_20260328_5/run_manifest.json)
2. read [phase2_diagnostics.json](/home/irene/Edge/data/reports/phase2/codex_real_btc_vol_shock_202211_202212_20260328_5/search_engine/phase2_diagnostics.json)
3. inspect [phase2_candidates.parquet](/home/irene/Edge/data/reports/phase2/codex_real_btc_vol_shock_202211_202212_20260328_5/search_engine/phase2_candidates.parquet)
4. read [funnel_summary.json](/home/irene/Edge/data/reports/codex_real_btc_vol_shock_202211_202212_20260328_5/funnel_summary.json)

Pass if:

- you can prove from artifacts that:
  - runtime postflight passed
  - search was event-scoped
  - only `VOL_SHOCK` appears in the funnel
  - candidates were statistically interesting but bridge-rejected

Stop if:

- the repaired run does not reconcile cleanly

## A09: Narrow Real Rerun Audit

Purpose:

- verify current code still reproduces a known bounded real-run path

Command:

```bash
.venv/bin/python -m project.pipelines.run_all \
  --run_id audit_btc_vol_shock_202211_202212 \
  --symbols BTCUSDT \
  --start 2022-11-01 \
  --end 2022-12-31 \
  --timeframes 5m \
  --run_phase2_conditional 1 \
  --phase2_event_type VOL_SHOCK \
  --run_edge_candidate_universe 1 \
  --run_strategy_builder 0 \
  --run_expectancy_analysis 0 \
  --run_expectancy_robustness 0 \
  --run_recommendations_checklist 0 \
  --run_candidate_promotion 0
```

Pass if:

- run completes
- runtime postflight passes
- phase-2 search stays event-scoped

Stop if:

- postflight fails
- unrelated families dominate outputs

## A10: Search Integrity Audit

Purpose:

- verify narrow event-pinned runs remain narrow

Artifacts to inspect from `A09`:

- `data/reports/phase2/audit_btc_vol_shock_202211_202212/search_engine/resolved_search_spec__VOL_SHOCK.yaml`
- `data/runs/audit_btc_vol_shock_202211_202212/phase2_search_engine.log`
- `data/reports/phase2/audit_btc_vol_shock_202211_202212/discovery_quality_summary.json`

Pass if:

- resolved search spec is event-scoped
- search log does not widen to the global frontier
- discovery summary only contains `VOL_SHOCK`

Stop if:

- broad search leakage reappears

## A11: Bridge Policy Audit

Purpose:

- verify bridge gating is explicit, spec-driven, and visible in outputs

Actions:

1. inspect [spec/gates.yaml](/home/irene/Edge/spec/gates.yaml)
2. inspect [project/specs/gates.py](/home/irene/Edge/project/specs/gates.py)
3. inspect [project/research/search/bridge_adapter.py](/home/irene/Edge/project/research/search/bridge_adapter.py)
4. inspect candidate rows from `A09`

Pass if:

- bridge thresholds in code resolve from spec
- candidate outputs reflect those thresholds coherently

Stop if:

- hardcoded undocumented policy is reintroduced

## A12: Failure-Injection Audit

Purpose:

- verify the repo fails loudly and locally

Recommended injection:

- temporarily point a narrow search run at the broad [spec/search_space.yaml](/home/irene/Edge/spec/search_space.yaml) without event scoping, or
- remove an expected state/feature column from a copied local test fixture and run the targeted test surface

Safe default command for a non-destructive injection audit:

```bash
.venv/bin/python -m pytest -q project/tests/research/test_phase2_search_engine_scope.py project/tests/runtime/test_runtime_postflight.py
```

Pass if:

- the tests prove failure modes are pinned by regression coverage

Higher-strength variant:

- add a temporary local patch that breaks event scoping or postflight semantics and confirm the targeted tests fail before reverting your own patch

Stop if:

- known historical failure classes are not pinned by tests

## Completion Criteria

The project is strongly audited for a coding agent when:

1. `A01-A06` all pass
2. `A07-A08` both reconstruct the intended historical conclusions
3. `A09-A10` confirm current narrow-run behavior
4. `A11` confirms gate policy is spec-driven
5. `A12` confirms critical regressions are pinned

If any of these fail, the correct outcome is not "audit complete with caveats." The correct outcome is:

- `repair`
- rerun the failed audit
- only then continue

## Minimal 8-Run Variant

If time is constrained, run:

- `A01`
- `A02`
- `A03`
- `A04`
- `A05`
- `A06`
- `A08`
- `A09`

That is the minimum credible audit. It is not the strongest audit.
