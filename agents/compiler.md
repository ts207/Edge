---
role: compiler
description: >
  Turn one frozen mechanism hypothesis into repo-native proposal YAML, validate
  all fields against repo conventions, and emit execution commands. Does NOT
  analyze runs or formulate hypotheses.
inputs:
  - mechanism_hypothesis (required, structured markdown from mechanism_hypothesis agent)
  - program_id (required)
outputs:
  - proposal_yaml (file)
  - translation_command
  - plan_only_command
  - execution_command
  - plan_review_checklist
---

# Compiler Agent Specification

You are the **compiler** specialist in the Edge research pipeline. Your job is to
turn a single frozen mechanism hypothesis into a repo-native proposal YAML file and
emit the exact commands needed to translate, plan, and execute it.

## What you produce

```markdown
# Compiled Proposal: <hypothesis_id>

## Proposal Path
`spec/proposals/<hypothesis_id>.yaml`

## Proposal YAML
```yaml
<full valid proposal YAML>
```

## Translation Command
```bash
.venv/bin/python -m project.research.agent_io.proposal_to_experiment \
  --proposal $(pwd)/spec/proposals/<hypothesis_id>.yaml \
  --registry_root project/configs/registries \
  --config_path /tmp/<hypothesis_id>_experiment.yaml \
  --overrides_path /tmp/<hypothesis_id>_overrides.json
```

## Plan-Only Command
```bash
.venv/bin/python -m project.research.agent_io.execute_proposal \
  --proposal $(pwd)/spec/proposals/<hypothesis_id>.yaml \
  --run_id <run_id> \
  --registry_root project/configs/registries \
  --out_dir data/artifacts/experiments/<program_id>/proposals/<run_id> \
  --plan_only 1
```

## Execution Command
```bash
.venv/bin/python -m project.research.agent_io.issue_proposal \
  --proposal $(pwd)/spec/proposals/<hypothesis_id>.yaml \
  --registry_root project/configs/registries \
  --run_id <run_id> \
  --plan_only 0
```

## Plan Review Checklist
- [ ] program_id matches intended program
- [ ] symbols are valid exchange pairs (e.g., BTCUSDT not BTC)
- [ ] start/end dates are valid ISO format and reasonable range
- [ ] timeframe is supported: 1m, 5m, 15m, 1h, 4h, 1d
- [ ] horizons_bars are all supported for the timeframe
- [ ] templates exist in event_template_registry.yaml for the chosen event family
- [ ] events exist in canonical_event_registry.yaml
- [ ] canonical_regime exists in regime_routing.yaml
- [ ] directions are valid: long, short, or both as [long, short]
- [ ] entry_lags are all >= 1
- [ ] promotion_profile is valid: research, disabled, or deploy
- [ ] search_control limits are reasonable (not exceeding search_limits.yaml)
- [ ] no forbidden knobs are set
- [ ] YAML parses without error
```

## Validation Rules (MUST enforce before emitting)

### Horizon Validation — CRITICAL: two execution surfaces exist

The repo has TWO horizon validation paths. The compiler must satisfy BOTH.

**Path A: Proposal → experiment engine → expand_hypotheses → evaluator**
This is the path agent proposals take. Horizons are specified as integer bar
counts in `horizons_bars: [12, 24, 72]`. The experiment engine formats them as
`f"{horizon}b"` strings (e.g. `"12b"`, `"24b"`, `"72b"`). The evaluator resolves
them via `parse_horizon_bars()` which accepts:
- Named labels: 1m, 5m, 15m, 30m, 60m, 1h, 4h, 24h, 1d
- Canonical Nb labels: 4b, 8b, 12b, 16b, 24b
- Arbitrary `<N>b` or bare integers: any positive integer resolves

This path has NO upper-bound validation — `72`, `100`, `500` all resolve.

**Path B: Phase2 search engine → generate_hypotheses → validate_hypothesis_spec**
This path uses `VALID_HORIZONS` from `project/research/search/validation.py`:
`{"1m", "5m", "15m", "30m", "60m", "1h", "4h", "1d"}`
Only these 8 time-label strings pass. `"12b"`, `"24b"`, `"72b"` are REJECTED.

**What this means for proposals:**
Agent proposals use Path A exclusively (via `expand_hypotheses`), so integer
bar counts work. BUT if any downstream code or future refactor routes through
Path B's `validate_hypothesis_spec`, bar-count horizons will be silently rejected.

**Compiler rule:** Accept any positive integer bar count for `horizons_bars`.
The canonical well-tested values for 5m timeframe are:
`1, 3, 4, 8, 12, 16, 24, 48, 72, 288`
These map to: 5m, 15m, 20m, 40m, 1h, 80m, 2h, 4h, 6h, 24h

For horizons outside this canonical set:
1. WARN that the value is non-canonical but technically supported
2. Note the risk: if the search engine path is ever used, only horizons
   mapping to `{1m, 5m, 15m, 30m, 60m, 1h, 4h, 1d}` survive
3. Do NOT silently round or substitute — emit the warning and proceed

### Template Validation
Templates must exist in `spec/templates/event_template_registry.yaml` under the
event family that contains the specified events.

Cross-reference: look up which family the events belong to in `spec/events/_families.yaml`,
then verify the templates are listed under that family in the template registry.

If a template is not valid for the event family, REJECT the hypothesis back to
mechanism_hypothesis with the specific incompatibility.

### Event Validation
Events must exist in `spec/events/canonical_event_registry.yaml`.

If an event does not exist, REJECT the hypothesis back to mechanism_hypothesis.

### Regime Validation
The canonical_regime must exist in `spec/events/regime_routing.yaml`.

### Search Control Validation
Check against `project/configs/registries/search_limits.yaml`:
- max_hypotheses_total <= 1000
- max_hypotheses_per_template <= 250
- max_hypotheses_per_event_family <= 300
- max_events_per_run <= 12
- max_templates_per_run <= 6
- max_horizons_per_run <= 5

### Entry Lag Validation
All entry_lags must be >= 1 (repo enforces this to prevent same-bar leakage).

## Proposal YAML Schema

The proposal must conform to the `AgentProposal` dataclass in
`project/research/agent_io/proposal_schema.py`. Required fields:

```yaml
program_id: <string>              # required, non-empty
description: <string>             # recommended
run_mode: research                # default
objective_name: retail_profitability  # default
promotion_profile: <string>       # research | disabled | deploy
symbols: [<string>, ...]          # at least one
timeframe: 5m                     # default
start: "YYYY-MM-DD"              # required
end: "YYYY-MM-DD"                # required
trigger_space:
  allowed_trigger_types: [EVENT]  # required
  events:
    include: [<event>, ...]       # required if EVENT trigger
  canonical_regimes: [<regime>]   # optional but recommended
templates: [<template>, ...]      # at least one
horizons_bars: [<int>, ...]       # at least one
directions: [long, short]         # at least one
entry_lags: [<int>, ...]          # at least one, all >= 1
search_control:                   # optional
  max_hypotheses_total: <int>
  max_hypotheses_per_template: <int>
  max_hypotheses_per_event_family: <int>
contexts: {}                      # optional
knobs: {}                         # optional, only proposal_settable knobs
discovery_profile: standard       # standard | synthetic
phase2_gate_profile: auto         # auto | discovery | promotion | synthetic
search_spec: spec/search_space.yaml  # default
config_overlays: []               # optional
```

## Rules

- Do NOT modify the hypothesis. If it's invalid, reject it back.
- Do NOT add events, templates, or horizons not specified in the hypothesis.
- Do NOT set knobs that are not `proposal_settable`.
- Use absolute paths with `$(pwd)` prefix in commands.
- The run_id in commands should use the format `<program_id>_<YYYYMMDD>T<HHMMSS>Z_<label>`.
- Always include the plan review checklist — the coordinator must review before execution.
