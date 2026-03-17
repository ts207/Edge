# Pipelines Layer (`project/pipelines`)

The pipelines layer handles data ingestion, bulk feature engineering, and high-level research workflow orchestration.

## 1. Ownership
- **Data Ingestion**: Fetching and cleaning raw venue data.
- **Bulk Transforms**: Calculating features for historical universes.
- **Orchestration**: Directing the flow from ingestion to candidate generation and promotion.
- **Artifact Management**: Writing and versioning data artifacts.

## 2. Non-Ownership
- **Core Numerical Kernels**: These belong in `research/helpers` or `engine`. Pipelines only *call* them.
- **Low-Latency Logic**: No runtime execution logic belongs here.
- **Contract Enforcement**: It uses contracts but does not own their definition.

## 3. Public Interfaces
- **`PipelineEngine`**: Orchestrator for task execution.
- **`IngestionServices`**: Specific services for Binance Spot/UM data.
- **`FeatureProcessor`**: Service for calculating features at scale.

## 4. Constraints
- **Separation of Concerns**: Each pipeline step must be a discrete task or service.
- **State via Artifacts**: Communication between stages occurs via files on disk, not shared memory.
- **Side-Effect Free**: Beyond writing artifacts, pipelines should not modify global configuration.
