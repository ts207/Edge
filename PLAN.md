Sprint 6 should be the **runtime hardening sprint**. In the roadmap, Sprint 6 is explicitly: **paper deploy hardening, decay monitor, simple caps, end-to-end golden runs**. It also says the deploy phase should stay **simple, explicit, and safe**, keep thesis store / retriever / explicit thesis selection / deployment state / paper-live modes / overlap checks / runtime logging, and add early: **decay monitor**, **max gross exposure**, **per-symbol cap**, **per-family cap**, and **max active theses**. It also explicitly says **do not prioritize** a full portfolio orchestrator, complex correlation optimizer, multi-venue routing, or on-chain integration yet.  

## Sprint 6 objective

Make deploy operationally safe enough for repeatable paper trading under the new stage model:

**discover → validate → promote → deploy**

with one hard rule preserved from the overhaul: **only promoted theses can reach deployment**. The acceptance target for deploy is:

* paper deployment works from promoted thesis batch only
* live deployment requires explicit opt-in and risk caps
* runtime can auto-flag decay and downsize/disable 

---

## What Sprint 6 is for

Sprint 6 is where you stop reshaping research semantics and start enforcing runtime discipline.

It is for:

* hardening deploy entry conditions
* adding minimal risk caps
* adding a decay monitor with explicit disable/downsize behavior
* proving the whole system with golden end-to-end runs
* ensuring runtime stays subordinate to validated/promoted artifacts

It is not for:

* portfolio optimizer sophistication
* dynamic cross-thesis correlation control
* execution venue expansion
* on-chain integration
* regime forecasting
* self-calibration
* institutional reporting
* advanced runtime assurance as a feature family  

---

## Core Sprint 6 outcome

By the end of Sprint 6, you should be able to:

1. select a promoted thesis batch
2. launch a paper deployment only from those promoted artifacts
3. enforce simple portfolio/risk caps at runtime
4. monitor thesis decay against explicit rules
5. automatically downsize or disable degraded theses
6. run a full golden pipeline from discover to deploy(paper) and verify artifact lineage and stage boundaries  

---

# Sprint 6 workstreams

## Workstream 1 — deploy admission control

### Goal

Make deployment reject anything that is not a promoted thesis artifact.

This is the most important runtime boundary. The overhaul success criteria say runtime clarity means **only promoted theses can reach deployment**, and the stage-boundary tests say deploy must not accept raw research candidates.  

### Required rules

Deployment input must include:

* `promoted_theses.json` or equivalent canonical promoted bundle
* promotion metadata
* validation lineage
* deployment-state default

Deployment must reject:

* discovery candidate tables
* validated-only candidates not yet promoted
* ad hoc proposal specs
* research candidate rows loaded directly from validation or search artifacts

### Concrete implementation

Touch first:

* `project/live/*`
* `project/portfolio/*`
* live config layer 

Add:

* deployment artifact loader that validates promoted-thesis schema
* runtime guard: `assert_promoted_input(...)`
* promotion-lineage validator
* failure messages that explicitly name missing stage

### Exit criteria

* deploy fails fast on non-promoted input
* paper deploy requires promoted thesis batch ID
* runtime state records promotion + validation lineage

---

## Workstream 2 — minimal risk caps

### Goal

Add the simple caps the roadmap names, without drifting into portfolio-system complexity.

Required early caps are:

* max gross exposure
* per-symbol cap
* per-family cap
* max active theses 

### Strong recommendation

Implement these as **deterministic pre-trade guards**, not optimization outputs.

### Cap definitions

#### 1. max gross exposure

Global ceiling across all active positions.

Use as:

* sum of absolute target exposures cannot exceed configured threshold
* new signals beyond threshold are clipped or rejected

#### 2. per-symbol cap

Prevents thesis crowding on one instrument.

Use as:

* total exposure on one symbol cannot exceed threshold
* multiple theses on same symbol share the cap

#### 3. per-family cap

Controls concentration by thesis family, template family, or strategy family.

Use as:

* all theses tagged with same family cannot exceed threshold

#### 4. max active theses

Hard count cap on concurrently active deployed theses.

Use as:

* new thesis activation rejected once count is reached
* prioritization is simple and deterministic

### Concrete implementation choices

Add a single runtime policy object, for example:

* `RuntimeRiskCaps`

  * `max_gross_exposure`
  * `max_symbol_exposure`
  * `max_family_exposure`
  * `max_active_theses`

Add one enforcement layer before order generation / target issuance.

### Decision rules

Prefer this order:

1. reject thesis if not promoted
2. reject if thesis is disabled/decayed
3. apply active-thesis count cap
4. apply symbol cap
5. apply family cap
6. apply gross cap
7. clip only if policy explicitly allows clipping; otherwise reject

### Exit criteria

* every paper deployment enforces all configured caps
* cap breach behavior is explicit and logged
* no hidden optimizer is introduced

---

## Workstream 3 — thesis decay monitor

### Goal

Add a minimal but real decay monitor that can downsize or disable a promoted thesis during runtime.

The roadmap explicitly says deploy should add a decay monitor early and that runtime should be able to auto-flag decay and downsize/disable. 

### Design principle

Keep it narrow. This is not a full online model governance platform.

### Required outputs

For each active thesis:

* current health state
* last decay check timestamp
* decay reason codes
* action taken: none / warn / downsize / disable

### Recommended first-pass decay signals

Use a compact set of interpretable signals:

#### Signal group A — realized-vs-expected edge deterioration

* rolling realized edge materially below validation expectation
* edge sign inversion over sustained window

#### Signal group B — hit-rate / payoff deterioration

* realized hit-rate below threshold
* realized payoff ratio collapse

#### Signal group C — cost drag deterioration

* realized slippage/fees materially exceed modeled assumptions

#### Signal group D — inactivity / sample starvation

* thesis not triggering enough to assess health
* effective live sample too low for confidence

### Simple health states

Use four states:

* `healthy`
* `watch`
* `degraded`
* `disabled`

### Action policy

Suggested default:

* `healthy` → normal sizing
* `watch` → keep size, log warning
* `degraded` → downsize to configured fraction
* `disabled` → stop new entries and optionally unwind by policy

### Important boundary

Decay monitor must not silently re-validate research semantics. It is a runtime health layer, not a replacement for validation.

### Concrete implementation

Add:

* `ThesisHealthSnapshot`
* `DecayRuleEngine`
* `RuntimeThesisState`
* `DecayAction`

Persist:

* runtime health log
* thesis disable events
* size adjustment events

### Exit criteria

* runtime can flag thesis deterioration from live/paper outcomes
* action mapping is deterministic
* degraded theses are visibly downsized/disabled

---

## Workstream 4 — deployment state machine

### Goal

Formalize runtime states so caps and decay actions operate cleanly.

### Recommended states

For each thesis:

* `eligible`
* `active`
* `paused`
* `degraded`
* `disabled`

Transitions:

* `eligible -> active`
* `active -> degraded`
* `degraded -> paused`
* `degraded -> disabled`
* `paused -> active` only by explicit policy/review
* `disabled` should not auto-reactivate by default

### Why this matters

Without an explicit state machine, caps and decay logic become scattered conditionals.

### Required metadata

Each thesis runtime state should track:

* thesis ID
* promotion class
* deployment mode
* current size scalar
* disable reason
* last health update
* cap breach history

### Exit criteria

* runtime actions are explainable from state transitions
* disable/downsize behavior is audit-friendly

---

## Workstream 5 — explicit paper vs live gate

### Goal

Keep live mode harder to access than paper mode.

The roadmap says paper deployment should work from promoted thesis batch only, while live deployment requires explicit opt-in and risk caps. 

### Required behavior

#### Paper mode

Allowed when:

* promoted thesis batch present
* caps configured
* runtime logging enabled

#### Live mode

Allowed only when:

* explicit live enable flag present
* caps configured
* promoted thesis batch present
* optional approval marker / operator confirmation / live-ready readiness class

### Strong recommendation

Even if live exists, Sprint 6 should optimize for **paper-first reliability**, not live feature breadth.

### Exit criteria

* paper is the default and easiest mode
* live has additional gating and explicit opt-in
* same thesis cannot silently cross from paper assumptions to live without config boundary

---

## Workstream 6 — runtime observability and artifact logging

### Goal

Make deploy runs inspectable enough to support golden tests and operational debugging.

The deploy phase explicitly keeps runtime logging. End-to-end golden runs require confirming artifact lineage and stage transitions.  

### Required deploy artifacts

At minimum:

* `deploy_run_summary.json`
* `active_thesis_state.parquet`
* `cap_breach_events.parquet`
* `decay_events.parquet`
* `runtime_actions.parquet`

### Required summary fields

* deploy run ID
* promoted batch ID
* promotion artifact path
* validation run IDs referenced
* deploy mode: paper/live
* caps config hash
* thesis count loaded
* thesis count activated
* thesis count downsized
* thesis count disabled
* symbols traded
* time window

### Exit criteria

* every deploy run has auditable runtime artifacts
* decay and cap decisions are reconstructible

---

## Workstream 7 — golden end-to-end runs

### Goal

Prove the full stage model with deterministic examples.

The roadmap explicitly names the third testing layer as end-to-end golden tests that run:

* discover
* validate
* promote
* deploy (paper mode)

and confirm artifact lineage and stage transitions.  

### Required golden scenarios

#### Golden A — happy path

* discover yields candidates
* validate yields validated subset
* promote yields promoted theses
* deploy paper activates promoted theses
* runtime artifacts created
* no stage leakage

#### Golden B — empty promotion path

* discover yields candidates
* validate rejects all
* promote emits none
* deploy refuses to start

#### Golden C — cap breach path

* promoted batch valid
* deploy attempts over-concentrated set
* caps reject or clip deterministically
* events logged

#### Golden D — decay disable path

* promoted thesis starts active
* synthetic or controlled degraded runtime metrics trigger decay
* thesis is downsized or disabled
* state transition logged

### Important testing property

These tests should validate **lineage**, not just numerical results.

They should prove:

* discovery outputs candidates only
* validation outputs validated candidates and rejection reasons
* promotion outputs promoted theses only
* deploy accepts promoted theses only 

### Exit criteria

* golden runs are reproducible
* failures isolate the broken stage boundary quickly

---

## Workstream 8 — config simplification

### Goal

Prevent runtime from becoming configuration-chaotic.

### Recommended config split

#### Global deploy config

* mode
* max gross exposure
* max active theses
* log paths
* decay policy toggle

#### Symbol/family caps config

* per-symbol cap map
* per-family cap map

#### Thesis runtime overrides

* allowed only for:

  * size scalar
  * enabled/disabled state
  * review status

### Avoid in Sprint 6

Do not add:

* multi-layer optimizer configs
* dynamic correlation models
* venue routing policy matrices
* adaptive execution families

### Exit criteria

* configs are short and explainable
* cap/decay policies are visible in one place

---

# Concrete tickets

## Deploy boundary

* add promoted-thesis-only loader
* reject raw candidate / validated-only artifacts
* add deployment lineage validation
* add clear stage-boundary error messages

## Caps

* implement `RuntimeRiskCaps`
* enforce gross, symbol, family, active-thesis caps
* log cap violations
* decide reject-vs-clip policy

## Decay

* add thesis health model
* implement rolling health checks
* map health to actions
* persist downsize/disable events

## Runtime state

* add thesis runtime state machine
* add state transition logger
* block auto-reactivation by default

## Modes

* enforce stronger gate for live than paper
* make paper default
* validate caps presence before start

## Artifacts

* emit deploy summary
* emit cap breach events
* emit decay events
* emit active thesis state snapshots

## Testing

* happy path golden run
* all-rejected path
* cap-breach path
* decay-disable path

---

# Suggested implementation order

1. **Deploy admission control**

   * make deploy accept promoted theses only

2. **Simple caps**

   * add deterministic runtime guards

3. **Decay monitor**

   * add health states and downsize/disable actions

4. **Deploy artifacts/logging**

   * make actions inspectable

5. **Golden end-to-end runs**

   * prove the pipeline

This order is strongest because golden tests are only useful after the runtime boundary and policy mechanics are fixed.

---

# Definition of done

Sprint 6 is done when all of these are true:

* paper deploy loads promoted theses only
* live mode requires explicit opt-in plus configured caps
* runtime enforces max gross / symbol / family / active-thesis caps
* runtime can auto-flag thesis decay and downsize/disable
* deploy artifacts record lineage, cap events, and decay events
* end-to-end golden tests pass from discover through deploy(paper)
* no portfolio orchestrator or execution-complexity expansion was introduced  

# Strongest recommendation

Start Sprint 6 with a single invariant and build outward from it:

**deploy only promoted theses**

Then add **deterministic caps**, then **decay-driven downsize/disable**, then **golden runs**.

That sequence preserves the overhaul’s core runtime rule while keeping deploy simple, explicit, and safe.
