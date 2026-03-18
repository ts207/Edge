# Gemini Code Guide

This repository is prepared to use Gemini as an external research controller. The operating model below is intentionally aligned with agent-driven research: narrow hypotheses, proposal validation, artifact-first evaluation, and reflection-backed iteration.

When operating via GitHub Actions, the agent is named **AI Irene** and follows the protocols defined in `.github/commands/`.

## Local Setup

Assume the repository root as the working directory.

Preferred Python entrypoint:

```bash
.venv/bin/python
```

Install the package if the environment is not already prepared:

```bash
pip install -e .
pip install -r requirements-dev.txt
```

Low-risk validation commands:

```bash
make help
.venv/bin/python -m project.research.knowledge.query knobs
.venv/bin/python -m project.research.agent_io.issue_proposal --help
.venv/bin/python -m project.research.agent_io.proposal_to_experiment --help
```

The controller should do four things here:

1. read structured knowledge and memory
2. issue narrow validated experiment proposals
3. run `plan_only` or `dry_run` first
4. inspect reflections and memory before proposing the next run

The repo should do four things:

1. validate proposals
2. translate them into native experiment configs
3. execute `run_all`
4. write artifacts, memory, and reflections back to disk

## Canonical Loop

The intended controller loop is:

`query static knowledge -> query campaign memory -> issue proposal -> run plan_only/dry_run -> run full pipeline when justified -> inspect reflections -> adapt`

Do not start with broad full-month runs unless the path is already mechanically stable.

## Primary Entry Points

Query knowledge and memory:

```bash
.venv/bin/python -m project.research.knowledge.query static --event BASIS_DISLOC
.venv/bin/python -m project.research.knowledge.query memory --program_id btc_campaign --event_type BASIS_DISLOC
.venv/bin/python -m project.research.knowledge.query knobs
.venv/bin/python -m project.research.knowledge.query knobs --include_advanced 1 --mutability any
```

Translate a proposal into a validated experiment config:

```bash
.venv/bin/python -m project.research.agent_io.proposal_to_experiment \
  --proposal /abs/path/to/proposal.yaml \
  --registry_root project/configs/registries \
  --config_path /tmp/experiment.yaml \
  --overrides_path /tmp/run_all_overrides.json
```

Execute a validated proposal with explicit `run_id`:

```bash
.venv/bin/python -m project.research.agent_io.execute_proposal \
  --proposal /abs/path/to/proposal.yaml \
  --run_id btc_basis_slice_001 \
  --registry_root project/configs/registries \
  --out_dir data/artifacts/experiments/btc_campaign/proposals/btc_basis_slice_001 \
  --plan_only 1
```

Issue a proposal through the higher-level memory-backed wrapper:

```bash
.venv/bin/python -m project.research.agent_io.issue_proposal \
  --proposal /abs/path/to/proposal.yaml \
  --registry_root project/configs/registries \
  --plan_only 1
```

The issuer will:

- choose a `run_id` if needed
- copy the proposal into the program memory tree
- write `experiment.yaml`
- write `run_all_overrides.json`
- invoke `run_all`
- append a proposal audit row to `proposals.parquet`

## Repository Landmarks

- `project/pipelines/run_all.py`: orchestration entrypoint
- `project/contracts/pipeline_registry.py`: stage and artifact contract registry
- `project/research/knowledge/`: static knowledge, memory, reflection, and query surfaces
- `project/research/agent_io/`: proposal validation, translation, and execution wrappers
- `project/pipelines/research/analyze_events.py`: canonical single-event detector execution entrypoint
- `project/pipelines/research/generic_detector_task.py`: generic detector runner with CLI override parsing
- `project/events/detectors/catalog.py`: explicit detector loading surface
- `project/configs/registries/`: authoritative events, templates, contexts, and search limits
- `docs/`: operating policy and research loop documents
- `tests/research/`: coverage for agent I/O and knowledge workflows

## Proposal Shape

The controller should write compact proposals, not raw `run_all` argv.

Minimal shape:

```yaml
program_id: btc_campaign
description: basis continuation under low liquidity
run_mode: research
objective: retail_profitability
promotion_mode: research
symbols: [BTCUSDT]
timeframe: 5m
start: 2026-01-01
end: 2026-01-31
instrument_classes: [crypto]
trigger_space:
  allowed_trigger_types: [EVENT]
  events:
    include: [BASIS_DISLOC]
templates: [continuation]
contexts:
  liquidity_regime: [low]
horizons_bars: [12]
directions: [long, short]
entry_lags: [0]
knobs:
  candidate_promotion_min_events: 60
```

Only `proposal_settable` knobs are allowed in proposals. Claude should discover them through:

```bash
.venv/bin/python -m project.research.knowledge.query knobs
```

By default, that command returns the safe core subset only.

## Default Operating Policy

The controller should default to:

- `plan_only` first
- `dry_run` second if plan looks correct
- full execution only after plan and path look mechanically clean

The controller should prefer:

- one objective per run
- narrow event/template/context slices
- memory-backed iteration over repeated broad exploration

The controller should avoid:

- changing `inspect_only` knobs
- broad config churn across many unrelated knobs
- full runs when reflections show unresolved mechanical failures

## Artifact Locations

Static knowledge:

- `data/knowledge/static/entities.parquet`
- `data/knowledge/static/relations.parquet`
- `data/knowledge/static/documents.parquet`
- `data/knowledge/static/agent_knobs.parquet`

Campaign memory:

- `data/artifacts/experiments/<program_id>/memory/tested_regions.parquet`
- `data/artifacts/experiments/<program_id>/memory/reflections.parquet`
- `data/artifacts/experiments/<program_id>/memory/failures.parquet`
- `data/artifacts/experiments/<program_id>/memory/proposals.parquet`
- `data/artifacts/experiments/<program_id>/memory/belief_state.json`
- `data/artifacts/experiments/<program_id>/memory/next_actions.json`
- `data/artifacts/experiments/<program_id>/memory/proposals/<run_id>/`

Pipeline outputs:

- `data/runs/<run_id>/`
- `data/reports/phase2/<run_id>/`
- `data/reports/edge_candidates/<run_id>/`
- `data/reports/promotions/<run_id>/`
- `data/lake/runs/<run_id>/features/perp/<symbol>/<tf>/features_feature_schema_v2/`
- `data/lake/runs/<run_id>/features/spot/<symbol>/<tf>/features_feature_schema_v2/`

## Reading Results

After a run, the controller should inspect:

1. `reflections.parquet`
2. `tested_regions.parquet`
3. `failures.parquet`
4. `belief_state.json`
5. `next_actions.json`

The reflection engine already separates:

- market findings
- system findings

Do not interpret market evidence from a run whose primary next action is `repair_pipeline`.

For synthetic discovery runs, also inspect:

1. `synthetic/<run_id>/synthetic_generation_manifest.json`
2. `synthetic/<run_id>/synthetic_regime_segments.json`
3. `docs/generated/detector_coverage.md` if detector inventory changed
4. `project.scripts.validate_synthetic_detector_truth` output before treating synthetic misses as strategy evidence

## Important Constraints

- `parquet/json` are canonical; there is no database dependency
- the repo validates proposals; gemini should not bypass the proposal layer
- `research` promotion and `deploy` promotion are intentionally different
- the knob catalog is comprehensive, but gemini should usually operate on the core default subset
- existing uncommitted changes may be user work; do not revert them unless explicitly asked
- feature-stage contracts must match the raw inputs implementations may read
- detector ownership config, runtime registration, and generated detector-coverage docs must stay in sync
- sequence detectors and other event-stream detectors must run against registry events, not bar features
- no-candidate bridge runs are valid no-op successes; do not treat them as automatic pipeline failures
- promotion fallback artifacts must match the canonical normalized export contract

## Detector And Synthetic Guidance

gemini should assume:

- detector registration is explicit, not import-side-effect driven
- unknown CLI flags passed into `analyze_events.py` or `generic_detector_task.py` can be meaningful detector parameter overrides
- funding thresholds named `*_bps` are bps values even when the underlying feature column is decimal-scaled

When working on synthetic discovery:

- verify that truth windows represent detector preconditions the generator actually seeds
- separate truth-alignment failures from ordinary phase-2 or promotion failures
- rerun `project.scripts.validate_synthetic_detector_truth` after detector or generator edits before widening scope

## Best First Command

For a fresh session, start here:

```bash
.venv/bin/python -m project.research.knowledge.query knobs
```

Then query the relevant memory for the target `program_id`, write a small proposal, and issue it with `--plan_only 1`.


## Synthetic Dataset Discipline

When operating on synthetic data, the controller should:

- freeze the generator profile before inspecting outcomes
- keep the truth map and generation manifest with the run
- rerun `project.scripts.validate_synthetic_detector_truth` after detector or generator changes
- compare claims across more than one profile before strengthening belief

Recommended reference: `docs/SYNTHETIC_DATASETS.md`.
