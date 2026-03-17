# Contracts Layer (`project/contracts`)

The contracts layer defines the formal interfaces and data schemas between all other layers.

## 1. Ownership
- **Schema Definitions**: Pydantic models for data interchange.
- **System Mapping**: Formal representation of platform components.
- **Invariant Validation**: Rules for artifact integrity (manifests, traces).

## 2. Non-Ownership
- **Business Logic**: It never performs calculations; it only validates their results.
- **Configuration**: It defines the *schema* for config, but not the values.
- **Pipeline Execution**: It doesn't run tasks; it verifies the artifacts they produce.

## 3. Public Interfaces
- **`SystemMap`**: The graph of the entire platform.
- **`SchemaRegistry`**: Central access point for all Pydantic schemas.
- **`ContractVerification`**: API for checking if a dataframe or artifact adheres to a schema.

## 4. Constraints
- **Core-Only Dependency**: Contracts can only import from `core`.
- **Side-Effect Free**: Importing or using a contract must not modify system state.
- **Truth Source**: For any artifact (e.g., `strategy_trace`), this layer is the source of truth for its schema.
- **Honest Dependency Declaration**: Stage contracts must declare optional raw inputs that implementations may read at runtime.
