# Advanced Trigger Discovery (Internal Research Lane)

> [!WARNING]
> **Internal Research Lane Only**
> This module is designed for proposing new trigger candidate definitions. It is **PROPOSAL-GENERATING ONLY** and has exactly zero effect on the canonical runtime or live trading paths until a maintainer manually adopts the output.

## Overview

The trigger discovery lane allows the system to move beyond the current named ontology by scanning raw data for recurring patterns or optimized parameterizations. It aims to bridge the gap between "validating known triggers" and "proposing new triggers worth formalizing."

There are two primary modes of operation:
1. **Parameter Sweep (Lane A)**: Takes a known detector family (e.g., `vol_shock`) and sweeps a parameter grid to find the most robust configuration for a specific symbol or regime.
2. **Feature Excursion Clustering (Lane B)**: Scans arbitrary continuous feature columns for high-magnitude excursions, clustering temporally concurrent spikes into "new interaction families."

## Workflow: Discovery to Adoption

To prevent research from contaminating the production environment, a strict human-in-the-loop gate is enforced:

1. **Run Discovery**: Use `edge discover triggers` to generate candidates.
2. **Review Artifacts**: Inspect the `candidate_trigger_report.md` and registry novelty scores.
3. **Manual Approval**: A researcher evaluates the support count, fold stability, and redundancy with the existing registry.
4. **Registry Adoption**: If a trigger is approved, use `edge discover triggers emit-registry-payload` to generate the YAML snippet.
5. **Formalization**: Copy the snippet into the appropriate `spec/events/` file. Only then can the new trigger be used in canonical `edge discover run` proposals.

## Usage

### Parameter Sweep
```bash
# Via CLI
edge discover discover triggers parameter-sweep --family vol_shock --symbol BTCUSDT

# Via Makefile
make advanced-discover-triggers-parameter FAMILY=vol_shock SYMBOLS=BTCUSDT
```

### Feature Excursion Clustering
```bash
# Via CLI
edge discover discover triggers feature-cluster --symbol BTCUSDT

# Via Makefile
make advanced-discover-triggers-cluster SYMBOLS=BTCUSDT
```

## Artifact Contract

Discovery outputs are written to `data/trigger_proposals/` by default.

| Artifact | Content | Purpose |
| :--- | :--- | :--- |
| `candidate_trigger_report.md` | Human-readable summary | **Primary review source of truth** |
| `candidate_trigger_proposals.jsonl` | Structured proposal objects | Machine-readable candidate list |
| `candidate_trigger_scored.parquet` | Detailed metrics and scores | Data-science audit and diagnostic |
| `candidate_trigger_signatures.parquet` | Boolean occurrence vectors | Registry overlap verification |

## Key Metrics

- **Quality Score**: A weighted composite of T-stat, fold stability, and registry novelty.
- **Novelty vs Registry**: (1.0 - Jaccard Similarity) against the existing canonical trigger set.
- **Fold Stability**: Consistency of the trigger's performance sign across temporal holdout folds.
- **Lineage Burden**: Penalty for "over-mining" similar structural variations.

## Mandatory Guardrails

1. **NO AUTO-REGISTRATION**: Trigger discovery MUST NOT automatically modify the canonical event registry.
2. **NO LIVE ACCESS**: Mined triggers are invisible to the `deploy` stage.
3. **EXPLICIT PROVENANCE**: Any edges built using a mined trigger must record the `candidate_trigger_id` in their lineage metadata.
4. **HUMAN GATE**: Direct promotion of a mined trigger without a signed-off `spec/events/` file is forbidden.
