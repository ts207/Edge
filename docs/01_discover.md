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
   edge discover run --proposal spec/proposals/my_alpha.yaml
   ```
3. **Inspect Candidates**: Review the ranked candidate set produced in `phase2_candidates.parquet`.

## Key Outputs
* `phase2_candidates.parquet`: All candidates generated during the discovery run.
* `phase2_diagnostics.json`: Metadata and coverage statistics for the run.

## Failure Modes
* **Low Signal**: No candidates with positive expectancy found.
* **Insufficient Coverage**: Data for the requested symbols/dates is missing or corrupted.
* **Anchor Mismatch**: The chosen anchor does not occur enough times to be statistically meaningful.
