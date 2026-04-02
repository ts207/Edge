# Founding thesis evidence summary

This artifact records the first raw-data empirical bundle generation pass against the founding thesis queue.

## Policy notes

- Generate canonical evidence bundles directly from raw perp market data.
- This archive does not include spot-perp basis inputs, so BASIS_DISLOC and FND_DISLOC are not part of the first supported empirical run.
- The first supported raw-data pass targets volatility, liquidity, and forced-flow theses.
- The next supported structural thesis is VOL_SHOCK + LIQUIDITY_VACUUM confirmation, which shares raw-data inputs with the first volatility/liquidity passes.
- A second supported structural thesis uses LIQUIDITY_VACUUM + LIQUIDATION_CASCADE co-occurrence to deepen the overlap graph around liquidity stress and forced-flow conditions.

- generated_theses: `0`
- unsupported_or_skipped: `5`

## Generated evidence bundles

| Candidate | Event | Symbols | Horizon | Bundles | Sample size | Mean net expectancy (bps) |
|---|---|---|---:|---:|---:|---:|

## Unsupported or skipped

- `THESIS_VOL_SHOCK` — insufficient_event_count_after_detection
- `THESIS_LIQUIDITY_VACUUM` — insufficient_event_count_after_detection
- `THESIS_LIQUIDATION_CASCADE` — required_input_dataset_missing
- `THESIS_VOL_SHOCK_LIQUIDITY_CONFIRM` — insufficient_event_count_after_detection
- `THESIS_LIQUIDITY_VACUUM_CASCADE_CONFIRM` — insufficient_event_count_after_detection
