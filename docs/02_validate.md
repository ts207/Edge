# Stage 2: Validate

Validation is the most critical stage in the Edge pipeline. It is designed to falsify candidates through rigorous statistical and mechanical testing.

## Concept
A candidate appearing in Discovery is merely an idea. Validation turns it into a *Validated Candidate* by testing:
* **Effect Stability**: Is the edge consistent across different market regimes and time slices?
* **Cost Sensitivity**: Does the edge survive realistic transaction costs and slippage?
* **Falsification**: Does the edge disappear when subject to placebo tests or negative controls?

## Workflow
1. **Execute Validation**:
   ```bash
   edge validate run --run_id <discovery_run_id>
   ```
2. **Generate Reports**:
   ```bash
   edge validate report --run_id <discovery_run_id>
   ```
3. **Diagnose Failures**:
   ```bash
   edge validate diagnose --run_id <discovery_run_id>
   ```

## Key Outputs
* `validated_candidates.parquet`: Candidates that passed all validation gates.
* `rejection_reasons.parquet`: Detailed logs of why certain candidates failed.
* `validation_report.json`: High-level summary of validation success rates.
* `effect_stability_report.json`: Detailed regime split analysis.

## Rejection Reasons
* `failed_stability`: The effect is inconsistent across time or regimes.
* `failed_cost_survival`: The edge is too thin to cover trading costs.
* `insufficient_sample_support`: Not enough occurrences to trust the statistical result.
