# Synthetic Datasets

This repository includes a deterministic synthetic regime generator for agent-driven research.

## Purpose

Synthetic datasets should be used to validate:

- detector truth recovery
- artifact and contract plumbing
- promotion and gate behavior
- robustness to regime variation
- falsification on negative controls

They should not be treated as direct evidence of live-market profitability.

## Available Profiles

The generator supports these built-in profiles:

- `default`: balanced baseline with recurring event regimes
- `2021_bull`: higher drift, higher turnover, faster cycle cadence
- `range_chop`: low-drift, tighter regime amplitudes, more frequent resets
- `stress_crash`: wider spreads, higher noise, stronger stress episodes
- `alt_rotation`: higher altcoin-style participation and stronger rotations

## Generate One Dataset

```bash
python3 -m project.scripts.generate_synthetic_crypto_regimes \
  --run_id synthetic_range_chop \
  --start_date 2026-03-01 \
  --end_date 2026-05-31 \
  --symbols BTCUSDT,ETHUSDT,SOLUSDT \
  --volatility_profile range_chop \
  --noise_scale 0.9
```

## Generate A Curated Suite

```bash
python3 -m project.scripts.generate_synthetic_crypto_regimes \
  --suite_config project/configs/synthetic_dataset_suite.yaml \
  --run_id synthetic_suite
```

The suite manifest is written to:

- `data/synthetic/<suite_name>/synthetic_dataset_suite_manifest.json`

Each dataset also writes:

- `synthetic/<run_id>/synthetic_generation_manifest.json`
- `synthetic/<run_id>/synthetic_regime_segments.json`
- run-scoped lake partitions under `data/lake/runs/<run_id>/...`

## Recommended Agent Workflow

1. Pick one profile matching the research question.
2. Generate the dataset.
3. Run the narrowest detector or discovery slice that answers the question.
4. Validate detector truth before interpreting misses.
5. Compare across at least one additional profile before strengthening belief.

## Dataset Selection Heuristics

Use:

- `default` for smoke and balanced discovery checks
- `2021_bull` for strong-trend and crowding-sensitive templates
- `range_chop` for false-breakout and mean-reversion stress
- `stress_crash` for liquidity, deleveraging, and spread-sensitive logic
- `alt_rotation` for multi-symbol rotation and cross-sectional tests

## Verification Workflows

### 1. Detector Truth Validation
Use the `project.scripts.validate_synthetic_detector_truth` script to compare detector hits against the generation manifest.
- **Pass Requirement**: Usually > 70% hit rate with < 10% off-regime noise.
- **Example**:
  ```bash
  python3 -m project.scripts.validate_synthetic_detector_truth --run_id my_run --truth_map_path data/synthetic/my_run/synthetic_regime_segments.json
  ```

### 2. Cross-Profile Validation
Always validate a hypothesis against at least two distinct profiles (e.g., `default` and `stress_crash`).
- Use the `synthetic` gate profile in `run_all` to allow low-sample-size validation without failing the research pipeline.
- **Set**: `--phase2_gate_profile synthetic --discovery_profile synthetic`.

## Guardrails

- **Standardized Event Names**: Ensure event types match the authoritative registry (e.g., use `LIQUIDATION_EXHAUSTION_REVERSAL` instead of legacy aliases).
- **Data Path Alignment**: Synthetic OI data must be written to `raw/binance/perp/<symbol>/open_interest/5m/` for correct pipeline ingestion.
- **Sizing Discipline**: Portfolios built from synthetic edges should maintain gross leverage limits even when expectancy is artificially high.
- **Freeze the profile** before reviewing outcomes.
- Do not keep redesigning features against one synthetic profile.
- Prefer cross-profile survival to single-profile peak performance.
- Keep truth validation artifacts with the run.
