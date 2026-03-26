# Architecture Surface Inventory

This document describes the canonical and transitional surfaces in the Edge system.

## Canonical Surfaces

Canonical surfaces are stable, production-ready modules that form the core of the system.

### Core Surfaces
- `project.core` - Core data structures and utilities
- `project.events` - Event detection and processing
- `project.features` - Feature engineering
- `project.domain` - Domain models
- `project.specs` - Specification definitions
- `project.spec_registry` - Specification registry
- `project.strategy` - Strategy definitions
- `project.engine` - Execution engine
- `project.portfolio` - Portfolio management
- `project.research` - Research services

### Transitional Surfaces

Transitional surfaces are modules in the process of being stabilized.

- `project.strategy.dsl` - Strategy DSL interpreter (transitional)
- `project.strategy_templates` - Strategy templates (transitional)

## Removed Surfaces

Previously existing surfaces that have been removed or consolidated:

- Legacy surface 1 (removed in v2.0)
- Legacy surface 2 (merged into core)

## Surface Dependencies

```
project.core -> [project.spec_registry, project.artifacts, project.specs, project.io]
project.events -> [project.core, project.features, project.specs, project.spec_registry, ...]
project.research -> [project.core, project.specs, project.events, ...]
```
