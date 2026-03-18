# Research Docs

This repository is operated as a research system, not a general-purpose backtest sandbox.

Use this docs set to answer four questions:

1. What is the repo for?
2. How should an operator run research safely?
3. How should results be interpreted?
4. Which docs are policy, reference, or machine output?

## Start Here

If you are a new operator, read in this order:

1. [Root Operator Guide](../CLAUDE.md)
2. [Research Operator Playbook](./RESEARCH_OPERATOR_PLAYBOOK.md)
3. [Autonomous Research Loop](./AUTONOMOUS_RESEARCH_LOOP.md)
4. [Experiment Protocol](./EXPERIMENT_PROTOCOL.md)
5. [Artifacts And Contracts](./ARTIFACTS_AND_CONTRACTS.md)
6. [Operations And Guardrails](./OPERATIONS_AND_GUARDRAILS.md)

That sequence is the minimum onboarding path.

## Read By Task

Use these docs when you need to answer a specific operator question.

### I am new and need the repo mental model

- [Root Operator Guide](../CLAUDE.md)
- [Research Operator Playbook](./RESEARCH_OPERATOR_PLAYBOOK.md)
- [Event Families, Templates, Contexts, And Regimes](./FAMILIES_TEMPLATES_AND_REGIMES.md)

### I need to run one disciplined research loop

- [Autonomous Research Loop](./AUTONOMOUS_RESEARCH_LOOP.md)
- [Experiment Protocol](./EXPERIMENT_PROTOCOL.md)
- [Research Workflow Example](./RESEARCH_WORKFLOW_EXAMPLE.md)

### I need to understand how to communicate and decide

- [Interaction Protocol](./INTERACTION_PROTOCOL.md)
- [Memory And Reflection](./MEMORY_AND_REFLECTION.md)

### I need to trust or debug a run

- [Artifacts And Contracts](./ARTIFACTS_AND_CONTRACTS.md)
- [Operations And Guardrails](./OPERATIONS_AND_GUARDRAILS.md)

### I need to work with synthetic data

- [Synthetic Datasets](./SYNTHETIC_DATASETS.md)
- [Research Calibration Baseline](./RESEARCH_CALIBRATION_BASELINE.md)

### I need ontology or feature reference

- [Event Families, Templates, Contexts, And Regimes](./FAMILIES_TEMPLATES_AND_REGIMES.md)
- [Feature Catalog](./FEATURE_CATALOG.md)

### I need roadmap context

- [Future Milestones](./FUTURE_MILESTONES.md)
- [Benchmark Status](./BENCHMARK_STATUS.md)

### I need the current maintained benchmark baseline

- [Benchmark Status](./BENCHMARK_STATUS.md)
- [Research Operator Playbook](./RESEARCH_OPERATOR_PLAYBOOK.md)

Current verified artifact baseline:

- [/tmp/benchmark_research_family_v1_post_zscore_20260318/benchmark_review.json](/tmp/benchmark_research_family_v1_post_zscore_20260318/benchmark_review.json)

## Core Policy Docs

These are the maintained operator policy docs.

- [Root Operator Guide](../CLAUDE.md)
- [Research Operator Playbook](./RESEARCH_OPERATOR_PLAYBOOK.md)
- [Autonomous Research Loop](./AUTONOMOUS_RESEARCH_LOOP.md)
- [Interaction Protocol](./INTERACTION_PROTOCOL.md)
- [Experiment Protocol](./EXPERIMENT_PROTOCOL.md)
- [Artifacts And Contracts](./ARTIFACTS_AND_CONTRACTS.md)
- [Memory And Reflection](./MEMORY_AND_REFLECTION.md)
- [Operations And Guardrails](./OPERATIONS_AND_GUARDRAILS.md)
- [Synthetic Datasets](./SYNTHETIC_DATASETS.md)

## Reference Docs

These explain ontology, examples, baseline expectations, and future direction.

- [Event Families, Templates, Contexts, And Regimes](./FAMILIES_TEMPLATES_AND_REGIMES.md)
- [Feature Catalog](./FEATURE_CATALOG.md)
- [Benchmark Status](./BENCHMARK_STATUS.md)
- [Research Workflow Example](./RESEARCH_WORKFLOW_EXAMPLE.md)
- [Research Calibration Baseline](./RESEARCH_CALIBRATION_BASELINE.md)
- [Future Milestones](./FUTURE_MILESTONES.md)

## Architecture And Maintenance Docs

These are for repo maintenance, package boundaries, and contract inventory.

- [Architecture Surface Inventory](./ARCHITECTURE_SURFACE_INVENTORY.md)
- [Architecture Maintenance Checklist](./ARCHITECTURE_MAINTENANCE_CHECKLIST.md)

## Machine-Owned Diagnostics

The files under `docs/generated/` are generated diagnostics, not authored policy docs.

Treat them as evidence surfaces:

- `detector_coverage.*`: detector inventory and coverage state
- `system_map.*`: stage, service, and ownership structure
- `ontology_audit.json`: ontology consistency output
- `architecture_metrics.json`: architecture summary metrics

Do not edit generated files manually. Regenerate them from the code and contract surfaces that own them.
