# Core Concepts & Glossary

This is the canonical terminology guide for the current Edge repo. Older docs mixed conceptual and legacy terms. This version prefers the terms that match the current CLI, artifact contracts, and runtime thesis model.

## Semantic Model

### Proposal

The YAML file passed to `discover`. In conceptual terms this is the bounded Structured Hypothesis. In code and commands, the repo usually calls it a proposal.

### Structured Hypothesis

The research claim frozen into a proposal: which Anchor, Filter, scope, and search dimensions should be tested.

### Anchor

The market event or transition that defines the start of the opportunity.

Examples:

- `VOL_SHOCK`
- `OI_SPIKE`
- `BREAKOUT`

### Filter

The contextual predicate that narrows where or when the Anchor should count.

Examples:

- volatile regime only
- specific directional context
- supportive market-state requirements

### Sampling Policy

The rule that determines how many observations or episodes are taken from an event sequence.

Examples:

- once per episode
- episodic sampling
- repeated bar extraction with constraints

### Template

The behavioral or structural logic used to interpret or package an Anchor-based opportunity.

## Research Lifecycle Objects

### Candidate

A discovered research opportunity with concrete parameters, evidence estimates, and ranking metadata.

### Validation Bundle

The persisted stage-2 output written under `data/reports/validation/<run_id>/`. This is the contract object that promotion consumes.

### Validated Candidate

A Candidate that survived stage-2 validation gates and is present in the validation bundle as a survivor rather than only as a rejected or inconclusive record.

### Promotion Class

The class assigned during promotion that describes readiness and intended operational maturity.

Current classes:

- `paper_promoted`
- `production_promoted`

### Thesis

The runtime-facing packaged object exported from promotion. A thesis contains evidence, lineage, governance, requirements, source metadata, and deployment state.

The repo now prefers Thesis rather than Strategy as the top-level runtime object name.

## Runtime Concepts

### Deployment State

The thesis lifecycle state that controls what the runtime is allowed to do with the thesis.

Current states include:

- `monitor_only`
- `paper_only`
- `promoted`
- `paper_enabled`
- `paper_approved`
- `live_eligible`
- `live_enabled`
- `live_paused`
- `live_disabled`
- `retired`

### DeploymentGate

The live runtime gate that validates approval metadata, cap profiles, and live-trading eligibility before live theses are admitted.

### Live Approval

Operator sign-off metadata carried in the thesis contract. This includes approval status, approver identity, approval timestamp, risk profile, and paper-run sufficiency details.

### Cap Profile

Per-thesis hard risk caps such as max notional, max position notional, max daily loss, and kill-switch scope.

## Stage Terms

### Discover

Generate and rank candidates from a bounded proposal.

### Validate

Falsify and stress-test candidates, then write the canonical validation bundle.

### Promote

Select, classify, and package validated results into thesis inventory candidates, then export them into runtime-facing storage.

### Deploy

Load exported thesis batches into paper or live runtime under explicit gating.

## Compatibility Terms

### Operator

A deprecated but still-supported compatibility command family around bounded research issuance, proposal explanation, reporting, and campaign execution.

### Catalog

A support plane for listing runs, comparing runs, and auditing historical artifacts. It is not a fifth lifecycle stage.

### Trigger Discovery

An advanced internal research lane that mines candidate trigger ideas and manages adoption state. It is not the same as ordinary discover-stage execution.
