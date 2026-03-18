# Artifacts And Contracts

Artifacts are contracts, not incidental files.

A run is trustworthy only when the expected artifacts exist and reconcile with the manifests and logs that describe them.

## Artifact Layers

### Run Layer

Located under `data/runs/<run_id>/`.

Use it for:

- overall run status
- planned stages
- per-stage manifests
- stage logs
- reconciliation checks

### Research Report Layer

Located under `data/reports/`.

Use it for:

- phase 2 outputs
- candidate exports
- discovery summaries
- promotion audits
- benchmark and comparison reports

### Event Layer

Located under `data/events/<run_id>/`.

Use it for:

- event materialization
- event-level debugging
- detector registry and event report verification

### Lake Layer

Located under `data/lake/runs/<run_id>/`.

Use it for:

- cleaned bars
- feature tables
- context features
- market-state features
- rollups used downstream

## Core Contract Expectations

Normal expectations:

- manifests match actual stage outcomes
- stage success implies the expected outputs exist
- zero-candidate no-op stages are still successful if that is the intended behavior
- exported candidates carry required downstream fields
- split-aware metrics survive into promotion-facing artifacts
- generated diagnostics agree with the code and registry surfaces that produced them

## Failure Classes

### Mechanical Contract Failure

Examples:

- missing input artifact
- stale manifest after replay
- success status with missing outputs
- logs disagree with manifests

### Semantic Contract Failure

Examples:

- field exists but means the wrong thing
- units drift from the canonical definition
- train metrics are computed over all rows
- regime-conditioned outputs duplicate unconditional rows

### Statistical Contract Failure

Examples:

- zero validation or test support
- invalid multiplicity interpretation
- no cost-surviving expectancy

## Trust Order

Inspect in this order:

1. top-level run manifest
2. stage manifests
3. stage logs
4. report artifacts
5. generated diagnostics

If those disagree, treat the disagreement as a first-class finding.

## Required Checks Before Trusting A Run

- top-level run status matches stage outcomes
- candidate counts reconcile across summaries and exports
- declared feature-stage inputs match what the implementation actually reads
- split counts exist where required
- expected artifacts exist where manifests say they do
- detector ownership, registry, and coverage diagnostics agree when relevant
- warning noise does not hide runtime faults

## Response To Contract Breakage

When contracts break:

1. stop broad experimentation
2. isolate the broken path
3. repair the propagation or bookkeeping issue
4. replay the smallest affected chain
5. resume interpretation only after reconciliation

## Operator Rule

Do not call a run good because the command exited with code `0`.

Call it good only when:

- the artifacts exist
- the artifacts reconcile
- the interpretation is being made at the correct layer
