Use this as the coding-agent plan.

# Objective

Replace the current operator-facing **search-space proposal** with a **single-hypothesis proposal**, while preserving the existing backend by compiling the new format into the current `AgentProposal`.

At the same time, move the repo toward **one canonical path**:

**proposal → bounded run → promotion → thesis batch export → runtime**

Seed is not part of this path.

---

# Scope

## In scope

* add a new operator-facing proposal schema
* add loader + validator + compiler
* switch operator entry points to the new loader
* keep downstream engine unchanged where possible
* add one canonical example proposal
* add tests for compatibility and strictness
* update docs/examples to show only the new path

## Out of scope for this pass

* redesigning experiment engine internals
* rewriting phase-2 search logic
* changing runtime thesis format
* deleting all seed code immediately
* broad refactors outside proposal/loading surfaces

---

# Repo facts to anchor implementation

Current files that matter:

* `project/research/agent_io/proposal_schema.py`
* `project/research/agent_io/proposal_to_experiment.py`
* `project/operator/bounded.py`

Current state:

* `AgentProposal` is the core internal object
* `load_agent_proposal(...)` only accepts legacy search-space format
* `proposal_to_experiment.py` already translates `AgentProposal` to experiment config
* bounded comparison logic already works on normalized `AgentProposal` fields

That means the safest move is:

**change the front door only**
and keep everything after `AgentProposal` mostly intact.

---

# Deliverables

## Code deliverables

1. `SingleHypothesisProposal` schema
2. `TriggerSpec` schema
3. `load_operator_proposal(...)`
4. `validate_single_hypothesis_proposal(...)`
5. `compile_single_hypothesis_to_agent_proposal(...)`
6. trigger compiler for supported trigger types
7. operator entry points switched to new loader
8. new canonical example proposal
9. tests
10. docs/examples updated

## Behavioral deliverables

* operator can submit one clean hypothesis YAML
* repo compiles it into legacy `AgentProposal`
* existing experiment translation still works
* bounded mode still works
* canonical docs/examples no longer expose `trigger_space` to normal users

---

# Implementation sequence

## Phase 1 — add the new schema without changing behavior

### Files

* edit `project/research/agent_io/proposal_schema.py`

### Tasks

Add:

* `TriggerSpec`
* `SingleHypothesisProposal`

Keep `AgentProposal` unchanged.

### Design rules

The new operator-facing format should represent exactly one hypothesis.

Recommended field shape:

* `program_id`
* `description`
* `start`
* `end`
* `symbols`
* `timeframe`
* `instrument_classes`
* `hypothesis.trigger`
* `hypothesis.template`
* `hypothesis.direction`
* `hypothesis.horizon_bars`
* `hypothesis.entry_lag_bars`
* optional `contexts`
* optional `config_overlays`
* optional `bounded`

### Constraint

Do not delete or alter legacy `AgentProposal` fields yet.

### Stop condition

* new dataclasses/types exist
* legacy proposal loading still works untouched

---

## Phase 2 — implement strict single-hypothesis validation

### Files

* edit `project/research/agent_io/proposal_schema.py`

### Tasks

Add validation that enforces:

* exactly 1 symbol
* exactly 1 template
* exactly 1 direction
* exactly 1 horizon
* exactly 1 entry lag
* exactly 1 trigger object
* trigger-type-specific required fields

### Trigger validation rules

#### event

Require:

* `event_id`

#### state

Require:

* `state_id`

#### transition

Require:

* `from_state`
* `to_state`

#### feature_predicate

Require:

* `feature`
* `operator`
* `threshold`

#### sequence

Require:

* `events`
  Optional:
* `max_gap_bars`

#### interaction

Require:

* `left`
* `right`
* `op`

### Strong recommendation

For first pass, make canonical support:

* `event` only in docs/examples
* but code can support all mapped types if easy

### Stop condition

* invalid single-hypothesis proposals fail early with clear errors

---

## Phase 3 — add compiler into current `AgentProposal`

### Files

* edit `project/research/agent_io/proposal_schema.py`

### Tasks

Add:

* `_compile_trigger_spec_to_trigger_space(...)`
* `compile_single_hypothesis_to_agent_proposal(...)`

### Required mapping

#### event

maps to:

* `allowed_trigger_types = ["EVENT"]`
* `events.include = [event_id]`

#### state

maps to:

* `allowed_trigger_types = ["STATE"]`
* `states.include = [state_id]`

#### transition

maps to:

* `allowed_trigger_types = ["TRANSITION"]`
* `transitions.include = [from->to]` or current expected internal shape

#### feature_predicate

maps to:

* `allowed_trigger_types = ["FEATURE_PREDICATE"]`
* `feature_predicates.include = [...]`

#### sequence

maps to:

* `allowed_trigger_types = ["SEQUENCE"]`
* `sequences.include = [...]`

#### interaction

maps to:

* `allowed_trigger_types = ["INTERACTION"]`
* `interactions.include = [...]`

### Key rule

Compiler output must be a valid `AgentProposal` that downstream code already accepts.

### Stop condition

* a new-format proposal compiles into legacy `AgentProposal`
* `proposal.to_dict()` remains compatible with downstream consumers

---

## Phase 4 — add a dual-format loader

### Files

* edit `project/research/agent_io/proposal_schema.py`

### Tasks

Add:

* `load_operator_proposal(path_or_payload)`

Behavior:

* if payload contains `hypothesis` or single-trigger format, load new schema, validate, compile to `AgentProposal`
* otherwise fall back to `load_agent_proposal(...)`

### Important

Do not break `load_agent_proposal(...)`
Keep it for backwards compatibility.

### Stop condition

* both legacy and new proposal files can be loaded into `AgentProposal`

---

## Phase 5 — switch operator entry points to the new loader

### Files

* edit `project/research/agent_io/proposal_to_experiment.py`
* edit `project/operator/bounded.py`
* inspect any operator or ChatGPT wrapper code that reads proposals directly

### Tasks

#### In `proposal_to_experiment.py`

Replace direct calls to:

* `load_agent_proposal(...)`

with:

* `load_operator_proposal(...)`

#### In `bounded.py`

Make sure both current proposal and baseline proposal are normalized through the same loader/compiler path before comparison.

This preserves bounded diffing on:

* `trigger_space`
* `templates`
* `directions`
* `horizons_bars`
* `entry_lags`

### Stop condition

* legacy proposals still run
* new proposals also run
* bounded comparison still works after normalization

---

## Phase 6 — add canonical operator example

### Files

* add `spec/proposals/canonical_event_hypothesis.yaml`

### Content

Create one minimal event-driven proposal:

* 1 symbol
* 1 event trigger
* 1 template
* 1 direction
* 1 horizon
* 1 entry lag

Example shape:

```yaml
program_id: volshock_btc_long_12b
description: Long continuation after VOL_SHOCK on BTCUSDT 5m

start: "2024-01-01"
end: "2024-01-31"
symbols: [BTCUSDT]
timeframe: 5m
instrument_classes: [crypto]

hypothesis:
  trigger:
    type: event
    event_id: VOL_SHOCK
  template: continuation
  direction: long
  horizon_bars: 12
  entry_lag_bars: 1

run_mode: research
promotion_profile: research
config_overlays:
  - project/configs/golden_synthetic_discovery_fast.yaml
```

### Stop condition

* repo has one canonical example that represents the new path clearly

---

## Phase 7 — add tests before broader docs cleanup

### Files to add

* `project/tests/research/agent_io/test_single_hypothesis_loader.py`
* `project/tests/operator/test_single_hypothesis_bounded.py`

### Required test cases

#### Compatibility

* legacy proposal loads successfully
* new proposal loads successfully
* both become valid `AgentProposal`

#### Strictness

* multiple symbols fails
* multiple templates fails
* multiple directions fails
* multiple horizons fails
* multiple entry lags fails
* missing event_id fails for event trigger

#### Trigger compilation

* event compiles correctly
* state compiles correctly if supported
* feature predicate compiles correctly if supported

#### Translation

* `proposal_to_experiment_config(...)` works on compiled new proposal

#### Bounded mode

* baseline + current proposal compare correctly after normalization

### Stop condition

* tests cover loader, compiler, compatibility, and bounded behavior

---

## Phase 8 — documentation cleanup for the front door

### Files to update

* main proposal docs
* operator workflow docs
* any examples under `docs/` or `spec/proposals/`
* ChatGPT/app docs if they show proposal format

### Rules

Show only:

* new single-hypothesis proposal format

Do not show in primary docs:

* `trigger_space`
* `allowed_trigger_types`
* multi-template lists
* multi-horizon lists
* multi-direction search spaces

Legacy format can be mentioned only as:

* compatibility mode
* internal/legacy surface

### Stop condition

* a new user sees only one proposal format

---

# Seed removal plan boundary for this coding pass

Do not fully remove seed in this same pass.

## Do now

* remove seed from operator-facing docs
* stop presenting seed as canonical thesis source
* plan runtime/config migration separately

## Do later

* remove `load_latest_theses` fallback behavior
* require explicit `thesis_path` or `thesis_run_id`
* stop pointing `data/live/theses/index.json` at seed by default
* delete seed packaging as canonical path

This keeps this coding change bounded.

---

# Agent execution instructions



## Step 1

Read:

* `project/research/agent_io/proposal_schema.py`
* `project/research/agent_io/proposal_to_experiment.py`
* `project/operator/bounded.py`

Build a dependency map of where proposals are loaded.

## Step 2

Implement `SingleHypothesisProposal`, `TriggerSpec`, validation, compiler, and dual-format loader in `proposal_schema.py`.

## Step 3

Switch proposal-loading call sites from `load_agent_proposal` to `load_operator_proposal`.

## Step 4

Add the canonical example proposal.

## Step 5

Add compatibility + strictness + bounded tests.

## Step 6

Run targeted tests only for touched surfaces first.

## Step 7

Update docs/examples to expose only the new proposal format.

## Step 8

Produce a short migration summary:

* files changed
* behavior preserved
* remaining legacy surfaces

---

# Success criteria

The pass is complete when all of these are true:

1. a single-hypothesis YAML can be submitted
2. it loads through one operator loader
3. it compiles to valid `AgentProposal`
4. `proposal_to_experiment.py` works without internal redesign
5. bounded comparison still works
6. canonical examples use only the new format
7. legacy proposals still load for compatibility
8. no primary doc tells users to author `trigger_space` directly

---

# Failure conditions to avoid

* do not rewrite the experiment engine
* do not delete `AgentProposal`
* do not break old proposal files
* do not expose both new and old formats equally in docs
* do not mix seed-removal runtime changes into this same code pass unless necessary

---

# Best implementation choice

Make the new schema a **strict front-door contract** and keep the rest of the repo on `AgentProposal` for now.

That gives:

* one clean user path
* minimal breakage
* bounded implementation surface
* clear migration sequencing

