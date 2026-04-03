# Thesis bootstrap and promotion

This document explains the packaging lane that turns surviving research into packaged thesis objects.

Before using this lane, lock in one rule:

`python -m project.research.export_promoted_theses --run_id <run_id>` is the shortest canonical bridge from one bounded run to one runtime thesis batch.

The bootstrap lane is broader governance/packaging work, not the default path for every operator run.
Treat it as advanced/internal unless you are intentionally maintaining bootstrap-era thesis artifacts or fixture-like packaging summaries.

## Why the bootstrap lane exists

A bounded run can produce promising candidates without producing reusable live/runtime objects.

The bootstrap lane exists to answer a different question:

> Which claims deserve to become packaged theses that the runtime can retrieve and reason over?

That requires more than a good candidate row. It requires evidence packaging, governance metadata, and packaging outputs that downstream systems can consume.

It is not the canonical answer to "how do I produce a runtime batch from run `<run_id>`?".
The canonical answer to that question is still:

```bash
make export RUN_ID=<run_id>
```

If an operator needs an explicit bridge from export into named runtime registration or deployment-state marking, use the module form:

```bash
python -m project.research.export_promoted_theses \
  --run_id <run_id> \
  --register-runtime <name> \
  --set-deployment-state <thesis_id_or_candidate_id>=paper_only|live_enabled
```

## Bootstrap lifecycle

The repo uses this progression:

`candidate -> tested -> seed_promoted -> paper_promoted -> production_promoted`

No thesis should jump from candidate directly to production.

## Canonical bridge before bootstrap

If you already have one promoted run and want runtime-readable output, do this first:

```bash
python -m project.research.export_promoted_theses --run_id <run_id>
```

This writes the explicit runtime batch for that run under `data/live/theses/<run_id>/promoted_theses.json`.

## Bootstrap blocks

### Block A — seed inventory and baseline

Purpose:

- inspect pre-existing thesis-store state
- build the queue of candidate theses worth deeper packaging work
- materialize seed-promotion policy references

Primary scripts:

```bash
python -m project.scripts.build_seed_bootstrap_artifacts
# optional explicit thesis context:
# python -m project.scripts.build_seed_bootstrap_artifacts --thesis_run_id <run_id>
```

Typical outputs:

- `docs/generated/thesis_bootstrap_baseline.md`
- `docs/generated/promotion_seed_inventory.md`
- `docs/generated/promotion_seed_inventory.csv`
- `docs/generated/seed_promotion_policy.md`

### Block B — thesis testing

Purpose:

- score seed candidates on testing readiness and governance-oriented criteria

Primary script:

```bash
python -m project.scripts.build_seed_testing_artifacts
```

### Block C — empirical mapping

Purpose:

- connect actual evidence and scorecards to thesis candidates
- classify where evidence is sufficient, weak, or missing

Primary script:

```bash
python -m project.scripts.build_seed_empirical_artifacts
```

Typical outputs already present in this snapshot include:

- `docs/generated/thesis_empirical_scorecards.csv`
- `docs/generated/thesis_empirical_summary.md`

### Block D — evidence bundle generation

Purpose:

- write canonical evidence bundles for packaging-ready theses

Primary script:

```bash
python -m project.scripts.build_founding_thesis_evidence
```

Current snapshot evidence bundles exist under paths such as:

- `data/reports/promotions/THESIS_VOL_SHOCK/evidence_bundles.jsonl`
- `data/reports/promotions/THESIS_LIQUIDATION_CASCADE/evidence_bundles.jsonl`

### Block E — thesis packaging

Purpose:

- serialize promoted thesis objects into the live thesis store
- generate human-readable packaging summaries

Primary script:

```bash
python -m project.scripts.build_seed_packaging_artifacts
```

Core outputs:

- `data/live/theses/index.json`
- `data/live/theses/<batch>/promoted_theses.json`
- `docs/generated/seed_thesis_catalog.md`
- `docs/generated/seed_thesis_packaging_summary.md`

### Block F — structural confirmation and overlap

Purpose:

- support conservative bridge theses where policy allows it
- build the overlap graph used by downstream allocation logic

Primary scripts:

```bash
python -m project.scripts.build_structural_confirmation_artifacts
python -m project.scripts.build_thesis_overlap_artifacts --run_id <run_id>
```

Outputs already present in this snapshot:

- `docs/generated/structural_confirmation_summary.md`
- `docs/generated/thesis_overlap_graph.md`

## Advanced maintenance shortcut

The maintained bootstrap shortcut is:

```bash
make package
```

This runs the maintained packaging chain in the intended order.

Use it only when repairing or inspecting a particular packaging block.
Do not teach it as the normal answer to "how do I get a runtime thesis batch?".

## How to read bootstrap state

If you are maintaining bootstrap state, inspect in this order:

1. `docs/generated/promotion_seed_inventory.md`
2. `docs/generated/thesis_empirical_summary.md`
3. `docs/generated/founding_thesis_evidence_summary.md`
4. `docs/generated/seed_thesis_catalog.md`
5. `docs/generated/seed_thesis_packaging_summary.md`
6. `docs/generated/thesis_overlap_graph.md`
7. `data/live/theses/index.json`

## Policy implications

- deployment state is the first runtime permission field to inspect
- `seed_promoted` is enough for thesis-store membership and monitor-oriented use.
- `paper_promoted` is stronger but still not equivalent to production.
- `production_promoted` should remain the rare high-bar class.
- Derived or structurally confirmed support must not be treated as equivalent to direct evidence without the policy explicitly allowing it.

## Current snapshot state

This snapshot already contains:

- a packaged thesis store under `data/live/theses/`
- multiple evidence-bundle directories under `data/reports/promotions/`
- generated packaging summaries under `docs/generated/`

So the packaging lane is active and should be documented as present-tense infrastructure, not future work.
