# core_features_costs

## Scope
- project/core/
- project/features/
- project/eval/
- project/domain/
- project/io/
- project/research/ (cost/return integration cross-references only)
- project/tests/core/
- project/tests/features/
- project/tests/eval/
- project/tests/domain/

## Summary
Proposal/spec objects feed search and gating in project/research/search/evaluator.py and project/research/gating.py, which then feed candidate_discovery_scoring, eval robustness/cost models, bridge evaluation, and blueprint compilation. Cost semantics are split across project/core/execution_costs.py, project/eval/cost_model.py, and research-side helpers.

## Findings
### Execution cost units diverge across core, eval, and research paths
- Severity: high
- Confidence: verified
- Category: correctness
- Affected: project/core/execution_costs.py, project/eval/cost_model.py, project/research/search/evaluator.py, project/research/phase2_cost_integration.py
- Evidence: project/core/execution_costs.py resolves a one-sided fee+slippage total, project/research/search/evaluator.py subtracts that once, while project/eval/cost_model.py applies 2 * (fee + slippage) as round-trip cost.
- Why it matters: The same fee config produces different after-cost returns depending on the path that computed them.
- Validation: Compare resolve_execution_costs(), estimate_transaction_cost_bps(), apply_cost_model(), and evaluate_hypothesis_batch() under the same fee/slippage config.
- Remediation: Adopt one repo-wide cost unit contract and rename fields/sites so per-side and round-trip values cannot be confused.

### Funding carry can make stressed-cost robustness improve as costs are stressed
- Severity: high
- Confidence: verified
- Category: economic_realism
- Affected: project/research/gating.py, project/research/services/candidate_discovery_scoring.py, project/eval/robustness.py
- Evidence: build_event_return_frame() records cost_return = per_trade_cost - funding_carry_return, which can go negative, and evaluate_structural_robustness() subtracts that negative cost again, making higher stress multipliers improve pnl retention.
- Why it matters: A cost-stress panel can certify fragile candidates as more robust when stressed harder.
- Validation: Generate a short-side return frame with positive funding_rate_scaled and feed the negative costs_bps into evaluate_structural_robustness().
- Remediation: Stress transaction costs separately from funding carry and clamp transaction-cost inputs to non-negative values.

### Funding carry is applied as a flat trade adjustment independent of holding horizon
- Severity: medium
- Confidence: verified
- Category: economic_realism
- Affected: project/research/gating.py
- Evidence: _funding_carry_return() reads one scalar funding rate and applies it once per trade regardless of horizon length or funding-interval count.
- Why it matters: A 5-minute hold and a 1-hour hold can receive identical funding carry, distorting horizon comparisons.
- Validation: Call build_event_return_frame() with the same event and constant funding rate but different horizons and compare funding_carry_return.
- Remediation: Accrue carry over the actual holding window using aligned funding timestamps and interval counts.

### Research helper integrate_execution_costs is broken and does not call the shared core utility correctly
- Severity: medium
- Confidence: verified
- Category: architecture
- Affected: project/research/cost_integration.py, project/core/execution_costs.py
- Evidence: integrate_execution_costs() calls resolve_execution_costs(symbol) positionally, but resolve_execution_costs is keyword-only and requires a full cost-config contract.
- Why it matters: A purported shared research integration path fails immediately and cannot share semantics with the maintained core path.
- Validation: Import integrate_execution_costs() and call it on a dummy DataFrame and symbol.
- Remediation: Delete the dead helper or rewrite it against the actual resolve_execution_costs() keyword contract.

### The repo marks after-cost outputs as including funding carry even when actual carry coverage can be zero
- Severity: medium
- Confidence: likely
- Category: contract_integrity
- Affected: project/research/services/candidate_discovery_service.py, project/research/services/candidate_discovery_scoring.py, project/research/gating.py
- Evidence: candidate_discovery_service hard-codes after_cost_includes_funding_carry=True, while candidate_discovery_scoring separately computes funding_carry_eval_coverage and gating only includes carry when funding fields are present.
- Why it matters: Consumers can assume net expectancy already includes carry economics when the observed coverage is actually zero.
- Validation: Trace the hard-coded flag in candidate_discovery_service.py and compare it with funding_carry_eval_coverage on candidate sets lacking funding columns.
- Remediation: Derive the flag from observed coverage or split formula capability from observed carry coverage.
