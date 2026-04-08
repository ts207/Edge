# Stage 1: Discover

Discovery is the entry point of the Edge pipeline. Its purpose is to generate a broad set of candidates based on a research hypothesis.

## Concept
In discovery, we define:
* **Anchor**: What market event or price transition are we anchoring to? (e.g., `VOL_SHOCK`, `OI_SPIKE`)
* **Filters**: What contextual states must be true? (e.g., `regime == "volatile"`)
* **Sampling Policy**: How should we handle multiple triggers within the same timeframe?

## Workflow
1. **Define Structured Hypothesis**: Create a YAML spec defining the anchor and filters.
2. **Run Discovery**:
   ```bash
   edge discover run --proposal spec/proposals/canonical_event_hypothesis_h24.yaml
   ```
3. **Inspect Candidates**: Review the ranked candidate set produced in `phase2_candidates.parquet`.

## Key Outputs
* `phase2_candidates.parquet`: All candidates generated during the discovery run.
* `phase2_diagnostics.json`: Metadata and coverage statistics for the run.
## What stable default discovery currently includes

The canonical discovery path currently uses:

- a single-hypothesis operator proposal
- flat search expansion
- discovery v2 scoring
- repeated walk-forward validation support
- standard candidate diagnostics

Discovery ranking in the stable default path considers:

- statistical significance
- support / sample quality
- cheap falsification prechecks
- tradability prechecks
- overlap / novelty penalties
- fold stability

The canonical discovery path does **not** enable these by default:

- hierarchical search
- ledger-adjusted ranking
- diversified shortlist
- trigger discovery lane

## Discovery mode maturity levels

### Stable
- flat search
- discovery v2 scoring
- current validation path
- explicit runtime lineage and deployment-state permission model

### Experimental
- hierarchical search
- ledger-adjusted discovery ranking
- diversified shortlist
- trigger discovery

Current example:
- `LIQUIDATION_CASCADE_PROXY` is an experimental proxy event that extends liquidation-style discovery when direct `liquidation_notional` feeds are unavailable. It remains registry-governed and does not bypass validation or promotion gates.

### Compatibility-only
- legacy proposal/operator surfaces retained for migration or internal support

## Failure Modes
* **Low Signal**: No candidates with positive expectancy found.
* **Insufficient Coverage**: Data for the requested symbols/dates is missing or corrupted.
* **Anchor Mismatch**: The chosen anchor does not occur enough times to be statistically meaningful.
