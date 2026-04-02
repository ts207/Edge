# Repository Map

This file explains where the important logic lives and what each layer owns.
The `project/research/phase2_search_engine.py` module is the canonical planner-owned discovery stage.

## High-level layout

- [project/](../project): Python implementation
- [spec/](../spec): YAML domain specs and policies
- [data/](../data): run outputs, raw lake, reports, artifacts, thesis store
- [tests/](../tests): top-level tests
- [docs/](.): hand-authored documentation

## `project/`

Most day-to-day work lands in these directories:

- [project/pipelines/](../project/pipelines): orchestration, planning, stage execution, manifests
- [project/research/](../project/research): discovery, search, robustness, promotion, reporting, thesis bootstrap, packaging, memory
- [project/episodes/](../project/episodes): episode registry and episode-contract loading
- [project/live/](../project/live): thesis retrieval, context building, decisioning, attribution, OMS integration
- [project/events/](../project/events): detector loading, event helpers, runtime event semantics
- [project/portfolio/](../project/portfolio): overlap graph, budget policy, thesis grouping
- [project/engine/](../project/engine): execution engine and risk allocator infrastructure
- [project/contracts/](../project/contracts): stage-family and artifact contracts
- [project/scripts/](../project/scripts): maintained artifact builders and bootstrap utilities
- [project/reliability/](../project/reliability): smoke and reliability workflows
- [project/domain/](../project/domain): compiled registry model and loader surfaces
- [project/specs/](../project/specs): code-side accessors for YAML specs like gates and policies

### High-value bootstrap modules

- `project/research/campaign_contract.py`
- `project/research/seed_bootstrap.py`
- `project/research/seed_testing.py`
- `project/research/seed_empirical.py`
- `project/research/thesis_evidence_runner.py`
- `project/research/seed_package.py`
- `project/research/derived_confirmation.py`
- `project/research/live_export.py`
- `project/research/meta_ranking.py`
- `project/portfolio/thesis_overlap.py`

## `spec/`

This is the policy and ontology surface. Important areas:

- [spec/events/](../spec/events): event rows and unified registry
- [spec/episodes/](../spec/episodes): episode contracts and registry
- [spec/campaigns/](../spec/campaigns): canonical campaign contract
- [spec/promotion/](../spec/promotion): seed promotion and founding-thesis evaluation policies
- [spec/templates/](../spec/templates): template compatibility
- [spec/grammar/](../spec/grammar): families, states, stress scenarios, interactions, sequences
- [spec/search_space.yaml](../spec/search_space.yaml): default broad search surface
- [spec/gates.yaml](../spec/gates.yaml): phase-2, bridge, and fallback gate policies

## `data/`

Key subtrees:

- `data/lake/raw/...`: raw ingested market data
- `data/runs/<run_id>/`: stage logs and manifests for a run
- `data/reports/<...>/<run_id>/`: stage outputs and summaries
- `data/reports/phase2/<run_id>/search_engine/`: search outputs
- `data/reports/promotions/<thesis_or_run_id>/evidence_bundles.jsonl`: thesis evidence bundles
- `data/live/theses/index.json`: canonical thesis index
- `data/live/theses/<batch>/promoted_theses.json`: packaged thesis batches

## Ownership boundaries

Use these boundaries when debugging:

- orchestration bug: start in [project/pipelines/](../project/pipelines)
- artifact contract mismatch: start in [project/contracts/](../project/contracts)
- detector semantics issue: start in [project/events/](../project/events) and [spec/events/](../spec/events)
- episode packaging issue: start in [project/episodes/](../project/episodes) and [spec/episodes/](../spec/episodes)
- search/robustness/gating issue: start in [project/research/](../project/research) and [spec/gates.yaml](../spec/gates.yaml)
- thesis bootstrap or packaging issue: start in `project/research/seed_*`, `project/research/thesis_evidence_runner.py`, and `project/research/live_export.py`
- overlap or allocator issue: start in [project/portfolio/](../project/portfolio) and [project/engine/](../project/engine)

## Highest-value files

If you only have time to learn ten files, start with:

- [project/pipelines/run_all.py](../project/pipelines/run_all.py)
- [project/contracts/pipeline_registry.py](../project/contracts/pipeline_registry.py)
- [project/research/phase2_search_engine.py](../project/research/phase2_search_engine.py)
- [project/research/services/promotion_service.py](../project/research/services/promotion_service.py)
- [project/research/thesis_evidence_runner.py](../project/research/thesis_evidence_runner.py)
- [project/research/seed_package.py](../project/research/seed_package.py)
- [project/live/retriever.py](../project/live/retriever.py)
- [project/portfolio/thesis_overlap.py](../project/portfolio/thesis_overlap.py)
- [spec/events/event_registry_unified.yaml](../spec/events/event_registry_unified.yaml)
- [spec/promotion/seed_promotion_policy.yaml](../spec/promotion/seed_promotion_policy.yaml)
