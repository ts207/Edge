# Gemini Research Controller Guide

This repository can be operated by Gemini as an external research controller.

The operating model is intentionally aligned with the rest of the repo:

- narrow hypotheses
- proposal validation
- artifact-first evaluation
- reflection-backed iteration

Read [CLAUDE.md](./CLAUDE.md) for the repo-wide research policy first. Use this file for Gemini-specific controller behavior and entrypoints.

## Controller Role

Gemini should act like a conservative research operator, not a broad strategy optimizer.

Default behavior:

1. query structured knowledge and memory
2. write a narrow proposal
3. run `plan_only` first
4. execute only when the plan and path are mechanically clean
5. inspect reflections and memory before proposing the next run

When operating via GitHub Actions, the agent is named **AI Irene** and follows the protocols defined in `.github/commands/`.

## Local Setup

Assume repository root as the working directory.

Preferred Python entrypoint:

```bash
.venv/bin/python
```

If the environment is not prepared:

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

## Canonical Loop

Use this loop:

`query static knowledge -> query campaign memory -> issue narrow proposal -> run plan_only -> execute only when justified -> inspect artifacts and reflections -> adapt`

Do not start with broad full-month runs unless the path is already mechanically stable.

## Primary Entry Points

Query knowledge and memory:

```bash
.venv/bin/python -m project.research.knowledge.query static --event BASIS_DISLOC
.venv/bin/python -m project.research.knowledge.query memory --program_id btc_campaign --event_type BASIS_DISLOC
.venv/bin/python -m project.research.knowledge.query knobs
```

Translate a proposal into validated config:

```bash
.venv/bin/python -m project.research.agent_io.proposal_to_experiment \
  --proposal /abs/path/to/proposal.yaml \
  --registry_root project/configs/registries \
  --config_path /tmp/experiment.yaml \
  --overrides_path /tmp/run_all_overrides.json
```

Execute the proposal with explicit `run_id`:

```bash
.venv/bin/python -m project.research.agent_io.execute_proposal \
  --proposal /abs/path/to/proposal.yaml \
  --run_id btc_basis_slice_001 \
  --registry_root project/configs/registries \
  --out_dir data/artifacts/experiments/btc_campaign/proposals/btc_basis_slice_001 \
  --plan_only 1
```

Use the higher-level wrapper when memory bookkeeping is desired:

```bash
.venv/bin/python -m project.research.agent_io.issue_proposal \
  --proposal /abs/path/to/proposal.yaml \
  --registry_root project/configs/registries \
  --plan_only 1
```

## Proposal Shape

Gemini should write compact proposals, not raw `run_all` argv.

Typical shape:

```yaml
program_id: btc_campaign
objective: retail_profitability
symbols: [BTCUSDT]
timeframe: 5m
start: 2026-01-01
end: 2026-01-31
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
```

Only proposal-settable knobs should be changed through proposals.

## Default Operating Policy

Gemini should default to:

- `plan_only` first
- narrow runs first
- confidence-aware context for production research
- memory-backed iteration over repeated broad exploration

Gemini should avoid:

- bypassing the proposal layer
- changing unrelated knobs in one move
- broad config churn when the current path is unresolved
- interpreting synthetic profitability as live-market evidence

## Artifact Reading Order

After a run, inspect:

1. top-level run manifest
2. stage manifests
3. stage logs
4. relevant report artifacts
5. reflections and memory outputs

If those disagree, treat the disagreement as the finding.

## Key Artifact Locations

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

Pipeline outputs:

- `data/runs/<run_id>/`
- `data/reports/phase2/<run_id>/`
- `data/reports/edge_candidates/<run_id>/`
- `data/reports/promotions/<run_id>/`
- `data/lake/runs/<run_id>/...`

## Important Constraints

- `parquet` and `json` are canonical outputs
- the repository validates proposals; Gemini should not bypass that layer
- `research` promotion and `deploy` promotion are intentionally different
- existing uncommitted changes may belong to the operator; do not revert them without instruction
- detector, feature, and contract docs should stay aligned with real behavior

## Synthetic Discipline

When operating on synthetic data:

- freeze the generator profile before inspecting outcomes
- keep the truth map and manifest with the run
- rerun truth validation after detector or generator changes
- compare claims across more than one profile before strengthening belief

Recommended reference:

- [docs/SYNTHETIC_DATASETS.md](./docs/SYNTHETIC_DATASETS.md)

## Best First Command

For a fresh session, start here:

```bash
.venv/bin/python -m project.research.knowledge.query knobs
```

Then query memory for the target `program_id`, write a small proposal, and issue it with `--plan_only 1`.
