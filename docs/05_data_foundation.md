# Data Foundation

This document describes the datasets, artifact structures, and lineage rules that underpin the Edge pipeline.

## Source Data
* **OHLCV**: 1-minute bars ingested from external exchanges.
* **Funding**: Funding rate data for perpetual swaps.
* **Open Interest**: Aggregate open interest metrics.

## Artifact Lineage
Every artifact in Edge includes a `run_id` and is stored in a deterministic path under `data/reports/`.

| Stage | Main Artifact | Storage Path |
| :--- | :--- | :--- |
| Discover | `phase2_candidates.parquet` | `data/reports/phase2/<run_id>/` |
| Validate | `validated_candidates.parquet` | `data/reports/validation/<run_id>/` |
| Promote | `promoted_theses.json` | `data/reports/promoted_theses/<run_id>/` |

## Retention Rules
* **Research Runs**: Retained indefinitely for baseline comparison.
* **Temporary Artifacts**: Cleaned up after 30 days of inactivity.
* **Production Logs**: Archived to long-term storage monthly.

## Reproducibility
A discovery run can be reproduced by re-issuing the `Structured Hypothesis` against the same `data_fingerprint`. Validation results are reproducible by re-running the validation stage against the persisted discovery artifacts.
