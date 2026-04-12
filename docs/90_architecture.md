# Architecture

Edge separates the platform into four concerns:

1. bounded hypothesis intake and discovery
2. validation and evidence generation
3. promotion and live-thesis packaging
4. runtime deployment and enforcement

A practical split across the codebase is:

- `project/research/` owns candidate generation, validation, promotion, and export.
- `project/live/` owns runtime loading, gating, ranking, and execution safeguards.
- `project/contracts/` provides normalized structural views consumed by tests and generated artifacts.
- `project/apps/chatgpt/` and `dashboard/` expose operator-facing inspection and control surfaces.
