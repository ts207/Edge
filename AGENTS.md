# AGENTS.md

## Project audit mode

You are auditing this repository, not casually reviewing it.

Source-of-truth precedence:
1. runtime artifacts and test behavior
2. code
3. specs and configs
4. prose docs

Priorities:
- correctness
- statistical integrity
- contract integrity
- artifact integrity
- runtime safety
- economic realism
- reproducibility
- operator hazards
- maintainability after the above

For every nontrivial claim:
- cite exact file paths
- cite function/class names when possible
- explain why it matters
- explain how to reproduce or validate it

Always separate:
- verified defects
- likely defects
- speculative concerns
- architectural debt
- missing tests / missing evidence

Required repo-wide path map:
proposal -> search -> validation -> promotion -> blueprint/spec -> engine/live

When auditing:
- do not trust docs unless verified in code, tests, or generated outputs
- prefer code-path tracing over directory-summary prose
- find hidden assumptions, drift, false-green paths, stale artifact reuse, and boundary mismatches
- focus on high-leverage failure modes, not style
- preserve evidence for every finding

Expected outputs:
- audit_outputs/subagents/<agent>.md
- audit_outputs/merged/issue_ledger.md
- audit_outputs/final/repo_map.md
- audit_outputs/final/audit_findings.md
- audit_outputs/final/remediation_plan.md
- audit_outputs/final/risk_matrix.csv
- audit_outputs/final/missing_tests.md