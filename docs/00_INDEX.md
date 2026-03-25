# Edge — Documentation Index

This document set fully deconstructs the EDGEE research platform from its source repository. It is organized for three reader types: researchers, engineers, and operators.

---

## Document Set

| # | Document | Contents | Primary Audience |
|---|---|---|---|
| 1 | **Project Overview** | What EDGEE is, philosophy, operating principles, canonical event families, project stats | Everyone |
| 2 | **Architecture Reference** | Pipeline stage families, artifact flow, package topology, live engine, event detector architecture, strategy DSL, CI tiers | Engineers, Researchers |
| 3 | **Component Reference** | Every module in every package — pipelines, events, research, strategy, core, contracts, live, scripts | Engineers |
| 4 | **Spec & Ontology Reference** | Events, features, states, grammar, gates, global defaults, cost model, runtime lanes, hypotheses | Researchers |
| 5 | **Dependencies & Technical Stack** | Python version, all dependencies with roles, tooling, data layer, CI/CD, deployment | Engineers, Operators |
| 6 | **Operator & Research Workflow** | Full research loop, proposal writing, planning, execution, evaluation layers, make targets | Researchers, Operators |
| 7 | **Data Flow & Contracts** | Artifact token system, full stage-by-stage flow, manifest system, PIT correctness, cost propagation, FDR | Engineers, Researchers |
| 8 | **Entry Points & CLI** | All CLI commands with full flag reference and examples | Researchers, Operators |
| 9 | **Research Concepts & Hypotheses** | Bootstrap concepts, pre-registered hypotheses, stress scenarios, search space, benchmark configs | Researchers |
| 10 | **Testing & Quality Gates** | Test suite structure, CI tiers, E1/V1/P3 gates, Pandera schemas, drift detection, determinism | Engineers, Researchers |

---

## Quick Navigation by Task

### "I want to run a discovery experiment"

→ Start with **Doc 6** (Operator Workflow), specifically the 7-step research loop.

### "I want to understand what events exist and how they're defined"

→ **Doc 4** (Spec & Ontology), Section 1 (Events).

### "I want to add a new event detector"

→ **Doc 3** (Component Reference), Events Layer section. Then **Doc 4** to understand the YAML spec format.

### "I want to understand the full data flow"

→ **Doc 7** (Data Flow & Contracts). The ASCII diagram shows every stage.

### "I want to understand what a 'good' research result looks like"

→ **Doc 6** (Workflow), Step 6 (Evaluate Output) — the three evaluation layers.

### "I want to deploy the live engine"

→ **Doc 5** (Stack), Deployment section. Plus `deploy/systemd/` and `deploy/env/` in the repo.

### "I want to know what gates a hypothesis must pass"

→ **Doc 4**, Sections 5 (Gates). Plus **Doc 10** (Testing), Quality Gate Hierarchy section.

### "CI is failing — what does it check?"

→ **Doc 10** (Testing), CI Gate Tiers section.

### "I want to understand the research philosophy and discipline"

→ **Doc 1** (Overview), especially "Operating Principles" and "What a Good Run Looks Like".

---

## Key Platform Invariants (Summary)

These are the hard rules that all research on EDGEE must respect:

1. **Exit codes are not sufficient.** Read manifests.
2. **Plan before material runs.** Always use `--plan_only 1` first.
3. **Synthetic ≠ live.** Synthetic profitability is not evidence of live edge.
4. **Promotion is a gate, not a reward.** Attractive numbers ≠ promotion readiness.
5. **Narrow first.** One family, one template, one context per run.
6. **Artifacts are truth.** If manifests disagree, the disagreement is a finding.
7. **PIT must hold.** No feature may observe data beyond t0.
8. **Cost must be after-cost.** No gross-return claims count.
9. **FDR must be controlled.** q-value ≤ 0.05.
10. **Determinism must hold.** Same inputs + code + config = same outputs.

---

## Platform Architecture Summary (One Page)

```
EDGEE Platform
══════════════

DATA SOURCES           Binance UM Perpetuals + Spot (via REST + WebSocket)

PIPELINE (8 stages)
  ingest              → raw.perp.{ohlcv,funding,oi,liquidations} + raw.spot.ohlcv
  clean               → clean.perp.* + clean.spot.* + basis state + TOB aggs
  build_features      → features.perp.v2 + features.spot.v2 (34 feature families)
  build_market_context → regime labels, microstructure context
  phase1_analysis     → 74 event detectors → episode files (per family .parquet)
  phase2_discovery    → hypothesis scoring, FDR control → scored candidates
  promotion           → E1/V1/P3 gate → edge registry + campaign memory
  strategy_packaging  → Blueprints → Executable strategy specs → live engine

RESEARCH PRIMITIVES
  74 event types      across 9 canonical families
  34 feature families  from microstructure to ML signals
  19 market states    tied to source events and families
  Legal templates     per family (7–8 templates each)
  Named sequences     for multi-event composite triggers

QUALITY GATES
  Gate E1             Event prevalence + clustering (Phase 1)
  Gate V1             q ≤ 0.05, after-cost ≥ 0.1 bps, sign stable (Phase 2)
  Gate P3             OOS ESS ≥ 50, ≥ 2 regimes, cost stress 2× (Promotion)

LIVE ENGINE
  Binance WebSocket   kline_1m, kline_5m, bookTicker per symbol
  Lane alpha_5s       Alpha signal computation (no exec state visibility)
  Lane exec_1s        Order management (exec state visible)
  Kill switch         Configurable hard shutdown

TECH STACK
  Python 3.11+        pandas, numpy, numba, pyarrow, pydantic, scikit-learn
  Storage             Parquet (all artifacts)
  CI                  3-tier GitHub Actions + Pyright + Ruff

SCALE
  1,153 Python files  407 test files
  38% test coverage   0 circular dependencies
  1,722 total files   2,417 module couplings
```
