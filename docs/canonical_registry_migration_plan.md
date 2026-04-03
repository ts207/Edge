# Canonical Registry Plan

## Current State

The canonical event registry migration is complete for authored event data.

- `spec/events/*.yaml` is now the authored source for event identity, governance, runtime metadata, local semantics, and event-local arbitration rules.
- `spec/states/state_registry.yaml` is now the authored source for state semantics, runtime metadata, and context-dimension mappings.
- `spec/templates/event_template_registry.yaml` is now the authored source for template semantics, operator metadata, and filter-template policy.
- `spec/theses/thesis_registry.yaml` is now the authored source for canonical thesis clauses in the founding/bootstrap lane.
- `spec/events/event_registry_unified.yaml` is rebuilt from event specs plus regime-level defaults and template policy.
- `spec/domain/domain_graph.yaml` is rebuilt from the compiled registry and is now the preferred read artifact for `project/domain/*` consumers.
- `project/configs/registries/states.yaml` and `spec/grammar/state_registry.yaml` are rebuilt from the canonical state registry.
- `project/configs/registries/templates.yaml` and `spec/ontology/templates/template_registry.yaml` are rebuilt from the canonical template registry.
- `project/configs/registries/events.yaml` is generated from compiled registry metadata.
- `spec/events/event_ontology_mapping.yaml` is generated from the compiled registry.
- `spec/events/event_contract_overrides.yaml` is generated from compiled event contracts.
- `spec/events/canonical_event_registry.yaml` is generated as a legacy proxy-tier compatibility shim.

## Policy Boundaries

These files remain authored because they are system-level policy rather than event authorship:

- `spec/events/precedence.yaml`
  - `family_precedence` remains the authored family-level policy.
  - `event_overrides` should stay empty; event-level precedence now lives in event specs.
- `spec/events/compatibility.yaml`
  - `composite_events` remains the authored system-level policy.
  - `suppression_rules` should stay empty; event-level suppression now lives in event specs.
- `spec/events/regime_routing.yaml`
  - regime-level routing policy remains centralized.

## Operating Rules

1. Author event changes in `spec/events/<EVENT>.yaml`.
2. Rebuild derived artifacts with:
   - `python3 project/scripts/build_unified_event_registry.py`
   - `python3 project/scripts/build_state_registry_sidecars.py`
   - `python3 project/scripts/build_template_registry_sidecars.py`
   - `python3 project/scripts/build_domain_graph.py`
   - `python3 project/scripts/build_runtime_event_registry.py`
   - `python3 project/scripts/build_canonical_registry_sidecars.py`
3. Regenerate docs/artifacts when registry changes affect generated references.

## Stop Conditions

The migration should be treated as regressed if any of the following becomes true:

- A behavior-changing event edit requires changing `event_ontology_mapping.yaml`.
- A behavior-changing event edit requires changing `event_contract_overrides.yaml`.
- Runtime detector wiring is edited in `project/configs/registries/events.yaml` instead of the event spec.
- State runtime wiring is edited in `project/configs/registries/states.yaml` instead of `spec/states/state_registry.yaml`.
- Context mappings are edited in `spec/grammar/state_registry.yaml` instead of `spec/states/state_registry.yaml`.
- Template semantics are edited in `project/configs/registries/templates.yaml` or `spec/ontology/templates/template_registry.yaml` instead of `spec/templates/event_template_registry.yaml`.
- Thesis clause semantics are edited only in packaged `promoted_theses.json` output instead of `spec/theses/thesis_registry.yaml`.
- Event-specific precedence is added back to `spec/events/precedence.yaml`.
- Event-specific suppression is added back to `spec/events/compatibility.yaml`.

## Remaining Cleanup

The remaining work is optional cleanup, not structural migration:

- remove redundant flat legacy fields from event specs once all downstream readers have been audited,
- add generated compatibility / precedence matrix docs if operator visibility is useful,
- retire any remaining legacy-family control logic outside compatibility joins.
