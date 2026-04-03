# Thesis bootstrap and promotion

This document explains the advanced bootstrap/package lane.

Start with the rule that keeps scope clean:

`python -m project.research.export_promoted_theses --run_id <run_id>` is the canonical way to produce a runtime thesis batch from one run.

The bootstrap lane is broader governance and packaging maintenance. It is not the default next step after every good run.

## When to use this lane

Use bootstrap/package work only when you intentionally need to:

- rebuild or inspect broader thesis-governance inventories
- regenerate packaging summaries or evidence bundles
- maintain bootstrap-era catalogs and overlap views
- repair advanced packaging outputs beyond a single run export

If your question is “how do I make runtime read run `<run_id>`?”, use export, not package.

## Canonical bridge before bootstrap

```bash
make export RUN_ID=<run_id>
```

Module form:

```bash
python -m project.research.export_promoted_theses --run_id <run_id>
```

Optional runtime registration and deployment-state controls:

```bash
python -m project.research.export_promoted_theses \
  --run_id <run_id> \
  --register-runtime <name> \
  --set-deployment-state <thesis_id_or_candidate_id>=paper_only|live_enabled
```

## Internal promotion ladder

The bootstrap lane still reasons over:

`candidate -> tested -> seed_promoted -> paper_promoted -> production_promoted`

Treat that as internal evidence/governance vocabulary. Runtime permission still comes from `deployment_state`.

## Bootstrap blocks

### Block A: baseline and seed inventory

Purpose:

- inspect current thesis-store state
- build the bootstrap queue
- materialize policy references

Primary script:

```bash
python -m project.scripts.build_seed_bootstrap_artifacts
```

### Block B: testing artifacts

Primary script:

```bash
python -m project.scripts.build_seed_testing_artifacts
```

### Block C: empirical summaries

Primary script:

```bash
python -m project.scripts.build_seed_empirical_artifacts
```

### Block D: evidence bundles

Primary script:

```bash
python -m project.scripts.build_founding_thesis_evidence
```

### Block E: packaging artifacts

Primary script:

```bash
python -m project.scripts.build_seed_packaging_artifacts
```

This block updates bootstrap-maintenance packaging summaries and thesis-store catalog surfaces.

### Block F: structural confirmation and overlap

Primary scripts:

```bash
python -m project.scripts.build_structural_confirmation_artifacts
python -m project.scripts.build_thesis_overlap_artifacts --run_id <run_id>
```

## Maintenance shortcut

```bash
make package
```

Use it only when you intentionally want the full advanced packaging chain.

## How to inspect bootstrap state

1. `docs/generated/promotion_seed_inventory.md`
2. `docs/generated/thesis_empirical_summary.md`
3. `docs/generated/founding_thesis_evidence_summary.md`
4. `docs/generated/seed_thesis_catalog.md`
5. `docs/generated/seed_thesis_packaging_summary.md`
6. `docs/generated/thesis_overlap_graph.md`
7. `data/live/theses/index.json`

## Policy reminders

- bootstrap/package work does not override explicit runtime selection
- runtime should still be pointed at one run-derived thesis batch explicitly
- `seed_promoted` is not live permission
- `live_enabled` is the only deployment state that may reach trading runtime
