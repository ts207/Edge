# Repository Map

This file explains where the important logic lives and what each layer owns.

## High-Level Layout

- [project/](/home/irene/Edge/project): Python implementation
- [spec/](/home/irene/Edge/spec): YAML domain specs and policies
- [data/](/home/irene/Edge/data): run outputs, raw lake, reports, artifacts
- [tests/](/home/irene/Edge/tests): top-level tests
- [docs/](/home/irene/Edge/docs): hand-authored documentation

## `project/`

Most day-to-day work lands in these directories:

- [project/pipelines/](/home/irene/Edge/project/pipelines): orchestration, planning, stage execution, manifests
- [project/research/](/home/irene/Edge/project/research): discovery, search, robustness, promotion, reporting, memory
- [project/contracts/](/home/irene/Edge/project/contracts): stage-family and artifact contracts
- [project/engine/](/home/irene/Edge/project/engine): execution engine and ledger infrastructure
- [project/strategy/](/home/irene/Edge/project/strategy): strategy DSL, templates, and models
- [project/core/](/home/irene/Edge/project/core): foundational classes and shared components
- [project/features/](/home/irene/Edge/project/features): feature engineering and event detector implementations
- [project/events/](/home/irene/Edge/project/events): detector loading, event helpers, runtime event semantics
- [project/runtime/](/home/irene/Edge/project/runtime): replay and runtime invariants
- [project/scripts/](/home/irene/Edge/project/scripts): auxiliary scripts and utilities
- [project/reliability/](/home/irene/Edge/project/reliability): smoke and reliability workflows
- [project/domain/](/home/irene/Edge/project/domain): compiled registry model and loader surfaces
- [project/specs/](/home/irene/Edge/project/specs): code-side accessors for YAML specs like gates

## `spec/`

This is the policy and ontology surface. Important areas:

- [spec/events/](/home/irene/Edge/spec/events): event rows and unified registry
- [spec/templates/](/home/irene/Edge/spec/templates): template compatibility
- [spec/grammar/](/home/irene/Edge/spec/grammar): families, states, stress scenarios, interactions, sequences
- [spec/search_space.yaml](/home/irene/Edge/spec/search_space.yaml): default broad search surface
- [spec/gates.yaml](/home/irene/Edge/spec/gates.yaml): phase-2, bridge, and fallback gate policies

## `data/`

Key subtrees:

- `data/lake/raw/...`: raw ingested market data
- `data/runs/<run_id>/`: stage logs and manifests for a run
- `data/reports/<...>/<run_id>/`: stage outputs and summaries
- `data/reports/phase2/<run_id>/search_engine/`: search outputs
- `data/reports/edge_candidates/<run_id>/`: edge export outputs

## Ownership Boundaries

Use these boundaries when debugging:

- orchestration bug: start in [project/pipelines/](/home/irene/Edge/project/pipelines)
- artifact contract mismatch: start in [project/contracts/](/home/irene/Edge/project/contracts)
- detector semantics issue: start in [project/features/](/home/irene/Edge/project/features) and [spec/events/](/home/irene/Edge/spec/events)
- search/robustness/gating issue: start in [project/research/](/home/irene/Edge/project/research) and [spec/gates.yaml](/home/irene/Edge/spec/gates.yaml)

## Highest-Value Files

If you only have time to learn ten files, start with:

- [project/pipelines/run_all.py](/home/irene/Edge/project/pipelines/run_all.py)
- [project/contracts/pipeline_registry.py](/home/irene/Edge/project/contracts/pipeline_registry.py)
- [project/research/phase2_search_engine.py](/home/irene/Edge/project/research/phase2_search_engine.py)
- [project/research/bridge_evaluate_phase2.py](/home/irene/Edge/project/research/bridge_evaluate_phase2.py)
- [project/research/analyze_events.py](/home/irene/Edge/project/research/analyze_events.py)
- [project/features/](/home/irene/Edge/project/features)
- [project/research/knowledge/query.py](/home/irene/Edge/project/research/knowledge/query.py)
- [project/research/agent_io/execute_proposal.py](/home/irene/Edge/project/research/agent_io/execute_proposal.py)
- [spec/events/event_registry_unified.yaml](/home/irene/Edge/spec/events/event_registry_unified.yaml)
- [spec/gates.yaml](/home/irene/Edge/spec/gates.yaml)
