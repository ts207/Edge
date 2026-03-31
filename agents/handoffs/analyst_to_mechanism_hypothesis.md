# Handoff: Analyst -> Mechanism Hypothesis

## Context

You are the mechanism_hypothesis agent. The coordinator has invoked you after
reviewing the analyst's diagnosis of a completed run.

## Your Specification

Follow the mechanism_hypothesis spec in `agents/mechanism_hypothesis.md` exactly.

## Provided Data

### Run Identity
- run_id: {{run_id}}
- program_id: {{program_id}}
- proposal_path: {{proposal_yaml_path}}
- research_stage: {{observation | validation | holdout}}
- cycle_number: {{N}}

### Analyst Report
{{analyst_report}}

### Analyst Classification
- overall: {{keep | modify | kill}}
- confidence: {{low | medium | high}}

### Original Proposal
```yaml
{{proposal_yaml}}
```

### Coordinator Notes
{{coordinator_notes}}

### Scope Boundary (from coordinator)
The following scope boundaries are HARD — do not exceed them:
- max_symbols: {{symbols from original proposal}}
- max_date_range: {{start}} to {{end}}
- max_event_families: {{families in original trigger_space}}
- allowed_regimes: {{regimes in original trigger_space}}

## Instructions

1. Check the analyst classification first:
   - If `kill` with `high` confidence: output KILL notice, do not formulate hypotheses
   - If `kill` with `low`/`medium` confidence: output KILL notice but note what
     a reframe would look like (coordinator decides)
   - If `keep` or `modify`: proceed to formulation
2. Read the analyst report's "Recommended Next Experiments" section
3. For each recommended experiment (up to 3), formulate a frozen mechanism hypothesis
4. Each hypothesis must name specific events from the canonical registry
5. Each hypothesis must specify templates valid for the event family
6. Each hypothesis must specify supported horizons
7. Clearly separate allowed knobs from frozen knobs
8. Do not exceed the scope boundary above

Return your output in the exact format specified in `agents/mechanism_hypothesis.md`.

Do NOT analyze run data directly — rely on the analyst report.
Do NOT compile proposals — that is the compiler's job.
