# Pipelines Layer (`project/pipelines`)

The pipelines layer handles data ingestion, feature generation, orchestration, manifest bookkeeping, and stage execution.

## Ownership

- `run_all.py` and its helper modules for full-pipeline orchestration
- ingestion, clean, feature, and context stage scripts
- pipeline planning, execution, provenance, and summary utilities
- research-facing stage entrypoints under `project/pipelines/research/`

## Non-Ownership

- detector business logic
- research policy and promotion rules
- low-latency runtime execution
- schema ownership for stage and artifact contracts

## Important Modules

- `run_all.py`
- `run_all_bootstrap.py`
- `run_all_support.py`
- `run_all_finalize.py`
- `run_all_provenance.py`
- `execution_engine.py`
- `execution_engine_support.py`
- `pipeline_planning.py`
- `pipeline_execution.py`
- `pipeline_provenance.py`
- `pipeline_summary.py`

## Explicit Package Surfaces

The layer now exposes package-root entrypoint groups for active stage families:

- `project.pipelines.clean`
- `project.pipelines.features`
- `project.pipelines.ingest`
- `project.pipelines.smoke`

These package roots should stay lightweight. They exist to make stage-family imports explicit, not to become new orchestration layers.

## Constraints

- Each stage should communicate through declared artifacts rather than shared in-memory state.
- Wrappers should stay thin when a canonical service module already exists.
- Orchestration code should remain coordinator-oriented rather than absorbing domain logic.
- If a pipeline module grows large, extract pure support helpers before weakening size or import-boundary guardrails.
