# Engine Layer (`project/engine`)

The engine layer defines the core execution logic, matching logic (for replays), and risk enforcement.

## 1. Ownership
- **Order Execution Logic**: Sending and modifying orders.
- **Risk Control**: Invariants for position limits and leverage.
- **Backtest Engine**: Simulating venue matching behavior for offline replay.

## 2. Non-Ownership
- **Research Policy**: It does not decide *why* to trade, only *how* to execute.
- **Data Ingestion**: It operates on pre-cleaned data streams.
- **High-Level Orchestration**: It is called by `runtime` but does not orchestrate the session.

## 3. Public Interfaces
- **`OrderEngine`**: Core interface for order placement.
- **`RiskEngine`**: Invariant enforcement for risk and compliance.
- **`BacktestEngine`**: Matching simulation for historical traces.

## 4. Constraints
- **Bit-for-Bit Determinism**: Given identical inputs, the engine must produce identical outputs.
- **Zero Allocations**: In performance-critical sections, minimize memory allocations.
- **Minimal Dependencies**: The engine should not depend on large research libraries like Scipy.
