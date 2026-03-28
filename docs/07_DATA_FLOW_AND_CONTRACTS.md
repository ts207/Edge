# Data Flow and Contracts

## Contract Source of Truth

Stage-family and artifact-token contracts live in:

- `project/contracts/pipeline_registry.py`

Do not treat prose descriptions as authoritative when that file says otherwise.

## Stage Family Contract Model

Two important registries exist in code:

- stage family registry
- stage artifact registry

The stage family registry maps:

- stage name patterns
- script path patterns
- family ownership

The artifact registry maps:

- required inputs
- optional inputs
- outputs
- external inputs

This lets the planner validate execution structure before the run starts.

## Current Stage Families

Current family names:

- `ingest`
- `core`
- `runtime_invariants`
- `phase1_analysis`
- `phase2_event_registry`
- `phase2_discovery`
- `promotion`
- `research_quality`
- `strategy_packaging`

This is the correct architectural vocabulary for current runs.

## Artifact Token Style

Artifact contracts use named tokens rather than only concrete paths.

Examples from the registry:

- `raw.perp.ohlcv_{tf}`
- `raw.spot.ohlcv_{tf}`
- `raw.perp.funding_{tf}`
- `raw.perp.liquidations`
- `raw.perp.open_interest`
- `clean.perp.*`
- `clean.spot.*`
- `features.perp.v2`
- `features.spot.v2`
- `metadata.universe_snapshots`

This token model allows structural reasoning before concrete artifact paths are resolved.

## Run Manifest Layer

`run_all` writes a run manifest that captures:

- config resolution
- effective behavior
- planned stages
- stage timings
- objective and retail profile metadata
- spec hashes and ontology hashes
- runtime invariant settings
- status / failed stage state

This manifest is a primary debugging artifact, not a side-product.

Typical companion artifacts:

- `effective_config.json`
- per-stage manifests and outputs
- comparison reports
- smoke/regression summaries

## Planning and Preflight

Planning performs more than argument parsing. It also:

- resolves experiment overlays
- computes stage instances
- validates artifact contracts
- resolves runtime invariant mode
- determines effective behavior for discovery and promotion tails

If contract resolution fails during planning, execution should not proceed.

## Runtime Invariants and Replay

The current data-flow model includes explicit runtime/replay surfaces:

- normalized replay stream
- causal lane ticks
- optional determinism replay checks
- optional OMS replay checks

These are not optional documentation details. They are part of the pipeline architecture and quality model.

## Promotion and Research-Quality Tails

After phase 2 discovery, the pipeline can continue into:

- naive entry evaluation
- negative control summaries
- candidate promotion
- edge registry update
- campaign memory update
- expectancy analysis
- expectancy trap validation
- recommendations checklist

This means "phase 2 finished" is not the same thing as "the research result is fully evaluated."

## Generated Contract and Inventory Surfaces

Use:

- `docs/generated/system_map.json`
- `docs/generated/detector_coverage.json`
- `docs/generated/ontology_audit.json`
- `docs/generated/event_ontology_audit.json`
- `docs/generated/regime_routing_audit.json`

to reconcile what the repo currently exposes.

## Practical Debugging Order

When a run looks wrong:

1. inspect the top-level run manifest
2. confirm planned stages and effective behavior
3. inspect stage outputs expected by the contract registry
4. inspect report artifacts
5. inspect generated audits and comparison outputs

If an artifact exists but violates its declared contract, treat that as a correctness failure even when the script returned `0`.
