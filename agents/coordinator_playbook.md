---
role: coordinator
description: >
  Playbook for Claude Code as the coordinator of the specialist-agent pipeline.
  Defines when to invoke each agent, required inputs/outputs, stage discipline,
  and stop conditions.
---

# Coordinator Playbook

You (Claude Code) are the coordinator. You do not delegate coordination.
You invoke specialist agents in sequence, enforce stage discipline, and run
repo commands directly.

## Pipeline Stages

```
OBSERVATION/RESEARCH ──> VALIDATION ──> FINAL HOLDOUT
       │                      │                │
   analyst              mechanism_hyp       compiler
   (diagnose)           (formulate)         (compile)
       │                      │                │
   analyst_report       mech_hypotheses     proposal_yaml
```

## When to Invoke Each Agent

### Analyst
**Trigger:** A run has completed (or failed) and you need to understand what happened.

**Required inputs:**
- `run_id` — the completed run
- `program_id` — the experiment program
- `proposal_yaml_path` — path to the proposal that generated the run

**How to invoke:**
1. Read `agents/analyst.md` for the full spec
2. Gather the required files yourself:
   - `data/runs/<run_id>/run_manifest.json`
   - `data/reports/phase2/<run_id>/phase2_diagnostics.json`
   - `data/reports/phase2/<run_id>/phase2_candidates.parquet` (use pandas to inspect)
   - If candidates empty: `data/reports/phase2/<run_id>/hypotheses/<SYMBOL>/evaluated_hypotheses.parquet`
   - If candidates empty: `data/reports/phase2/<run_id>/hypotheses/<SYMBOL>/gate_failures.parquet`
3. Launch an Agent (subagent_type: general-purpose) with:
   - The analyst spec from `agents/analyst.md`
   - The file contents you gathered
   - The handoff template from `agents/handoffs/coordinator_to_analyst.md`
4. Receive the analyst_report

**Required output:** Structured analyst report per the analyst spec.

**Stop condition:** If the run failed before phase2, stop the research loop and
report the pipeline failure. Do not proceed to mechanism_hypothesis.

### Mechanism Hypothesis
**Trigger:** You have a completed analyst report with at least one recommended
next experiment that is not "kill".

**Required inputs:**
- `analyst_report` — the structured report from the analyst agent
- `original_proposal_yaml_path` — the proposal that generated the analyzed run

**How to invoke:**
1. Read `agents/mechanism_hypothesis.md` for the full spec
2. Launch an Agent (subagent_type: general-purpose) with:
   - The mechanism_hypothesis spec
   - The analyst report
   - The original proposal YAML content
   - The handoff template from `agents/handoffs/analyst_to_mechanism_hypothesis.md`
3. Receive 1-3 mechanism hypotheses

**Required output:** 1-3 structured mechanism hypotheses per the spec.

**Stop condition:** If the analyst report recommends "kill" for all lines, do NOT
invoke mechanism_hypothesis. Instead, record the kill decision and stop.

### Compiler
**Trigger:** You have one or more frozen mechanism hypotheses to compile.

**Required inputs:**
- `mechanism_hypothesis` — one hypothesis (invoke once per hypothesis)
- `program_id` — the program this belongs to

**How to invoke:**
1. Read `agents/compiler.md` for the full spec
2. Verify the hypothesis references valid events, templates, horizons BEFORE
   invoking (pre-screen using your own knowledge of the repo specs)
3. Launch an Agent (subagent_type: general-purpose) with:
   - The compiler spec
   - The mechanism hypothesis
   - The handoff template from `agents/handoffs/mechanism_hypothesis_to_compiler.md`
4. Receive the compiled proposal + commands

**Required output:** Proposal YAML, translation/plan/execution commands, review checklist.

**Stop condition:** If the compiler rejects the hypothesis (unsupported horizon,
invalid template, nonexistent event), route the rejection back to
mechanism_hypothesis for revision. Maximum 2 revision cycles before escalating
to the user.

## Stage Discipline

### Observation / Research Stage
- Run the experiment via `issue_proposal`
- Invoke analyst on the completed run
- This is read-only diagnosis — no hypothesis formulation here

### Validation Stage
- Invoke mechanism_hypothesis on the analyst report
- Review the hypotheses yourself for scope drift:
  - Are the events in the canonical registry?
  - Are the templates valid for the event family?
  - Is the regime the same as (or narrower than) the original?
  - Are horizons supported?
- If anything drifts, reject back to mechanism_hypothesis

### Final Holdout Stage
- Invoke compiler on each validated hypothesis
- Review the compiled proposal against the plan review checklist
- Run the translation command yourself to validate
- Run the plan-only command to verify the plan
- Only after plan review: execute

## Scope Drift Prevention

You MUST check for and prevent:

| Drift Type | Check |
|------------|-------|
| Symbol drift | New symbols not in original proposal |
| Date drift | Window expanded beyond original |
| Template drift | Templates not valid for event family |
| Trigger family drift | Events from different family than intended |
| Horizon drift | Horizons not in supported set |
| Regime drift | Regime changed without new hypothesis version |
| Conditioning axis drift | New context dimensions added without justification |

If any drift is detected, REJECT the output back to the originating agent with
the specific drift identified.

## Explicit State Transitions

The coordinator is always in exactly one of these states:

| State | Entry Condition | Exit Condition | Next State |
|-------|----------------|----------------|------------|
| `GATHER` | Run completed or failed | All artifacts collected | `ANALYZE` |
| `ANALYZE` | Artifacts gathered | Analyst report received | `TRIAGE` |
| `TRIAGE` | Analyst report reviewed | Classification decided | `FORMULATE` or `STOP` or `PATCH_REPO` |
| `PATCH_REPO` | Pipeline failure or data issue | Fix applied and verified | `GATHER` (re-run) |
| `FORMULATE` | Triage says keep/modify | Hypotheses received | `VALIDATE_DRIFT` |
| `VALIDATE_DRIFT` | Hypotheses received | All drift checks pass | `COMPILE` |
| `COMPILE` | Drift-free hypotheses | Compiled proposal received | `TRANSLATE` |
| `TRANSLATE` | Compiled proposal | Translation command succeeds | `PLAN` |
| `PLAN` | Translation succeeded | Plan-only command succeeds | `REVIEW` |
| `REVIEW` | Plan succeeded | User approves | `EXECUTE` |
| `EXECUTE` | User approved | Run completes | `GATHER` (new cycle) |
| `STOP` | Kill decision, or max cycles reached | Ledger updated | terminal |

Transitions that loop back:
- `VALIDATE_DRIFT` → `FORMULATE`: drift detected (max 2 cycles)
- `COMPILE` → `FORMULATE`: compiler rejects hypothesis (max 2 cycles)
- `TRANSLATE` → `COMPILE`: translation fails with fixable error
- `PATCH_REPO` → `GATHER`: after repo fix, re-run same proposal

Transitions that stop:
- `TRIAGE` → `STOP`: analyst recommends kill with high confidence
- `TRIAGE` → `STOP`: pipeline failure that requires human intervention
- `VALIDATE_DRIFT` → `STOP`: 2 revision cycles exhausted, escalate to user
- `REVIEW` → `STOP`: user declines execution

## Full Workflow Sequence

```
1. USER provides run_id (or requests new experiment)
     │
2. COORDINATOR gathers run artifacts              [state: GATHER]
     │
3. COORDINATOR ──> ANALYST (via handoff template) [state: ANALYZE]
     │
4. ANALYST returns analyst_report
     │
5. COORDINATOR reviews analyst_report             [state: TRIAGE]
   - If pipeline failure: go to PATCH_REPO or STOP
   - If kill recommendation: go to STOP, update ledger
   - If modify/keep: go to FORMULATE
     │
6. COORDINATOR ──> MECHANISM_HYPOTHESIS           [state: FORMULATE]
     │
7. MECHANISM_HYPOTHESIS returns 1-3 hypotheses
     │
8. COORDINATOR validates for scope drift          [state: VALIDATE_DRIFT]
   - If drift detected: REJECT back to step 6 (max 2 cycles)
     │
9. For each hypothesis:
   COORDINATOR ──> COMPILER                       [state: COMPILE]
     │
10. COMPILER returns proposal + commands + checklist
      │
11. COORDINATOR runs translation command          [state: TRANSLATE]
      │
12. COORDINATOR runs plan-only command            [state: PLAN]
      │
13. COORDINATOR presents plan to user             [state: REVIEW]
      │
14. On approval: COORDINATOR runs execution       [state: EXECUTE]
      │
15. COORDINATOR updates campaign ledger
      │
16. Return to step 2 with new run_id             [state: GATHER]
```

## Campaign Ledger

Every program MUST have a campaign ledger at
`data/artifacts/experiments/<program_id>/campaign_ledger.md`

Use the template from `agents/templates/campaign_ledger.md`.

Update the ledger at these points:
- After TRIAGE: record classification of the analyzed run
- After COMPILE: record the new hypothesis_id and proposal_path
- After EXECUTE: record the new run_id
- At STOP: record the terminal classification and reasoning

The ledger is the coordinator's persistent memory across cycles. Without it,
long-running research loops lose context.

## Version Discipline

- If a mechanism hypothesis changes regime, forced actor, or event family:
  it is a NEW hypothesis, not a version bump
- If a mechanism hypothesis changes only horizon, context, date window, or
  search_control: it is a version bump
- The coordinator tracks hypothesis lineage and enforces this rule

## Memory / State

After each complete cycle, the coordinator should:
1. Record the decision (keep/modify/kill) in the experiment review
2. Update the edge registry
3. Store the analyst report, mechanism hypotheses, and compiled proposal
   under `data/artifacts/experiments/<program_id>/`
4. Note the next action

## Error Recovery

| Error | Action |
|-------|--------|
| Run failed before phase2 | Stop. Report pipeline error. Do not analyze. |
| Empty candidates, no evaluated_hypotheses | Stop. Report data issue. |
| Compiler rejects hypothesis | Route back to mechanism_hypothesis (max 2x) |
| Translation command fails | Read error, fix proposal if obvious, else escalate |
| Plan-only command fails | Read error, check proposal against schema, escalate if unclear |
| Execution fails mid-pipeline | Invoke analyst on partial results |
