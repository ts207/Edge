# Edge documentation

This doc set is organized around the unified 4-stage public operating model:

`discover → validate → promote → deploy`

## Baseline State Inventory
- **Current Canonical Model:** The 4-stage pipeline defined in `project/cli.py` and `docs/00_overview.md`.
- **Current Compatibility Model:** The legacy `operator` CLI and related abstractions which wrap the older research loop model.
- **Known Drift:** We are in the process of deprecating the older "founding seed" documentation paths.
- **Current Registry State:** Event metadata is authored per event under `spec/events/*.yaml`, compiled into `spec/events/event_registry_unified.yaml`, and then projected into `spec/domain/domain_graph.yaml`.
- **Current Runtime Gate:** Research-generated ideas do not become deployable until they pass the explicit `discover -> validate -> promote -> deploy` artifact chain.

## Canonical spine

Read these first, in order:

1. [00_overview.md](00_overview.md) — System model, the 4 stages, and core objects
2. [01_discover.md](01_discover.md) — Generating candidates and issuing structured proposals
3. [02_validate.md](02_validate.md) — Truth-testing candidates, cost-sensitivity, robust stability
4. [03_promote.md](03_promote.md) — Packaging robust candidates into trading theses 
5. [04_deploy.md](04_deploy.md) — Running promoted theses in paper or live mode with explicit deployment-state gating

## Supplementary Foundations

- Data access and ingest: [05_data_foundation.md](05_data_foundation.md)
- Definitions and primitives: [06_core_concepts.md](06_core_concepts.md)
- Subsystem map: [02_REPOSITORY_MAP.md](02_REPOSITORY_MAP.md)

## Maintenance and Architecture References

- [90_architecture.md](90_architecture.md) — High-level architecture decisions
- [91_advanced_research.md](91_advanced_research.md) — Advanced topics (Internal maintenance lane)
- [92_assurance_and_benchmarks.md](92_assurance_and_benchmarks.md) — Maintenance checks and tests
- [93_trigger_discovery.md](93_trigger_discovery.md) — Advanced Trigger Discovery (Internal research lane)
- [ARCHITECTURE_SURFACE_INVENTORY.md](ARCHITECTURE_SURFACE_INVENTORY.md) — Surface API boundaries

## Generated docs

Generated docs are inventory and evidence, not onboarding.
Important generated surfaces include:

- [generated/system_map.md](generated/system_map.md)
- [generated/event_contract_reference.md](generated/event_contract_reference.md)
- [generated/event_contract_completeness.md](generated/event_contract_completeness.md)
- [generated/event_tiers.md](generated/event_tiers.md)
- [operator_command_inventory.md](operator_command_inventory.md)

## Templates and notes

Templates:
- [templates/bounded_experiment_template.md](templates/bounded_experiment_template.md)
- [templates/experiment_review_template.md](templates/experiment_review_template.md)
- [templates/hypothesis_template.md](templates/hypothesis_template.md)
- [templates/edge_registry_template.md](templates/edge_registry_template.md)

Research notes:
- `docs/research/`

## Documentation rules

- teach the canonical 4-stage operator story once, then link instead of repeating it
- keep legacy and bootstrap surfaces visible, but clearly marked as compatibility or advanced maintenance
- update the owning canonical doc when behavior changes
- regenerate generated docs instead of editing them by hand
