# Proposal to live-trade trace

This document answers one specific question in full:

> **What exactly happens, step by step, from the moment a proposal is submitted until something could be live traded?**

The answer is more nuanced than a single linear chain because this repo has **three distinct states** that are easy to confuse:

1. **a proposal was issued and run**
2. **a run produced promoted candidates and exported runtime-readable theses**
3. **the runtime is actually allowed to submit real orders**

Those are **not** the same thing.

The most important repo-state conclusion first:

- A canonical proposal run **does** translate the proposal, execute the research pipeline, write promotion artifacts, and export a thesis-store payload.
- That thesis export is **not automatically live-trading eligible**.
- In the code snapshot in this repo, the canonical proposal path exports theses as **`paper_promoted` + `paper_only`**, and because proposal-driven operator runs do **not** include blueprint compilation, those theses will usually start as **`pending_blueprint`**.
- The live runtime in `runtime_mode='trading'` rejects any thesis whose `deployment_state != 'live_enabled'`.
- There is now an explicit operator-managed bridge on the export surface:
  `python -m project.research.export_promoted_theses --run_id <run_id> --register-runtime <name> --set-deployment-state <thesis_id_or_candidate_id>=live_enabled`
  but it is still an explicit human decision, not an automatic promotion.

So the correct narrative is:

`proposal -> bounded run -> phase-2 candidates -> promotion evidence -> thesis export -> optional blueprint activation -> runtime matching -> trade-intent decision -> order-plan submission`,

with a critical caveat:

> **the canonical proposal path reaches runtime-readable thesis export, but not automatic live-enabled trading permission.**

---

## 1. The starting object: the proposal

A proposal is the operator-facing contract that narrows the search surface.

Canonical loader and schema:

- `project/research/agent_io/proposal_schema.py`

A proposal specifies, among other things:

- `program_id`
- time window: `start`, `end`
- `symbols`
- `hypothesis.trigger`
- `hypothesis.template`
- `hypothesis.direction`
- `hypothesis.horizon_bars`
- `hypothesis.entry_lag_bars`
- `objective_name`
- `promotion_profile`
- `timeframe`
- contexts and exclusions
- optional bounded-change contract via `bounded`
- optional config overlays and knob overrides

This is not yet a runnable backtest config. It is a **bounded search instruction**.

What the proposal is saying is roughly:

- which market slice to inspect
- which event families and template families are allowed
- how large the hypothesis search surface may be
- whether promotion is disabled/research-oriented/deployment-oriented
- whether the run is a fresh discovery or a bounded confirmation against a baseline

---

## 2. Operator preflight: can this proposal even be issued?

Canonical entry:

```bash
edge operator preflight --proposal <proposal.yaml>
```

Implementation:

- `project/operator/preflight.py`

Preflight does **not** execute the run. It checks whether the proposal can be translated and whether the repo has the minimum local conditions to run safely.

It performs these checks:

1. **proposal loads and validates**
   - `load_operator_proposal(...)`
2. **proposal can be translated into an experiment plan**
   - `translate_and_validate_proposal(...)`
3. **search spec exists**
4. **required local data coverage exists**
   - required: OHLCV for the proposal timeframe
   - optional/warn-level: funding, open interest
5. **artifact output root is writable**

What preflight produces:

- a structured preflight result
- a status of `pass`, `warn`, or `block`

What preflight does **not** do:

- it does not choose winners
- it does not create a research run
- it does not create a live thesis
- it does not change any runtime state

---

## 3. Proposal planning: the proposal is translated into the actual run contract

Canonical entry:

```bash
edge operator plan --proposal <proposal.yaml>
```

Planning path:

- `project.cli` -> `project.research.agent_io.issue_proposal.issue_proposal(...)`
- `issue_proposal(...)` calls `execute_proposal(...)` with `plan_only=True`
- `execute_proposal(...)` calls `translate_and_validate_proposal(...)`

This is the first major transformation.

### 3.1 What translation does

File:

- `project/research/agent_io/proposal_to_experiment.py`

The translator converts the proposal into two artifacts:

1. **`experiment.yaml`**
   - a normalized experiment config that the experiment engine can validate
2. **`run_all_overrides.json`**
   - CLI-level overrides used to drive `project.pipelines.run_all`

The translation step resolves:

- search limits from `project/configs/registries/search_limits.yaml`
- evaluation horizons, directions, entry lags
- whether promotion is enabled
- bounded baseline comparison settings
- explicit config overlays
- proposal-settable knobs

Then it validates that this translated config can actually form an experiment plan by calling:

- `project.research.experiment_engine.build_experiment_plan(...)`

The validated plan returns the key “search surface summary”:

- `program_id`
- `estimated_hypothesis_count`
- `required_detectors`
- `required_features`
- `required_states`

### 3.2 Why this matters

This is where the repo turns:

- a human/operator description of the search

into

- a concrete executable research contract

If translation fails here, nothing downstream should be trusted.

---

## 4. Proposal issuance: the repo assigns identity and stores memory

Canonical path for both `plan` and `run`:

- `project/research/agent_io/issue_proposal.py`

This step does several important things before the pipeline runs.

### 4.1 A run id is generated

`generate_run_id(...)` builds a deterministic-ish run id from:

- `program_id`
- UTC timestamp
- a short hash of the proposal payload

This matters because the run id becomes the primary join key across:

- manifests
- reports
- promotion outputs
- live thesis exports
- proposal memory

### 4.2 The proposal is written into memory

The proposal is copied into program memory under a stable path such as:

- `data/artifacts/experiments/<program_id>/memory/proposals/<run_id>/proposal.yaml`

And the proposal-memory table is updated, typically:

- `data/artifacts/experiments/<program_id>/memory/proposals.parquet`

### 4.3 Bounded proposals are checked against their baseline

If `bounded:` is present in the proposal, the repo enforces a one-change discipline via:

- `project/operator/bounded.py`

It loads the baseline proposal from memory and verifies:

- the baseline exists
- the baseline belongs to the same `program_id`
- exactly one tracked field changed
- the changed field equals `allowed_change_field`

This is how the repo prevents a “confirmation” proposal from silently becoming a new unconstrained discovery run.

---

## 5. Operator run: the translated proposal becomes a real pipeline execution

Canonical entry:

```bash
edge operator run --proposal <proposal.yaml>
```

Execution path:

- `project.cli` -> `issue_proposal(...)`
- `issue_proposal(...)` -> `execute_proposal(...)`
- `execute_proposal(...)` builds a `python -m project.pipelines.run_all ...` command
- `subprocess.run(...)` launches the canonical pipeline

At this point the proposal has crossed the boundary from:

- **operator intent**

into

- **artifacted pipeline execution**

The important consequence is that the rest of the lifecycle is driven by `run_all` stage planning and execution, not by the proposal layer directly.

---

## 6. Run bootstrap and manifest seeding inside `run_all`

Canonical engine:

- `project/pipelines/run_all.py`

Before stages execute, `run_all` performs a bootstrap pass:

- resolves CLI/config context
- builds the stage plan
- performs preflight on stage/artifact contracts
- initializes run manifest state
- records effective behavior and overrides
- validates runtime invariant specs if configured
- evaluates startup guards

Key bootstrap helpers:

- `project.pipelines.pipeline_planning`
- `project.pipelines.run_all_bootstrap`
- `project.pipelines.pipeline_provenance`
- `project.pipelines.pipeline_execution`

Primary run identity artifact:

- `data/runs/<run_id>/run_manifest.json`

This manifest is the authoritative record of:

- what stages were planned
- what actually ran
- what failed
- timings
- lineage and fingerprints
- postflight audit state

Nothing in the live/runtime layer should be inferred from loose stdout alone; the manifest is the durable mechanical truth.

---

## 7. The stage plan: what actually runs for a proposal-driven research run

The canonical proposal path uses `experiment_config`, so stage planning follows the experiment-driven branch in:

- `project/pipelines/stages/research.py`
- `project/pipelines/stages/core.py`

A representative planned run for `spec/proposals/demo_synthetic_fast.yaml` resolves to this stage sequence:

1. `ingest_binance_um_ohlcv_5m`
2. `ingest_binance_um_funding`
3. `ingest_binance_spot_ohlcv_5m`
4. `build_cleaned_5m`
5. `build_features_5m`
6. `build_universe_snapshots`
7. `build_market_context_5m`
8. `build_microstructure_rollup_5m`
9. `validate_feature_integrity_5m`
10. `validate_data_coverage_5m`
11. `build_cleaned_5m_spot`
12. `build_features_5m_spot`
13. `build_normalized_replay_stream`
14. `run_causal_lane_ticks`
15. `analyze_events__VOL_SHOCK_5m`
16. `build_event_registry__VOL_SHOCK_5m`
17. `canonicalize_event_episodes__VOL_SHOCK_5m`
18. `phase1_correlation_clustering`
19. `phase2_search_engine`
20. `summarize_discovery_quality`
21. `export_edge_candidates`
22. `generate_negative_control_summary`
23. `promote_candidates`
24. `update_edge_registry`
25. `update_campaign_memory`
26. `analyze_conditional_expectancy`
27. `validate_expectancy_traps`
28. `generate_recommendations_checklist`
29. `finalize_experiment`

A different proposal may change:

- which event analyzers are included
- which timeframes are planned
- whether runtime replay stages are present
- whether promotion is disabled
- whether campaign memory is updated

But the broad lifecycle remains the same.

---

## 8. What each stage family does

### 8.1 Ingest and cleaned-bar stages

Representative stages:

- `ingest_binance_um_ohlcv_*`
- `ingest_binance_um_funding`
- `ingest_binance_spot_ohlcv_*`
- `build_cleaned_*`
- `build_cleaned_*_spot`

Purpose:

- materialize raw market inputs
- normalize them into run-scoped cleaned bars
- provide the minimum time series base for downstream feature generation

If this layer is wrong, everything above it is contaminated.

### 8.2 Feature and market-context stages

Representative stages:

- `build_features_*`
- `build_market_context_*`
- `build_microstructure_rollup_*`
- `validate_feature_integrity_*`
- `validate_data_coverage_*`

Purpose:

- derive the feature state used by event analyzers and phase-2 search
- validate gaps and schema integrity
- build the run-scoped context needed for downstream regime and tradability checks

### 8.3 Runtime replay certification stages

Representative stages:

- `build_normalized_replay_stream`
- `run_causal_lane_ticks`

These are not the live runtime itself.

They are run-time-oriented replay/certification surfaces that ensure the run can satisfy runtime invariant expectations when enabled.

### 8.4 Event detection and episode canonicalization stages

Representative stages:

- `analyze_events__<EVENT>_<TF>`
- `build_event_registry__<EVENT>_<TF>`
- `canonicalize_event_episodes__<EVENT>_<TF>`
- `phase1_correlation_clustering`

Purpose:

- detect the concrete trigger events in the requested market slice
- register them into canonical event records
- merge or canonicalize them into episodes suitable for later reasoning
- produce the event/episode substrate on which hypotheses can be tested

This is where the proposal’s trigger space starts becoming actual empirical objects.

### 8.5 Phase-2 search stage

Canonical stage:

- `phase2_search_engine`

Purpose:

- enumerate candidate hypotheses allowed by the experiment plan
- combine trigger definitions, templates, horizons, directions, and lag rules
- score/evaluate candidate setups over the bounded sample
- write the candidate universe

This is the main search/discovery stage. It turns:

- event/episode substrate + search rules

into

- evaluated candidate rows

Primary output family:

- `data/reports/phase2/<run_id>/phase2_candidates.parquet`

### 8.6 Candidate export stage

Canonical stage:

- `export_edge_candidates`

Purpose:

- collect and normalize phase-2 outputs into a promotion-ready candidate universe
- write candidate records in a schema expected by downstream promotion logic

This is the boundary between raw discovery and governed promotion.

### 8.7 Negative-control stage

Canonical stage:

- `generate_negative_control_summary`

Purpose:

- summarize placebo and negative-control evidence needed by promotion gates
- ensure promotion is not just a naive “best-looking row wins” filter

### 8.8 Promotion stage

Canonical stage:

- `promote_candidates`
- implementation anchor: `project/research/services/promotion_service.py`

This is the most important transition after search.

It does **not** merely sort candidates. It performs a gate-based promotion decision using:

- q-value limits
- minimum event counts
- stability score thresholds
- sign consistency thresholds
- cost survival thresholds
- TOB coverage thresholds
- negative-control requirements
- multiplicity diagnostics
- retail/low-capital viability constraints
- promotion profile policy
- evidence bundle validation

Outputs include:

- `promotion_statistical_audit.parquet`
- `promoted_candidates.parquet`
- `promotion_decisions.parquet`
- `promotion_summary.csv`
- `evidence_bundles.jsonl`
- promotion contract markdown/json artifacts

Conceptually this stage answers:

> Which candidate claims survive enough statistical, economic, and falsification pressure to be carried forward?

### 8.9 Post-promotion review stages

Representative stages:

- `update_edge_registry`
- `update_campaign_memory`
- `analyze_conditional_expectancy`
- `validate_expectancy_traps`
- `generate_recommendations_checklist`
- `finalize_experiment`

Purpose:

- register the run into program memory and registry surfaces
- compute economic diagnostics and trap checks
- produce operator-readable recommendations
- finalize the bounded experiment record

These improve decision quality, but they do not, by themselves, grant live trading permission.

---

## 9. The first runtime-facing transition: promotion exports a thesis store payload

This happens **inside** the promotion service.

After promotion reports are written, `project/research/services/promotion_service.py` calls:

- `project.research.live_export.export_promoted_theses_for_run(...)`

This is a critical design point.

It means the proposal path does not stop at `promoted_candidates.parquet`. It already exports a runtime-readable thesis payload.

### 9.1 What gets written

The live-export step writes:

- `data/live/theses/<run_id>/promoted_theses.json`
- `data/live/theses/index.json`
- promotion-side contract summaries such as:
  - `data/reports/promotions/<run_id>/promoted_thesis_contracts.json`
  - `data/reports/promotions/<run_id>/promoted_thesis_contracts.md`

### 9.2 What is inside a promoted thesis

Contract:

- `project/live/contracts/promoted_thesis.py`

A promoted thesis carries fields such as:

- `thesis_id`
- `promotion_class`
- `deployment_state`
- `status`
- symbol scope
- timeframe
- primary event id / event family
- canonical regime
- side
- required/supportive context
- invalidation
- evidence metrics
- lineage
- governance metadata
- requirement clauses
- source provenance

This is the object consumed by the live/runtime layer.

It is much richer than a raw candidate row.

---

## 10. Why a proposal run still does not equal “ready to live trade”

This is the main place where people misread the repo.

### 10.1 The proposal path exports theses as paper-only by default

Inside `project/research/live_export.py`, the proposal-run thesis export currently constructs theses as:

- `promotion_class="paper_promoted"`
- `deployment_state="paper_only"`

That means the proposal-driven export is runtime-readable, but not live-trading eligible unless an explicit deployment-state override is later applied.

### 10.2 Proposal runs do not compile strategy blueprints

This is a second major distinction.

`project/pipelines/stages/evaluation.py` returns **no evaluation stages** when `experiment_config` is present.

Proposal-driven operator runs always pass an experiment config.

So the canonical operator path does **not** include:

- `compile_strategy_blueprints`
- `build_strategy_candidates`
- `select_profitable_strategies`

Those belong to the advanced strategy-packaging path, not the core proposal path.

### 10.3 Consequence: proposal-run theses are usually `pending_blueprint`

In `project/research/live_export.py`, thesis status is determined by whether a blueprint with invalidation data exists.

- no blueprint -> `pending_blueprint`
- valid blueprint/invalidation -> `active`

Because the canonical proposal path skips blueprint compilation, the first exported thesis objects will usually be:

- `paper_promoted`
- `paper_only`
- `pending_blueprint`

That is enough for runtime visibility and inspection, but not enough for trading.

---

## 11. The optional blueprint-activation step

Outside the canonical proposal path, an advanced packaging flow can run:

- `compile_strategy_blueprints`

Implementation:

- `project/research/compile_strategy_blueprints.py`

That stage writes strategy blueprints and then calls:

- `export_promoted_theses_for_run(...)`

again.

The effect is important:

- the thesis store can be re-exported with blueprint-linked theses
- statuses may move from `pending_blueprint` to `active`

But even here, by default, the export still sets:

- `promotion_class="paper_promoted"`
- `deployment_state="paper_only"`

So blueprint activation improves runtime usability, but still does not make the thesis live-enabled unless an operator explicitly marks deployment state during or after export.

---

## 12. The bootstrap packaging lane is a separate path, not the operator proposal path

The repo also has a thesis bootstrap lane invoked by:

```bash
make package
```

This runs scripts such as:

- `build_seed_bootstrap_artifacts` optionally with `--thesis_run_id <run_id>`
- `build_seed_testing_artifacts`
- `build_seed_empirical_artifacts`
- `build_founding_thesis_evidence`
- `build_seed_packaging_artifacts`
- `build_structural_confirmation_artifacts`
- `build_thesis_overlap_artifacts --run_id <run_id>`

This path is handled primarily by:

- `project/research/seed_bootstrap.py`
- `project/research/seed_package.py`

This lane builds packaged theses from bootstrap/founding-thesis artifacts, not directly from a single proposal-issued operator run.
It is not the canonical answer to "which runtime thesis batch should this config load?".

Its output uses explicit promotion/deployment classes such as:

- `seed_promoted` -> typically `monitor_only`
- `paper_promoted` -> typically `paper_only`

The repo also defines the conceptual mapping:

- `production_promoted` -> `live_enabled`

via `project/research/services/promotion_service.py`

But the canonical operator story should still be read as:

- export from one run
- point runtime at that explicit run batch
- inspect `deployment_state` for permission

---

## 13. What the live runtime actually does with the thesis store

The live runtime does not reason from proposal YAML or promotion CSV files directly.

It loads a thesis store:

- `project/live/thesis_store.py`

The store is retrieved either:

- from a specific run id
- or from an explicitly configured thesis batch path

The runtime then evaluates incoming market state against those theses.

### 13.1 Live event detection

In `project/live/runner.py`, new market bars are processed and passed through:

- `detect_live_event(...)`

If no supported event is detected, nothing happens.

If an event is detected, the runner builds a:

- `LiveTradeContext`

including:

- symbol
- timeframe
- detected event
- market features
- portfolio state
- execution environment

### 13.2 Thesis retrieval and ranking

Then the runtime calls:

- `decide_trade_intent(...)`

which internally calls:

- `retrieve_ranked_theses(...)`

This step checks whether each thesis matches the current context based on things like:

- symbol scope
- timeframe
- event ids / event families
- canonical regime
- governance metadata
- freshness policy
- contradiction events
- overlap suppression
- deployment state

### 13.3 The hard gate that blocks real trading

In `project/live/retriever.py`:

- if `runtime_mode == "trading"` and `deployment_state != "live_enabled"`, the thesis is rejected

So:

- `monitor_only` is blocked in trading mode
- `paper_only` is blocked in trading mode
- only `live_enabled` passes the deployment-state gate for actual trading

This is the single cleanest code-level answer to “when is the runtime willing to consider real order submission?”

---

## 14. Additional runtime conditions before any real order can be sent

Even if a thesis were `live_enabled`, the runner still does not immediately fire orders without more conditions.

`project/live/runner.py` requires:

1. `runtime_mode == "trading"`
2. `strategy_runtime.implemented == true`
3. a loaded thesis store
4. a detected live event that generates a non-reject trade intent
5. `auto_submit == true` for automatic submission
6. the trade intent action must be in the allowed submission actions
7. order-plan checks must pass
8. order-manager checks must pass
9. kill-switch and execution-quality checks must not block the submission

So even after a thesis becomes runtime-eligible, the actual live order path is still:

`eligible thesis -> trade intent -> order plan -> execution risk checks -> order submission`

---

## 15. The final trade-submission path

When all gates are satisfied, the runtime reaches:

- `build_order_plan(...)`
- `order_manager.submit_order_async(...)`

The runner enriches the order plan with thesis-derived fields such as:

- expected return bps
- expected adverse bps
- expected net edge bps
- thesis id
- governance and overlap metadata

Only here does the lifecycle become an actual tradable action.

This is **far downstream** from proposal issuance.

---

## 16. The complete stage-by-stage narrative

Here is the full story in one pass.

### Stage A — proposal authoring

You write a proposal that narrows:

- market slice
- trigger space
- template scope
- horizon/direction search
- promotion intent
- optional bounded-change discipline

### Stage B — preflight

The repo checks:

- schema validity
- translation validity
- search-spec existence
- local data coverage
- writable artifact roots

### Stage C — planning

The proposal is translated into:

- `experiment.yaml`
- `run_all_overrides.json`
- a validated experiment plan

### Stage D — issuance and memory registration

The repo:

- chooses `run_id`
- copies the proposal into experiment memory
- appends a row to proposal memory
- validates bounded-change rules if needed

### Stage E — pipeline bootstrap

`run_all`:

- resolves config context
- builds stage plan
- seeds run manifest
- applies provenance and startup guards

### Stage F — market data preparation

The pipeline builds:

- cleaned bars
- feature tables
- market context
- microstructure rollups
- data integrity checks

### Stage G — event substrate construction

The pipeline:

- detects events
- writes event registry rows
- canonicalizes episodes
- clusters phase-1 structure

### Stage H — phase-2 search

The pipeline:

- enumerates allowed hypotheses
- evaluates them in the bounded sample
- writes `phase2_candidates`

### Stage I — candidate normalization

The pipeline:

- collects phase-2 survivors into exportable edge candidates

### Stage J — negative controls and promotion

The pipeline:

- builds falsification summaries
- applies promotion thresholds
- writes promotion audits and evidence bundles
- writes `promoted_candidates`

### Stage K — live thesis export

The promotion service:

- converts promoted candidates + evidence bundles into `PromotedThesis` objects
- writes them into `data/live/theses/<run_id>/promoted_theses.json`
- updates `data/live/theses/index.json`

At this point the run has become **runtime-readable**.

### Stage L — optional blueprint activation

A separate advanced flow can compile strategy blueprints and re-export the thesis batch.

This can change thesis status from:

- `pending_blueprint` -> `active`

But not, in the current snapshot, to `live_enabled`.

### Stage M — runtime matching

The live runtime:

- loads the thesis store
- detects live events from incoming market data
- builds a live trade context
- ranks matching theses
- rejects anything with invalid freshness/governance/deployment state

### Stage N — trade-intent generation

If a thesis survives matching and eligibility:

- a decision score is computed
- a `TradeIntent` is produced

### Stage O — order planning and submission

If runtime mode, automation, and execution checks all pass:

- an order plan is built
- the order manager submits the order

Only **here** is the proposal’s downstream effect actually live traded.

---

## 17. The exact repo-state answer to “when is a proposal live traded?”

In this repo snapshot, the honest answer is:

A proposal becomes **research-executed** when `edge operator run` completes successfully.

It becomes **promotion-surviving** when `promote_candidates` writes promoted outputs and evidence bundles.

It becomes **runtime-readable** when the promotion service exports `PromotedThesis` objects to `data/live/theses/<run_id>/promoted_theses.json` and updates the thesis index.

It becomes **runtime-matchable** when the live runtime can load that thesis store and the thesis matches a live event/context.

It becomes **eligible for real trading** only when the thesis has `deployment_state="live_enabled"` and the runtime is in `runtime_mode="trading"` with strategy runtime and submission checks satisfied.

And in the current code snapshot:

- the canonical proposal path reaches runtime-readable thesis export,
- and the explicit export surface can register a named runtime batch and mark selected theses `live_enabled`,
- but that promotion-to-runtime step is still operator-driven rather than automatic.

So the current proposal path is best described as:

**proposal -> paper thesis export -> optional blueprint activation -> explicit deployment-state decision -> runtime inspection/paper/live path**,

not an automatic:

**proposal -> production live trading**.

---

## 18. Artifact trace: where to inspect each handoff

### Proposal and planning

- `spec/proposals/<proposal>.yaml`
- `data/artifacts/experiments/<program_id>/memory/proposals/<run_id>/proposal.yaml`
- `data/artifacts/experiments/<program_id>/memory/proposals/<run_id>/experiment.yaml`
- `data/artifacts/experiments/<program_id>/memory/proposals/<run_id>/run_all_overrides.json`
- `data/artifacts/experiments/<program_id>/memory/proposals.parquet`

### Run mechanics

- `data/runs/<run_id>/run_manifest.json`
- `data/runs/<run_id>/kpi_scorecard.json`

### Discovery and phase 2

- `data/reports/phase2/<run_id>/phase2_candidates.parquet`
- `data/reports/phase2/<run_id>/phase2_diagnostics.json`

### Promotion

- `data/reports/promotions/<run_id>/promotion_statistical_audit.parquet`
- `data/reports/promotions/<run_id>/promoted_candidates.parquet`
- `data/reports/promotions/<run_id>/promotion_decisions.parquet`
- `data/reports/promotions/<run_id>/promotion_summary.csv`
- `data/reports/promotions/<run_id>/evidence_bundles.jsonl`
- `data/reports/promotions/<run_id>/promoted_thesis_contracts.json`
- `data/reports/promotions/<run_id>/promoted_thesis_contracts.md`

### Runtime-facing thesis export

- `data/live/theses/<run_id>/promoted_theses.json`
- `data/live/theses/index.json`

### Optional blueprint path

- `data/reports/strategy_blueprints/<run_id>/blueprints.jsonl`

---

## 19. Practical interpretation

If you are reading a proposal-run output and asking, “is this live tradable yet?”, the correct checklist is:

1. Did the run succeed mechanically?
2. Did phase 2 produce non-empty candidates?
3. Did promotion produce promoted candidates and valid evidence bundles?
4. Did the promotion service export a thesis batch to `data/live/theses/`?
5. Is the thesis `pending_blueprint` or `active`?
6. What is its `deployment_state`?
7. Is it `live_enabled`?
8. Is the runtime in trading mode with strategy runtime enabled and auto submission allowed?

In the current repo snapshot, most canonical proposal runs can answer “yes” only through step 4, sometimes step 5 if a separate blueprint flow ran, and typically “no” at step 7.

That is the exact point where proposal execution ends and true live-trading eligibility still remains unresolved.
