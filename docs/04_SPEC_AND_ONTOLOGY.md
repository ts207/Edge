# Spec and Ontology Reference

## Two Declarative Layers

The repository has both:

- `spec/`
  - static domain policy and research-spec layer
- `project/configs/`
  - runnable configuration layer

Older docs often collapsed these into one concept. That is incorrect.

## `spec/` Tree

Current top-level `spec/` areas:

- `benchmarks/`
- `concepts/`
- `events/`
- `features/`
- `grammar/`
- `hypotheses/`
- `multiplicity/`
- `objectives/`
- `ontology/`
- `proposals/`
- `runtime/`
- `search/`
- `states/`
- `strategies/`
- `templates/`

Interpretation:

- `events/`, `states/`, `templates/`, `ontology/`, `multiplicity/`, `grammar/`
  - market-language and legality layer
- `objectives/`, `runtime/`, `benchmarks/`, `search/`
  - execution policy and gating layer
- `proposals/`, `hypotheses/`, `concepts/`
  - research expression layer

## `project/configs/` Layer

Current runtime config areas include:

- workflow configs such as `golden_workflow.yaml`
- certification configs such as `golden_certification.yaml`
- live configs such as `live_paper.yaml` and `live_production.yaml`
- synthetic suite configs
- `retail_profiles.yaml`
- `registries/`
  - contexts
  - detectors
  - events
  - features
  - search limits
  - states
  - templates

Use `project/configs/registries/` when documenting current proposal translation and validated experiment planning. Use `spec/` when documenting the deeper domain and policy layer.

## Event Ontology

The event system now has an explicit mapping and audit layer. Do not describe it only as "a list of detectors."

There are multiple related concepts:

- raw event specs
- canonical event / regime mapping
- context tags
- composite events
- strategy constructs
- executable event subset
- routing profile for regimes

These are emitted into generated artifacts, which are the correct inventory surfaces:

- `docs/generated/event_ontology_mapping.md`
- `docs/generated/canonical_to_raw_event_map.md`
- `docs/generated/context_tag_catalog.md`
- `docs/generated/composite_event_catalog.md`
- `docs/generated/strategy_construct_catalog.md`
- `docs/generated/event_ontology_audit.md`
- `docs/generated/regime_routing_audit.md`

## Code Surfaces for Ontology

Important implementation files:

- `project/events/event_specs.py`
- `project/events/ontology_mapping.py`
- `project/events/ontology_deconfliction.py`
- `project/events/config.py`
- `project/research/regime_routing.py`
- `project/spec_validation/ontology.py`

Important generation / audit scripts:

- `project/scripts/build_unified_event_registry.py`
- `project/scripts/build_event_ontology_artifacts.py`
- `project/scripts/event_ontology_audit.py`
- `project/scripts/regime_routing_audit.py`
- `project/scripts/ontology_consistency_audit.py`

## Proposal Translation and Registry Usage

Proposal translation uses `project/configs/registries/`, not the raw `spec/` tree directly.

The proposal path is:

1. load proposal schema
2. resolve defaults and registry constraints
3. emit experiment config
4. validate plan
5. emit `run_all` overrides

Relevant code:

- `project/research/agent_io/proposal_schema.py`
- `project/research/agent_io/proposal_to_experiment.py`
- `project/research/agent_io/execute_proposal.py`
- `project/research/agent_io/issue_proposal.py`

## Spec Validation

The validation CLI currently runs:

- ontology validation
- grammar validation
- placeholder traversal over search specs

Entry point:

```bash
python -m project.spec_validation.cli
```

This is part of CI tier 1 and should be treated as a structural gate, not a documentation-only tool.

## Practical Rule

When documenting current legal event/template/context behavior:

- use generated docs for live inventory
- use `spec/` for policy intent
- use `project/configs/registries/` for proposal/runtime constraints
- use code when prose and generated inventory diverge
