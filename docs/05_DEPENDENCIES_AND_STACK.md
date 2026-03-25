# Edge — Dependencies & Technical Stack

## Python Version Requirement

**Python 3.11+** (strict — typed union syntax, match statements, and other 3.11 features are used throughout).

---

## Production Dependencies (`pyproject.toml`)

| Package | Version | Role |
|---|---|---|
| `numpy` | 1.26.0 | Numerical arrays, vectorized operations |
| `numba` | 0.59.1 | JIT compilation for performance-critical detector math |
| `pandas` | 2.2.2 | Time-series data manipulation, the primary data structure throughout |
| `pyarrow` | 17.0.0 | Parquet I/O (all artifact files are `.parquet`) |
| `requests` | 2.32.4 | HTTP client (Binance REST API for historical data) |
| `PyYAML` | 6.0.1 | Spec file loading from `spec/` YAML definitions |
| `pandera` | 0.19.3 | DataFrame schema validation and contract enforcement |
| `scikit-learn` | 1.5.0 | ML utilities (random forest features, clustering) |
| `scipy` | 1.13.1 | Statistical tests (bootstrap, KS, t-test) |
| `statsmodels` | 0.14.2 | Econometric models, regression diagnostics |
| `websockets` | latest | Binance WebSocket streaming (live engine) |
| `pydantic` | 2.8.0 | Data validation for all schemas and DSL models |
| `aiohttp` | 3.9.5 | Async HTTP for live data fetching |
| `networkx` | latest | Dependency graph construction (stage DAG) |

---

## Optional Dependencies

| Group | Package | Role |
|---|---|---|
| `[dev]` | `pyright==1.1.350` | Static type checking |

### Installation

```bash
# Standard research
pip install -e .
```

---

## Development Dependencies (`requirements-dev.txt`)

| Package | Version | Role |
|---|---|---|
| `ruff` | 0.15.4 | Linter and formatter |
| `pytest` | 8.2.2 | Test runner |

---

## Tooling

### Linting & Formatting

- **Ruff** — linter + formatter, configured in `pyproject.toml`:
  - `line-length: 100`
  - `target-version: py311`
  - Rules: `E`, `F`, `I`, `W`, `E9`, `F63`, `F7`, `F82`
  - Excluded: `data/`, `.venv/`, `MEMORY/`, `.agents/`

### Type Checking

- **Pyright** v1.1.350 — run on `project/` package. Checked in Tier 1 CI gate.

### Testing

- **pytest** 8.2.2
  - Config in `pytest.ini`
  - 407 test files
  - Markers: `@pytest.mark.slow` (excluded in fast profile)
  - `make test` — full suite
  - `make test-fast` — excludes slow tests

### Build System

- **setuptools** ≥ 69 + **wheel**
- Package discovery: `where=["."]`, `include=["project*"]`

---

## Data Layer

### Storage Format

All pipeline artifacts are stored as **Parquet files** (via PyArrow). No SQL database.

### Data Root

Configured at runtime via `project.core.config.get_data_root()`. Default: `data/` directory at project root.

```
data/
└── lake/          Runtime outputs (not version controlled)
    ├── raw/       Ingested data (ohlcv, funding, OI, liquidations)
    ├── clean/     Cleaned bars
    ├── features/  Computed feature frames
    └── reports/   Pipeline output artifacts
```

### Data Sources

All market data ingested from **Binance** via:

- REST API (historical OHLCV, funding rates, OI, liquidations)
- WebSocket (live klines at 1m and 5m, book ticker)

Supported instruments:

- Binance USDⓈ-M Perpetuals (UM)
- Binance Spot

Supported timeframes: `1m`, `5m` (primary research timeframes). Additional timeframes configurable.

---

## CI/CD Infrastructure

### GitHub Actions Workflows

| Workflow | File | Trigger | Role |
|---|---|---|---|
| Tier 1 — Structural Fast Gate | `tier1.yml` | push/PR to main | Compile, architecture tests, spec validation, drift checks, fast regressions, Pyright |
| Tier 2 | `tier2.yml` | Scheduled/manual | Broader test suite |
| Tier 3 | `tier3.yml` | Manual/release | Full suite + golden workflow |
| Codex PR Review | `codex_pr_review.yml` | PR | Automated code review |
| Gemini Dispatch | `gemini-dispatch.yml` | Various | AI-assisted dispatch |
| Gemini Triage | `gemini-triage.yml` | Issues | Automated issue triage |
| Gemini Scheduled Triage | `gemini-scheduled-triage.yml` | Cron | Periodic triage |
| Gemini Invoke | `gemini-invoke.yml` | Manual | Manual AI invocation |
| Gemini Review | `gemini-review.yml` | PR | AI code review |

### Codex Configuration (`.codex/`)

| File | Purpose |
|---|---|
| `config.toml` | Codex agent configuration |
| `setup.sh` | Environment setup for Codex |
| `maintenance.sh` | Maintenance commands for Codex |
| `rules/default.rules` | Default behavior rules for Codex |

---

## Deployment

### Systemd Services

Three service templates in `deploy/systemd/`:

| Service | Config | Purpose |
|---|---|---|
| `edge-live-engine.service` | `golden_certification.yaml` | Generic template |
| `edge-live-engine-paper.service` | Paper trading env | Paper mode |
| `edge-live-engine-production.service` | Production env | Production mode |

**Service configuration:**

```ini
[Service]
WorkingDirectory=/opt/edge
ExecStart=/opt/edge/.venv/bin/edge-live-engine \
  --config /opt/edge/project/configs/golden_certification.yaml \
  --snapshot_path /var/lib/edge/live_state.json
Restart=on-failure
RestartSec=5
```

### Environment Templates

`deploy/env/` contains `.env.example` files specifying required environment variables for paper and production modes.

---

## Constraints Lock

`constraints.lock` — records pinned dependency constraints for reproducible environments. Checked in to ensure research runs are reproducible across machines.

---

## Key Configuration Files

| File | Purpose |
|---|---|
| `pyproject.toml` | Package metadata, dependencies, entry points, Ruff config |
| `pytest.ini` | Pytest configuration |
| `pyrightconfig.json` | Pyright static analysis config |
| `constraints.lock` | Pinned dependency constraints |
| `spec/global_defaults.yaml` | Default horizons, templates, conditioning dimensions |
| `spec/gates.yaml` | Promotion gate thresholds |
| `spec/cost_model.yaml` | Execution cost parameters |
| `spec/blueprint_policies.yaml` | Stop/target/sizing policy defaults |
| `spec/runtime/lanes.yaml` | Processing lane definitions |
| `spec/runtime/firewall.yaml` | Alpha/execution firewall rules |
| `project/configs/golden_certification.yaml` | Golden certification run config |
| `project/configs/fees.yaml` | Authoritative fee config |
| `project/configs/registries/` | Experiment and type registries |
| `project/configs/venues/` | Venue-specific configs |
