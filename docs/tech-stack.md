# Tech Stack

## Core Technologies

- Python 3.10+
- NumPy, Pandas (Internal processing)
- Logging (Standard library)
- Pytest (Testing framework)

## Architectural Decisions

- **Explicit Mode Boundaries**: Promotion logic distinguishes between 'research' and 'deploy-ready' modes using explicit helpers instead of inline checks.
- **Auditable Results**: Promotion output explicitly records the normalized run mode and whether deploy-only gates were active.
- **Isolated Deploy Reasons**: Strict-mode failures are captured in a separate `deploy_only_reject_reason` field to prevent them from being lost in the general `reject_reason` field.
- **Explicit Scoring Composition**: Promotion scores are computed from a named vector of components, making the formula auditable and versioned.
- **Auditable Score Components**: Every component of the promotion score is explicitly recorded in the output to enable detailed debugging of candidate rankings.
