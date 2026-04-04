# Stage 3: Promote

Promotion is the packaging and governance layer. It takes already-validated candidates and prepares them for real-world deployment.

## Concept
Validation answers "Is this real?", while Promotion answers "Is this worth trading?".
Promotion applies business constraints:
* **Retail Profile Matching**: Is this edge viable for our capital constraints and cost model?
* **Inventory Decision**: Do we have a budget/slot for this new alpha idea?
* **Readiness Assignment**: Is this ready for Live trading or only for Paper testing?

## Workflow
1. **Run Promotion**:
   ```bash
   edge promote run --run_id <validation_run_id> --symbols BTC
   ```
2. **Export Theses**:
   ```bash
   edge promote export --run_id <validation_run_id>
   ```

## Key Outputs
* `promoted_candidates.parquet`: Selection of candidates chosen for promotion.
* `promotion_audit.parquet`: Detailed record of promotion gate evaluations.
* `promoted_theses.json`: Canonical packaged artifacts for the deployment stage.

## Maturity Classes
* `seed_promoted`: New ideas with minimal but valid evidence.
* `paper_promoted`: Robust ideas ready for out-of-sample paper testing.
* `production_promoted`: Mature ideas ready for live capital deployment.
