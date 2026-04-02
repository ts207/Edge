---
name: edge-analyst
description: Diagnose completed Edge experiment runs using the repo's analyst spec. Use when a run has finished or failed and the next step depends on understanding run health, funnel collapse, near-misses, or bounded follow-up directions.
---

# Edge Analyst

This skill follows `agents/analyst.md`.

## Read first

1. `agents/analyst.md`
2. `agents/handoffs/coordinator_to_analyst.md`
3. `docs/AGENT_CONTRACT.md`

## Required inputs

- `run_id`
- `program_id`
- `proposal_yaml_path`

## Files to inspect

- `data/runs/<run_id>/run_manifest.json`
- `data/reports/phase2/<run_id>/phase2_diagnostics.json`
- `data/reports/phase2/<run_id>/phase2_candidates.parquet`
- If candidates are empty:
  - `data/reports/phase2/<run_id>/hypotheses/<SYMBOL>/evaluated_hypotheses.parquet`
  - `data/reports/phase2/<run_id>/hypotheses/<SYMBOL>/gate_failures.parquet`
  - `data/reports/phase2/<run_id>/hypotheses/<SYMBOL>/rejected_hypotheses.parquet`

## Non-negotiable rules

- Diagnose the exact funnel collapse stage when candidates are empty.
- Use exact repo column names such as `effect_raw`, `q_value`, and `selection_score`.
- Do not propose hypotheses or compile proposals here.
- Follow the fixed analyst report schema from `agents/analyst.md`.

## Minimum result

- Run health
- Funnel summary
- Primary rejection mechanism
- Top near-misses
- Mechanistic meaning
- 1-3 bounded next experiments
- keep / modify / kill classification
