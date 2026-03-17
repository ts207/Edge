# Product Guidelines: Edge Framework

## Documentation & Communication
*   **Prose Style:** All documentation, comments, and project communications must be **Formal & Technical**. The tone should be precise, authoritative, and focused on implementation and research details.
*   **Documentation Method:**
    *   **YAML-Centric Specs:** Define events, strategies, and search spaces primarily through structured YAML files to ensure machine-readability and automation.
    *   **Modular Markdown Docs:** Maintain a dedicated `docs/` directory for high-level architectural designs, protocols, and guides.

## Architectural Principles
*   **Functional-First Logic:** Prioritize pure functions and stateless logic for core research and feature engineering to enhance testability and parallelism.
*   **Modular Object-Oriented Programming:** Use well-defined class hierarchies for detectors and strategies to ensure modularity, extensibility, and clean integration with the Nautilus runtime.

## Engineering Standards
*   **Performance-Optimized:** Every stage of the pipeline must be optimized for high processing throughput and memory efficiency. Use Numba, NumPy, and PyArrow effectively to handle large-scale market data.
*   **Research Integrity:** Maintain high fidelity between synthetic testing and real-market simulations to ensure strategy reproducibility.
