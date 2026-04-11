# Architecture Surface Inventory

Tracks the canonical, transitional, and removed surfaces in the Edge codebase.
Updated as part of each sprint's platformization review.

---

## Canonical Surfaces

These surfaces are stable, contract-enforced, and safe to depend on.

| Surface | Location | Description |
|---|---|---|
| Pipeline registry | `project/contracts/pipeline_registry.py` | Stage family + artifact DAG contracts |
| Pipeline planner | `project/pipelines/planner.py` | Builds stage plan from proposal |
| Phase 2 search engine | `project/research/phase2_search_engine.py` | Canonical planner-owned discovery stage |
| Promotion service | `project/research/services/promotion_service.py` | Candidate promotion pipeline |
| Live runner | `project/live/runner.py` | Live trading engine with risk/decay/OMS |
| Strategy DSL | `project.strategy.dsl` | Strategy spec DSL and schema |
| Normalized event stream | `project/runtime/normalized_event.py` | Runtime event normalization |
| Gate spec | `spec/gates.yaml` | Phase 2 and confirmatory gate parameters |
| Event registry | `spec/events/event_registry_unified.yaml` | Canonical event definitions |

---

## Transitional Surfaces

These surfaces are functional but scheduled for migration or consolidation.

| Surface | Location | Status | Target |
|---|---|---|---|
| Binance ingest | `project/pipelines/ingest/ingest_binance_*.py` | Active, secondary venue | Bybit-first migration |
| `build_cleaned_bars.py` | `project/pipelines/clean/` | Active, Binance-era naming | To be venue-agnostic |
| Vendorless raw paths | `data/lake/raw/{market}/...` | Fallback only | Migrate to vendor-qualified |

---

## Removed Surfaces

These surfaces have been removed and must not be referenced in new code.

| Surface | Removed in | Replacement |
|---|---|---|
| Legacy CLI `pipeline run-all` | Cleanup batch | `discover run` or explicit Make wrappers |
| `project/pipelines/research` wrapper package | Cleanup batch | Canonical `project/research` modules and `project/research/cli` |
| `phase2_candidate_discovery.py` | Sprint 6 | `phase2_search_engine.py` |
| `load_latest_theses` runtime flag | Sprint 7 | `thesis_path` or `thesis_run_id` |
| Legacy proposal format (`trigger_space` / `horizons_bars`) | Sprint 6.6 | StructuredHypothesis format |

---

## Cross-Boundary Import Policy

The architectural DAG is enforced by `test_dependency_matrix`. Key rules:

- `project.core` / `project.io` — no upward imports
- `project.domain` — may import core/specs/events only
- `project.live` — may import domain, research, engine, portfolio
- `project.portfolio` — may import research for artifact utilities
- `project.research` — may import most layers; is the top-level research hub
- `project.pipelines` — top layer; may import all above
