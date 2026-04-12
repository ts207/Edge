# Portfolio Orchestration Layer Design

## Overview
The Portfolio Orchestration Layer is the single dominant layer responsible for portfolio-level capital allocation and cross-thesis constraint enforcement. It takes all active thesis-level intents and determines which are allowed to express, at what size, under a single coherent portfolio policy.

This layer sits above individual thesis signal generation (the "Research" and "Engine" layer) and owns global decisions that cannot be made in isolation. It absorbs responsibilities currently fragmented across the system: cross-strategy limit enforcement, overlap and correlation control, symbol/family exposure budgeting, real-time resizing and throttling, drawdown-aware rebalancing, and decay-driven capital reallocation.

## Core Responsibilities
The orchestration layer acts as the **single owner of portfolio expression**. Its primary function is to resolve competing demands for scarce portfolio resources (capital, risk budgets, venue liquidity) by converting multiple valid thesis-level intents into a coherent portfolio decision.

### Inputs
1. Active thesis inventory (all approved strategies currently deployed).
2. Thesis-level trade intents (raw signals and desired sizes before portfolio constraints).
3. Current live portfolio positions.
4. Global risk budgets (max capital, max drawdown).
5. Overlap/correlation graph (from `thesis_overlap.py`).
6. Live PnL and global drawdown state.
7. Thesis decay state (real-time degradation of historical edge).
8. Venue liquidity and capacity constraints.

### Decision Pipeline
For each incoming or active thesis intent, the layer determines whether to:
* **Approve:** Allow expression at requested size.
* **Resize:** Scale down the intent due to constraints or partial capital availability.
* **Queue:** Delay execution until capacity frees up.
* **Suppress:** Block expression entirely (e.g., due to drawdown or extreme overlap).
* **Unwind/De-risk:** Actively reduce existing exposure based on portfolio-level necessity, not just thesis-level exit signals.

### Outputs
* **Target Portfolio State:** An explicit mapping of approved target exposures (capital allocations by thesis, family, and symbol).
* **Risk Actions:** Specific rebalancing instructions, suppressions, or de-risking commands.
* **Portfolio Snapshot:** A coherent view of the approved state passed to the live execution engine.

## Architecture and Execution Model
The Portfolio Orchestration Layer operates as an asynchronous **Target-State Generator**.
Rather than functioning as a synchronous, blocking gate that evaluates every trade intent inline, the layer continuously reconciles the incoming inventory of intents against the current live portfolio state and global limits.

It emits a desired target portfolio composition. The execution layer is then responsible for diffing this target state against the actual live state and generating the necessary orders to chase the target. This pattern decouples strategy evaluation from execution latency and allows the portfolio layer to enforce sweeping rebalancing (e.g., a global drawdown stop) instantly, regardless of when the next thesis signal arrives.

## Arbitration Policy: Dynamic Constraint-Weighted Greedy
When aggregate thesis intents exceed portfolio capacity or limits, the layer arbitrates using a dynamic marginal-utility ranking.

**First-come-first-served and static priority lists are explicitly rejected.** Capital is allocated based on the expected marginal portfolio value of each thesis at the current moment, after portfolio penalties are applied.

### Stage 1: Hard Gates
Before ranking, intents are filtered against non-negotiable rules:
* Deployment permission and active state.
* Setup-match floor and live approval requirements.
* Per-thesis hard caps.
* Global portfolio drawdown stops.
* Hard limits on symbol, family, or venue exposure.
Ineligible intents are suppressed or unwound.

### Stage 2: Dynamic Utility Ranking
Eligible theses are scored using a dynamic priority function:

`priority_score = setup_match * thesis_strength * freshness_multiplier * execution_quality * diversification_multiplier * capital_efficiency`

*   `setup_match`: Current market alignment with the thesis.
*   `thesis_strength`: Promotion-time evidence (q-value, sample support, etc.).
*   `freshness_multiplier`: Decays < 1.0 as the thesis ages or shows alpha decay.
*   `execution_quality`: Current liquidity, spread, and fill risk metrics.
*   `diversification_multiplier`: Decays dynamically *during the allocation loop* as related exposures (same family, correlated symbols) are funded.
*   `capital_efficiency`: Expected net value per unit of risk or capacity.

### Stage 3: Greedy Allocation Loop
Capital is allocated in descending order of `priority_score`. As capital is assigned to a thesis, the `diversification_multiplier` for remaining, correlated theses is dynamically penalized in the loop. This ensures that the highest-utility ideas win capital while preventing any single cluster (e.g., a specific event family) from dominating the portfolio, achieving structural diversification without rigid silos.

## Integration Points
*   **`project/portfolio/allocation_spec.py`:** Will evolve to support dynamic utility scoring.
*   **`project/engine/risk_allocator.py`:** Refactored to consume the Target Portfolio State emitted by this new layer, shifting its role from ad-hoc orchestration to target enforcement.
*   **`project/portfolio/thesis_overlap.py`:** Provides the correlation graph used to calculate the dynamic `diversification_multiplier`.
