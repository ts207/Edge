# Commands And Entry Points

This file is a reference, not the front door.

Use the repo through four actions:

1. `discover`
2. `package`
3. `validate`
4. `review`

If you are choosing where to start, use [00_START_HERE.md](00_START_HERE.md) and [03_OPERATOR_WORKFLOW.md](03_OPERATOR_WORKFLOW.md) first.

## Preferred front door

### Discover

```bash
edge operator preflight --proposal /abs/path/to/proposal.yaml
edge operator plan --proposal /abs/path/to/proposal.yaml
edge operator run --proposal /abs/path/to/proposal.yaml
```

### Review

```bash
edge operator diagnose --run_id <run_id>
edge operator regime-report --run_id <run_id>
edge operator compare --run_ids <baseline_run,followup_run>
```

### Package

```bash
python -m project.scripts.build_seed_bootstrap_artifacts
python -m project.scripts.build_seed_testing_artifacts
python -m project.scripts.build_seed_empirical_artifacts
python -m project.scripts.build_seed_packaging_artifacts
python -m project.scripts.build_thesis_overlap_artifacts
```

### Validate

```bash
.venv/bin/python -m project.scripts.run_researcher_verification --mode contracts
make minimum-green-gate
```

## Console scripts

Defined in [pyproject.toml](../pyproject.toml):

- `edge`: canonical operator CLI
- `edge-backtest` (alias `backtest`): compatibility alias for the same CLI
- `edge-run-all`: full orchestrator
- `edge-live-engine`: live runtime entry point
- `edge-phase2-discovery`: phase-2 discovery entry point via [project/research/cli/candidate_discovery_cli.py](../project/research/cli/candidate_discovery_cli.py)
- `edge-promote`: promotion entry point via [project/research/cli/promotion_cli.py](../project/research/cli/promotion_cli.py)
- `edge-smoke`: smoke workflow
- `compile-strategy-blueprints`: strategy blueprint compiler via [project/research/compile_strategy_blueprints.py](../project/research/compile_strategy_blueprints.py)
- `build-strategy-candidates`: candidate packager via [project/research/build_strategy_candidates.py](../project/research/build_strategy_candidates.py)
- `ontology-consistency-audit`

## Main Python entry points

- [project/pipelines/run_all.py](../project/pipelines/run_all.py)
- [project/research/cli/candidate_discovery_cli.py](../project/research/cli/candidate_discovery_cli.py)
- [project/research/cli/promotion_cli.py](../project/research/cli/promotion_cli.py)
- [project/research/compile_strategy_blueprints.py](../project/research/compile_strategy_blueprints.py)
- [project/research/build_strategy_candidates.py](../project/research/build_strategy_candidates.py)
- [project/research/agent_io/execute_proposal.py](../project/research/agent_io/execute_proposal.py)
- [project/research/agent_io/issue_proposal.py](../project/research/agent_io/issue_proposal.py)
- [project/research/agent_io/proposal_to_experiment.py](../project/research/agent_io/proposal_to_experiment.py)
- [project/research/knowledge/query.py](../project/research/knowledge/query.py)

## Bootstrap / thesis-packaging scripts

These scripts are maintained entry points for the thesis lifecycle after bounded runs have produced plausible candidates:

- `python -m project.scripts.build_seed_bootstrap_artifacts`
- `python -m project.scripts.build_seed_testing_artifacts`
- `python -m project.scripts.build_seed_empirical_artifacts`
- `python -m project.scripts.build_founding_thesis_evidence`
- `python -m project.scripts.build_seed_packaging_artifacts`
- `python -m project.scripts.build_structural_confirmation_artifacts`
- `python -m project.scripts.build_thesis_overlap_artifacts`
- `./project/scripts/regenerate_artifacts.sh`

## `make` targets

Maintained targets from `make help`:

- `discover-blueprints`: full research pipeline
- `discover-edges`: phase-2 discovery for all events
- `discover-edges-from-raw`: discovery starting from raw data ingest
- `discover-target`: targeted discovery for specific symbols and events
- `discover-concept`: targeted conceptual discovery run
- `discover-hybrid`: specialized hybrid discovery profile
- `run`: ingest, clean, and feature preparation
- `baseline`: full discovery plus profitable strategy packaging
- `golden-workflow`: canonical end-to-end smoke workflow
- `golden-certification`: golden workflow plus certification manifest
- `test-fast`: fast research test profile
- `lint`
- `format-check`
- `format`
- `style`
- `compile`: rust extension compilation
- `clean`: cleans ephemeral files
- `clean-all-data`: wipe all data/lake and reports
- `clean-hygiene`: remove dangling temp files/cache
- `check-hygiene`: fail if temp files violate hygiene
- `governance`
- `benchmark-m0`
- `benchmark-maintenance-smoke`
- `benchmark-maintenance`
- `minimum-green-gate`

## Canonical operator commands

Use these first for normal bounded research:

```bash
edge operator preflight --proposal /abs/path/to/proposal.yaml
edge operator plan --proposal /abs/path/to/proposal.yaml
edge operator run --proposal /abs/path/to/proposal.yaml
```

## Best usage by intent

### I want to inspect prior work

Use:

```bash
.venv/bin/python -m project.research.knowledge.query knobs
.venv/bin/python -m project.research.knowledge.query memory --program_id btc_campaign
.venv/bin/python -m project.research.knowledge.query static --event VOL_SHOCK
```

### I want to translate a proposal without executing it

Use:

```bash
.venv/bin/python -m project.research.agent_io.proposal_to_experiment   --proposal /abs/path/to/proposal.yaml   --registry_root project/configs/registries   --config_path /tmp/experiment.yaml   --overrides_path /tmp/run_all_overrides.json
```

### I want to inspect a full plan first

Preferred command:

```bash
edge operator plan --proposal /abs/path/to/proposal.yaml
```

Equivalent internal command:

```bash
.venv/bin/python -m project.research.agent_io.execute_proposal   --proposal /abs/path/to/proposal.yaml   --run_id my_run   --registry_root project/configs/registries   --out_dir data/artifacts/experiments/my_program/proposals/my_run   --plan_only 1
```

### I want memory bookkeeping with proposal issuance

Preferred command:

```bash
edge operator run --proposal /abs/path/to/proposal.yaml
```

Equivalent internal command:

```bash
.venv/bin/python -m project.research.agent_io.issue_proposal   --proposal /abs/path/to/proposal.yaml   --registry_root project/configs/registries   --plan_only 1
```

### I want to bootstrap or refresh the thesis store

Use the bootstrap scripts rather than ad hoc notebooks:

```bash
python -m project.scripts.build_seed_bootstrap_artifacts
python -m project.scripts.build_seed_testing_artifacts
python -m project.scripts.build_seed_empirical_artifacts
python -m project.scripts.build_seed_packaging_artifacts
python -m project.scripts.build_thesis_overlap_artifacts
```

Use the evidence and structural confirmation builders only when you are adding or refreshing empirical support for specific theses.

### I want a narrow direct run

Use `run_all` directly when you already know the slice:

```bash
.venv/bin/python -m project.pipelines.run_all   --run_id btc_vol_shock_slice   --symbols BTCUSDT   --start 2022-11-01   --end 2022-12-31   --mode research   --phase2_event_type VOL_SHOCK   --phase2_gate_profile discovery
```

## Command selection rule

Prefer:

- `knowledge.query` for reading prior state
- proposal tools for disciplined research issuance
- bootstrap scripts for thesis inventory, evidence, packaging, and overlap artifacts
- `run_all` for direct bounded execution
- `make` targets for maintained common workflows

Do not default to ad hoc Python one-offs when a maintained entry point already exists.

## Internal / maintenance surfaces

These still exist, but they should not be the first surface an operator learns:

- direct proposal compiler modules
- raw `run_all` orchestration entry points
- broad `make` targets used as workflow bundles
- migration utilities
- low-level loader and sidecar scripts
