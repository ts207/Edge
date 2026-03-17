# Runtime Layer (`project/runtime`)

The runtime layer is responsible for low-latency trade execution, live order management, and bit-for-bit deterministic replays.

## 1. Ownership
- **Trading Session Lifecycle**: Order management, fills, and account state.
- **Replay Engine**: Precise deterministic playback of historical events.
- **Execution Drivers**: Adapters for specific venues (e.g., Nautilus).

## 2. Non-Ownership
- **Research Policy**: It must not contain policy-specific "why" logic. It only executes "what."
- **Data Ingestion**: It does not own data cleaning; it expects clean streams from `pipelines`.
- **Promotion**: It has no knowledge of candidate promotion logic.

## 3. Public Interfaces
- **`ExecutionService`**: Central service for starting/stopping trading sessions.
- **`ReplayRunner`**: Service for executing backtests.
- **`OMS` (Order Management System)**: The core state machine for order lifecycle.

## 4. Constraints
- **Zero Global State**: All state must be contained within session-specific objects.
- **Strict Determinism**: Replaying a trace must result in identical state transitions.
- **No Large Dependencies**: Heavy libraries (like `pandas`) are restricted to boundary conversion only.
