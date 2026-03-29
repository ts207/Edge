# Edge Documentation

Start here if you need to understand the repository, run research correctly, or interpret outputs without guessing.

Recommended reading order:

1. [00_START_HERE.md](/home/irene/Edge/docs/00_START_HERE.md)
2. [01_PROJECT_MODEL.md](/home/irene/Edge/docs/01_PROJECT_MODEL.md)
3. [02_REPOSITORY_MAP.md](/home/irene/Edge/docs/02_REPOSITORY_MAP.md)
4. [03_OPERATOR_WORKFLOW.md](/home/irene/Edge/docs/03_OPERATOR_WORKFLOW.md)
5. [04_COMMANDS_AND_ENTRY_POINTS.md](/home/irene/Edge/docs/04_COMMANDS_AND_ENTRY_POINTS.md)
6. [05_ARTIFACTS_AND_INTERPRETATION.md](/home/irene/Edge/docs/05_ARTIFACTS_AND_INTERPRETATION.md)
7. [06_QUALITY_GATES_AND_PROMOTION.md](/home/irene/Edge/docs/06_QUALITY_GATES_AND_PROMOTION.md)
8. [07_BEST_PRACTICES_AND_FAILURE_MODES.md](/home/irene/Edge/docs/07_BEST_PRACTICES_AND_FAILURE_MODES.md)
9. [08_TESTING_AND_MAINTENANCE.md](/home/irene/Edge/docs/08_TESTING_AND_MAINTENANCE.md)
10. [09_WORKED_EXAMPLE_VOL_SHOCK.md](/home/irene/Edge/docs/09_WORKED_EXAMPLE_VOL_SHOCK.md)
11. [10_WORKED_EXAMPLE_MECHANICAL_FAILURE.md](/home/irene/Edge/docs/10_WORKED_EXAMPLE_MECHANICAL_FAILURE.md)
12. [11_AUDIT_MATRIX.md](/home/irene/Edge/docs/11_AUDIT_MATRIX.md)
13. [12_AUDIT_RUN_SCHEDULE.md](/home/irene/Edge/docs/12_AUDIT_RUN_SCHEDULE.md)

Reference surfaces:

- event registry: [spec/events/event_registry_unified.yaml](/home/irene/Edge/spec/events/event_registry_unified.yaml)
- search surface: [spec/search_space.yaml](/home/irene/Edge/spec/search_space.yaml)
- gate policy: [spec/gates.yaml](/home/irene/Edge/spec/gates.yaml)
- stage and artifact contract source: [project/contracts/pipeline_registry.py](/home/irene/Edge/project/contracts/pipeline_registry.py)
- full orchestrator: [project/pipelines/run_all.py](/home/irene/Edge/project/pipelines/run_all.py)

Generated inventories and audits may be written under [docs/generated/](/home/irene/Edge/docs/generated), but hand-authored docs in this directory should explain the system without depending on generated markdown being present.
