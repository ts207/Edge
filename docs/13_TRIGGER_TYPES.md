# Trigger Types

This document defines the trigger types supported by the hypothesis model and the agent proposal layer.

Primary sources:

- [project/domain/hypotheses.py](../project/domain/hypotheses.py)
- [project/research/agent_io/proposal_schema.py](../project/research/agent_io/proposal_schema.py)

## Overview

The repository supports six trigger types:

- `EVENT`
- `STATE`
- `TRANSITION`
- `FEATURE_PREDICATE`
- `SEQUENCE`
- `INTERACTION`

At the operator proposal layer, trigger types are declared in `hypothesis.trigger.type`.
The operator loader compiles that bounded front-door shape into the legacy internal trigger space.

Use the narrowest trigger type that directly matches the claim being tested.

## EVENT

Definition:

- Trigger on a named event in the event registry.

Required fields:

- `event_id`

Validation:

- `event_id` must exist in the compiled event registry.

Shape:

```yaml
hypothesis:
  trigger:
    type: event
    event_id: BASIS_DISLOC
```

Use when:

- The claim is about what happens after a specific event.
- The run is organized around one event family or one event type.
- You want the cleanest attribution path.

Examples:

- `BASIS_DISLOC`
- `VOL_SHOCK`
- `LIQUIDATION_CASCADE`

Why use it:

- It is the most direct and most common trigger type for bounded event research.
- It aligns with the operator rule to start narrow.

## STATE

Definition:

- Trigger on being in a named state.

Required fields:

- `state_id`

Optional fields:

- `state_active`

Validation:

- `state_id` must exist in the state registry.

Shape:

```yaml
hypothesis:
  trigger:
    type: state
    state_id: HIGH_VOL_REGIME
```

Use when:

- The claim is about a regime holding, not a point event.
- You care about persistent conditions rather than isolated detections.

Why use it:

- It expresses “while in state X” directly.
- It avoids forcing a state-like idea into an event-only shape.

## TRANSITION

Definition:

- Trigger on moving from one named state to another.

Required fields:

- `from_state`
- `to_state`

Validation:

- Both states must exist in the state registry.

Shape:

```yaml
hypothesis:
  trigger:
    type: transition
    from_state: CHOP_REGIME
    to_state: BULL_TREND_REGIME
```

Use when:

- The claim is about a regime change.
- Entry logic depends on entering or leaving a state.

Why use it:

- It encodes change explicitly instead of approximating it with two separate state checks.

## FEATURE_PREDICATE

Definition:

- Trigger when a feature satisfies a threshold rule.

Required fields:

- `feature`
- `operator`
- `threshold`

Allowed operators:

- `>=`
- `<=`
- `>`
- `<`
- `==`

Shape:

```yaml
hypothesis:
  trigger:
    type: feature_predicate
    feature: funding_rate_scaled
    operator: ">="
    threshold: 2.0
```

Use when:

- The claim is directly about a measured feature crossing a rule.
- You do not want to depend on a named event detector.

Why use it:

- It makes the trigger surface explicit and numerical.
- It is appropriate for threshold-based claims such as “when feature X exceeds Y”.

## SEQUENCE

Definition:

- Trigger on an ordered list of events.

Required fields:

- `events`

Optional fields:

- `max_gap_bars`

Validation:

- Every event in `events` must exist in the event registry.
- `max_gap_bars` must be non-negative.

Shape:

```yaml
hypothesis:
  trigger:
    type: sequence
    events:
      - FUNDING_EXTREME_ONSET
      - RANGE_BREAKOUT
    max_gap_bars: 12
```

Use when:

- Order matters.
- The claim is “A then B” or “A followed by B within N bars”.

Why use it:

- It captures temporal ordering directly.
- It is the correct form for multi-step event narratives.

## INTERACTION

Definition:

- Trigger on a logical relationship between two components.

Required fields:

- `left`
- `right`
- `op`

Optional fields:

- `lag`

Allowed `op` values:

- `and`
- `or`
- `confirm`
- `exclude`

Validation:

- `left` and `right` must resolve to known event IDs or state IDs.

Shape:

```yaml
hypothesis:
  trigger:
    type: interaction
    left: VOL_SHOCK
    right: HIGH_VOL_REGIME
    op: confirm
    lag: 6
```

Use when:

- The claim depends on two conditions jointly.
- One event must confirm or exclude another.

Why use it:

- It is the correct representation for combined triggers.
- It avoids flattening a two-part claim into a single synthetic event.

## Selection Rules

Prefer:

- `EVENT` for most narrow event-family research
- `STATE` for regime-held claims
- `TRANSITION` for regime-change claims
- `FEATURE_PREDICATE` for threshold rules on features
- `SEQUENCE` for ordered multi-event claims
- `INTERACTION` for logical combinations of event/state components

Avoid:

- using `SEQUENCE` when order does not matter
- using `INTERACTION` when one plain event is enough
- using `FEATURE_PREDICATE` when there is already a named event that expresses the same idea cleanly
- mixing unrelated trigger types in one narrow confirmatory run

## Proposal Surface vs Hypothesis Surface

Operator proposal layer:

- Trigger types are declared in `hypothesis.trigger.type`.
- The operator-facing shape is always single-hypothesis and lowercase: `event`, `state`, `transition`, `feature_predicate`, `sequence`, `interaction`.
- The loader compiles that shape into legacy `trigger_space.allowed_trigger_types` internally.

Hypothesis layer:

- Runtime hypotheses use `TriggerSpec`.
- `TriggerSpec.trigger_type` is normalized to lowercase internally.

This means:

- operator proposal YAML uses `event`, `state`, `transition`, `feature_predicate`, `sequence`, `interaction`
- internal `TriggerSpec` instances use `event`, `state`, `transition`, `feature_predicate`, `sequence`, `interaction`

## Default Recommendation

If the claim is event-driven and you are starting a fresh research slice, use `EVENT` first.

That matches:

- the repo’s event registry
- the operator guidance to start narrow
- the most stable attribution path for experiment interpretation

## Concrete Repo Examples

These examples use identifiers that exist in the current registries:

- event registry: [events.yaml](../project/configs/registries/events.yaml)
- state registry: [states.yaml](../project/configs/registries/states.yaml)

### EVENT example

```yaml
hypothesis:
  trigger:
    type: event
    event_id: BASIS_DISLOC
```

Other valid event examples:

- `VOL_SHOCK`
- `FALSE_BREAKOUT`
- `CROSS_ASSET_DESYNC_EVENT`

### STATE example

```yaml
hypothesis:
  trigger:
    type: state
    state_id: HIGH_VOL_REGIME
```

Other valid state examples:

- `LOW_VOL_REGIME`
- `BULL_TREND_REGIME`
- `BEAR_TREND_REGIME`
- `CHOP_REGIME`
- `OVERBOUGHT_STATE`
- `OVERSOLD_STATE`
- `CROWDING_STATE`
- `MS_LIQUIDATION_STATE`

### TRANSITION example

```yaml
hypothesis:
  trigger:
    type: transition
    from_state: CHOP_REGIME
    to_state: BULL_TREND_REGIME
```

Other valid transition shapes:

- `LOW_VOL_REGIME` -> `HIGH_VOL_REGIME`
- `BEAR_TREND_REGIME` -> `CHOP_REGIME`

### FEATURE_PREDICATE example

```yaml
hypothesis:
  trigger:
    type: feature_predicate
    feature: funding_rate_scaled
    operator: ">="
    threshold: 2.0
```

Use this style only when the feature exists in the feature surface for the run you are planning.

### SEQUENCE example

```yaml
hypothesis:
  trigger:
    type: sequence
    events:
      - BASIS_DISLOC
      - BREAKOUT_TRIGGER
    max_gap_bars: 12
```

Other valid sequence ingredients from the current event registry:

- `FUNDING_EXTREME_ONSET`
- `VOL_SHOCK`
- `FALSE_BREAKOUT`
- `LIQUIDATION_CASCADE`

### INTERACTION example

```yaml
hypothesis:
  trigger:
    type: interaction
    left: VOL_SHOCK
    right: HIGH_VOL_REGIME
    op: confirm
    lag: 6
```

Other valid interaction shapes:

- `left: BASIS_DISLOC`, `right: CHOP_REGIME`, `op: and`
- `left: FALSE_BREAKOUT`, `right: BEAR_TREND_REGIME`, `op: confirm`
- `left: LIQUIDATION_CASCADE`, `right: LOW_VOL_REGIME`, `op: exclude`

## Full Hypothesis Examples

These examples show complete hypothesis shapes, not just trigger fragments.

There are two useful surfaces:

- proposal-style examples for agent input
- runtime `HypothesisSpec` examples for internal hypothesis materialization

Primary source:

- [project/domain/hypotheses.py](../project/domain/hypotheses.py)

### Proposal-style event hypothesis

This is the narrowest and most common pattern for a fresh research slice.

```yaml
program_id: btc_basis_slice
run_mode: research
objective_name: retail_profitability
promotion_profile: research
symbols:
  - BTCUSDT
timeframe: 5m
start: "2022-11-01"
end: "2022-12-31"
instrument_classes:
  - crypto
hypothesis:
  trigger:
    type: event
    event_id: BASIS_DISLOC
  template: mean_reversion
  direction: short
  horizon_bars: 12
  entry_lag_bars: 1
```

What this means:

- symbol scope: `BTCUSDT`
- trigger: `BASIS_DISLOC`
- template: `mean_reversion`
- direction: `short`
- horizon: `12` bars
- entry lag: `1`

### Runtime `HypothesisSpec` event example

This matches the internal hypothesis object shape.

```yaml
trigger:
  trigger_type: event
  event_id: BASIS_DISLOC
direction: short
horizon: 12b
template_id: mean_reversion
entry_lag: 1
cost_profile: standard
objective_profile: mean_return
```

### Runtime `HypothesisSpec` state example

```yaml
trigger:
  trigger_type: state
  state_id: HIGH_VOL_REGIME
  state_active: true
direction: long
horizon: 24b
template_id: continuation
entry_lag: 1
cost_profile: standard
objective_profile: mean_return
```

### Runtime `HypothesisSpec` transition example

```yaml
trigger:
  trigger_type: transition
  from_state: CHOP_REGIME
  to_state: BULL_TREND_REGIME
direction: long
horizon: 24b
template_id: continuation
entry_lag: 1
cost_profile: standard
objective_profile: mean_return
```

### Runtime `HypothesisSpec` feature-predicate example

```yaml
trigger:
  trigger_type: feature_predicate
  feature: funding_rate_scaled
  operator: ">="
  threshold: 2.0
direction: short
horizon: 12b
template_id: mean_reversion
entry_lag: 1
cost_profile: standard
objective_profile: mean_return
```

### Runtime `HypothesisSpec` sequence example

```yaml
trigger:
  trigger_type: sequence
  sequence_id: BASIS_THEN_BREAKOUT
  events:
    - BASIS_DISLOC
    - BREAKOUT_TRIGGER
  max_gap:
    - 12
direction: long
horizon: 24b
template_id: continuation
entry_lag: 1
cost_profile: standard
objective_profile: mean_return
```

### Runtime `HypothesisSpec` interaction example

```yaml
trigger:
  trigger_type: interaction
  interaction_id: VOL_CONFIRM
  left: VOL_SHOCK
  right: HIGH_VOL_REGIME
  op: confirm
  lag: 6
direction: long
horizon: 24b
template_id: continuation
entry_lag: 1
cost_profile: standard
objective_profile: mean_return
```

### Context-conditioned hypothesis example

Runtime hypotheses can also carry a `context` object.

```yaml
trigger:
  trigger_type: event
  event_id: FALSE_BREAKOUT
direction: short
horizon: 12b
template_id: mean_reversion
context:
  market_regime: HIGH_VOL_REGIME
entry_lag: 1
cost_profile: standard
objective_profile: mean_return
```

Use context only when the claim actually depends on context. Do not add it by default.
