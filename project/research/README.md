# Research Layer (`project/research`)

The research layer owns strategy discovery, statistical evaluation, and promotion.

## 1. Ownership
- **Candidate Discovery**: Finding potential edge-bearing conditions.
- **Statistical Gating**: Applying shrinkage, multiple testing, and OOS validation.
- **Promotion Workflow**: Moving candidates from research into potential deployment.
- **Numerical Kernels**: Shrinkage math and evaluation metrics.

## 2. Non-Ownership
- **Live Execution**: It does not execute live trades; that is `runtime`.
- **Data Cleaning**: It expects clean events from `pipelines`.
- **Venue Interfaces**: It is agnostic of venue-specific APIs.

## 3. Public Interfaces
- **`CandidateDiscoveryService`**: Service for finding new edges.
- **`PromotionService`**: Service for evaluating and promoting candidates.
- **`EvaluationSummaryService`**: Service for generating research quality reports.
- **`ShrinkageWrapper`**: API for applying hierarchical shrinkage.

## 4. Constraints
- **Statistical Determinism**: Repeated runs on identical data must yield identical metrics.
- **Concerns Separation**: No single function should mix metric computation with policy decisions.
- **Library Reliance**: Pandas/Numpy/Scipy are core to this layer.
- **Façade Pattern**: Complex logic must be exposed through stable façades in `core.py` or services.
