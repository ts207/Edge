# Project Model

This repository is built around explicit research objects. Most confusion comes from mixing them up.

## Core Objects

### Event

An event is a discrete trigger at a timestamp.

Examples:

- `VOL_SHOCK`
- `BASIS_DISLOC`
- `LIQUIDATION_CASCADE`

Question it answers:
"What happened now?"

### Family

A family is the higher-level category an event or state belongs to. Families constrain compatible templates and organize search.

Examples:

- `VOLATILITY_TRANSITION`
- `LIQUIDITY_DISLOCATION`
- `TREND_STRUCTURE`

Question it answers:
"What class of phenomenon is this?"

### Template

A template is the hypothesis shape tested around a trigger.

Examples:

- `mean_reversion`
- `continuation`
- `trend_continuation`
- `only_if_regime`

Question it answers:
"How are we trying to extract edge from this trigger?"

### State

A state is a market-condition label on bars.

Examples:

- `TRENDING_STATE`
- `CHOP_STATE`
- `HIGH_VOL_REGIME`
- `LOW_LIQUIDITY_STATE`

Question it answers:
"What condition is the market in around the trigger?"

### Regime

Regime is used in two distinct ways in this repo:

1. canonical grouping on an event row, such as `VOLATILITY_TRANSITION`
2. composite evaluation buckets built from states, such as `high_vol.funding_pos.trend.wide`

Question it answers:
"Does this candidate survive across environments?"

## Example: `VOL_SHOCK`

`VOL_SHOCK` is a good anchor example.

- object type: event
- family: `VOLATILITY_TRANSITION`
- detector meaning: realized-volatility shock onset
- later tested with templates like `mean_reversion`, `continuation`, `only_if_regime`
- evaluated across state-derived regime buckets

So `VOL_SHOCK` is not a family and not a state. It is an event inside a family.

## What The Pipeline Actually Tests

A narrow research claim usually looks like:

"When event X occurs, does template Y in direction Z over horizon H produce post-cost expectancy that survives robustness and bridge gating?"

That means the repo is not merely checking whether an event exists. It is checking whether a trade idea around that event survives:

- sample size thresholds
- `t_stat` thresholds
- multiple-testing control
- cost adjustments
- regime robustness
- stress scenarios
- bridge tradability

## Searchable Universe

Current compiled counts in this workspace:

- `70` event types
- `72` state IDs
- `10` searchable event families
- `8` searchable state families

Those counts come from the compiled domain registry exposed through [project/domain/](/home/irene/Edge/project/domain).

## Family And Template Compatibility

Family compatibility is maintained in:

- [spec/templates/event_template_registry.yaml](/home/irene/Edge/spec/templates/event_template_registry.yaml)
- [spec/events/event_registry_unified.yaml](/home/irene/Edge/spec/events/event_registry_unified.yaml)

This matters because not every template is legal for every family. A clean search run should avoid generating obviously incompatible combinations.

## Practical Rule

When you read a result, ask in this order:

1. what event or state triggered the candidate
2. what family constrained the template set
3. what template generated the trade idea
4. what states and regimes qualified or disqualified the idea
5. whether the candidate died in search, bridge, or promotion

---

## Glossary

These terms look similar but mean different things.

### Proposal

A compact operator input that defines a bounded research run.

Typical fields: `program_id`, objective, symbols, timeframe, start/end, trigger space, templates, horizons, directions, entry lags.

Main surface: [project/research/agent_io/proposal_schema.py](/home/irene/Edge/project/research/agent_io/proposal_schema.py)

### Experiment

A repo-native execution config produced from a proposal. It is the translated, fully structured configuration that the pipeline actually uses.

Main surfaces: [proposal_to_experiment.py](/home/irene/Edge/project/research/agent_io/proposal_to_experiment.py), [experiment_engine.py](/home/irene/Edge/project/research/experiment_engine.py)

### Run

A concrete execution instance with a specific `run_id`. A run writes artifacts under directories keyed by `run_id`.

### Hypothesis

A single explicit claim evaluated by the research/search layer.

Examples: after `BASIS_DISLOC`, `BTCUSDT`, `short`, `12b`, `mean_reversion`.

Main surface: [project/domain/hypotheses.py](/home/irene/Edge/project/domain/hypotheses.py)

### Candidate

A hypothesis that has been evaluated and materialized into a row with metrics and gates. A candidate has: metrics, fail reasons or pass flags, and promotion-related fields.

### Blueprint

An executable strategy specification describing: entry logic, exit logic, sizing, overlays, and lineage. It is the object the DSL/runtime layer interprets.

Main surfaces: [project/strategy/dsl](/home/irene/Edge/project/strategy/dsl), [blueprint.py](/home/irene/Edge/project/strategy/models/blueprint.py)

### Strategy

A runtime-executable trading logic object. The engine runs strategies, not raw hypotheses.

### Trigger

The condition that causes a hypothesis or strategy entry logic to activate.

Supported types: `EVENT`, `STATE`, `TRANSITION`, `FEATURE_PREDICATE`, `SEQUENCE`, `INTERACTION`.

Reference: [13_TRIGGER_TYPES.md](/home/irene/Edge/docs/13_TRIGGER_TYPES.md)

### Artifact

A file written by the system that records what happened. Examples: run manifest, stage manifest, hypothesis table, candidate parquet, funnel summary, metrics JSON, engine trace.

Artifacts are the source of truth.

### Promotion

The gating process that decides whether a candidate is eligible to move forward. Promotion is not the same as detection success, positive expectancy in one slice, or a completed run.

### Backtest

Using the engine/runtime path to simulate strategy execution and produce a ledger/PnL trace.

Main surface: [runner.py](/home/irene/Edge/project/engine/runner.py)

This is different from the canonical search evaluator, which is a statistical trigger-conditioned evaluation path.

### Evaluation

This word has two senses in the repo:

- **Research evaluation**: score a hypothesis statistically in the search pipeline.
- **Execution evaluation**: run a strategy and evaluate realized ledger/PnL behavior in the engine.

Do not treat those as the same thing.
