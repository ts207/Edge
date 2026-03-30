# Edge Documentation

Start here if you need to understand the repository, run research correctly, or interpret outputs without guessing.

Recommended reading order:

1. [00_START_HERE.md](00_START_HERE.md)
2. [01_PROJECT_MODEL.md](01_PROJECT_MODEL.md) — core objects + glossary
3. [02_REPOSITORY_MAP.md](02_REPOSITORY_MAP.md)
4. [03_OPERATOR_WORKFLOW.md](03_OPERATOR_WORKFLOW.md) — canonical loop + exact sequence
5. [04_COMMANDS_AND_ENTRY_POINTS.md](04_COMMANDS_AND_ENTRY_POINTS.md)
6. [05_ARTIFACTS_AND_INTERPRETATION.md](05_ARTIFACTS_AND_INTERPRETATION.md)
7. [06_QUALITY_GATES_AND_PROMOTION.md](06_QUALITY_GATES_AND_PROMOTION.md)
8. [07_BEST_PRACTICES_AND_FAILURE_MODES.md](07_BEST_PRACTICES_AND_FAILURE_MODES.md)
9. [08_TESTING_AND_MAINTENANCE.md](08_TESTING_AND_MAINTENANCE.md)

Worked examples:


12. [10b_WORKED_EXAMPLE_ENGINE_BACKTEST.md](10b_WORKED_EXAMPLE_ENGINE_BACKTEST.md)

Reference:


15. [13_TRIGGER_TYPES.md](13_TRIGGER_TYPES.md)
16. [15_EVENT_REFERENCE.md](15_EVENT_REFERENCE.md)

Agent and operator contracts:

17. [AGENT_CONTRACT.md](AGENT_CONTRACT.md) — allowed/forbidden actions, hypothesis definition, verification obligations
18. [VERIFICATION.md](VERIFICATION.md) — verification script commands


Architecture references:

20. [ARCHITECTURE_MAINTENANCE_CHECKLIST.md](ARCHITECTURE_MAINTENANCE_CHECKLIST.md)
21. [ARCHITECTURE_SURFACE_INVENTORY.md](ARCHITECTURE_SURFACE_INVENTORY.md)
22. [RESEARCH_CALIBRATION_BASELINE.md](RESEARCH_CALIBRATION_BASELINE.md)

## Operator Templates

For bounded research work, use the templates in `docs/templates/`:

- [hypothesis_template.md](templates/hypothesis_template.md) — fill in before executing
- [experiment_review_template.md](templates/experiment_review_template.md) — fill in after executing
- [edge_registry_template.md](templates/edge_registry_template.md) — update after every run
- [bounded_experiment_template.md](templates/bounded_experiment_template.md) — lane selection, governance, promotion gates

## Spec Sources

- event registry: [spec/events/event_registry_unified.yaml](../spec/events/event_registry_unified.yaml)
- search surface: [spec/search_space.yaml](../spec/search_space.yaml)
- gate policy: [spec/gates.yaml](../spec/gates.yaml)
- stage and artifact contract source: [project/contracts/pipeline_registry.py](../project/contracts/pipeline_registry.py)
- full orchestrator: [project/pipelines/run_all.py](../project/pipelines/run_all.py)

## Generated Inventories

Generated inventories and audits are written under [docs/generated/](generated). Hand-authored docs in this directory explain the system without depending on generated markdown being present.
