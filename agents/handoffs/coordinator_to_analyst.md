# Handoff: Coordinator -> Analyst

## Context

You are the analyst agent. The coordinator has invoked you to diagnose a completed
experiment run.

## Your Specification

Follow the analyst spec in `agents/analyst.md` exactly. Return the FIXED SCHEMA —
every field must be present.

## Provided Data

### Run Identity
- run_id: {{run_id}}
- program_id: {{program_id}}
- proposal_path: {{proposal_yaml_path}}
- research_stage: {{observation | validation | holdout}}
- cycle_number: {{N}}
- parent_run_id: {{parent_run_id or "none"}}

### Artifact Paths
- run_manifest: `data/runs/{{run_id}}/run_manifest.json`
- phase2_diagnostics: `data/reports/phase2/{{run_id}}/phase2_diagnostics.json`
- phase2_candidates: `data/reports/phase2/{{run_id}}/phase2_candidates.parquet`
- evaluated_hypotheses: `data/reports/phase2/{{run_id}}/hypotheses/{{SYMBOL}}/evaluated_hypotheses.parquet`
- gate_failures: `data/reports/phase2/{{run_id}}/hypotheses/{{SYMBOL}}/gate_failures.parquet`
- rejected_hypotheses: `data/reports/phase2/{{run_id}}/hypotheses/{{SYMBOL}}/rejected_hypotheses.parquet`
- stage_manifests: `data/runs/{{run_id}}/*.json`

### Run Manifest
```json
{{run_manifest_json}}
```

### Phase2 Diagnostics
```json
{{phase2_diagnostics_json}}
```

### Phase2 Candidates Summary
{{phase2_candidates_summary}}

### Upstream Artifacts (if candidates empty)
{{evaluated_hypotheses_summary}}
{{gate_failures_summary}}
{{rejected_hypotheses_summary}}

### Original Proposal
```yaml
{{proposal_yaml}}
```

### Prior Cycle Classification (if not first cycle)
{{prior_classification or "first cycle"}}

## Instructions

1. Diagnose run health from the manifest
2. Trace the funnel from generation through gating
3. If candidates empty: inspect evaluated_hypotheses and gate_failures — identify
   the exact stage where the funnel collapsed
4. Identify the primary rejection mechanism
5. Find the strongest near-misses (by selection_score desc)
6. Read the asymmetry (long/short, horizon, event type)
7. Interpret the mechanistic meaning in regime terms
8. Recommend 1-3 bounded next experiments
9. Classify overall: keep / modify / kill with confidence

Return your output in the exact FIXED SCHEMA specified in `agents/analyst.md`.

Do NOT propose mechanism hypotheses or compile proposals.
Do NOT recommend broadening scope unless structurally necessary.
