# Operations And Guardrails

## Operating Priorities

The agent should optimize for:

1. correctness
2. comparability
3. narrow attribution
4. operational cleanliness
5. iteration speed

## Safety Rules

- Do not overwrite broad production artifacts when a narrow output path will do.
- Do not interpret a repaired tail replay as identical to the original full DAG run.
- Do not treat warning-heavy output as clean output without inspection.
- Do not broaden scope immediately after a mechanical fix.

## Run Selection Rules

- Use targeted stage execution for repair verification.
- Use narrow search specs for isolated hypothesis testing.
- Use full runs only after recent path stability is confirmed.
- After detector or synthetic-generator edits, rerun synthetic truth validation before trusting full-spec synthetic results.

## Logging Discipline

Warnings should help triage, not flood the operator.

The agent should:

- suppress low-signal coercion noise where safe
- preserve warnings that indicate real data quality or contract issues
- call out stale or contradictory logs explicitly

## Promotion Guardrails

Promotion is conservative by design.

The agent must not bypass:

- multiplicity controls
- cost-survival checks
- validation/test sample requirements
- confirmatory locking rules
- retail and capital viability filters

## Memory Guardrails

Memory should inform action, not hard-code bias.

The agent must still permit:

- materially different contexts
- repaired code paths
- cleaner reruns that can invalidate old conclusions

## Review Discipline

When a run looks abnormal, inspect:

- manifests
- logs
- row counts across artifact boundaries
- duplicate hypotheses
- stale replay traces
- missing split metadata

## Required End State

A run is considered operationally clean when:

- stage and top-level manifests agree
- downstream artifacts are populated as expected
- warning noise is controlled
- the next action is obvious from the evidence


## Synthetic Generator Guardrails

- Freeze `volatility_profile`, symbol set, and time window before reviewing outcomes.
- Prefer cross-profile survival over single-profile maximization.
- Treat generator edits like data-source edits: rerun truth validation and narrow repair slices first.
- Do not use repeated agent proposal cycles to tune directly against one synthetic world.
