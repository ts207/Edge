# Edge — Project Overview

## What It Is

EDGEE is a **research platform for event-driven alpha discovery in crypto markets**. It is not a generic backtesting sandbox. Its stated purpose is to convert market observations into explicit, testable hypotheses, run them through a structured multi-stage pipeline, and gate any result on mechanical, statistical, and deployment-readiness checks before a finding can be promoted.

The design philosophy is: *reproducible, cost-aware, narrowly attributed research — not output volume.*

---

## Core Research Philosophy

The platform is built around **hypotheses**, not detectors and not strategies. A hypothesis specifies:

| Field | Description |
| --- | --- |
| `event` | The market event type being tested (e.g., `VOL_SHOCK`, `BASIS_DISLOC`) |
| `canonical_family` | The high-level event family it belongs to |
| `template` | The strategy template to apply (e.g., `mean_reversion`, `continuation`) |
| `context` | Market regime context under which the hypothesis holds |
| `side` | Long / short |
| `horizon` | Time horizon in bars |
| `entry_lag` | Bars after event to enter |
| `symbol_scope` | Which instruments the hypothesis applies to |

This is what gets evaluated, stored in memory, and gated in promotion — not aggregate P&L curves.

---

## The 9 Canonical Event Families

All events belong to one of 9 canonical families. Templates are only legal for their matching family.

| Family | Description |
| --- | --- |
| `LIQUIDITY_DISLOCATION` | Sudden breakdown in market depth or spread abnormality (34 events) |
| `POSITIONING_EXTREMES` | Extreme open interest, funding, or leverage positioning (29 events) |
| `FORCED_FLOW_AND_EXHAUSTION` | Liquidation cascades and exhaustion reversals (22 events) |
| `STATISTICAL_DISLOCATION` | Z-score stretches, basis dislocations, band breaks (21 events) |
| `VOLATILITY_TRANSITION` | Regime shifts in realized/implied volatility (19 events) |
| `TREND_STRUCTURE` | Breakouts, pullbacks, momentum divergence, trend acceleration (18 events) |
| `REGIME_TRANSITION` | Macro or microstructure regime changes (15 events) |
| `TEMPORAL_STRUCTURE` | Session-based, scheduled, or time-of-day effects (12 events) |
| `INFORMATION_DESYNC` | Cross-venue lead-lag breaks, index divergence, desync (12 events) |

---

## Operating Principles   ?clarity and reasoning for these principles and improve depth

The platform enforces a strict research discipline:

1. **Artifacts are the source of truth.** Exit codes alone are not sufficient. Run manifests must reconcile.
2. **`plan_only` before material runs.** Scope must be verified before execution.
3. **Synthetic runs are calibration, not proof.** Synthetic profitability is not live-market evidence.
4. **Promotion is a gate.** Attractive discovery output is not promotion readiness.
5. **Narrow before broad.** One family, one template, one context per run by default. ?review rule, as it restricts research flexibility and potential alphas

---

## What a "Good Run" Looks Like

A good run is **not** the run with the best headline metric. A good run leaves behind:

- A bounded question
- A clean artifact trail
- A defensible interpretation
- A recorded next action (`exploit` / `explore` / `repair` / `hold` / `stop`)

---

---

## High-Level System Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Edge Research Platform                   │
│                                                             │
│  Data Sources (Binance UM Perp + Spot)                      │
│       │                                                      │
│       ▼                                                      │
│  [ingest] → raw OHLCV, funding, OI, liquidations, book      │
│       │                                                      │
│       ▼                                                      │
│  [clean] → cleaned bars, basis state, TOB aggregates        │
│       │                                                      │
│       ▼                                                      │
│  [build_features] → 34 feature families                     │
│       │                                                      │
│       ▼                                                      │
│  [build_market_context] → regime labels, microstructure     │
│       │                                                      │
│       ▼                                                      │
│  [phase1_analysis] → 74 event detectors → event episodes    │
│       │                                                      │
│       ▼                                                      │
│  [phase2_discovery] → hypothesis scoring, FDR control       │
│       │                                                      │
│       ▼                                                      │
│  [promotion] → gated promotion, edge registry, memory       │
│       │                                                      │
│       ▼                                                      │
│  [strategy_packaging] → blueprints → live engine            │
└─────────────────────────────────────────────────────────────┘
```

---

## Project Stats

| Metric | Value |
| --- | --- |
| Python source files | 1,153 |
| Total files in repo | 1,722 |
| Test files | 407 |
| Event types (spec) | 74 |
| Feature definitions | 34 |
| Market states | 19 |
| Module coupling count | 2,417 |
| Cross-boundary imports | 1,665 |
| Circular dependencies | 0 |
| Test coverage ratio | ~38% |
| Requires Python | 3.11+ |
