# engine_live_runtime

## Scope
- project/engine/
- project/execution/
- project/portfolio/
- project/live/
- project/runtime/
- project/scripts/run_live_engine.py
- project/tests/engine/
- project/tests/live/
- project/tests/runtime/
- project/tests/replays/

## Summary
Live startup flows through project/scripts/run_live_engine.py into LiveEngineRunner, which owns an OMS, kill-switch logic, health checks, and periodic account sync. The proactive trading gate is split from reactive kill-switch and accounting paths. Runtime postflight/replay checks are batch artifacts that do not always exercise the same normalization path as live runtime.

## Findings
### Monitor-only runners can still send real flatten orders when the kill-switch fires
- Severity: critical
- Confidence: verified
- Category: runtime_safety
- Affected: project/scripts/run_live_engine.py, project/live/runner.py, project/live/oms.py, project/configs/live_paper.yaml, project/configs/live_production.yaml
- Evidence: build_live_runner() creates an exchange-backed OMS in monitor_only when credentials exist, and _handle_kill_switch_trigger() always calls cancel_all_orders() and flatten_all_positions(), which submit reduce_only market orders.
- Why it matters: A supposedly non-trading observer can place real venue orders during a stale-feed or health-triggered unwind.
- Validation: Instantiate LiveEngineRunner(runtime_mode="monitor_only") with an exchange-backed OrderManager and positions, then await _handle_kill_switch_trigger().
- Remediation: Hard-gate all venue mutation paths on runtime_mode, or rename/document the mode if protective order placement is intentional.

### Monitor-only startup still requires a tradable Binance account and trading credentials
- Severity: high
- Confidence: verified
- Category: contract_integrity
- Affected: project/scripts/run_live_engine.py, project/tests/scripts/test_run_live_engine.py, project/tests/contracts/test_live_environment_config_contract.py
- Evidence: main() always runs preflight_binance_venue_connectivity() and validate_binance_account_preflight() regardless of runtime_mode, while config contracts label live_paper/live_production as monitor_only.
- Why it matters: There is no safe read-only deployment tier despite the naming and config contract.
- Validation: Supply a non-tradable account preflight payload to validate_binance_account_preflight() while using a monitor_only config.
- Remediation: Branch startup requirements on runtime_mode and allow monitor_only to use read-only credentials/connectivity checks.

### Incubation or paper gating is ineffective and graduation status is inverted
- Severity: high
- Confidence: verified
- Category: correctness
- Affected: project/live/runner.py, project/portfolio/incubation.py, project/live/oms.py
- Evidence: _prepare_strategy_order() only writes order.metadata["is_paper"], submit_order_async() ignores it, and IncubationLedger.is_graduated() returns False even after graduate() sets status="live".
- Why it matters: Incubating strategies are not truly kept out of live trading, and explicit graduation status is misreported.
- Validation: Exercise IncubationLedger.graduate() and submit a non-graduated strategy order through a venue-backed OMS.
- Remediation: Fix is_graduated() semantics and enforce incubation at the OMS submission boundary.

### Any caller can forge a StrategyResult and reach live trading by flipping strategy_runtime.implemented
- Severity: high
- Confidence: verified
- Category: runtime_safety
- Affected: project/live/runner.py, project/live/oms.py, project/engine/strategy_executor.py
- Evidence: submit_strategy_result_async() accepts arbitrary StrategyResult-like payloads, and _ensure_trading_enabled() only checks runtime_mode and strategy_runtime["implemented"]. build_live_order_from_strategy_result() derives orders directly from result.data.
- Why it matters: Unsafe or fabricated runtime objects can bypass provenance checks and create venue orders.
- Validation: Pass a handcrafted StrategyResult with target_position and fill_price into submit_strategy_result_async() on a trading runner.
- Remediation: Bind live-trading eligibility to validated runtime object type or signed strategy provenance, not a free-form implemented flag.

### Runtime postflight audit can return pass for malformed event rows because normalization is skipped
- Severity: medium
- Confidence: verified
- Category: artifact_integrity
- Affected: project/runtime/invariants.py, project/runtime/normalized_event.py, project/pipelines/runtime/build_normalized_replay_stream.py
- Evidence: run_runtime_postflight_audit() never calls normalize_event_rows(); it counts raw rows, and run_watermark_audit() skips rows missing timestamps.
- Why it matters: Replay/postflight artifacts can go green on malformed runtime data that the real normalization stage would reject or truncate.
- Validation: Call run_runtime_postflight_audit() on an events_df missing timestamp fields and inspect the returned status and normalization counts.
- Remediation: Normalize first or consume the normalized replay artifact before performing postflight checks.

### OMS fills do not update LiveStateStore, so safety decisions run on stale account state until the next snapshot sync
- Severity: medium
- Confidence: verified
- Category: correctness
- Affected: project/live/runner.py, project/live/oms.py, project/live/state.py
- Evidence: on_order_fill() updates the OMS and execution-quality report, but it does not mutate LiveStateStore; account state only changes on periodic exchange snapshots.
- Why it matters: Sizing, drawdown checks, and kill-switch logic can act on stale balances and positions between exchange syncs.
- Validation: Call on_order_fill() on a runner with an in-memory order and inspect state_store.account before and after.
- Remediation: Apply provisional local state updates on fills or maintain a merged local execution ledger for safety-critical logic.
