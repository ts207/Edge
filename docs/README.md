# Edge documentation

This doc set is organized as a spine, not a dump. Each canonical doc owns one question.

The shortest correct operator story is:

`single hypothesis proposal -> plan -> run -> review -> export thesis batch -> explicit runtime selection`

## Canonical spine

Read these first, in order:

1. [00_START_HERE.md](00_START_HERE.md) — shortest onboarding path and first commands
2. [01_PROJECT_MODEL.md](01_PROJECT_MODEL.md) — stable system model and core objects
3. [02_REPOSITORY_MAP.md](02_REPOSITORY_MAP.md) — subsystem map and code ownership
4. [03_OPERATOR_WORKFLOW.md](03_OPERATOR_WORKFLOW.md) — end-to-end operator loop
5. [04_COMMANDS_AND_ENTRY_POINTS.md](04_COMMANDS_AND_ENTRY_POINTS.md) — which surface to run for each job
6. [05_ARTIFACTS_AND_INTERPRETATION.md](05_ARTIFACTS_AND_INTERPRETATION.md) — where outputs land and how to inspect them
7. [06_QUALITY_GATES_AND_PROMOTION.md](06_QUALITY_GATES_AND_PROMOTION.md) — what “good” means and how permission differs from evidence
8. [07_BEST_PRACTICES_AND_FAILURE_MODES.md](07_BEST_PRACTICES_AND_FAILURE_MODES.md) — bounded-work rules and common mistakes
9. [08_TESTING_AND_MAINTENANCE.md](08_TESTING_AND_MAINTENANCE.md) — verification and regeneration rules
10. [09_THESIS_BOOTSTRAP_AND_PROMOTION.md](09_THESIS_BOOTSTRAP_AND_PROMOTION.md) — advanced/internal bootstrap packaging lane
11. [10_APPS_PLUGINS_AND_AGENTS.md](10_APPS_PLUGINS_AND_AGENTS.md) — app, plugin, and specialist-agent surfaces
12. [11_LIVE_THESIS_STORE_AND_OVERLAP.md](11_LIVE_THESIS_STORE_AND_OVERLAP.md) — runtime thesis-batch model
13. [14_PROPOSAL_TO_LIVE_TRADE_TRACE.md](14_PROPOSAL_TO_LIVE_TRADE_TRACE.md) — detailed trace from proposal to live trading eligibility

## What each doc owns

- orientation and first-day path: [00_START_HERE.md](00_START_HERE.md)
- stable mental model: [01_PROJECT_MODEL.md](01_PROJECT_MODEL.md)
- code layout and subsystem boundaries: [02_REPOSITORY_MAP.md](02_REPOSITORY_MAP.md)
- proposal, preflight, plan, run, review, export: [03_OPERATOR_WORKFLOW.md](03_OPERATOR_WORKFLOW.md)
- command selection and preferred surfaces: [04_COMMANDS_AND_ENTRY_POINTS.md](04_COMMANDS_AND_ENTRY_POINTS.md)
- manifests, reports, thesis batches, inspection order: [05_ARTIFACTS_AND_INTERPRETATION.md](05_ARTIFACTS_AND_INTERPRETATION.md)
- evidence ladder, promotion class, deployment state: [06_QUALITY_GATES_AND_PROMOTION.md](06_QUALITY_GATES_AND_PROMOTION.md)
- bounded-work discipline: [07_BEST_PRACTICES_AND_FAILURE_MODES.md](07_BEST_PRACTICES_AND_FAILURE_MODES.md)
- tests, regeneration, and doc-coupled maintenance: [08_TESTING_AND_MAINTENANCE.md](08_TESTING_AND_MAINTENANCE.md)
- bootstrap/package maintenance: [09_THESIS_BOOTSTRAP_AND_PROMOTION.md](09_THESIS_BOOTSTRAP_AND_PROMOTION.md)
- runtime thesis consumption and overlap: [11_LIVE_THESIS_STORE_AND_OVERLAP.md](11_LIVE_THESIS_STORE_AND_OVERLAP.md)

## Recommended reading paths

New operator:

`00 -> 01 -> 03 -> 04 -> 05 -> 06`

Research maintainer:

`01 -> 02 -> 03 -> 04 -> 06 -> 08 -> VERIFICATION.md`

Runtime maintainer:

`01 -> 03 -> 05 -> 06 -> 11 -> 14`

Bootstrap/package maintainer:

`03 -> 05 -> 06 -> 09 -> 11`

## Maintenance and architecture references

Use these when changing contracts, verification behavior, or architectural boundaries:

- [VERIFICATION.md](VERIFICATION.md)
- [AGENT_CONTRACT.md](AGENT_CONTRACT.md)
- [ARCHITECTURAL_BASELINE_B.md](ARCHITECTURAL_BASELINE_B.md)
- [ARCHITECTURE_SURFACE_INVENTORY.md](ARCHITECTURE_SURFACE_INVENTORY.md)
- [ARCHITECTURE_MAINTENANCE_CHECKLIST.md](ARCHITECTURE_MAINTENANCE_CHECKLIST.md)
- [RESEARCH_CALIBRATION_BASELINE.md](RESEARCH_CALIBRATION_BASELINE.md)
- [operator_command_inventory.md](operator_command_inventory.md)

## Generated docs

Generated docs are inventory and evidence, not onboarding.

Important generated surfaces include:

- [generated/system_map.md](generated/system_map.md)
- [generated/event_contract_reference.md](generated/event_contract_reference.md)
- [generated/thesis_overlap_graph.md](generated/thesis_overlap_graph.md)
- [generated/thesis_empirical_summary.md](generated/thesis_empirical_summary.md)
- [generated/founding_thesis_evidence_summary.md](generated/founding_thesis_evidence_summary.md)
- bootstrap-maintenance summaries such as [generated/promotion_seed_inventory.md](generated/promotion_seed_inventory.md), [generated/seed_thesis_catalog.md](generated/seed_thesis_catalog.md), and [generated/seed_thesis_packaging_summary.md](generated/seed_thesis_packaging_summary.md)

## Templates and notes

Templates:

- [templates/bounded_experiment_template.md](templates/bounded_experiment_template.md)
- [templates/experiment_review_template.md](templates/experiment_review_template.md)
- [templates/hypothesis_template.md](templates/hypothesis_template.md)
- [templates/edge_registry_template.md](templates/edge_registry_template.md)

Research notes:

- `docs/research/`

## Documentation rules

- teach the canonical operator story once, then link instead of repeating it
- keep legacy and bootstrap surfaces visible, but clearly marked as compatibility or advanced maintenance
- update the owning canonical doc when behavior changes
- regenerate generated docs instead of editing them by hand
