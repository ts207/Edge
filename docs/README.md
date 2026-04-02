# Edge Documentation

Start here if you need to understand the repository, run research correctly, or interpret outputs without guessing.

## Current state

The repo now has two connected lanes:

1. **bounded experiment lane** — proposal -> plan -> run -> diagnose -> keep/modify/kill
2. **thesis bootstrap lane** — seed inventory -> testing -> empirical evidence -> packaging -> thesis store -> overlap graph

Read the bounded lane first, then the bootstrap lane if you are trying to populate or maintain the canonical thesis store.

## Recommended reading order

1. [00_START_HERE.md](00_START_HERE.md)
2. [01_PROJECT_MODEL.md](01_PROJECT_MODEL.md) — core objects + glossary
3. [02_REPOSITORY_MAP.md](02_REPOSITORY_MAP.md)
4. [03_OPERATOR_WORKFLOW.md](03_OPERATOR_WORKFLOW.md) — canonical loop + thesis bootstrap lane
5. [04_COMMANDS_AND_ENTRY_POINTS.md](04_COMMANDS_AND_ENTRY_POINTS.md)
6. [05_ARTIFACTS_AND_INTERPRETATION.md](05_ARTIFACTS_AND_INTERPRETATION.md)
7. [06_QUALITY_GATES_AND_PROMOTION.md](06_QUALITY_GATES_AND_PROMOTION.md)
8. [07_BEST_PRACTICES_AND_FAILURE_MODES.md](07_BEST_PRACTICES_AND_FAILURE_MODES.md)
9. [08_TESTING_AND_MAINTENANCE.md](08_TESTING_AND_MAINTENANCE.md)
10. [09_THESIS_BOOTSTRAP_AND_PROMOTION.md](09_THESIS_BOOTSTRAP_AND_PROMOTION.md)
11. [11_LIVE_THESIS_STORE_AND_OVERLAP.md](11_LIVE_THESIS_STORE_AND_OVERLAP.md)

## Worked examples

- [10b_WORKED_EXAMPLE_ENGINE_BACKTEST.md](10b_WORKED_EXAMPLE_ENGINE_BACKTEST.md)

## Reference

- [13_TRIGGER_TYPES.md](13_TRIGGER_TYPES.md)
- [15_EVENT_REFERENCE.md](15_EVENT_REFERENCE.md)

## Agent and operator contracts

- [AGENT_CONTRACT.md](AGENT_CONTRACT.md) — allowed/forbidden actions, hypothesis definition, thesis lifecycle restrictions, verification obligations
- [VERIFICATION.md](VERIFICATION.md) — verification script commands

## Architecture references

- [ARCHITECTURE_MAINTENANCE_CHECKLIST.md](ARCHITECTURE_MAINTENANCE_CHECKLIST.md)
- [ARCHITECTURE_SURFACE_INVENTORY.md](ARCHITECTURE_SURFACE_INVENTORY.md)
- [RESEARCH_CALIBRATION_BASELINE.md](RESEARCH_CALIBRATION_BASELINE.md)
- [chatgpt_apps_sdk_plan.md](chatgpt_apps_sdk_plan.md)

## Operator templates

For bounded research work, use the templates in `docs/templates/`:

- [hypothesis_template.md](templates/hypothesis_template.md) — fill in before executing
- [experiment_review_template.md](templates/experiment_review_template.md) — fill in after executing
- [edge_registry_template.md](templates/edge_registry_template.md) — update after every run
- [bounded_experiment_template.md](templates/bounded_experiment_template.md) — lane selection, governance, promotion gates

## Spec sources

- event registry: [spec/events/event_registry_unified.yaml](../spec/events/event_registry_unified.yaml)
- episode registry: [spec/episodes/episode_registry.yaml](../spec/episodes/episode_registry.yaml)
- campaign contract: [spec/campaigns/campaign_contract_v1.yaml](../spec/campaigns/campaign_contract_v1.yaml)
- seed promotion policy: [spec/promotion/seed_promotion_policy.yaml](../spec/promotion/seed_promotion_policy.yaml)
- founding thesis evaluation policy: [spec/promotion/founding_thesis_eval_policy.yaml](../spec/promotion/founding_thesis_eval_policy.yaml)
- search surface: [spec/search_space.yaml](../spec/search_space.yaml)
- gate policy: [spec/gates.yaml](../spec/gates.yaml)
- stage and artifact contract source: [project/contracts/pipeline_registry.py](../project/contracts/pipeline_registry.py)
- full orchestrator: [project/pipelines/run_all.py](../project/pipelines/run_all.py)

## Generated inventories

Generated inventories and audits are written under [docs/generated/](generated). Hand-authored docs in this directory explain the system without depending on generated markdown being present.

Pay special attention to:

- `control_plane_inventory.*`
- `promotion_seed_inventory.*`
- `thesis_testing_scorecards.*`
- `thesis_empirical_scorecards.*`
- `seed_thesis_catalog.md`
- `seed_thesis_packaging_summary.*`
- `thesis_overlap_graph.*`
