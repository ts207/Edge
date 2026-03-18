# Synthetic Datasets

Synthetic datasets are controlled research worlds, not substitutes for live-market evidence.

Use them to validate mechanisms, contracts, and detector behavior under known conditions.

## What Synthetic Data Is For

Use synthetic datasets to validate:

- detector truth recovery
- artifact and contract plumbing
- search and promotion behavior under controlled regimes
- negative controls
- robustness across different synthetic worlds

Do not use synthetic output as standalone proof of live profitability.

## Built-In Profiles

Maintained profiles:

- `default`: balanced baseline with recurring event regimes
- `2021_bull`: stronger drift, faster cycle cadence, more crowding-like behavior
- `range_chop`: lower drift, tighter amplitudes, more resets
- `stress_crash`: wider spreads, higher noise, stronger stress episodes
- `alt_rotation`: stronger cross-sectional rotation behavior

## What Gets Written

Each generated run writes:

- `synthetic/<run_id>/synthetic_generation_manifest.json`
- `synthetic/<run_id>/synthetic_regime_segments.json`
- run-scoped lake partitions under `data/lake/runs/<run_id>/...`

Synthetic cleaned bars include a minimal microstructure contract:

- `spread_bps`
- `depth_usd`
- `bid_depth_usd`
- `ask_depth_usd`
- `imbalance`

## Main Workflows

### Broad Maintained Workflow

Use the maintained broad workflow for detector truth and broad synthetic discovery behavior:

```bash
python3 -m project.scripts.run_golden_synthetic_discovery
```

### Fast Certification Workflow

Use the fast workflow for narrow detector-and-plumbing certification:

```bash
python3 -m project.scripts.run_fast_synthetic_certification
```

That path is intentionally narrow in symbols, date range, event fanout, templates, and search budget.

Interpret it as:

- detector truth and artifacts can pass
- discovery and promotion may still produce zero viable candidates because holdout support is too small

## Truth Validation

Validate a synthetic run with:

```bash
python3 -m project.scripts.validate_synthetic_detector_truth \
  --run_id golden_synthetic_discovery
```

Important distinction:

- `expected_event_types` are the hard pass or fail truth contract
- `supporting_event_types` are informational supporting signals

To include supporting-signal reporting without changing the main pass or fail result:

```bash
python3 -m project.scripts.validate_synthetic_detector_truth \
  --run_id my_run \
  --include_supporting_events 1
```

## Recommended Workflow

1. choose the profile that matches the question
2. freeze the profile and slice before reviewing outcomes
3. run the narrowest path that answers the question
4. validate truth before interpreting misses
5. compare against at least one additional profile before strengthening belief

## Current Limits

`ABSORPTION_PROXY` and `DEPTH_STRESS_PROXY` are currently:

- measurable on synthetic data
- supporting-only in synthetic reporting
- treated as live-data diagnostics by default

They are not reliable hard synthetic truth targets under the current `liquidity_stress` generator family.

Because of that:

- the default synthetic detector audit skips them
- opt in explicitly when you want informational measurement

## Selection Heuristics

Use:

- `default` for balanced discovery checks
- `2021_bull` for trend and crowding-sensitive templates
- `range_chop` for false-breakout and mean-reversion stress
- `stress_crash` for liquidity, deleveraging, and spread-sensitive logic
- `alt_rotation` for multi-symbol rotation behavior

## Guardrails

- keep truth validation artifacts with the run
- separate detector recovery claims from profitability claims
- prefer cross-profile survival over single-profile peak performance
- do not redesign directly against one synthetic world
- rerun truth validation after detector or generator changes
- treat short certification windows as calibration unless real holdout support exists
