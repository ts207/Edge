# Repo Map

## High-level architecture
- Research proposals enter through `project/research/agent_io/proposal_schema.py`, `project/research/agent_io/proposal_to_experiment.py`, and `project/research/agent_io/execute_proposal.py`.
- Pipeline orchestration is centralized in `project/pipelines/run_all.py`, with planning in `project/pipelines/planner.py` and family builders in `project/pipelines/stages/*.py`.
- Search and inference live under `project/research/search/*`, `project/research/validation/*`, and service wrappers in `project/research/services/*`.
- Promotion and packaging use `project/research/services/promotion_service.py`, `project/research/compile_strategy_blueprints.py`, and `project/strategy/*`.
- Runtime and live execution use `project/engine/*`, `project/live/*`, `project/runtime/*`, and `project/scripts/run_live_engine.py`.
- Governance artifacts and audit surfaces sit under `docs/generated/`, `project/contracts/*`, `project/reliability/*`, and `project/scripts/*`.

## Stage-family map
- `proposal`: `project/research/agent_io/*`, `project/research/experiment_engine.py`, `project/research/experiment_engine_validators.py`
- `search`: `project/research/search/*`, `project/spec_validation/search.py`, `spec/search*.yaml`, `spec/search_space.yaml`
- `validation`: `project/research/validation/*`, `project/research/services/candidate_discovery_scoring.py`, `project/research/search/validation.py`
- `promotion`: `project/research/services/promotion_service.py`, `project/specs/gates.py`, `spec/gates.yaml`
- `blueprint/spec`: `project/research/compile_strategy_blueprints.py`, `project/strategy/*`, `spec/events/*`, `spec/ontology/templates/template_registry.yaml`, `spec/grammar/*`
- `engine/live`: `project/engine/*`, `project/live/*`, `project/runtime/*`, `project/scripts/run_live_engine.py`

## Actual critical path
1. Proposal issuance and translation: `project/research/agent_io/proposal_to_experiment.py`, `project/research/agent_io/execute_proposal.py`
2. Pipeline plan creation: `project/pipelines/run_all.py`, `project/pipelines/pipeline_planning.py`, `project/pipelines/planner.py`
3. Raw/core data stages: `project/pipelines/ingest/*`, `project/pipelines/clean/*`, `project/pipelines/features/*`
4. Event and search stages: `project/pipelines/research/analyze_events.py`, `build_event_registry.py`, `canonicalize_event_episodes.py`, `phase2_search_engine.py`
5. Validation and promotion: `project/research/search/evaluator.py`, `project/research/validation/*`, `project/research/services/promotion_service.py`
6. Strategy packaging: `project/research/compile_strategy_blueprints.py`, `project/strategy/models/executable_strategy_spec.py`
7. Engine and live runtime: `project/engine/runner.py`, `project/live/runner.py`, `project/runtime/invariants.py`

## Where artifacts are produced and consumed
- Run manifests: `data/runs/<run_id>/run_manifest.json`, stage manifests under the same run tree.
- Search outputs: `data/reports/phase2/<run_id>/...` plus compatibility support for nested `search_engine/` layouts in `project/artifacts/catalog.py`.
- Promotion outputs: promotion bundles, decisions, and evidence artifacts written by `project/research/services/promotion_service.py`.
- Blueprint/runtime outputs: blueprint JSONL and executable strategy contracts from `project/research/compile_strategy_blueprints.py` and `project/research/compile_strategy_blueprints_artifacts.py`.
- Runtime artifacts: replay/normalized event outputs and postflight audits under `project/pipelines/runtime/*` and `project/runtime/invariants.py`.
- Governance artifacts: `docs/generated/*`, but these are not runtime inputs.

## Boundary hotspots
- Static contract surface vs real planner: `project/contracts/pipeline_registry.py` vs `project/pipelines/stages/*`
- Search split semantics vs experiment-config path: `project/research/search/evaluator.py` vs `project/research/experiment_engine_validators.py`
- Spec defaults vs compiled registry: `spec/ontology/templates/template_registry.yaml` vs `project/domain/models.py`
- Runtime safety gates vs monitor-only docs/config: `project/scripts/run_live_engine.py`, `project/live/runner.py`, `project/live/oms.py`
- Artifact verification vs manifest status: `project/pipelines/pipeline_provenance.py`, `project/runtime/invariants.py`, `project/scripts/ontology_consistency_audit.py`
- Operator entrypoints vs hidden prerequisites: `project/scripts/run_live_engine.py`, `project/scripts/run_benchmark_matrix.py`, `project/scripts/run_researcher_verification.py`
