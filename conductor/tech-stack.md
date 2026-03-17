# Tech Stack: Edge Framework

## Core Language
*   **Python 3.11+:** The primary language for research, pipeline orchestration, and strategy development.

## Data & Research Stack
*   **Pandas & NumPy:** Core libraries for data manipulation and vectorized calculations.
*   **PyArrow:** Used for high-performance data storage and retrieval via Parquet artifacts.
*   **scikit-learn & SciPy:** Leveraged for statistical analysis, signal processing, and machine learning components.

## Trading & Simulation
*   **Nautilus Trader:** High-fidelity, event-driven trading simulation engine used for backtesting and strategy certification.

## Validation & Infrastructure
*   **Pandera:** Strict schema enforcement for dataframe-based artifacts to ensure data integrity across pipeline stages.
*   **Pydantic:** Type-safe configuration management and validation.
*   **Modular Pipeline Engine:** A custom, artifact-centric orchestration layer for reproducible research loops.
