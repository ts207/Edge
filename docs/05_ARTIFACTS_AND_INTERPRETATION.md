# Artifacts and interpretation

This document explains where outputs go and how to read them.

## Artifact classes

Edge produces four different artifact classes.

### 1. Proposal artifacts

Written during proposal issuance.

Typical paths:

- `data/artifacts/experiments/<program_id>/memory/proposals.parquet`
- `data/artifacts/experiments/<program_id>/memory/proposals/<run_id>/proposal.yaml`
- `data/artifacts/experiments/<program_id>/memory/proposals/<run_id>/experiment.yaml`
- `data/artifacts/experiments/<program_id>/memory/proposals/<run_id>/run_all_overrides.json`

Use these when you need to know exactly what was asked and how it was translated.

### 2. Run artifacts

Written during execution.

Core path:

- `data/runs/<run_id>/run_manifest.json`

The manifest is the run spine. It is the first file to inspect after execution.

Typical questions answered by the manifest:

- what run actually executed
- status and terminal status
- what configs and parameters were used
- what artifacts were produced or expected
- whether the run ended mechanically or statistically cleanly

### 3. Research and promotion reports

Common report roots:

- `data/reports/phase2/<run_id>/`
- `data/reports/promotions/<run_id>/`
- `data/reports/operator/<run_id>/`
- `data/reports/shadow_live/<run_id>/`

Common files include:

- `phase2_candidates.parquet`
- `phase2_diagnostics.json`
- `promotion_statistical_audit.parquet`
- `promoted_candidates.parquet`
- `promotion_decisions.parquet`
- `promotion_summary.csv`
- `operator_summary.json`
- `operator_summary.md`

Use these to answer what survived, what failed, and why.

### 4. Packaged thesis artifacts

Primary packaged-thesis surfaces:

- `data/live/theses/<run_id>/promoted_theses.json`
- runtime config or runtime invocation that references that batch explicitly
- `data/live/theses/index.json`
- `docs/generated/thesis_overlap_graph.md`

Use these when the question is no longer “did the run look good?” and instead becomes “what reusable thesis objects exist right now?”

## How to inspect a bounded run

Inspect in this order.

### Step 1 — run manifest

Read `data/runs/<run_id>/run_manifest.json` first.

Why:

- it anchors status
- it defines the run identifier and primary provenance
- it tells you whether the failure was mechanical before you waste time on candidate-level interpretation

### Step 2 — phase-2 outputs

Read the phase-2 candidate table and diagnostics.

Typical paths:

- `data/reports/phase2/<run_id>/phase2_candidates.parquet`
- `data/reports/phase2/<run_id>/phase2_diagnostics.json`

Questions to answer:

- was there any signal at all
- which event/template/direction/horizon rows were strongest
- was the sample size large enough to trust the rejection or survival
- did stability or regime issues appear early

### Step 3 — promotion outputs

Read the promotion tables next.

Typical paths:

- `data/reports/promotions/<run_id>/promotion_statistical_audit.parquet`
- `data/reports/promotions/<run_id>/promoted_candidates.parquet`
- `data/reports/promotions/<run_id>/promotion_decisions.parquet`
- `data/reports/promotions/<run_id>/promotion_summary.csv`

Questions to answer:

- did the candidate survive promotion-oriented gates
- what was the primary fail gate
- what evidence class and promotion class does it support
- was the problem statistical, stability-related, cost-related, or contract-related

### Step 4 — operator summary

Read the operator summary for compact decision support.

Paths:

- `data/reports/operator/<run_id>/operator_summary.json`
- `data/reports/operator/<run_id>/operator_summary.md`

Use this when you need a short diagnosis without re-reading raw tables.

## How to inspect packaged thesis state

Inspect in this order.

1. `data/live/theses/<run_id>/promoted_theses.json`
2. runtime config or runtime invocation that references that batch explicitly
3. `docs/generated/thesis_overlap_graph.md`
4. `docs/generated/founding_thesis_evidence_summary.md`
5. `data/live/theses/index.json` only as a catalog of available batches
6. advanced packaging inventories such as `docs/generated/seed_thesis_catalog.md` only if you are maintaining the bootstrap lane

Questions to answer:

- what specific run produced the batch
- how many active theses exist
- which deployment states are present
- what deployment-state restrictions apply
- what promotion-class caveats still apply
- how overlap groups are formed
- where evidence gaps remain

## Current snapshot note

This snapshot already contains a packaged thesis store and several promotion evidence bundles under `data/reports/promotions/`.

That means the docs should treat the thesis store as an active surface, not a future concept.

## Generated docs to use as inventory

Already present in `docs/generated/`:

- `system_map.md`
- `event_contract_reference.md`
- `promotion_seed_inventory.md` for advanced bootstrap maintenance
- `thesis_empirical_summary.md`
- `seed_thesis_catalog.md` for advanced bootstrap maintenance
- `seed_thesis_packaging_summary.md` for advanced bootstrap maintenance
- `thesis_overlap_graph.md`
- `founding_thesis_evidence_summary.md`
- `structural_confirmation_summary.md`
- `shadow_live_thesis_summary.md`

These are inventory and summary views. They do not replace manifest- and code-level interpretation.

## Common interpretation errors

- reading only markdown summaries and ignoring the manifest
- treating a positive phase-2 row as equivalent to promotion survival
- treating packaged thesis presence as proof of production readiness
- confusing proposal memory with run execution output
- interpreting missing generated docs as absence of capability rather than absence of regeneration
