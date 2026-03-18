# Event Families, Templates, Contexts, And Regimes

This document explains the research ontology used by the repository.

The key hierarchy is:

`regime -> market state/context -> event -> canonical family -> template -> hypothesis`

Each layer has a different job. Confusing them leads to bad research decisions.

## Executive Model

Use this short model when reasoning about a run:

1. the market sits in a regime
2. the feature pipeline turns that regime into state and context features
3. detectors emit concrete events
4. each event belongs to a canonical family
5. the family constrains legal templates
6. search expands event plus template plus context into hypotheses
7. research evaluates hypotheses, not raw events alone

## Definitions

### Regime

The underlying market environment.

Examples:

- synthetic `liquidity_stress`
- synthetic `funding_dislocation`
- inferred volatility, carry, trend, and spread environments

Regimes describe the world the market is in.

### Market State

A normalized label derived from features.

Examples:

- `vol_regime`
- `carry_state`
- `ms_trend_state`
- `ms_spread_state`

States are context surfaces, not detector outputs.

### Context

The actual filter applied to an event-template combination.

Examples:

- only high volatility rows
- only acceptable spread rows
- only confident trend rows

Context is where a broad event claim becomes a narrower research claim.

### Event

A concrete detector output at a time for a symbol.

Examples:

- `FND_DISLOC`
- `BASIS_DISLOC`
- `VOL_SHOCK`
- `FALSE_BREAKOUT`

An event is evidence of a condition, not a strategy.

### Canonical Family

The semantic class assigned to an event in the registry.

Examples:

- `LIQUIDITY_DISLOCATION`
- `VOLATILITY_TRANSITION`
- `TREND_STRUCTURE`
- `POSITIONING_EXTREMES`

The family controls how an event should be interpreted and which templates are legal.

### Template

A trade or evaluation shape applied to an event.

Examples:

- `mean_reversion`
- `continuation`
- `pullback_entry`
- `tail_risk_avoid`
- `slippage_aware_filter`

Templates describe how the event should be tested.

### Hypothesis

The explicit research unit scored in discovery.

A hypothesis combines:

- event
- family
- template
- context
- side
- horizon
- entry lag
- symbol scope

This is the correct comparison and memory unit.

## How The Stack Uses The Ontology

### Pipelines Build Context

The feature and context stages build:

- cleaned bars
- feature tables
- context features
- market-state features

These outputs create the context surface used by detectors and research.

### Detectors Emit Events

Detectors consume bars and features and emit event rows.

Every maintained event type is tied to:

- a canonical family
- parameter defaults
- report paths
- template eligibility

### Families Constrain Templates

The template registry prevents invalid pairings.

Without this:

- search would cross events with semantically invalid templates
- promotion would compare unlike things
- memory would store shallow name matches instead of ontology-native claims

### Search Expands To Hypotheses

Phase 2 evaluates explicit hypotheses built from:

- event type
- template
- context
- horizon
- direction
- entry lag

This is why raw event counts are not the same as research success.

## Family Guide

### `EXECUTION_FRICTION`

Meaning:

- the market is mechanically expensive or fragile to trade

Typical use:

- gating
- tail-risk avoidance
- slippage-aware suppression

Common mistake:

- treating friction as alpha

### `TEMPORAL_STRUCTURE`

Meaning:

- a time-window or schedule condition exists

Typical use:

- validity windows
- time-conditioned comparisons

Common mistake:

- reading timing labels as standalone edge

### `VOLATILITY_TRANSITION`

Meaning:

- volatility changed materially

Typical use:

- continuation after expansion
- contraction or breakout conditioning
- horizon adaptation

Common mistake:

- using volatility labels without checking whether execution and liquidity still allow the trade

### `LIQUIDITY_DISLOCATION`

Meaning:

- liquidity is impaired, stressed, or recovering

Typical use:

- repair
- replenishment
- selective continuation or avoidance

Common mistake:

- ignoring execution feasibility while treating the family as pure alpha

### `POSITIONING_EXTREMES`

Meaning:

- crowding, funding, OI, or liquidation pressure is extreme

Typical use:

- squeeze
- reversal
- forced-flow continuation

Common mistake:

- forgetting that crowding can be directionally meaningful but still untradeable if liquidity is hostile

### `FORCED_FLOW_AND_EXHAUSTION`

Meaning:

- a forced move or exhaustion structure exists

Typical use:

- exhaustion reversal
- continuation failure
- climax or rebound studies

Common mistake:

- overfitting local structure without enough holdout support

### `INFORMATION_DESYNC`

Meaning:

- cross-venue or cross-signal information is temporarily misaligned

Typical use:

- catch-up
- convergence
- lead-lag repair

Common mistake:

- ignoring that these effects often decay quickly and can be dominated by friction

### `TREND_STRUCTURE`

Meaning:

- breakout, pullback, false breakout, or continuation structure exists

Typical use:

- breakout follow-through
- pullback entry
- false-breakout reversal

Common mistake:

- treating a trend label as if it already implies the correct template

### `STATISTICAL_DISLOCATION`

Meaning:

- a z-score or basis-style anomaly exists

Typical use:

- mean reversion
- overshoot repair
- defensive filters around extremes

Common mistake:

- turning statistical stretch into a strategy claim without checking context and costs

### `REGIME_TRANSITION`

Meaning:

- the market is moving between structural states

Typical use:

- conditioning
- horizon changes
- regime-aware routing

Common mistake:

- treating broad regime labels as exact truth rather than as probabilistic context

## Using The Ontology Correctly

When you develop a research idea:

1. state the regime intuition
2. translate it into event and family terms
3. choose only legal templates
4. choose the context that makes the claim falsifiable
5. test the hypothesis, not the story

When you interpret results:

- detector success is not strategy success
- family compatibility is not evidence
- context improvement matters only if the conditioned slice still has enough support
- promotion is still a separate gate after discovery

## Safe Expansion Rules

When adding new ontology surfaces:

- add a new family only when a real semantic class is missing
- add a new template only when it represents a distinct evaluation shape
- add a new state only when it is reused across multiple research consumers
- add a new synthetic regime only when it changes a meaningful validation question

Do not add ontology breadth that does not improve decisions.
