# Stage 3: Promote

Promote is the governance and packaging boundary between validated research and runtime inventory. It answers a stricter question than validation:

"Given that this effect survived falsification, should it become thesis inventory, and if so in what deployment state?"

## What Promote Does

Promotion:

- reads the validation bundle
- selects validated candidates
- assigns promotion class and deployment state
- writes promotion evidence and summary artifacts
- supports explicit export into the live thesis store

Promotion does not itself start the runtime.

## Canonical Commands

### Run promotion

```bash
python -m project.cli promote run --run_id <run_id> --symbols BTCUSDT,ETHUSDT
```

or:

```bash
make promote RUN_ID=<run_id> SYMBOLS=BTCUSDT,ETHUSDT
```

### Export runtime-facing thesis inventory

```bash
python -m project.cli promote export --run_id <run_id>
```

or:

```bash
make export RUN_ID=<run_id>
```

### List promotion artifacts

```bash
python -m project.cli promote list-artifacts --run_id <run_id>
```

## The Important Boundary: Promotion vs Export

Older docs often merged these steps together. The current repo does not.

### `promote run`

Writes research-facing promotion outputs under:

- `data/reports/promotions/<run_id>/`

This is where selection, governance, audit, and summary outputs live.

### `promote export`

Writes runtime-facing thesis inventory under:

- `data/live/theses/<run_id>/promoted_theses.json`
- `data/live/theses/index.json`

This is the batch that `deploy` consumes.

If the docs do not make this separation explicit, operators will confuse "promoted" with "runtime-loadable."

## Main Code Surfaces

- `project/promote/`
- `project/research/services/promotion_service.py`
- `project/research/live_export.py`
- `project/live/contracts/promoted_thesis.py`

## Main Outputs

Promotion artifacts typically include:

- `promoted_candidates.parquet`
- `promotion_summary.json`
- `promotion_report.json`
- `promoted_blueprints.jsonl`
- evidence bundles and audit-related outputs in the same directory

Export then produces:

- `promoted_theses.json`
- thesis batch index entry under `data/live/theses/index.json`

## Promotion Classes And Default Deployment States

The current promotion service maps classes to default deployment states as follows:

| Promotion class | Default deployment state |
|-----------------|--------------------------|
| `paper_promoted` | `paper_only` |
| `production_promoted` | `live_enabled` |

Those defaults matter because deployment behavior and approval requirements are downstream of the assigned thesis state.

## Runtime-Facing Thesis Contract

By the time a candidate is exported, it is no longer just a row in a promotion table. It becomes a `PromotedThesis` object with:

- evidence
- lineage
- governance metadata
- requirements and trigger events
- source metadata
- deployment state
- live approval metadata
- cap profile

That is the actual runtime boundary object.

## Retail Profile

The canonical promotion command supports:

- `--retail_profile` with default `capital_constrained`

The compatibility bridge still exists in lower-level promotion tooling for explicit legacy recovery work, but it is not exposed on the canonical `project.cli promote run` front door.

## Why Promotion Is Separate From Validation

Validation asks:

- is the effect statistically and mechanically credible?

Promotion asks:

- is this worth carrying into operational inventory?
- what class should it receive?
- what deployment state should be attached?
- what evidence and governance metadata must travel with it?

That split is operationally important because not every validated result should become a live-facing thesis.

## Common Outcomes

### No validated candidates

Promotion may complete with zero promoted candidates if validation produced nothing usable.

### Paper-only inventory

A run may export theses that are suitable for paper testing but not live use.

### Live-eligible inventory

A run may export theses whose promotion class maps to live-capable states, but they still have to satisfy runtime gates and batch-level live checks before trading.
