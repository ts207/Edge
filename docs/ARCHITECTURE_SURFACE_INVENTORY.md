# Architecture Surface Inventory

Use this file for quick orientation.

## Primary Runtime Surfaces

- orchestrator
  - `project/pipelines/run_all.py`
- stage and artifact contracts
  - `project/contracts/pipeline_registry.py`
- planning
  - `project/pipelines/pipeline_planning.py`
- execution
  - `project/pipelines/pipeline_execution.py`
- provenance and manifest handling
  - `project/pipelines/pipeline_provenance.py`
- pipeline audit / summary
  - `project/pipelines/pipeline_audit.py`
  - `project/pipelines/pipeline_summary.py`

## Research Surfaces

- proposal schema and translation
  - `project/research/agent_io/`
- knowledge and memory
  - `project/research/knowledge/`
- services
  - `project/research/services/`
- validation
  - `project/research/validation/`

## Event / Ontology Surfaces

- detector implementations
  - `project/events/detectors/`
- grouped family surfaces
  - `project/events/families/`
- event specs and mapping
  - `project/events/event_specs.py`
  - `project/events/ontology_mapping.py`
  - `project/events/ontology_deconfliction.py`
- routing
  - `project/research/regime_routing.py`

## Strategy / Engine / Live

- strategy layer
  - `project/strategy/`
- engine layer
  - `project/engine/`
- live runtime
  - `project/live/`
  - `project/scripts/run_live_engine.py`

## Reliability and Generated Audit Surfaces

- smoke CLI
  - `project/reliability/cli_smoke.py`
- generated docs
  - `docs/generated/`
- maintenance scripts
  - `project/scripts/`

## Spec and Config Surfaces

- domain specs
  - `spec/`
- runnable configs
  - `project/configs/`
- YAML loading / validation
  - `project/spec_registry/`
  - `project/spec_validation/`
  - `project/specs/`
