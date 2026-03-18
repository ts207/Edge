# Event Families, Templates, Contexts, And Regimes

## Purpose

This document is the research guide for the repo ontology.

It explains:

- what regimes, market states, contexts, events, families, templates, and hypotheses mean
- how those layers interact in discovery and promotion
- how to develop research ideas from them
- how to interpret research results without collapsing the ontology
- where the current ontology can be extended safely

The core hierarchy is:

`regime -> market state/context -> event -> canonical family -> allowed template -> hypothesis`

Each layer has a different job.

Do not treat:

- a regime as a state label
- a state label as an event
- an event as a strategy
- a template as evidence
- a promoted edge as a production-ready strategy

## Executive Model

Use this short model when reasoning about a run:

1. the market sits in a regime
2. the pipeline turns that regime into state and context features
3. detectors emit concrete events
4. each event belongs to a canonical family
5. the family constrains which templates are legal
6. search expands event plus template plus context into explicit hypotheses
7. research evaluates hypotheses, not raw events alone

If you lose the distinction between those steps, interpretation quality collapses quickly.

## Definitions

### Regime

A regime is the underlying market environment.

Examples:

- synthetic `liquidity_stress`
- synthetic `funding_dislocation`
- synthetic `breakout_failure`
- inferred live volatility, carry, trend, and spread environments

Regimes answer:

- what world are we in
- what type of behavior is likely
- what kinds of events should or should not be expected

In synthetic runs, regimes are planted directly by the generator.
In ordinary runs, regimes are inferred indirectly through context and market-state features.

### Market State

A market state is a normalized label derived from features.

Common examples in this repo:

- `vol_regime`
- `carry_state`
- `ms_trend_state`
- `ms_spread_state`
- `severity_bucket`

States answer:

- how the current environment should be bucketed for conditioning and evaluation

States are not detector outputs. They are the structured context surface used by detectors, search, and later
stability analysis.

### Context

A context is the actual filter applied to an event-template combination.

Examples:

- only high-volatility rows
- only positive carry rows
- only wide-spread rows
- only trend-confirmed rows
- only severe events

Context answers:

- when should this event-template pair be considered valid

Context is where broad event logic becomes narrower, more testable research.

### Event

An event is a concrete detector output at a specific time for a specific symbol.

Examples:

- `FND_DISLOC`
- `BASIS_DISLOC`
- `VOL_SHOCK`
- `FALSE_BREAKOUT`
- `DELEVERAGING_WAVE`

Events answer:

- what happened
- when did it happen
- for which symbol did it happen

An event is evidence of a condition, not a trading policy by itself.

### Canonical Family

A canonical family is the semantic class assigned to an event in the event registry.

Examples:

- `LIQUIDITY_DISLOCATION`
- `VOLATILITY_TRANSITION`
- `TREND_STRUCTURE`
- `POSITIONING_EXTREMES`

The family answers:

- what kind of phenomenon this event represents
- how it should be interpreted relative to other events
- which templates are legal

The family is what gives the event a research role beyond its raw detector name.

### Template

A template is a trade or evaluation shape applied to an event.

Examples:

- `mean_reversion`
- `continuation`
- `pullback_entry`
- `exhaustion_reversal`
- `tail_risk_avoid`
- `slippage_aware_filter`
- `structural_regime_shift`

Templates answer:

- how should this event be turned into a testable setup

Multiple templates can often be paired with one event, but only if the family allows them.

### Hypothesis

A hypothesis is the explicit research unit scored in discovery.

In repo-native terms it combines:

- event type
- family
- side
- horizon
- template
- state filter
- symbol scope

Hypotheses answer:

- what exact claim is being tested

This is the correct unit for comparison, memory, promotion, and reflection.

## How The Stack Uses The Ontology

### 1. Pipelines Build The State Surface

The pipelines layer produces:

- cleaned bars
- feature tables
- context features
- market-state features
- microstructure rollups

Those outputs create the state surface used by both detectors and research.

### 2. Detectors Emit Events

Detector modules consume bars and features and emit event rows.

Every event type is registered, which means it is tied to:

- a canonical family
- a reports directory
- parameter defaults
- template eligibility

### 3. The Registry Constrains Interpretation

The event registry prevents the system from treating all events as interchangeable.

Without the registry:

- search would cross events with invalid templates
- promotion would compare unlike things
- memory would store shallow event-name matches without semantic structure

### 4. Families Constrain Templates

The template registry is where the ontology becomes operational.

Family membership controls:

- which templates are legal
- what default horizon should be expected
- which type of claim the event-template pairing represents

This matters because the same event can imply very different research claims depending on template choice.

### 5. Search Expands Event Plus Template Plus Context Into Hypotheses

Search specs define:

- which event types are in scope
- which contexts are expanded
- which templates are tested
- which horizons and entry lags are used

The hypothesis registry then turns that into explicit research units.

That is what phase 2 actually evaluates.

## Family Guide

### `EXECUTION_FRICTION`

Meaning:

- the market is expensive, fragile, or mechanically unattractive to trade

Typical examples:

- spread widening
- fee-regime changes
- friction and slippage-style conditions

Typical template style:

- defensive filters
- slippage-aware gating
- tail-risk suppression

Use this family to ask:

- should the strategy trade at all right now
- should position size be reduced or blocked
- is another apparently attractive signal actually untradeable

Common research mistake:

- treating friction events as alpha instead of as a gating layer

### `TEMPORAL_STRUCTURE`

Meaning:

- a time-window, schedule, or session condition exists

Typical examples:

- funding timestamps
- session opens or closes
- scheduled news windows

Typical template style:

- simple continuation
- simple mean reversion

Use this family to ask:

- does time-of-day or schedule create a valid or invalid action window
- does another setup only work during specific windows

Common research mistake:

- over-interpreting scheduled windows as standalone edge rather than as validity windows

### `VOLATILITY_TRANSITION`

Meaning:

- the volatility regime changed materially

Typical examples:

- `VOL_SHOCK`
- volatility cluster shifts
- vol-regime changes

Typical template style:

- continuation
- trend continuation
- volatility-expansion follow
- regime filters

Use this family to ask:

- should horizon or holding-time change
- should a setup only exist after vol expansion or contraction
- does a strategy survive when vol state changes

Common research mistake:

- treating volatility-transition events as directional edge without checking liquidity and trend context

### `LIQUIDITY_DISLOCATION`

Meaning:

- liquidity is impaired, stressed, or recovering

Typical examples:

- `LIQUIDITY_STRESS_DIRECT`
- `LIQUIDITY_STRESS_PROXY`
- liquidity dislocation proxies

Typical template style:

- mean reversion
- continuation under controlled conditions
- overshoot repair
- liquidity replenishment

Use this family to ask:

- is execution feasible
- does impaired liquidity create repair or continuation behavior
- how sensitive is the setup to spread and depth conditions

Common research mistake:

- treating liquidity-stress events as pure directional alpha without execution gating

### `POSITIONING_EXTREMES`

Meaning:

- the market is crowded or forced by funding, open interest, or liquidation pressure

Typical examples:

- `DELEVERAGING_WAVE`
- `OI_FLUSH`
- funding persistence or extreme events

Typical template style:

- reversal or squeeze
- convexity capture
- continuation with caution
- exhaustion-style entries

Use this family to ask:

- is the move crowded enough to mean revert
- is a squeeze or forced unwind still in progress
- does crowding survive costs and holdout

Common research mistake:

- reading crowding as sufficient on its own without checking liquidity and forced-flow context

### `FORCED_FLOW_AND_EXHAUSTION`

Meaning:

- the move is being driven by forced flow or is reaching exhaustion

Typical examples:

- climax-volume bars
- exhaustion and divergence triggers
- forced-flow exhaustion events

Typical template style:

- exhaustion reversal
- mean reversion
- momentum fade

Use this family to ask:

- is the move late enough to fade
- does the flow appear forced rather than informational
- are we seeing exhaustion or continuation after force

Common research mistake:

- fading too early without volatility, liquidity, or trend confirmation

### `INFORMATION_DESYNC`

Meaning:

- markets or venues temporarily disagree

Typical examples:

- `CROSS_VENUE_DESYNC`
- lead-lag breaks
- convergence failures

Typical template style:

- convergence
- desync repair
- lead-lag follow
- divergence continuation

Use this family to ask:

- will this mismatch mean revert or propagate
- how quickly does the mismatch decay
- is the edge still tradable after costs

Common research mistake:

- assuming every desync is mean-reverting without checking speed and execution feasibility

### `TREND_STRUCTURE`

Meaning:

- market structure is breaking out, pulling back, or failing structurally

Typical examples:

- `FALSE_BREAKOUT`
- `PULLBACK_PIVOT`
- breakout and continuation triggers

Typical template style:

- breakout followthrough
- pullback entry
- continuation
- structural reversal

Use this family to ask:

- is structure intact
- is this a trend continuation or a structural failure
- does breakout logic survive costs and holdout

Common research mistake:

- overfitting trend templates without checking volatility and friction regime

### `STATISTICAL_DISLOCATION`

Meaning:

- a basis, z-score, correlation, or relative-value relationship is displaced

Typical examples:

- `BASIS_DISLOC`
- `FND_DISLOC`
- correlation and spread dislocations

Typical template style:

- mean reversion
- overshoot repair
- tail-risk avoidance

Use this family to ask:

- is a relationship sufficiently displaced to normalize
- does normalization survive cost and holdout
- does another higher-precedence family confirm or invalidate the claim

Common research mistake:

- trusting the displacement alone without checking execution and regime confirmation

### `REGIME_TRANSITION`

Meaning:

- the broader market mode is changing

Typical examples:

- chop-to-trend and trend-to-chop shifts
- structural regime-shift events

Typical template style:

- structural regime shift
- continuation
- defensive or filtering templates

Use this family to ask:

- has the world changed enough that prior hypotheses are no longer comparable
- should search move to a different family or template set
- does a setup only work before or after a regime transition

Common research mistake:

- treating regime transitions as intraday directional signals instead of context setters

## Template Guide

Templates are the bridge between event semantics and a testable trade shape.

Broadly:

- `mean_reversion`, `overshoot_repair`, `exhaustion_reversal`, `false_breakout_reversal`
  Use when the event suggests displacement, exhaustion, or failed continuation.
- `continuation`, `trend_continuation`, `breakout_followthrough`, `lead_lag_follow`
  Use when the event suggests propagation rather than reversal.
- `pullback_entry`
  Use when the event identifies structure but direct chase entries are poor.
- `tail_risk_avoid`, `slippage_aware_filter`, `drawdown_filter`
  Use as conditioning or defensive templates, not as directional alpha claims.
- `structural_regime_shift`, `only_if_regime`, `only_if_trend`, `only_if_funding`, `only_if_oi`
  Use to condition an event rather than redefine what the event means.

Template choice should answer:

- is the expected post-event path continuation, normalization, repair, or suppression
- does this event family support that claim semantically
- does the template narrow the event into a more defensible hypothesis

Useful template heuristics by intent:

- choose `mean_reversion`, `overshoot_repair`, or `exhaustion_reversal` when the event describes displacement,
  crowding, or failure
- choose `continuation`, `trend_continuation`, or `breakout_followthrough` when the event describes propagation,
  structural confirmation, or regime expansion
- choose `pullback_entry` when the event story is still directional but direct entry is likely too late or too
  expensive
- choose defensive templates when the event is better used as a gate than as an alpha source

Template misuse usually comes from trying to force an attractive trade shape onto an event that does not support
it semantically.

## Context And State Guide

Context should do real work.

Good context use:

- narrowing a broad event to a regime where the mechanism makes sense
- separating continuation from reversal behavior
- isolating where a family survives costs

Bad context use:

- adding many loosely related filters until one split looks good
- using context as a post hoc explanation instead of a pre-run research claim

Useful state questions:

- does the event only matter in high `vol_regime`
- does the template require positive or negative `carry_state`
- does `ms_spread_state` block the setup operationally
- does `ms_trend_state` distinguish continuation from fade

## Precedence And Arbitration

Families are not peers when they conflict.

The precedence model is:

1. `EXECUTION_FRICTION`
2. `TEMPORAL_STRUCTURE`
3. `VOLATILITY_TRANSITION`
4. `LIQUIDITY_DISLOCATION`
5. `POSITIONING_EXTREMES`
6. `FORCED_FLOW_AND_EXHAUSTION`
7. `INFORMATION_DESYNC`
8. `TREND_STRUCTURE`
9. `STATISTICAL_DISLOCATION`
10. `REGIME_TRANSITION`

Interpretation:

- friction can block an otherwise attractive lower-precedence setup
- temporal windows can invalidate slower structural ideas
- vol and liquidity should usually be checked before trusting positioning or exhaustion claims
- statistical dislocations should not override execution or liquidity constraints

Per-event overrides can raise specific events above the family default.

In practical research terms:

- if `EXECUTION_FRICTION` is hostile, do not let a lower-precedence family talk you into trading anyway
- if `TEMPORAL_STRUCTURE` says the window is invalid, treat the setup as mis-timed even if the event itself is
  attractive
- if `VOLATILITY_TRANSITION` and `LIQUIDITY_DISLOCATION` disagree with a structural or statistical setup, first
  ask whether the trade is feasible before asking whether the idea is attractive
- if multiple lower-precedence families appear simultaneously, use context and artifacts to decide whether one is
  explanatory and the others are secondary consequences

## Family-Template Selection Matrix

This is the short-form decision map for turning ontology objects into testable research.

| If the event story is mostly about... | Start with these families | Usually start with these templates | Usually add these contexts first | Common failure mode |
| --- | --- | --- | --- | --- |
| execution cost, spread stress, slippage risk | `EXECUTION_FRICTION`, `LIQUIDITY_DISLOCATION` | `slippage_aware_filter`, `tail_risk_avoid`, `overshoot_repair` | `ms_spread_state`, liquidity severity, volume participation | treating the event as alpha instead of as a gate |
| sudden volatility expansion or contraction | `VOLATILITY_TRANSITION`, `REGIME_TRANSITION` | `continuation`, `trend_continuation`, `structural_regime_shift` | `vol_regime`, severity bucket, spread state | assuming volatility transition is directional by itself |
| crowding, squeezes, forced unwind | `POSITIONING_EXTREMES`, `FORCED_FLOW_AND_EXHAUSTION` | `exhaustion_reversal`, `mean_reversion`, selective `continuation` | `carry_state`, liquidity stress, recent forced-flow state | fading too early or ignoring execution feasibility |
| structural breakout, pullback, continuation failure | `TREND_STRUCTURE` | `breakout_followthrough`, `pullback_entry`, `false_breakout_reversal` | `ms_trend_state`, `vol_regime`, spread state | using one template for all trend events |
| statistical dislocation or relative-value mismatch | `STATISTICAL_DISLOCATION`, `INFORMATION_DESYNC` | `mean_reversion`, `overshoot_repair`, `lead_lag_follow` | `vol_regime`, carry, liquidity filters | trusting the spread/z-score alone |
| session, schedule, or timestamp effects | `TEMPORAL_STRUCTURE` | simple `continuation`, simple `mean_reversion` | session or funding window only | overfitting schedule effects without mechanism |

Use the matrix to choose a first experiment, not to justify broad search.

## Developing Research Ideas

The best research ideas usually start from one of four places:

### 1. Family-Driven Idea

Example:

- `LIQUIDITY_DISLOCATION` events may support `overshoot_repair` only when spread stress normalizes quickly

This is good when:

- you understand the family semantics and want to test one plausible mechanism

### 2. Template-Driven Idea

Example:

- `continuation` appears strong in one family but may fail in another under the same context

This is good when:

- you want to compare the same trade shape across multiple families or events

### 3. Context-Driven Idea

Example:

- high `vol_regime` may improve statistical-dislocation mean reversion but degrade trend-structure continuation

This is good when:

- you suspect the mechanism is real only inside a narrower world

### 4. Failure-Driven Idea

Example:

- a prior promotion failure may indicate missing split support rather than weak economics

This is good when:

- a previous run failed ambiguously and the next experiment should remove one ambiguity

## From Idea To Research Program

The ontology is most useful when it narrows the path from observation to experiment.

Use this sequence:

1. Observe a concrete pattern in artifacts, market behavior, or a prior failed run.
2. Name the likely family before naming a trade.
3. Choose one or two legal templates for that family.
4. State which context should make the claim stronger or weaker.
5. Pick the smallest horizon, side set, and symbol scope that can falsify the claim.
6. Run the narrowest experiment that tests the claim.
7. Store the result in family-template-context language.

Good example:

- "Liquidity stress appears to create short-lived repair behavior after spread normalization. Test
  `LIQUIDITY_DISLOCATION + overshoot_repair` only when `ms_spread_state` moves from wide to normal."

Bad example:

- "Liquidity stuff might be bullish, run more searches."

## Developing Hypotheses

A strong hypothesis should state:

- what event is the trigger
- what family it belongs to
- what template expresses the claim
- what context should make it stronger or weaker
- what side and horizon are expected
- what artifact will prove or falsify the claim

Example:

- `FND_DISLOC` in `STATISTICAL_DISLOCATION` with `mean_reversion` on 15m horizons should survive costs only when `vol_regime` is high and liquidity is not impaired

That is much better than:

- funding dislocations might be good

A complete hypothesis should usually include:

- trigger event
- canonical family
- template
- direction expectation
- horizon expectation
- gating states or contexts
- execution caveat
- falsification condition

Example with falsification:

- "`FALSE_BREAKOUT` in `TREND_STRUCTURE` with `false_breakout_reversal` should outperform raw continuation on
  15m to 60m horizons when `vol_regime` is high but `ms_spread_state` is normal; reject the claim if the
  conditioned setup loses validation/test support after costs."

## Developing New Families, Templates, States, Or Regimes

Expand the ontology only when the new concept changes research behavior in a durable way.

### Add A New Family When

- multiple event types share the same interpretation but do not fit an existing family cleanly
- the family would change template eligibility or precedence meaningfully
- the family would improve memory and promotion comparisons

Do not add a family just to describe one detector more elegantly.

### Add A New Template When

- the trade shape is distinct from existing templates
- the template would apply across multiple events or families
- it changes entry, hold, or gating semantics materially

Do not add a template that is only a renamed parameter variant.

### Add A New State Or Context When

- it changes experiment selection or interpretation consistently
- it is stable enough to become a reusable conditioning dimension
- it reduces confusion between different market worlds

Do not add a state that only explains one historical run after the fact.

### Add A New Synthetic Regime When

- an important family or template cannot be falsified under current synthetic worlds
- the regime supports mechanism testing, not just prettier synthetic outcomes
- truth windows and supporting signals can be defined clearly

Do not add a synthetic regime only to rescue a detector that is weak everywhere.

## Building Search Spaces Safely

The ontology should shrink search before it expands it.

Good search expansion:

- one family, one event, two legal templates, one or two key contexts
- same event across adjacent templates
- same template across adjacent events in one family

Bad search expansion:

- many unrelated families in one batch
- mixing defensive templates and directional templates without distinction
- adding every state filter available because one of them may work

A good rule is:

- change one semantic axis at a time: family, template, context, or horizon

If two axes must change, state why both are necessary.

## Using Research Results Correctly

Use results at the hypothesis level, not the raw detector-hit level.

Interpretation ladder:

1. detector fired
2. event materialized correctly
3. family-template-context hypothesis was scored
4. the result survived statistical gates
5. the result survived operational and contract checks
6. the result survived promotion rules

Do not skip steps.

A useful result can still be:

- detector recovery success with no tradeable edge
- a clean negative result that closes a region
- an operational repair confirmation
- a context discovery that sharpens the next run

Result classes worth distinguishing:

- detector result
  - did the event materialize correctly
- ontology result
  - did the family-template-context pairing make sense
- statistical result
  - did the claim survive validation, test, multiplicity, and costs
- operational result
  - were artifacts, contracts, and manifests clean
- promotion result
  - did the candidate survive hard gates

Do not let success on one level stand in for success on another.

Examples:

- good detector recovery with no economic edge is a detector success, not a strategy success
- a promoted candidate is a promotion success, not proof of production readiness
- a statistically weak result with perfect artifacts is still a negative research result

## Turning Results Into Next Steps

After a result, ask:

- did the family-template pairing make semantic sense
- did the context sharpen or weaken the claim
- was the failure statistical, mechanical, or operational
- should the next move be exploit, explore, repair, hold, or stop

Reasonable next moves:

- same family, narrower context
- same event, different allowed template
- same template, adjacent family
- repair the artifact path before further interpretation
- stop the line if holdout support keeps failing

Map outcome to action explicitly:

- exploit
  - same family and template, tighter scope, confirmatory run
- explore adjacent
  - same family, neighboring template or context
- repair
  - artifact or contract issue blocked interpretation
- hold
  - idea is plausible but support is too thin for escalation
- stop
  - repeated clean failures show the region is weak

The ontology gives you the language to say what is being repeated, adjusted, or abandoned.

## Potential Expansion Areas

The ontology is already useful, but it can be extended carefully.

High-value expansion areas:

- more explicit market-state ontologies beyond `vol_regime` and `carry_state`
- better family-level defaults for horizons, entry lags, and context suggestions
- stronger family-to-template documentation in the unified event registry
- clearer distinction between directional templates and defensive filter templates
- better regime-specific negative controls in synthetic runs
- richer synthetic microstructure worlds for families that depend on depth and execution friction

Good expansion rule:

- extend the ontology only when the new concept changes experiment selection or result interpretation in a durable way

Bad expansion rule:

- add new states, templates, or family labels just to describe one local run better

Concrete future expansion directions:

- family-level default recommendations for horizons, entry lags, and confirmatory contexts
- richer ontology around participation quality, not just volatility and carry
- explicit "gate-only" template classes that are never scored as standalone directional hypotheses
- more structured links between canonical families and promotion-policy expectations
- better live-versus-synthetic labeling for families that need microstructure realism
- research dashboards grouped by family-template-context rather than event name only

## Research Recommendations

### Idea Selection

- start from one family and one template family whenever possible
- add context only when it expresses a real mechanism
- avoid broad cross-products until the base path is trustworthy

### Experiment Design

- compare unconditional versus conditioned behavior for the same event-template pair
- compare adjacent templates inside one family before comparing distant families
- keep family semantics intact when choosing horizons and directions

### Interpretation

- trust higher-precedence families more for gating and feasibility
- trust lower-precedence families only after those gates pass
- treat synthetic regime success as mechanism evidence, not live alpha

### Memory

- store results in ontology-native language
- remember family-template-context combinations, not just event names
- record when a family is structurally weak under a specific context

### Promotion

- promote only after hypothesis-level evidence survives statistics, contracts, and operations
- do not promote because the detector is intuitive or the family story sounds good

### Idea Backlog Management

- keep the backlog organized by family, not by raw detector name alone
- retire repeated failures at the family-template-context level
- separate "needs better data" from "mechanism likely false"
- prefer ideas that close a specific uncertainty rather than ideas that merely add breadth

### Cross-Family Comparison

- compare families only when the template semantics are genuinely comparable
- do not compare a defensive filter template directly to a directional continuation template as if they answer the
  same question
- when comparing families, keep side, horizon, and context discipline tight

## Common Mistakes

- using event names as a substitute for hypotheses
- mixing family semantics and template semantics
- over-expanding contexts until something fits
- ignoring precedence when interpreting a setup
- treating synthetic planted regimes as if they were production-ready strategies
- using one detector recovery success as evidence that all templates on that family are attractive
- adding ontology complexity faster than the research process can support
- confusing supporting synthetic signals with hard-gate truth targets
- storing memory at the event-name level when the real lesson lives at the family-template-context level

## Minimal Working Checklist

Before running research on an event, ask:

1. what regime or state should make this event meaningful
2. what family does it belong to
3. which templates are actually legal for that family
4. what context should strengthen or weaken the claim
5. what higher-precedence families might gate it
6. what exact hypothesis will be scored
7. what result would justify exploit, explore, repair, hold, or stop

## Final Guidance

Use the ontology to improve discipline, not to create more labels.

The right outcome of this framework is:

- fewer vague experiments
- clearer negative results
- better reuse of memory
- cleaner promotion decisions
- safer expansion of the research surface

If a new state, template, regime, or family does not improve one of those outcomes, it probably should not be
added yet.
