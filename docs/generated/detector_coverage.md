# Detector Coverage Audit

- Status: `passed`
- Active event specs: `66`
- Registered detectors: `66`
- Raw registered detector entries: `81`
- Issues: `17`

## Maturity Counts

- `production`: 6
- `proxy`: 11
- `specialized`: 3
- `standard`: 46

## Issues

- [warning] Registered detector has no active event spec: BASIS_SNAPBACK (project/events/detectors/extended_detectors.py)
- [warning] Registered detector has no active event spec: CROSS_VENUE_CATCHUP (project/events/detectors/extended_detectors.py)
- [warning] Registered detector has no active event spec: DEPTH_RECOVERY_EVENT (project/events/detectors/extended_detectors.py)
- [warning] Registered detector has no active event spec: FUNDING_EXTREME_BREAKOUT (project/events/detectors/extended_detectors.py)
- [warning] Registered detector has no active event spec: FUNDING_EXTREME_STAGNATION (project/events/detectors/extended_detectors.py)
- [warning] Registered detector has no active event spec: IMBALANCE_ABSORPTION_REVERSAL (project/events/detectors/extended_detectors.py)
- [warning] Registered detector has no active event spec: OI_VOL_COMPRESSION_BUILDUP (project/events/detectors/extended_detectors.py)
- [warning] Registered detector has no active event spec: OI_VOL_DIVERGENCE (project/events/detectors/extended_detectors.py)
- [warning] Registered detector has no active event spec: SEQ_FND_EXTREME_THEN_BREAKOUT (project/events/detectors/extended_detectors.py)
- [warning] Registered detector has no active event spec: SEQ_LIQ_CASCADE_THEN_EXHAUST (project/events/detectors/extended_detectors.py)
- [warning] Registered detector has no active event spec: SEQ_LIQ_VACUUM_THEN_DEPTH_RECOVERY (project/events/detectors/extended_detectors.py)
- [warning] Registered detector has no active event spec: SEQ_OI_SPIKEPOS_THEN_VOL_SPIKE (project/events/detectors/extended_detectors.py)
- [warning] Registered detector has no active event spec: SEQ_VOL_COMP_THEN_BREAKOUT (project/events/detectors/extended_detectors.py)
- [warning] Registered detector has no active event spec: VOL_COMPRESSION_BREAKOUT (project/events/detectors/extended_detectors.py)
- [warning] Detector implementation has hardcoded numerical thresholds: CROSS_VENUE_DESYNC (project/events/families/basis.py)
- [warning] Detector implementation has hardcoded numerical thresholds: ORDERFLOW_IMBALANCE_SHOCK (project/events/families/canonical_proxy.py)
- [warning] Detector implementation has hardcoded numerical thresholds: PRICE_VOL_IMBALANCE_PROXY (project/events/families/canonical_proxy.py)

## Detector Inventory

- `ABSORPTION_EVENT`: `proxy` via `AbsorptionProxyDetector`
- `ABSORPTION_PROXY`: `proxy` via `AbsorptionProxyDetector`
- `BAND_BREAK`: `standard` via `BandBreakDetector`
- `BASIS_DISLOC`: `production` via `BasisDislocationDetector`
- `BETA_SPIKE_EVENT`: `standard` via `BetaSpikeDetector`
- `BREAKOUT_TRIGGER`: `standard` via `BreakoutTriggerDetector`
- `CHOP_TO_TREND_SHIFT`: `standard` via `ChopToTrendDetector`
- `CLIMAX_VOLUME_BAR`: `standard` via `ClimaxVolumeDetector`
- `COPULA_PAIRS_TRADING`: `standard` via `CopulaPairsTradingDetector`
- `CORRELATION_BREAKDOWN_EVENT`: `standard` via `CorrelationBreakdownDetector`
- `CROSS_VENUE_DESYNC`: `standard` via `CrossVenueDesyncDetector`
- `DELEVERAGING_WAVE`: `standard` via `DeleveragingWaveDetector`
- `DEPTH_COLLAPSE`: `proxy` via `DepthStressProxyDetector`
- `DEPTH_STRESS_PROXY`: `proxy` via `DepthStressProxyDetector`
- `FAILED_CONTINUATION`: `standard` via `FailedContinuationDetector`
- `FALSE_BREAKOUT`: `standard` via `FalseBreakoutDetector`
- `FEE_REGIME_CHANGE_EVENT`: `standard` via `FeeRegimeChangeDetector`
- `FLOW_EXHAUSTION_PROXY`: `proxy` via `FlowExhaustionDetector`
- `FND_DISLOC`: `production` via `FndDislocDetector`
- `FORCED_FLOW_EXHAUSTION`: `proxy` via `FlowExhaustionDetector`
- `FUNDING_EXTREME_ONSET`: `standard` via `FundingExtremeOnsetDetector`
- `FUNDING_FLIP`: `standard` via `FundingFlipDetector`
- `FUNDING_NORMALIZATION_TRIGGER`: `standard` via `FundingNormalizationDetector`
- `FUNDING_PERSISTENCE_TRIGGER`: `standard` via `FundingPersistenceDetector`
- `FUNDING_TIMESTAMP_EVENT`: `standard` via `FundingTimestampDetector`
- `GAP_OVERSHOOT`: `standard` via `GapOvershootDetector`
- `INDEX_COMPONENT_DIVERGENCE`: `standard` via `IndexComponentDivergenceDetector`
- `LEAD_LAG_BREAK`: `standard` via `LeadLagBreakDetector`
- `LIQUIDATION_CASCADE`: `specialized` via `LiquidationCascadeDetector`
- `LIQUIDATION_EXHAUSTION_REVERSAL`: `standard` via `LiquidationExhaustionReversalDetector`
- `LIQUIDITY_GAP_PRINT`: `standard` via `LiquidityGapDetector`
- `LIQUIDITY_SHOCK`: `production` via `LiquidityStressDetector`
- `LIQUIDITY_STRESS_DIRECT`: `production` via `DirectLiquidityStressDetector`
- `LIQUIDITY_STRESS_PROXY`: `proxy` via `ProxyLiquidityStressDetector`
- `LIQUIDITY_VACUUM`: `specialized` via `LiquidityVacuumDetector`
- `MOMENTUM_DIVERGENCE_TRIGGER`: `standard` via `MomentumDivergenceDetector`
- `OI_FLUSH`: `standard` via `OIFlushDetector`
- `OI_SPIKE_NEGATIVE`: `standard` via `OISpikeNegativeDetector`
- `OI_SPIKE_POSITIVE`: `standard` via `OISpikePositiveDetector`
- `ORDERFLOW_IMBALANCE_SHOCK`: `proxy` via `PriceVolImbalanceProxyDetector`
- `OVERSHOOT_AFTER_SHOCK`: `standard` via `OvershootDetector`
- `POST_DELEVERAGING_REBOUND`: `standard` via `PostDeleveragingReboundDetector`
- `PRICE_VOL_IMBALANCE_PROXY`: `proxy` via `PriceVolImbalanceProxyDetector`
- `PULLBACK_PIVOT`: `standard` via `PullbackPivotDetector`
- `RANGE_BREAKOUT`: `standard` via `RangeBreakoutDetector`
- `RANGE_COMPRESSION_END`: `standard` via `RangeCompressionDetector`
- `SCHEDULED_NEWS_WINDOW_EVENT`: `standard` via `ScheduledNewsDetector`
- `SESSION_CLOSE_EVENT`: `standard` via `SessionCloseDetector`
- `SESSION_OPEN_EVENT`: `standard` via `SessionOpenDetector`
- `SLIPPAGE_SPIKE_EVENT`: `standard` via `SlippageSpikeDetector`
- `SPOT_PERP_BASIS_SHOCK`: `production` via `SpotPerpBasisShockDetector`
- `SPREAD_BLOWOUT`: `standard` via `SpreadBlowoutDetector`
- `SPREAD_REGIME_WIDENING_EVENT`: `standard` via `SpreadRegimeWideningDetector`
- `SUPPORT_RESISTANCE_BREAK`: `standard` via `SREventDetector`
- `SWEEP_STOPRUN`: `proxy` via `WickReversalProxyDetector`
- `TREND_ACCELERATION`: `standard` via `TrendAccelerationDetector`
- `TREND_DECELERATION`: `standard` via `TrendDecelerationDetector`
- `TREND_EXHAUSTION_TRIGGER`: `standard` via `TrendExhaustionDetector`
- `TREND_TO_CHOP_SHIFT`: `standard` via `TrendToChopDetector`
- `VOL_CLUSTER_SHIFT`: `standard` via `VolClusterShiftDetector`
- `VOL_REGIME_SHIFT_EVENT`: `standard` via `VolRegimeShiftDetector`
- `VOL_RELAXATION_START`: `standard` via `VolRelaxationDetector`
- `VOL_SHOCK`: `specialized` via `VolShockRelaxationDetector`
- `VOL_SPIKE`: `production` via `VolSpikeDetector`
- `WICK_REVERSAL_PROXY`: `proxy` via `WickReversalProxyDetector`
- `ZSCORE_STRETCH`: `standard` via `ZScoreStretchDetector`
