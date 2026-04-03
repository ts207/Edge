# Edge documentation

This directory is organized around one question: **what is the shortest correct path from repo orientation to a trustworthy run or explicit runtime thesis batch?**

The documentation set is intentionally split into four classes.

## 1. Canonical operating docs

Read these first.

1. [00_START_HERE.md](00_START_HERE.md) — shortest onboarding path
2. [01_PROJECT_MODEL.md](01_PROJECT_MODEL.md) — system overview, core objects, lifecycle
3. [02_REPOSITORY_MAP.md](02_REPOSITORY_MAP.md) — top-level map and subsystem ownership
4. [03_OPERATOR_WORKFLOW.md](03_OPERATOR_WORKFLOW.md) — proposal issuance, run lifecycle, review flow
5. [04_COMMANDS_AND_ENTRY_POINTS.md](04_COMMANDS_AND_ENTRY_POINTS.md) — what to run and when
6. [05_ARTIFACTS_AND_INTERPRETATION.md](05_ARTIFACTS_AND_INTERPRETATION.md) — where outputs land and how to read them
7. [06_QUALITY_GATES_AND_PROMOTION.md](06_QUALITY_GATES_AND_PROMOTION.md) — quality model, promotion ladder, deployment meaning
8. [07_BEST_PRACTICES_AND_FAILURE_MODES.md](07_BEST_PRACTICES_AND_FAILURE_MODES.md) — bounded-work operating rules and common failure patterns
9. [08_TESTING_AND_MAINTENANCE.md](08_TESTING_AND_MAINTENANCE.md) — test surfaces, regeneration, maintenance workflow
10. [09_THESIS_BOOTSTRAP_AND_PROMOTION.md](09_THESIS_BOOTSTRAP_AND_PROMOTION.md) — advanced internal/bootstrap packaging lane
11. [10_APPS_PLUGINS_AND_AGENTS.md](10_APPS_PLUGINS_AND_AGENTS.md) — app, plugin, and agent surfaces
12. [11_LIVE_THESIS_STORE_AND_OVERLAP.md](11_LIVE_THESIS_STORE_AND_OVERLAP.md) — packaged thesis runtime model
13. [14_PROPOSAL_TO_LIVE_TRADE_TRACE.md](14_PROPOSAL_TO_LIVE_TRADE_TRACE.md) — full proposal-to-runtime and live-trading trace

## 2. Maintenance and architecture references

Use these when changing architecture, contracts, or verification behavior.

- [VERIFICATION.md](VERIFICATION.md)
- [ARCHITECTURE_SURFACE_INVENTORY.md](ARCHITECTURE_SURFACE_INVENTORY.md)
- [ARCHITECTURE_MAINTENANCE_CHECKLIST.md](ARCHITECTURE_MAINTENANCE_CHECKLIST.md)
- [RESEARCH_CALIBRATION_BASELINE.md](RESEARCH_CALIBRATION_BASELINE.md)
- [AGENT_CONTRACT.md](AGENT_CONTRACT.md)
- [operator_command_inventory.md](operator_command_inventory.md)

## 3. Generated inventories and artifact summaries

These files are generated. They are evidence and inventory, not narrative onboarding.

- [generated/system_map.md](generated/system_map.md)
- [generated/event_contract_reference.md](generated/event_contract_reference.md)
- [generated/promotion_seed_inventory.md](generated/promotion_seed_inventory.md) — advanced bootstrap inventory
- [generated/thesis_empirical_summary.md](generated/thesis_empirical_summary.md)
- [generated/seed_thesis_catalog.md](generated/seed_thesis_catalog.md) — advanced bootstrap packaging summary
- [generated/seed_thesis_packaging_summary.md](generated/seed_thesis_packaging_summary.md) — advanced bootstrap packaging summary
- [generated/thesis_overlap_graph.md](generated/thesis_overlap_graph.md)
- [generated/founding_thesis_evidence_summary.md](generated/founding_thesis_evidence_summary.md)
- [generated/structural_confirmation_summary.md](generated/structural_confirmation_summary.md)
- [generated/shadow_live_thesis_summary.md](generated/shadow_live_thesis_summary.md)

## 4. Templates and research notes

Use templates when authoring bounded work. Treat research notes as non-canonical support material.

Templates:

- [templates/bounded_experiment_template.md](templates/bounded_experiment_template.md)
- [templates/experiment_review_template.md](templates/experiment_review_template.md)
- [templates/hypothesis_template.md](templates/hypothesis_template.md)
- [templates/edge_registry_template.md](templates/edge_registry_template.md)

Research notes:

- `docs/research/`

## Recommended reading paths

### New operator

Read `00 -> 01 -> 02 -> 03 -> 04 -> 05`.

### Research maintainer

Read `01 -> 02 -> 03 -> 04 -> 06 -> 08 -> VERIFICATION.md`.

### Thesis/export maintainer

Read `03 -> 05 -> 06 -> 09 -> 11`.

### Live/runtime maintainer

Read `01 -> 02 -> 05 -> 06 -> 11 -> 10`.

## Documentation rules

- Narrative docs explain stable concepts and recommended usage.
- Generated docs reflect current repo or artifact state.
- When a command, path, or policy changes, update the canonical doc that owns that concept.
- Do not create new one-off narrative docs when an existing canonical doc already owns the topic.
