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
* **Deployment State**: Theses can be `monitor_only`, `paper_only`, or `live_enabled`.
* **Kill Switch**: Sessions can be disabled immediately if risk thresholds are breached.
