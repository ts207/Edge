## Current state (2026-04-09)

### What has run

**Infrastructure (pipeline bugs fixed — all working)**
- 9 pipeline bugs fixed this session (dependency races, zero-output rejections, exit code handling, search engine event type routing, filter template mis-classification, DataFrame.attrs concat crash)
- Pipeline runs end-to-end, exit 0, all stages succeed or warn

**Shared lake cache populated**
- BTC+ETH 2021–2024 cleaned bars, features, market context written to shared lake
- Subsequent runs use cache hits (fast)

**LIQUIDATION_CASCADE_PROXY campaign — STOPPED**

Run: `liq_proxy_combined` (BTC+ETH, 2021–2024, oi_quantile=0.98, vol_quantile=0.90)

| Symbol | Events | Best horizon | t_stat | mean bps | n_train |
|--------|--------|-------------|--------|----------|---------|
| BTCUSDT | ~1000 | 60m long | 1.73 | 10.1 | 597 |
| ETHUSDT | ~930 | 60m long (also 15m) | 1.79 | 12.5 | 549 |

**Decision: STOP.** Gate requires t≥2.0. Ceiling is ~1.8 per symbol across all threshold configs.

**Root cause:** Proxy detector fires on OI+volume coincidences that include false positives (funding payments, block trades, rollover events). Per-event return std ~150 bps vs 10 bps mean → SNR too low. Threshold calibration from 0.95→0.99 was fully explored; 0.98 is best known point.

**Signal is real:** direction (long 60m) replicates BTC+ETH with consistent effect size. Effect is not noise — it's genuine cascade exhaustion bounce. But the proxy can't select events cleanly enough to pass gate.

### What the detector needs

To reach t≥2.0, need ONE of:
1. **Confirmation bar requirement** — OI must remain suppressed N bars after signal (e.g., `oi_suppress_bars: 2`). This would filter false-positive OI spikes that recover immediately.
2. **Funding rate gate** — require `funding_rate > X` at signal time. Real cascades happen in funding-elevated regimes.
3. **Cascade true positive** — use `LIQUIDATION_CASCADE` (requires liquidation_notional feed). Check if Bybit cross-exchange liquidation data exists in the lake.

### Next campaign options

**Option A: Fix the proxy**
Add confirmation requirement to `LiquidationCascadeProxyDetector`. Spec change needed. Then re-run.

**Option B: Switch to FUNDING_EXTREME_ONSET**
This event has cleaner signal (funding state is a leading indicator). Known to fire cleanly on 5m data. Run:
```
python3 -m project.pipelines.run_all \
  --run_id funding_extreme_btc_full \
  --symbols BTCUSDT,ETHUSDT \
  --start 2021-01-01 \
  --end 2024-12-31 \
  --events FUNDING_EXTREME_ONSET \
  --timeframe 5m
```

**Option C: OI_FLUSH**
Adjacent event, tighter definition. Often co-occurs with LIQUIDATION_CASCADE_PROXY but OI_FLUSH focuses on the OI component only. May have cleaner signal.

### Infrastructure facts

- `spec/events/LIQUIDATION_CASCADE_PROXY.yaml` — `oi_drop_quantile: 0.98` is the best calibration point
- `spec/templates/registry.yaml` — LIQUIDATION_CASCADE_PROXY added (mirrors LIQUIDATION_CASCADE)
- `project/events/phase2.py` — LIQUIDATION_CASCADE_PROXY added to PHASE2_EVENT_CHAIN
- Pipeline runs with `--events EVENTNAME` correctly pins `phase2_event_type` to that event
- Filter templates (e.g., `only_if_regime`) are now correctly separated from expression templates in resolved search specs
- `promote_candidates` exits 1 + warns (not fails) when validation bundle is missing — expected in discovery runs

### Shared lake state

All BTC+ETH 2021–2024 cleaned/features/market_context are cached in `data/lake/runs/liq_proxy_combined/`. Re-use this run_id for re-runs of the same date range to skip data building.
