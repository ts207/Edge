# Artifacts And Contracts

## Principle

The agent must treat repository artifacts as durable contracts, not incidental files.

## Primary Artifact Layers

### Run Layer

Located under `data/runs/<run_id>/`.

Use for:

- run status
- planned stage list
- stage manifests
- stage logs
- reconciliation checks

### Research Report Layer

Located under `data/reports/`.

Use for:

- phase 2 candidate outputs
- discovery summaries
- edge candidate exports
- promotion audits
- registry updates

### Event Layer

Located under `data/events/<run_id>/`.

Use for:

- event materialization
- registry manifests
- event-level troubleshooting

### Lake Layer

Located under `data/lake/runs/<run_id>/`.

Use for:

- cleaned bars
- feature tables
- context features
- market context

## Contract Expectations

The agent should expect:

- manifests to match actual terminal stage status
- zero-candidate bridge stages to finalize as successful no-op stages rather than runner failures
- exported candidates to include downstream-required fields
- promotion fallbacks to emit the same normalized candidate contract as the canonical export path
- split-aware metrics to survive into promotion-facing artifacts
- storage writes for durable artifacts to flow through the shared IO helpers rather than direct parquet writes
- warnings to be informative rather than overwhelming

## Contract Failure Classes

### Mechanical Contract Failure

Examples:

- missing input artifact
- stale manifest after replay
- stage success with no outputs
- logs disagree with manifests
- detector registry metadata disagrees with the runnable detector inventory

### Semantic Contract Failure

Examples:

- field exists but carries wrong meaning
- parameter units drift from their canonical meaning, for example bps floors being compared against decimal funding rates
- train metric computed on all rows
- regime-conditioned run contains unconditional duplicates

### Statistical Contract Failure

Examples:

- zero validation/test support
- invalid multiplicity interpretation
- no cost-surviving expectancy

## Required Checks Before Trusting A Run

- top-level run status matches stage outcomes
- candidate counts reconcile across summary/export/promotion
- feature-stage declared inputs match the raw artifacts the implementation can actually read
- split counts are present where required
- artifacts exist where manifests say they do
- detector ownership, registry, and generated coverage diagnostics agree
- warnings do not conceal unexpected runtime faults

## Agent Response To Contract Breakage

When contracts break:

1. stop broad experimentation
2. isolate the failure path
3. repair propagation or bookkeeping
4. replay the smallest affected chain
5. only then resume research interpretation
