# Edge Documentation

Start here if you need to understand the repository, run research correctly, or interpret outputs without guessing.

Recommended reading order:

1. [00_START_HERE.md](/home/irene/Edge/docs/00_START_HERE.md)
2. [01_PROJECT_MODEL.md](/home/irene/Edge/docs/01_PROJECT_MODEL.md) — core objects + glossary
3. [02_REPOSITORY_MAP.md](/home/irene/Edge/docs/02_REPOSITORY_MAP.md)
4. [03_OPERATOR_WORKFLOW.md](/home/irene/Edge/docs/03_OPERATOR_WORKFLOW.md) — canonical loop + exact sequence
5. [04_COMMANDS_AND_ENTRY_POINTS.md](/home/irene/Edge/docs/04_COMMANDS_AND_ENTRY_POINTS.md)
6. [05_ARTIFACTS_AND_INTERPRETATION.md](/home/irene/Edge/docs/05_ARTIFACTS_AND_INTERPRETATION.md)
7. [06_QUALITY_GATES_AND_PROMOTION.md](/home/irene/Edge/docs/06_QUALITY_GATES_AND_PROMOTION.md)
8. [07_BEST_PRACTICES_AND_FAILURE_MODES.md](/home/irene/Edge/docs/07_BEST_PRACTICES_AND_FAILURE_MODES.md)
9. [08_TESTING_AND_MAINTENANCE.md](/home/irene/Edge/docs/08_TESTING_AND_MAINTENANCE.md)

Worked examples:

10. [09_WORKED_EXAMPLE_VOL_SHOCK.md](/home/irene/Edge/docs/09_WORKED_EXAMPLE_VOL_SHOCK.md)
11. [10_WORKED_EXAMPLE_MECHANICAL_FAILURE.md](/home/irene/Edge/docs/10_WORKED_EXAMPLE_MECHANICAL_FAILURE.md)
12. [10b_WORKED_EXAMPLE_ENGINE_BACKTEST.md](/home/irene/Edge/docs/10b_WORKED_EXAMPLE_ENGINE_BACKTEST.md)

Reference:

13. [11_AUDIT_MATRIX.md](/home/irene/Edge/docs/11_AUDIT_MATRIX.md)
14. [12_AUDIT_RUN_SCHEDULE.md](/home/irene/Edge/docs/12_AUDIT_RUN_SCHEDULE.md)
15. [13_TRIGGER_TYPES.md](/home/irene/Edge/docs/13_TRIGGER_TYPES.md)
16. [15_EVENT_REFERENCE.md](/home/irene/Edge/docs/15_EVENT_REFERENCE.md)

Agent and operator contracts:

17. [AGENT_CONTRACT.md](/home/irene/Edge/docs/AGENT_CONTRACT.md) — allowed/forbidden actions, hypothesis definition, verification obligations
18. [VERIFICATION.md](/home/irene/Edge/docs/VERIFICATION.md) — verification script commands
19. [RESEARCH_BACKLOG.md](/home/irene/Edge/docs/RESEARCH_BACKLOG.md) — prioritized research backlog

Architecture references:

20. [ARCHITECTURE_MAINTENANCE_CHECKLIST.md](/home/irene/Edge/docs/ARCHITECTURE_MAINTENANCE_CHECKLIST.md)
21. [ARCHITECTURE_SURFACE_INVENTORY.md](/home/irene/Edge/docs/ARCHITECTURE_SURFACE_INVENTORY.md)
22. [RESEARCH_CALIBRATION_BASELINE.md](/home/irene/Edge/docs/RESEARCH_CALIBRATION_BASELINE.md)

## Operator Templates

For bounded research work, use the templates in `docs/templates/`:

- [hypothesis_template.md](/home/irene/Edge/docs/templates/hypothesis_template.md) — fill in before executing
- [experiment_review_template.md](/home/irene/Edge/docs/templates/experiment_review_template.md) — fill in after executing
- [edge_registry_template.md](/home/irene/Edge/docs/templates/edge_registry_template.md) — update after every run
- [bounded_experiment_template.md](/home/irene/Edge/docs/templates/bounded_experiment_template.md) — lane selection, governance, promotion gates

## Spec Sources

- event registry: [spec/events/event_registry_unified.yaml](/home/irene/Edge/spec/events/event_registry_unified.yaml)
- search surface: [spec/search_space.yaml](/home/irene/Edge/spec/search_space.yaml)
- gate policy: [spec/gates.yaml](/home/irene/Edge/spec/gates.yaml)
- stage and artifact contract source: [project/contracts/pipeline_registry.py](/home/irene/Edge/project/contracts/pipeline_registry.py)
- full orchestrator: [project/pipelines/run_all.py](/home/irene/Edge/project/pipelines/run_all.py)

## Generated Inventories

Generated inventories and audits are written under [docs/generated/](/home/irene/Edge/docs/generated). Hand-authored docs in this directory explain the system without depending on generated markdown being present.
