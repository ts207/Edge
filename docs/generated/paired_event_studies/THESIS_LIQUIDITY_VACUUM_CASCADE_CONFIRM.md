# Direct paired-event study — THESIS_LIQUIDITY_VACUUM_CASCADE_CONFIRM

- thesis_id: `THESIS_LIQUIDITY_VACUUM_CASCADE_CONFIRM`
- selected_horizon_bars: `24`
- symbols: `BTCUSDT, ETHUSDT`
- trigger_component: `LIQUIDITY VACUUM`
- confirm_component: `LIQUIDATION CASCADE`
- split: `2021 validation / 2022 test`

## Aggregate selected-horizon comparison

| Cohort | Events | Validation mean (bps) | Test mean (bps) | Total mean (bps) | Stability | Q-value |
|---|---:|---:|---:|---:|---:|---:|
| liquidity_vacuum_only | 1224 |  | 61.59 | 61.59 | 0.000 | 0.000000 |
| liquidation_cascade_only | 0 |  |  |  | 0.000 |  |
| joint_trigger | 0 |  |  |  | 0.000 |  |

## Pair advantage diagnostics

- joint_minus_trigger_only_bps: `None`
- joint_minus_confirmation_only_bps: `None`
- joint_test_advantage_vs_trigger_only_bps: `None`
- joint_test_advantage_vs_confirmation_only_bps: `None`

## Interpretation

This study closes the missing direct paired-event evidence gap for the packaged confirmation thesis.
Use the pair-vs-component comparison to decide whether the thesis should stay confirmation-scoped or be granted broader paper-grade use.
