# Research Concepts and Hypotheses

## Primary Research Primitive

The core primitive is a bounded hypothesis carried by proposal and experiment config, not a detector in isolation.

A practical hypothesis surface includes:

- trigger space
- template include set
- contexts include set
- horizons
- directions
- entry lags
- symbol universe
- timeframe
- objective
- promotion profile

## Proposal Shape

In the current implementation, proposal translation produces:

- instrument scope
- trigger space
- template include rules
- context include rules
- evaluation grids
- search-control limits
- promotion settings
- artifact settings

This is done by `project/research/agent_io/proposal_to_experiment.py`.

## Trigger Space

Trigger space is not just a single event ID. It may imply:

- event family / event set
- executable event subset
- context restrictions
- search constraints

Because ontology and regime routing are now explicit repository surfaces, trigger documentation must stay aligned with generated ontology outputs.

## Templates and Legality

Template use is governed by registry/spec rules. Do not assume every template is legal for every event or regime.

Relevant layers:

- `spec/templates/`
- `spec/ontology/templates/`
- `project/configs/registries/templates.yaml`
- generated ontology / routing docs

## Contexts and States

Contexts are not generic tags. They are connected to state definitions, context-state maps, and search planning requirements.

Relevant layers:

- `spec/states/`
- `spec/ontology/states/`
- `project/configs/registries/contexts.yaml`
- `project/configs/registries/states.yaml`
- domain registry helpers in `project/domain/`

## Search Control

Proposal translation uses search limits to keep discovery bounded.

Current search-control defaults are loaded from:

- `project/configs/registries/search_limits.yaml`

Important concepts:

- total hypothesis cap
- per-template cap
- per-event-family cap
- random seed

This is part of the repo's anti-scope-creep discipline.

## Evaluation Layers

Every material research output should be read on three layers:

1. mechanical integrity
2. statistical quality
3. deployment relevance

Typical artifacts and metrics involved:

- candidate counts and split adequacy
- q-values
- after-cost expectancy
- stressed costs
- sign consistency / stability
- negative controls
- promotion evidence bundle completeness

## Promotion as a Gate

Promotion is not a post-processing vanity step.

It answers:

- is the candidate structurally supported?
- is the statistical evidence acceptable?
- is the cost-adjusted behavior still viable?
- does the evidence bundle justify keeping it in the promoted set?

The promotion layer is implemented in research services and promotion pipelines, not only in reports.

## Memory and Follow-Up

The operator flow is designed to learn across runs.

Research memory surfaces under `project/research/knowledge/` are used to:

- retrieve prior proposals
- avoid repeated near-duplicate work
- capture outcomes
- support follow-up exploration and repair

## Synthetic Research

Synthetic workflows are intended for:

- detector truth recovery
- infrastructure validation
- calibration of discovery and promotion behavior
- regime stress

Synthetic wins are not live-market proof. The documentation should not blur that line.

## Good Research Questions

Good questions in this repository are:

- narrow
- attributable
- cost-aware
- compatible with explicit event/template/context structure
- evaluable through the existing artifact and promotion system

Bad questions are broad sweeps over unrelated trigger families with weak attribution.
