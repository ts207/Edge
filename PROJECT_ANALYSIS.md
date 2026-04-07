# Edge: Deep Project Analysis

**Date**: 2026-04-07
**Scope**: Full repository audit — architecture, risk surface, maturity, potential, and proposed roadmap.

---

## 1. What Edge Is

Edge is a **crypto alpha discovery, validation, promotion, and live-execution platform**. It implements a four-stage pipeline:

```
Discover → Validate → Promote → Deploy
```

The system is designed to transform research hypotheses about crypto market microstructure events into validated, executable trading theses. It targets **perpetual futures** on Binance and Bybit, with a focus on event-driven edges (funding rate dislocations, volatility shocks, liquidity vacuums, etc.).

### Scale

- **~240k lines of Python** across **~1,477 source files** (excluding `.venv`).
- **76+ canonical event types** defined in YAML specs (funding, volatility, liquidity, trend, exhaustion, microstructure, cross-asset, sequence composites).
- **17+ event detector families** (volatility, funding, liquidity, trend, exhaustion, dislocation, interaction, sequence, etc.).
- **Dual exchange support** (Binance Futures, Bybit Derivatives) with unified OMS abstraction.
- **Systemd deployment units** for paper and production live engines.
- **ChatGPT/MCP integration** for operator-facing AI tooling.
- **Autonomous campaign controller** for batch research sequencing.

---

## 2. Architecture Assessment

### 2.1 Strengths

**Artifact-boundary isolation.** Stages communicate exclusively through persisted artifacts (Parquet, JSON). This is a sound architectural choice that ensures auditability, resumability, and clean failure isolation. Each stage can be re-run independently without corrupting another.

**Deep statistical rigor in validation.** The validation layer is unusually thorough for a crypto trading system:
- Benjamini-Hochberg FDR adjustment with explicit family grouping.
- Simes combination tests.
- Placebo/negative control generation for falsification.
- Regime stability testing (HIGH_VOL, LOW_VOL, BULL_TREND, BEAR_TREND, CHOP).
- Fold-based walk-forward validation with purging and embargo.
- Clustered standard errors for dependent observations.
- Split-sample discipline (train / validation / test).

**Rich event ontology.** The 76-event taxonomy with canonical families, ontology mapping, precedence rules, and interaction detection is a genuine intellectual asset. Events like `SEQ_FND_EXTREME_THEN_BREAKOUT` and `CROSS_VENUE_DESYNC` encode domain knowledge that is hard to replicate.

**Live engine maturity.** The live runner has production-grade concerns addressed:
- Kill switch with 7 distinct trigger reasons (feature drift, execution drift, drawdown, stale data, microstructure breakdown, account sync loss, manual).
- Per-thesis risk caps, daily loss ledgers, decay monitoring.
- Thesis reconciliation at startup.
- Execution attribution and degradation detection.
- Incubation ledger for thesis lifecycle management.

**Benchmark governance.** The A→F mode progression (baseline flat → v2 scoring → folds → hierarchical → ledger → diversification) is a well-designed ablation matrix that isolates exactly one variable per step. This is rare and valuable.

### 2.2 Structural Weaknesses

**Stage facades are empty.** `project/discover/`, `project/validate/`, `project/promote/` each contain only `__init__.py`. All real logic lives in `project/research/`. The four-stage model is conceptually clean but the facade layer is not wired. This means the CLI dispatches into research internals directly, and the canonical `edge discover run` / `edge validate run` verbs are routing into a monolithic research namespace.

**Research module is overloaded.** `project/research/` contains ~150+ Python files spanning discovery, validation, promotion, benchmarking, campaign control, knowledge management, clustering, cost modeling, and more. This is the architectural center of gravity, but it has grown beyond the point where the directory structure communicates intent. There is no clear sub-boundary between "research logic" and "production pipeline logic."

**Test coverage is thin.** Only **13 test files** for a 240k-line codebase. The test suite is concentrated in `tests/research/` and `tests/events/`. There are no tests for:
- The live engine (`project/live/`).
- The backtest engine (`project/engine/`).
- The portfolio/sizing layer.
- The strategy compiler/runtime.
- The event detectors (only integration-style tests via benchmarks).
- The CLI routing.

**Commit hygiene is poor.** Recent commit history contains many single-character messages (`r`, `z`, `x`, `d`, `g`, `t`, `b`, `f`). This makes bisection, blame analysis, and onboarding impossible. The git history is not a useful source of truth for understanding what changed or why.

**No CI/CD pipeline visible.** No `.github/workflows/`, no Jenkinsfile, no GitLab CI, no Makefile `ci` target. The `Makefile` has `lint` and `test-fast` targets, but there is no automated gate preventing broken code from landing on `main`.

---

## 3. Current State of Play

### 3.1 What Works

| Component | Status | Evidence |
|:---|:---|:---|
| Event detection & registration | **Stable** | 76 canonical events, detector families, ontology mapping |
| Phase 2 search engine (flat mode) | **Stable** | Benchmark harness ran all 30 jobs |
| Phase 2 search engine (hierarchical) | **Provisional signal** | Rescues candidates where flat produces 0, but quality unproven |
| Candidate scoring v1 | **Stable** | Production baseline |
| Candidate scoring v2 | **Provisional** | Not stable-internal until benchmark criteria met |
| Validation (split/purge/falsification) | **Stable** | Core statistical machinery works |
| Walk-forward folds | **Experimental** | No evidence yet that folds improve integrity |
| Concept ledger (v3 scoring) | **Experimental** | No evidence that ledger changes outcomes |
| Diversified shortlist selection | **Experimental** | No evidence that diversification changes outcomes |
| Promotion gates & governance | **Stable** | Multiplicity controls, search-burden accounting wired |
| Live engine (paper mode) | **Deployed** | Systemd unit exists, thesis reconciliation works |
| Live engine (production mode) | **Deployed** | Systemd unit exists, but no evidence of live PnL |
| Campaign controller | **Functional** | Autonomous sequencing with memory and repair logic |
| Benchmark harness | **Functional but incomplete** | Runs but metric extraction insufficient for decisions |

### 3.2 What Doesn't Work Yet

1. **Benchmark metric extraction** is too shallow — produces candidate counts but not quality/integrity/diversity scores needed to make promotion decisions (this is the current blocker per CLAUDE.md).
2. **m1_noisy_event** benchmark slice has 0 relevant events, functioning as dead weight rather than a meaningful comparison.
3. **No component has been promoted beyond "hold"** in the A→F benchmark progression. All are waiting on quality metrics.
4. **Scoring v2 stabilization report** was downgraded from STABLE-INTERNAL to PROVISIONAL after discovering fabricated event names in the benchmark spec (B1 integrity issue).

---

## 4. Risk Analysis

### 4.1 Critical Risks

**R1 — Overfitting to microstructure noise (HIGH).** The system generates a very large number of candidate hypotheses (all combinations of 76 events × multiple horizons × directions × lags × context conditions). Even with BH-FDR correction, the multiple testing burden is enormous. The concept ledger (v3) is designed to address this, but it is still experimental and has not demonstrated value. Without effective multiplicity control, promoted theses may be artifacts of noise.

**R2 — No out-of-sample live PnL attribution (HIGH).** The system has sophisticated backtesting and validation, but there is no visible feedback loop from live execution back to research. The live engine produces trade logs and decision outcomes, but there is no automated mechanism to compare live PnL against backtest expectations and flag decay or regime shift. The `decay_monitor` exists but its calibration from evidence data is ad-hoc.

**R3 — Single-operator dependency (HIGH).** The codebase, commit history, and operational knowledge appear concentrated in a single person. The test suite is too thin to serve as a safety net for a second contributor. The single-character commits suggest solo rapid iteration without review. This is a bus-factor-1 system.

**R4 — Regime non-stationarity (MEDIUM-HIGH).** Crypto market microstructure changes rapidly. The event detectors and their thresholds are calibrated to historical data. There is a regime classifier and regime stability testing, but no automated mechanism to detect when the entire event taxonomy has shifted (e.g., when funding rate distributions structurally change due to exchange policy updates, or when market maker composition shifts).

**R5 — Exchange API surface risk (MEDIUM).** The live engine depends on Binance and Bybit REST + WebSocket APIs. Exchange API changes, rate limit adjustments, or connectivity issues can cause silent failures. The kill switch handles some of this, but the recovery logic (especially `microstructure_recovery_streak`) is fragile.

**R6 — No data validation on ingest (MEDIUM).** The data lake appears to be populated by scripts and ingestion pipelines, but there is no visible schema validation, freshness checks, or data quality gates on the raw market data before it enters the feature pipeline. The `data_quality.py` module exists in `core/` but its integration into the ingestion path is unclear.

### 4.2 Moderate Risks

**R7 — Benchmark fixture staleness.** Benchmark slices use fixed date ranges (e.g., 2022-05-01 to 2022-07-01). These are valid for controlled experiments but do not reflect current market conditions. Benchmark results may not transfer to current regimes.

**R8 — Strategy template complexity.** The strategy DSL and template compiler add an abstraction layer between research signals and execution logic. Bugs in the compiler or template semantics could produce strategies that don't match the researcher's intent.

**R9 — Cost model drift.** Execution costs (fees, slippage, market impact) are configured via YAML. Real-world execution costs change with exchange fee tiers, market conditions, and position sizes. The gap between configured and actual costs erodes edge over time.

**R10 — Promotion gate inflation.** The promotion layer has many gates (delay robustness, timeframe consensus, microstructure, regime stability, falsification, fold stability). If gates are too strict, nothing promotes. If they are too loose, noise promotes. The current gate thresholds have not been calibrated against live PnL outcomes.

---

## 5. Unrealized Potential

### 5.1 Immediate (achievable within current architecture)

**P1 — Benchmark decision capability.** The CLAUDE.md already identifies this: upgrade `_extract_benchmark_metrics()` to compute quality, integrity, and diversity scores from candidate parquets. This is the single highest-leverage change because it unblocks the entire A→F promotion decision chain.

**P2 — Hierarchical search as a genuine edge.** The hierarchical search (Stage A→D: trigger viability → template refinement → execution refinement → context refinement) is architecturally sound and already shows signal (rescuing candidates where flat search produces zero). If quality metrics confirm these rescued candidates are economically meaningful, hierarchical search becomes a real competitive advantage — it finds edges that brute-force search misses.

**P3 — Campaign controller as an autonomous research agent.** The campaign controller already sequences proposals, tracks memory, repairs failed stages, and updates search intelligence. With better benchmark feedback loops, it could autonomously decide which event families to explore, which symbols to expand to, and which hypotheses to retire.

**P4 — Cross-campaign multiplicity governance.** Workstream A (cross-campaign multiplicity) is already wired into canonical promotion. Combined with the concept ledger, this could provide portfolio-level multiple testing control that most quantitative systems lack entirely.

### 5.2 Medium-term (requires new components)

**P5 — Live PnL → Research feedback loop.** Connecting live execution outcomes back to the validation layer would close the loop. A thesis that decays in live should update the concept ledger, trigger re-validation, and potentially de-promote. This is the difference between a static backtesting platform and an adaptive one.

**P6 — Regime-adaptive event detection.** Currently, event detector thresholds are static (defined in YAML specs with fixed percentile cutoffs). An adaptive layer that re-calibrates thresholds based on rolling market statistics would keep the event taxonomy relevant as market microstructure evolves.

**P7 — Multi-exchange arbitrage and cross-venue signal.** The system already has `CROSS_VENUE_DESYNC` and `SPOT_PERP_BASIS_SHOCK` events and dual-exchange support. Extending this to systematic cross-venue basis trading or funding rate arbitrage is a natural expansion.

**P8 — Portfolio-level optimization.** The sizing and risk budget modules exist but operate per-thesis. A portfolio optimization layer that considers correlation structure across active theses, capital allocation under constraints, and dynamic rebalancing would improve capital efficiency.

### 5.3 Long-term (vision)

**P9 — Self-improving alpha factory.** The combination of autonomous campaign control, benchmark-driven promotion, live PnL feedback, and concept ledger learning creates the architecture for a system that continuously discovers, validates, deploys, monitors, and retires trading edges with minimal human intervention. The current system has ~60% of the components needed for this vision; the missing pieces are the feedback loops and the decision autonomy.

---

## 6. Proposed End Vision

Edge should become an **autonomous alpha lifecycle manager** for crypto derivatives. The end state:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    AUTONOMOUS ALPHA LIFECYCLE                       │
│                                                                     │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐      │
│  │ DISCOVER │───▶│ VALIDATE │───▶│ PROMOTE  │───▶│  DEPLOY  │      │
│  │          │    │          │    │          │    │          │      │
│  │ Campaign │    │ Falsify  │    │ Gates +  │    │ Paper →  │      │
│  │ Control  │    │ + Folds  │    │ Govern   │    │ Live     │      │
│  └────▲─────┘    └──────────┘    └──────────┘    └────┬─────┘      │
│       │                                               │            │
│       │         ┌──────────────────────────┐          │            │
│       └─────────│    FEEDBACK & LEARN      │◀─────────┘            │
│                 │                          │                       │
│                 │ • Live PnL attribution   │                       │
│                 │ • Regime shift detection  │                       │
│                 │ • Concept ledger update   │                       │
│                 │ • Thesis decay/retire     │                       │
│                 │ • Benchmark recalibration │                       │
│                 └──────────────────────────┘                       │
│                                                                     │
│  Cross-cutting: Risk caps ─ Kill switches ─ Audit trail            │
└─────────────────────────────────────────────────────────────────────┘
```

The system would operate in three modes:
1. **Supervised** (current): Human reviews benchmark results, decides promotions, approves deployments.
2. **Semi-autonomous** (near-term): System proposes promotions and deployments with evidence bundles; human approves or rejects.
3. **Autonomous** (long-term): System discovers, validates, promotes, deploys, monitors, and retires theses within pre-configured risk boundaries, escalating to human only on anomalies.

---

## 7. Recommended Next Steps (Priority Order)

### Step 1: Make the benchmark decision-capable (IMMEDIATE)

This is the current blocker. Upgrade `_extract_benchmark_metrics()` in `discovery_benchmark.py` to compute:
- **Quality**: `median_discovery_quality_score`, `median_t_stat`, `median_estimate_bps`, `median_cost_survival_ratio`
- **Integrity**: `median_falsification_component`, `placebo_fail_rate_top10`, `median_fold_stability_component`, `sign_consistency_top10`
- **Diversity**: `unique_family_id_top10`, `unique_template_id_top10`, `overlap_penalty_rate_top10`
- **Search-topology**: `candidate_emergence_rate`, `top_quality_when_nonzero`, `runtime_seconds`

Then re-run the benchmark and answer: **Are the D-mode rescued candidates economically meaningful?**

### Step 2: Fix m1_noisy_event benchmark slice

Either replace the fixture with data that actually contains `FUNDING_PERSISTENCE_TRIGGER` / `TREND_DECELERATION` events, or explicitly designate it as a negative-control slice and exclude it from promotion logic.

### Step 3: Add test coverage for critical paths

Priority test targets:
1. Live engine decision flow (`decide_trade_intent` → scoring → order planning → risk enforcement).
2. Kill switch trigger and recovery logic.
3. Backtest engine PnL computation (slippage model, fills, attribution).
4. Event detector output schema compliance.

Target: 50+ test files covering the critical execution path from thesis → trade → PnL.

### Step 4: Wire stage facades

Connect `project/discover/`, `project/validate/`, `project/promote/` to their research internals with thin facade functions that enforce artifact contracts. This makes the four-stage model real rather than aspirational.

### Step 5: Close the live PnL feedback loop

Build a `project/live/reflection/` module that:
- Compares realized PnL per thesis against its evidence bundle expectations.
- Detects thesis decay (rolling Sharpe degradation against backtest baseline).
- Publishes decay events to the concept ledger.
- Triggers automatic re-validation when a thesis drifts beyond thresholds.

### Step 6: Establish CI/CD

Add a GitHub Actions workflow with:
- `ruff lint` + `ruff format --check` on all changed files.
- `pytest tests/ -x --timeout=120` on every push.
- Benchmark smoke test on PRs touching `project/research/`.
- Block merge on failure.

### Step 7: Commit hygiene

Adopt conventional commits (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`) enforced by a pre-commit hook. Ban single-character commit messages. This is essential for any future collaboration or audit.

---

## 8. Summary Assessment

| Dimension | Rating | Notes |
|:---|:---|:---|
| **Conceptual design** | Strong | Four-stage model, artifact boundaries, benchmark governance are well-conceived |
| **Domain knowledge** | Exceptional | 76-event ontology, microstructure detectors, regime classification encode deep crypto expertise |
| **Statistical rigor** | Strong | BH-FDR, Simes, falsification, fold validation, clustered SEs — better than most quant shops |
| **Code quality** | Mixed | Clean abstractions in some areas, monolithic sprawl in others |
| **Test coverage** | Weak | 13 test files for 240k lines is dangerously low |
| **Operational maturity** | Moderate | Systemd units, kill switches, risk caps exist; but no CI/CD, no monitoring, no alerting pipeline |
| **Live performance** | Unknown | No visible evidence of realized PnL, Sharpe ratios, or live trading outcomes |
| **Scalability** | Moderate | Single-machine design; campaign controller is sequential; no distributed compute for discovery |
| **Maintainability** | Low | Bus-factor-1, poor commit history, thin tests, no CI |

**Bottom line:** Edge is a genuinely sophisticated alpha discovery and execution platform with real intellectual depth. The statistical validation stack and event ontology are its strongest assets. The primary risks are the thin test coverage, single-operator dependency, and the missing feedback loop from live execution to research. The immediate priority is making the benchmark decision-capable so that the A→F component progression can advance beyond "hold" status.
