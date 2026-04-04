# Architecture

This document describes the internal structure of the Edge repository and how it implements the four-stage model.

## Module Map

### 1. Stage Façades
* `project/discover/`: Entry points for candidate generation.
* `project/validate/`: Entry points for statistical truth-testing.
* `project/promote/`: Entry points for packaging and governance.
* `project/deploy/`: Entry points for runtime execution.

### 2. Research Core
* `project/research/agent_io/`: Proposal handling and experiment execution.
* `project/research/services/`: Evaluation, promotion, and discovery services.
* `project/research/validation/`: Statistical tests, regimes, and evidence bundles.
* `project/research/promotion/`: Gate evaluators and decision logic.

### 3. Runtime Core
* `project/live/`: Execution engine, oms, and thesis store.
* `project/live/contracts/`: Data models for promoted theses and trade intents.

### 4. Infrastructure
* `project/io/`: Parquet and CSV utilities.
* `project/core/`: Configuration, logging, and common exceptions.

## Artifact Boundaries
Stages communicate exclusively through persisted artifacts. This ensures:
1. **Isolation**: A failure in one stage does not corrupt the state of another.
2. **Auditability**: Every deployment can be traced back through a chain of signed or versioned artifacts.
3. **Resumability**: Stages can be re-run independently if data or logic changes.

## Compatibility Layer
The `project/cli.py` contains a deprecation and alias registry that maps legacy `operator` and `pipeline` commands to the new stage-based façades.
