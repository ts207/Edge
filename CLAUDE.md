# Research Operator Guide

This repository is designed for disciplined market research by an autonomous or semi-autonomous operator.

The operator should behave like a conservative research lead:

- start narrow
- trust artifacts over impressions
- separate mechanical, statistical, and deployment conclusions
- treat promotion as a gate
- leave behind a clear next action after every meaningful run

When operating via GitHub Actions, the agent follows the protocols defined in `.github/commands/` and is designed to provide consistent, auditable research outcomes.

## Operating Objective

`observe -> retrieve memory -> define objective -> propose -> plan -> execute -> evaluate -> reflect -> adapt`

Optimize for: reproducibility, post-cost robustness, contract cleanliness, narrow attribution, decision quality.

## Key Commands

```bash
# Query prior state before anything else
.venv/bin/python -m project.research.knowledge.query knobs
.venv/bin/python -m project.research.knowledge.query memory --program_id btc_campaign
.venv/bin/python -m project.research.knowledge.query static --event BASIS_DISLOC

# Translate proposal to repo-native config
.venv/bin/python -m project.research.agent_io.proposal_to_experiment \
  --proposal /abs/path/to/proposal.yaml \
  --registry_root project/configs/registries \
  --config_path /tmp/experiment.yaml \
  --overrides_path /tmp/run_all_overrides.json

# Plan before executing (always)
.venv/bin/python -m project.research.agent_io.issue_proposal \
  --proposal /abs/path/to/proposal.yaml \
  --registry_root project/configs/registries \
  --plan_only 1
```

Full workflow: → [docs/03_OPERATOR_WORKFLOW.md](/home/irene/Edge/docs/03_OPERATOR_WORKFLOW.md)

Full command reference: → [docs/04_COMMANDS_AND_ENTRY_POINTS.md](/home/irene/Edge/docs/04_COMMANDS_AND_ENTRY_POINTS.md)

## Default Policy

Prefer one event family, one template family, one primary context family, one symbol, one date range per run.

Avoid broad search, reruns that differ only in wording, and treating synthetic wins as live-market evidence.

## Evaluation Discipline

Every meaningful run must be evaluated on three layers:

1. mechanical integrity
2. statistical quality
3. deployment relevance

Check: split counts, `q_value`, post-cost expectancy, stressed expectancy, promotion eligibility, artifact completeness, warning surface.

## Artifact Rule

Artifacts are the source of truth. Read in order:

1. top-level run manifest
2. stage manifests
3. stage logs
4. report artifacts
5. generated diagnostics

If those disagree, the disagreement is a first-class finding.

## Key Contracts And Rules

- Agent operating contract: → [docs/AGENT_CONTRACT.md](/home/irene/Edge/docs/AGENT_CONTRACT.md)
- Verification commands: → [docs/VERIFICATION.md](/home/irene/Edge/docs/VERIFICATION.md)
- Research backlog: → [docs/RESEARCH_BACKLOG.md](/home/irene/Edge/docs/RESEARCH_BACKLOG.md)
- Operator templates: → [docs/templates/](/home/irene/Edge/docs/templates/)

## Repository Landmarks

- `project/pipelines/run_all.py` — end-to-end orchestration
- `project/contracts/pipeline_registry.py` — stage and artifact contract source
- `project/research/knowledge/` — memory, static knowledge, reflection
- `project/research/agent_io/` — proposal validation, translation, execution
- `project/research/services/` — discovery, promotion, comparison, diagnostics
- `project/events/detectors/catalog.py` — detector loading surface
- `project/features/` — shared feature, regime, and guard helpers
- `docs/README.md` — maintained docs index
