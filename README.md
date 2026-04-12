# Edge

Edge is a bounded crypto research and execution platform organized around the canonical lifecycle:

**discover → validate → promote → deploy**

The platform turns a hypothesis into a governed live artifact rather than pushing raw ideas directly into execution.

## Core model

A hypothesis is expressed in three layers:

- **Anchor**: the event or trigger family that defines when the hypothesis is eligible to fire.
- **Filter**: the conditioning logic that narrows the hypothesis to the context where it is expected to hold.
- **Thesis**: the promoted, governed live object emitted after validation and promotion.

The repo intentionally uses *thesis* as the deployment object. Discovery can generate many candidates, but only promoted theses are eligible for runtime use.

## Canonical surfaces

Primary CLI entry point:

```bash
python project/cli.py --help
```

Core commands:

```bash
python project/cli.py discover --help
python project/cli.py validate --help
python project/cli.py promote --help
python project/cli.py deploy --help
```

Additional operational surfaces:

- `ingest` for raw market data ingestion
- `catalog` for artifact inspection and run intelligence
- export and certification helpers under `project/scripts/` for live-thesis packaging and control-plane checks

## Repository layout

- `project/` — application, research, runtime, contracts, and operator logic
- `spec/` — proposals, event specs, template registries, and bounded search definitions
- `dashboard/` — operator and inspection UI surface
- `plugins/edge-agents/` — repo-local plugin wrappers and guardrails
- `data/` — local artifacts, reports, and live-thesis materializations used by smoke and integration workflows

## Operational contract

1. **Discover** generates bounded candidates from proposals and event families.
2. **Validate** truth-tests candidates on holdout data and robustness gates.
3. **Promote** turns validated results into governance-aware deployment material.
4. **Deploy** consumes only promoted theses and enforces runtime gates.

Promotion and deployment are intentionally separated. A candidate that exists in research storage is not deployable until promotion artifacts and deployment checks are satisfied.

## Where to read next

- `docs/README.md`
- `docs/00_overview.md`
- `docs/01_discover.md`
- `docs/02_validate.md`
- `docs/03_promote.md`
- `docs/04_deploy.md`
- `docs/02_REPOSITORY_MAP.md`
- `docs/operator_command_inventory.md`
- `docs/90_architecture.md`
- `docs/92_assurance_and_benchmarks.md`
