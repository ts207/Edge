# Direct paired-event study — THESIS_VOL_SHOCK_LIQUIDITY_CONFIRM

- thesis_id: `THESIS_VOL_SHOCK_LIQUIDITY_CONFIRM`
- selected_horizon_bars: `8`
- symbols: `BTCUSDT, ETHUSDT`
- trigger_component: `VOL SHOCK`
- confirm_component: `LIQUIDITY VACUUM`
- split: `2021 validation / 2022 test`

## Aggregate selected-horizon comparison

| Cohort | Events | Validation mean (bps) | Test mean (bps) | Total mean (bps) | Stability | Q-value |
|---|---:|---:|---:|---:|---:|---:|
| vol_shock_only | 3505 |  | 53.98 | 53.98 | 0.000 | 0.000000 |
| liquidity_vacuum_only | 1102 |  | 36.93 | 36.93 | 0.000 | 0.000000 |
| joint_trigger | 119 |  | 35.78 | 35.78 | 0.000 | 0.000000 |

## Pair advantage diagnostics

- joint_minus_trigger_only_bps: `-18.19896897623933`
- joint_minus_confirmation_only_bps: `-1.143067252689967`
- joint_test_advantage_vs_trigger_only_bps: `-18.19896897623933`
- joint_test_advantage_vs_confirmation_only_bps: `-1.143067252689967`

## Interpretation

This study closes the missing direct paired-event evidence gap for the packaged confirmation thesis.
Use the pair-vs-component comparison to decide whether the thesis should stay confirmation-scoped or be granted broader paper-grade use.
