# Component Reference

This file is a package-level reference for the current repository.

It is intentionally organized by package responsibility rather than by individual module filenames. For module-level inventory, use `docs/generated/system_map.json`.

## Top-Level Python Packages

### `project/apps`

App- and pipeline-facing integration surfaces.

### `project/artifacts`

Artifact helpers, baseline support, and artifact-oriented utility code.

### `project/compilers`

Compilation-related support, used where higher-level research outputs are turned into executable or semi-executable forms.

### `project/configs`

Runnable repository configs, including:

- workflow configs
- synthetic configs
- live configs
- retail profiles
- registry defaults

This is not the same as `spec/`.

### `project/contracts`

Contract definitions for:

- stage families
- artifact token relationships
- schema-level expectations

The most important file here is `project/contracts/pipeline_registry.py`.

### `project/core`

Cross-cutting fundamentals:

- configuration roots
- exceptions
- timeframe helpers
- general shared helpers

### `project/domain`

Typed domain models and registry access helpers.

Current domain docs should assume this package is a first-class layer, not a minor helper package.

### `project/engine`

Engine-side execution and strategy handling logic used in strategy packaging and smoke/runtime validation.

### `project/eval`

Evaluation and correctness utilities, including detector verification and related analysis helpers.

### `project/events`

Event system implementation:

- detector implementations
- family aggregations
- canonical mapping
- routing / deconfliction
- registry loading

### `project/execution`

Backtest/runtime execution logic below the research layer.

### `project/experiments`

Experiment-centric code separate from the lower-level pipeline stages.

### `project/features`

Feature generation and feature-side shared logic.

### `project/infra`

Infrastructure and orchestration support code.

### `project/io`

Parquet compatibility, filesystem utilities, and shared IO helpers.

### `project/live`

Live ingest and runtime support package.

### `project/pipelines`

Scriptable stage entry points and orchestrator support.

Notable subpackages:

- `ingest`
- `clean`
- `features`
- `research`
- `runtime`
- `smoke`
- `report`

### `project/portfolio`

Portfolio and allocation support surfaces.

### `project/reliability`

Smoke workflow implementation and artifact validation helpers.

### `project/research`

Primary operator and research logic package.

Important subareas:

- `agent_io`
- `knowledge`
- `services`
- `validation`
- `recommendations`
- `search`
- `reports`
- `robustness`
- `promotion`

### `project/runtime`

Runtime-specific helper surfaces distinct from `project/live`.

### `project/schemas`

Schema definitions and related code-side schema helpers.

### `project/spec_registry`

YAML loading layer used by configs/specs.

### `project/spec_validation`

Validation CLI and validation routines for:

- ontology
- grammar
- search-spec surfaces

### `project/specs`

Code-side spec utilities:

- spec hashing
- ontology hash support
- invariant validation helpers

This package is separate from the repository-root `spec/` tree.

### `project/strategy`

Strategy layer:

- DSL
- runtime
- models
- templates
- compiler

### `project/synthetic_truth`

Synthetic-truth and truth-recovery tooling for calibration workflows.

### `project/tests`

Repository-wide test suite. Major areas include:

- architecture
- artifacts
- contracts
- docs
- domain
- events
- pipelines
- regressions
- replays
- reliability
- research
- runtime
- smoke
- spec validation
- strategy / strategy_dsl / strategy_templates
- synthetic_truth

## Root-Level Non-Python Surfaces

### `spec/`

Canonical YAML spec tree for:

- benchmarks
- concepts
- events
- features
- grammar
- hypotheses
- multiplicity
- objectives
- ontology
- proposals
- runtime
- search
- states
- strategies
- templates

### `docs/generated/`

Machine-generated inventories and audits. Use these instead of copying counts into prose.

### `.github/workflows/`

CI tiers and automation workflows.

### `deploy/`

Deployment templates such as systemd and environment files.
