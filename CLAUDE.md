# Research Operator Guide

This repository is designed for disciplined market research by an autonomous or semi-autonomous operator.

The operator should behave like a conservative research lead:

- start narrow
- trust artifacts over impressions
- separate mechanical, statistical, and deployment conclusions
- treat promotion as a gate
- leave behind a clear next action after every meaningful run

## Operating Objective

Use the repository to run bounded, replayable research loops:

`observe -> retrieve memory -> define objective -> propose -> plan -> execute -> evaluate -> reflect -> adapt`

Optimize for:

1. reproducibility
2. post-cost robustness
3. contract cleanliness
4. narrow attribution
5. decision quality

This is not a generic backtest sandbox. It is a system for testing explicit claims.

## Default Policy

Prefer:

- one event family or narrow trigger set per run
- one template family per run
- one primary context family per run
- confidence-aware context when context matters
- confirmatory follow-up over repeated broad discovery

Avoid:

- broad search over unrelated triggers in one run
- reruns that differ only in wording
- treating detector materialization as strategy proof
- treating synthetic wins as live-market evidence
- trusting command exit status without artifact reconciliation

## What Counts As A Good Run

A good run is not the run with the best headline metric.

A good run leaves behind:

- a bounded question
- a clean artifact trail
- a defensible interpretation
- a recorded next action

Valid next actions:

- `exploit`
- `explore`
- `repair`
- `hold`
- `stop`

## Canonical Workflow

Inspect knobs and prior memory first:

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

Inspect the plan before execution:

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

Minimum structure:

- `program_id`
- `objective`
- `symbols`
- `timeframe`
- `start`
- `end`
- `trigger_space`
- `templates`
- `contexts` when context matters
- `horizons_bars`
- `directions`
- `entry_lags`

Only set knobs that are explicitly proposal-settable.

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

## Synthetic Policy

Synthetic data is for:

- detector truth recovery
- infrastructure validation
- negative-control testing
- regime stress testing
- search and promotion calibration

Synthetic data is not direct proof of live profitability.

When using synthetic datasets:

- freeze the profile before evaluating outcomes
- keep the manifest and truth map with the run
- rerun truth validation after detector or generator edits
- compare across at least one additional profile before strengthening belief

Useful maintained commands:

```bash
python3 -m project.scripts.generate_synthetic_crypto_regimes \
  --suite_config project/configs/synthetic_dataset_suite.yaml \
  --run_id synthetic_suite
python3 -m project.scripts.run_golden_synthetic_discovery
python3 -m project.scripts.run_fast_synthetic_certification
python3 -m project.scripts.validate_synthetic_detector_truth \
  --run_id golden_synthetic_discovery
```

Short synthetic windows are calibration first:

- detector truth plus artifact completion means calibration success
- zero validation or test support means insufficient evidence
- promotion conclusions only count when holdout support is real

## Artifact Rule

Artifacts are the source of truth.

Read in this order:

1. top-level run manifest
2. stage manifests
3. stage logs
4. report artifacts
5. generated diagnostics

If those disagree, the disagreement is a first-class finding.

## Repository Landmarks

- `project/pipelines/run_all.py`: end-to-end orchestration
- `project/contracts/pipeline_registry.py`: stage and artifact contract source
- `project/research/knowledge/`: memory, static knowledge, reflection
- `project/research/agent_io/`: proposal validation, translation, execution
- `project/research/services/`: discovery, promotion, comparison, diagnostics
- `project/events/detectors/catalog.py`: detector loading surface
- `project/features/`: shared feature, regime, and guard helpers
- `docs/README.md`: maintained docs index

## Continue Reading

For the full operator doc set, continue with:

1. [docs/RESEARCH_OPERATOR_PLAYBOOK.md](./docs/RESEARCH_OPERATOR_PLAYBOOK.md)
2. [docs/AUTONOMOUS_RESEARCH_LOOP.md](./docs/AUTONOMOUS_RESEARCH_LOOP.md)
3. [docs/EXPERIMENT_PROTOCOL.md](./docs/EXPERIMENT_PROTOCOL.md)
4. [docs/ARTIFACTS_AND_CONTRACTS.md](./docs/ARTIFACTS_AND_CONTRACTS.md)
