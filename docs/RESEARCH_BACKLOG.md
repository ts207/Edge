# Researcher Backlog

This backlog is intentionally narrow. Every item matches existing canonical regimes, events, templates, and detector surfaces already present in this repository.

## Priority 1

### Basis normalization after forced payer flow

- Canonical regime: `BASIS_FUNDING_DISLOCATION`
- Primary event: `FUNDING_NORMALIZATION_TRIGGER`
- Optional confirmatory companion event: `SPOT_PERP_BASIS_SHOCK`
- Template family: `basis_repair`
- Mechanism: extreme perp premium and funding are a crowding artifact that mean-revert after the payer imbalance exhausts.
- Tradable expression: spot rebound or reduced-short-pressure expression, using futures funding/basis state as the informational regime filter.
- Why first:
  - regime exists in the compiled registry,
  - direct detectors exist in `project/configs/registries/detectors.yaml`,
  - templates exist in the compiled template registry,
  - the project is structurally suited to futures-state-informed spot expression.
- Stop condition:
  - if after-cost expectancy fails under realistic fee/slippage assumptions or promotion rejects on weak economics, kill rather than broaden.

## Priority 2

### Futures-led washout to spot rebound

- Canonical regime: `POSITIONING_UNWIND_DELEVERAGING`
- Primary event: `POST_DELEVERAGING_REBOUND`
- Optional precursor: `OI_FLUSH`
- Template family: `exhaustion_reversal`
- Mechanism: forced futures positioning unwind temporarily overshoots spot-discovery fundamentals, then rebounds after liquidation pressure clears.
- Tradable expression: spot-only rebound entry conditioned on futures unwind state.
- Why second:
  - the regime is explicit in the compiled registry,
  - it uses the repository’s intended "futures-native state discovery, spot expression where appropriate" shape,
  - it avoids pretending execution simulation equals truth.
- Stop condition:
  - if results require broader context spray or multiple unrelated templates, stop.

## Priority 3

### Cross-venue desync convergence

- Canonical regime: `BASIS_FUNDING_DISLOCATION`
- Primary event: `CROSS_VENUE_DESYNC`
- Template family: `desync_repair`
- Mechanism: temporary venue-level information or positioning imbalance should converge once routing/friction normalizes.
- Tradable expression: convergence expression or simpler spot proxy on the lagging venue signal.
- Why third:
  - this stays inside an already-modeled information-desync family,
  - detectors and template compatibility exist,
  - comparison across small bounded variants is straightforward.
- Stop condition:
  - if the edge only appears on one artifact surface and disappears in promotion review, hold or kill.

## Priority 4

### Liquidity stress abstention and rebound

- Canonical regime: `LIQUIDITY_STRESS`
- Primary event: `LIQUIDITY_VACUUM`
- Template family: `tail_risk_avoid` for abstention, then `overshoot_repair` for rebound
- Mechanism: local order-book absence increases execution damage during stress, but post-stress mean reversion can become tradable once liquidity refills.
- Tradable expression: first test abstention filter; only if that is coherent, test post-stress rebound as a second bounded run.
- Why fourth:
  - the repo has direct liquidity detectors and routing metadata,
  - execution-awareness matters here, which matches the system’s stated strengths.
- Stop condition:
  - never combine abstention and rebound into one run; if abstention fails, do not force a rebound claim.

## Priority 5

### Follower-flow exhaustion lifecycle

- Canonical regime: `TREND_FAILURE_EXHAUSTION`
- Primary event: `FORCED_FLOW_EXHAUSTION`
- Optional companion event: `LIQUIDATION_EXHAUSTION_REVERSAL`
- Template family: `exhaustion_reversal`
- Mechanism: late follower flow extends a move beyond sustainable liquidity, then reverses once aggressive participation exhausts.
- Tradable expression: reversal entry after exhaustion confirmation, not generic trend prediction.
- Why fifth:
  - the regime and detectors are already first-class,
  - this is a strong fit for the repository’s forced-flow framing,
  - but it must stay tightly bounded to avoid generic reversal mining.
- Stop condition:
  - if the hypothesis cannot specify the forced actor and unwind path clearly, do not run it.
