# Repository Map

## Directory Overview

```
Edge/
├── project/                  Core Python package
│   ├── core/                 Shared utilities, config, validation, timeframes
│   ├── io/                   Parquet/CSV I/O, lake path resolution
│   ├── contracts/            Pipeline stage registry and artifact contracts
│   ├── domain/               Domain models, compiled registry, hypothesis types
│   ├── events/               Event specs, registry, episode models
│   ├── features/             Feature derivation (Binance, Bybit derivatives)
│   ├── engine/               Backtest engine, PnL, execution state
│   ├── live/                 Live trading runtime (REST/WS clients, runner, OMS)
│   ├── pipelines/            Pipeline stages, planner, clean/ingest/feature scripts
│   ├── research/             Discovery, promotion, phase2 search engine, services
│   ├── portfolio/            Incubation ledger, thesis overlap
│   ├── runtime/              Normalized event stream
│   ├── strategy/             Strategy DSL, templates, executable specs
│   ├── specs/                Manifest, gates, ontology
│   ├── operator/             Preflight, lint, explain commands
│   └── scripts/              Entry-point scripts (run_live_engine, etc.)
├── spec/                     YAML specifications
│   ├── proposals/            Sprint proposals (StructuredHypothesis format)
│   ├── campaigns/            Campaign matrix definitions
│   ├── gates.yaml            Phase 2 promotion gate parameters
│   └── events/               Event registry and regime routing
├── docs/                     Documentation and generated reports
│   └── generated/            Auto-generated metrics, catalogs, summaries
└── plugins/                  Plugin extensions (edge-agents, edge-plugins)
```

## Discovery Pipeline

The canonical research flow uses a planner-owned stage graph:

```
ingest → build_cleaned → build_features → build_market_context
      → phase2_search_engine → export_edge_candidates → promote_candidates
```

`phase2_search_engine` is the **canonical planner-owned discovery stage** for
generating and evaluating hypothesis candidates. It replaced the legacy
`phase2_candidate_discovery.py` surface and is the single authoritative entry
point for Phase 2 discovery. All new proposals must route through this stage.

## Live Runtime Layer

The Sprint 7 live runtime uses a supervised deployment lifecycle:

```
ThesisStore → DeploymentGate → KillSwitchManager → RiskEnforcer → OMS
```

Only `live_enabled` theses may execute trades. Deployment progresses through:
`promoted → paper_enabled → paper_approved → live_eligible → live_enabled`

## Venue Support

- **Primary**: Bybit V5 Linear (perpetual derivatives)
- **Legacy**: Binance UM Futures (supported via explicit `venue="binance"`)

Raw data is resolved via `raw_dataset_dir_candidates(venue=...)`.
Default venue is `"bybit"`. Binance callers must pass `venue="binance"` explicitly.
