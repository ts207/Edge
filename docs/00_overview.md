# System Overview

Edge is architected as a sequential staging pipeline designed to transform raw research ideas into validated, deployable trading theses.

## The Four-Stage Model

### 1. Discover
The discovery stage focuses on **candidate generation**. Researchers define a *Structured Hypothesis* (formerly Proposal) that anchors an edge to specific market events and applies filters.
* **Goal**: Identify potential signals with positive raw expectancy.
* **Key Artifact**: `phase2_candidates.parquet`

### 2. Validate
The validation stage is the **truth-testing** filter. It is designed to falsify candidates that appear successful due to noise, luck, or over-fitting.
* **Goal**: Confirm the robustness and stability of the effect.
* **Key Artifact**: `validation_bundle.json`, `validated_candidates.parquet`

### 3. Promote
The promotion stage handles **packaging and governance**. It selects from the pool of validated candidates and prepares them for runtime use.
* **Goal**: Match validated ideas to business objectives and retail constraints.
* **Key Artifact**: `promoted_theses.json`

### 4. Deploy
The deployment stage is the **runtime execution** of promoted theses.
* **Goal**: Execute approved alpha in paper or live environments.
* **Key Artifact**: Live trade logs and performance metrics.

## Artifact Lineage

Data flows through the system with clear lineage:
1. `discover` produces raw **candidates**.
2. `validate` subjects candidates to tests, producing **validated candidates**.
3. `promote` packages validated candidates into **promoted theses**.
4. `deploy` executes **promoted theses**.

Each stage depends on the successful completion and artifact production of the previous stage.
