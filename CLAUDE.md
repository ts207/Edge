# Claude Code Guide

This repository is prepared for agent-driven research. The controller should behave like a conservative research operator, not a strategy optimizer.

## Operating Objective

Use the repository to run narrow, attributable, replayable research loops:

`observe -> retrieve memory -> propose -> validate plan -> execute -> evaluate -> reflect -> update memory`

The agent should optimize for:

1. post-cost robustness
2. reproducibility
3. mechanical cleanliness
4. narrow attribution
5. bounded search

## Default Policy

Start narrow.

- Prefer one event family, one template family, one context family, and one objective per run.
- Use `plan_only` before material runs.
- Use targeted replays after code or contract edits.
- Treat promotion as a hard gate, not a formality.
- Treat synthetic runs as calibration and falsification tools unless the operator explicitly says otherwise.

Avoid:

- broad search over many unrelated triggers in one run
- repeated proposal churn after inspecting outcomes
- using synthetic wins as direct evidence of live profitability
- bypassing memory because a run “looks different” without concrete differences

## Canonical Query / Proposal Flow

Read knobs and memory first:

```bash
.venv/bin/python -m project.research.knowledge.query knobs
.venv/bin/python -m project.research.knowledge.query memory --program_id btc_campaign
.venv/bin/python -m project.research.knowledge.query static --event BASIS_DISLOC
```

Translate a compact proposal into repo-native config:

```bash
.venv/bin/python -m project.research.agent_io.proposal_to_experiment \
  --proposal /abs/path/to/proposal.yaml \
  --registry_root project/configs/registries \
  --config_path /tmp/experiment.yaml \
  --overrides_path /tmp/run_all_overrides.json
```

Execute conservatively:

```bash
.venv/bin/python -m project.research.agent_io.execute_proposal \
  --proposal /abs/path/to/proposal.yaml \
  --run_id btc_basis_slice_001 \
  --registry_root project/configs/registries \
  --out_dir data/artifacts/experiments/btc_campaign/proposals/btc_basis_slice_001 \
  --plan_only 1
```

Use the higher-level issuer when memory bookkeeping is desired:

```bash
.venv/bin/python -m project.research.agent_io.issue_proposal \
  --proposal /abs/path/to/proposal.yaml \
  --registry_root project/configs/registries \
  --plan_only 1
```

## Proposal Rules

A proposal should be compact and hypothesis-shaped.

Required structure:

- `program_id`
- `objective`
- `symbols`
- `timeframe`
- `start` / `end`
- `trigger_space`
- `templates`
- `contexts` when context matters
- `horizons_bars`
- `directions`
- `entry_lags`

Only set knobs that are explicitly proposal-settable.

## Synthetic Research Policy

Synthetic data is for:

- detector truth recovery
- infrastructure validation
- negative-control testing
- regime stress testing
- promotion filter verification

Synthetic data is not, by itself, proof of market edge.

When using synthetic datasets:

- freeze the generator profile before evaluating outcomes
- keep the truth map and manifest with the run
- rerun truth validation after detector or generator edits
- prefer validation across multiple seeds or profiles rather than one “hero” run

Recommended commands:

```bash
python3 -m project.scripts.generate_synthetic_crypto_regimes --suite_config project/configs/synthetic_dataset_suite.yaml --run_id synthetic_suite
python3 -m project.scripts.run_golden_synthetic_discovery
python3 -m project.scripts.validate_synthetic_detector_truth --run_id golden_synthetic_discovery
```

Useful built-in synthetic profiles:

- `default`
- `2021_bull`
- `range_chop`
- `stress_crash`
- `alt_rotation`

## Evaluation Discipline

Every meaningful run should be evaluated on three layers:

1. mechanical integrity
2. statistical quality
3. deployment relevance

Check at minimum:

- split counts
- `q_value`
- post-cost expectancy
- stressed post-cost expectancy
- promotion eligibility
- artifact completeness
- warning surface

## Reflection Discipline

After each meaningful run, write down:

- what belief was tested
- what materially changed
- whether the result was market-driven or system-driven
- what should be repeated, repaired, or stopped

The next action must be explicit:

- exploit
- explore adjacent
- repair path
- hold
- stop

## Repository Landmarks

- `project/pipelines/run_all.py`: orchestrator
- `project/contracts/pipeline_registry.py`: contract source
- `project/research/knowledge/`: static knowledge, memory, reflection surfaces
- `project/research/agent_io/`: proposal validation, translation, execution
- `project/events/detectors/catalog.py`: detector loading surface
- `project/configs/registries/`: authoritative registry content
- `docs/SYNTHETIC_DATASETS.md`: synthetic dataset guidance
- `docs/AUTONOMOUS_RESEARCH_LOOP.md`: loop-level operating policy

## Definition Of A Good Agent Run

A good run is not the run with the highest headline metric.

It is the run that leaves behind:

- a bounded hypothesis
- a clean artifact trail
- an interpretable result
- a justified next action
