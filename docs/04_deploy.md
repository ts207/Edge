# Stage 4: Deploy

Deployment is the final stage where promoted theses are executed in a runtime environment.

## Concept
The deployment stage is responsible for:
* **Session Management**: Running paper or live trading sessions.
* **Risk Controls**: Applying hard caps on position size, drawdown, and correlation.
* **Lineage Tracking**: Ensuring every live trade can be traced back to its research run.

## Workflow
1. **List Theses**:
   ```bash
   edge deploy list-theses
   ```
2. **Start Paper Session**:
   ```bash
   edge deploy paper --run_id <run_id>
   ```
3. **Check Status**:
   ```bash
   edge deploy status
   ```

## Runtime Modes
* **Paper Trading**: Executing against live data with simulated fills. Used for final out-of-sample confirmation.
* **Live Trading**: Executing with real capital on exchange.

## Risk & Governance
* **Deployment State**: Operator-facing trade eligibility is enforced exclusively via `deployment_state`. A thesis can be explicitly limited to `monitor_only`, `paper_only`, or successfully promoted to `live_enabled`. This flag must pass gate validation prior to engine startup.
* **Kill Switch**: Sessions can be disabled immediately if risk thresholds are breached.

---

## Live Engine Parameters Reference

### Kill Switch (`project/live/kill_switch.py`)

| Parameter | Value | Notes |
|-----------|-------|-------|
| `PSI_ERROR_THRESHOLD` | 0.25 | Triggers kill-switch. PSI > 0.25 = major distributional shift. |
| `PSI_WARN_THRESHOLD` | 0.10 | Logs warning without triggering. |
| Tier-1 monitored features | 6 | `vol_regime`, `ms_spread_state`, `funding_abs_pct`, `basis_zscore`, `oi_delta_1h`, `spread_bps` |

PSI interpretation: < 0.10 stable · 0.10–0.25 minor shift (warn) · > 0.25 major shift (error trigger).

The `check_feature_drift` method uses a KS statistic alongside PSI (returned in the drift result dict as `ks_statistic`). KS is more sensitive to tail divergence and catches drift that PSI's bin-clumping behaviour can miss.

### Decay Monitor (`project/live/decay.py`)

When no `decay_rules` are passed at engine startup, the following conservative defaults are active:

| Rule | Metric | Threshold | Window | Action |
|------|--------|-----------|--------|--------|
| `edge_decay_default` | edge ratio | 0.50 of expected | 10 samples | downsize 50% |
| `slippage_spike_default` | slippage bps | 20 bps | 5 samples | downsize 50% |
| `hit_rate_decay_default` | hit rate | 0.40 | 10 samples | warn |

Operators may override by passing explicit `decay_rules` to `LiveEngineRunner`. The defaults are intentionally conservative — tighten thresholds for strategies with higher expected edge.

### Allocation Policy (`project/engine/risk_allocator.py`)

The default `AllocationPolicy.mode` is `"deterministic_optimizer"`. This ensures allocation decisions are reproducible and auditable, consistent with the artifact-lineage model. The `"heuristic"` mode remains available for testing but should not be used in production.

### Stressed Regime Correlation Limits (`project/engine/risk_allocator.py`)

The `stressed_regime_values` vocabulary covers all known regime-registry naming conventions:

```
stress, crisis, high_vol,
STRESS, CRISIS, HIGH_VOL, SHOCK, HIGH_VOL_REGIME,
high_vol_shock, vol_shock, crisis_regime, CRISIS_REGIME
```

If a new stressed-regime label is added to the registry, it must also be added here or the protective correlation limit will silently fail to activate.

### Funding Schedule (`project/engine/pnl.py`)

Use the correct named constant for each venue:

```python
from project.engine.pnl import FUNDING_HOURS_BINANCE, FUNDING_HOURS_BYBIT_4H

# Binance UM perpetuals and Bybit 8-hour contracts
compute_pnl_ledger(..., funding_hours=FUNDING_HOURS_BINANCE)   # (0, 8, 16)

# Bybit 4-hour contracts
compute_pnl_ledger(..., funding_hours=FUNDING_HOURS_BYBIT_4H)  # (0, 4, 8, 12, 16, 20)
```

Using the wrong schedule silently understates carry by 50% for Bybit 4-hour instruments.

### Decision Score Gate (`project/live/scoring.py`)

A hard `MIN_SETUP_MATCH = 0.20` floor is enforced before the additive score is computed. If `setup_match_score < 0.20`, `total_score` is forced to 0.0 regardless of execution quality, thesis strength, or regime alignment. This prevents the additive architecture from triggering trades when no qualifying event has fired.

Score components for reference:

| Component | Weight | Max contribution |
|-----------|--------|-----------------|
| Setup match | × 0.45 | 0.45 |
| Execution quality | additive | 0.30 |
| Thesis strength | additive | 0.50 |
| Regime alignment | additive | 0.10 |
| Contradiction penalty | subtractive | −1.0 |

Trade thresholds are defined in the policy config (typically `trade_normal ≥ 0.75`).
