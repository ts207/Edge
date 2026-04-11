# Edge Documentation

This doc set is the hand-authored documentation spine for the current Edge repository.

The organizing model is still:

`discover → validate → promote → deploy`

But the repo now has several adjacent surfaces that older docs underexplained:

- compatibility operator commands
- trigger-discovery governance
- explicit thesis export into runtime inventory
- live deployment gating and thesis-state lifecycle
- plugin and ChatGPT app interface layers
- generated audit / inventory docs

This index is the current map of that full surface.

## Start Here

Read these first, in order:

1. [00_overview.md](00_overview.md)
2. [01_discover.md](01_discover.md)
3. [02_validate.md](02_validate.md)
4. [03_promote.md](03_promote.md)
5. [04_deploy.md](04_deploy.md)

Those five docs explain the canonical stage story, the command surfaces behind it, and the artifact chain that binds research to runtime.

## What Is Canonical

The canonical public surface is:

- `python -m project.cli discover ...`
- `python -m project.cli validate ...`
- `python -m project.cli promote ...`
- `python -m project.cli deploy ...`

Helpful wrappers:

- `make discover`
- `make validate`
- `make promote`
- `make export`
- `make deploy-paper`
- `make check-hygiene`

Important clarifications:

- `promote export` is the runtime handoff into `data/live/theses/`
- `catalog` and `ingest` are support planes, not extra lifecycle stages
- `operator` is compatibility-only even though it still exists
- the old `pipeline run-all` CLI alias has been removed; use `discover run` or explicit Make wrappers

## If You Need...

### A conceptual model

- [00_overview.md](00_overview.md)
- [06_core_concepts.md](06_core_concepts.md)

### Stage-by-stage operations

- [01_discover.md](01_discover.md)
- [02_validate.md](02_validate.md)
- [03_promote.md](03_promote.md)
- [04_deploy.md](04_deploy.md)
- [operator_command_inventory.md](operator_command_inventory.md)

### Repo structure and subsystem ownership

- [02_REPOSITORY_MAP.md](02_REPOSITORY_MAP.md)
- [90_architecture.md](90_architecture.md)
- [ARCHITECTURE_SURFACE_INVENTORY.md](ARCHITECTURE_SURFACE_INVENTORY.md)

### Data paths, artifacts, and lineage

- [05_data_foundation.md](05_data_foundation.md)
- [02_validate.md](02_validate.md)
- [03_promote.md](03_promote.md)
- [04_deploy.md](04_deploy.md)

### Maintenance, validation, and regression discipline

- `operator_command_inventory.md`
- [92_assurance_and_benchmarks.md](92_assurance_and_benchmarks.md)
- [94_discovery_benchmarks.md](94_discovery_benchmarks.md)

### Advanced internal research lanes

- [91_advanced_research.md](91_advanced_research.md)
- [93_trigger_discovery.md](93_trigger_discovery.md)
- [operator_campaigns.md](operator_campaigns.md)

## Supporting Docs

### Foundations

- [05_data_foundation.md](05_data_foundation.md) — data roots, artifact directories, lineage boundaries
- [06_core_concepts.md](06_core_concepts.md) — glossary for proposals, candidates, theses, states, and evidence

### Architecture and ownership

- [02_REPOSITORY_MAP.md](02_REPOSITORY_MAP.md) — directory-level map of the repo
- [90_architecture.md](90_architecture.md) — current architectural boundaries and control planes

### Operations and commands

- [operator_command_inventory.md](operator_command_inventory.md) — canonical commands, compatibility mappings, and maintenance entrypoints
- [operator_campaigns.md](operator_campaigns.md) — bounded campaign loop in the legacy operator lane

## Generated Docs

`docs/generated/` is the tracked generated contract/reference surface. It is not the primary onboarding surface.

Use generated docs when you need current derived state:

- [generated/system_map.md](generated/system_map.md)
- [generated/event_contract_reference.md](generated/event_contract_reference.md)
- [generated/event_contract_completeness.md](generated/event_contract_completeness.md)
- [generated/event_tiers.md](generated/event_tiers.md)
- [generated/thesis_overlap_graph.md](generated/thesis_overlap_graph.md)

Do not hand-edit generated docs when a generator exists. Use `project/scripts/regenerate_artifacts.sh` for the approved tracked set.

## Templates and Notes

Templates:

- [templates/bounded_experiment_template.md](templates/bounded_experiment_template.md)
- [templates/experiment_review_template.md](templates/experiment_review_template.md)
- [templates/hypothesis_template.md](templates/hypothesis_template.md)
- [templates/edge_registry_template.md](templates/edge_registry_template.md)

Research notes live under `docs/research/`.

## Documentation Rules

- Teach the canonical stage story first, then link outward.
- Mark compatibility and internal research lanes explicitly.
- Prefer code-backed terminology from `project/cli.py`, `project/artifacts/`, and `project/live/contracts/`.
- Treat `project/tests/` as the only supported pytest root; `tmp/` and `live/persist/` are local-only scratch.
- Update the owning hand-authored doc when behavior changes.
- Regenerate generated docs instead of editing them manually.
