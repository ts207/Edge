---
name: edge-thesis-bootstrap
description: Run the Edge thesis bootstrap lane using the documented packaging sequence. Use when the task is converting tested claims into canonical thesis artifacts, scorecards, packaged theses, and overlap outputs rather than running another discovery experiment.
---

# Edge Thesis Bootstrap

Use this skill for the packaging lane, not for raw discovery.

## Read first

1. `docs/03_OPERATOR_WORKFLOW.md`
2. `docs/09_THESIS_BOOTSTRAP_AND_PROMOTION.md`
3. `docs/AGENT_CONTRACT.md`
4. `docs/VERIFICATION.md`

## Canonical sequence

```bash
python -m project.scripts.build_seed_bootstrap_artifacts
python -m project.scripts.build_seed_testing_artifacts
python -m project.scripts.build_seed_empirical_artifacts
python -m project.scripts.build_founding_thesis_evidence
python -m project.scripts.build_seed_packaging_artifacts
python -m project.scripts.build_structural_confirmation_artifacts
python -m project.scripts.build_thesis_overlap_artifacts
```

## Required review surfaces

- `docs/generated/promotion_seed_inventory.*`
- `docs/generated/thesis_testing_scorecards.*`
- `docs/generated/thesis_empirical_scorecards.*`
- `docs/generated/seed_thesis_packaging_summary.*`
- `docs/generated/thesis_overlap_graph.*`
- `data/live/theses/index.json`

## Hard rules

- Do not describe `seed_promoted` as production-ready.
- Regenerate overlap artifacts after packaging changes.
- Treat bootstrap artifacts as authoritative over hand-written notes.
