# Worked Example: Engine Backtest

This document covers two concrete engine-oriented workflows:

1. **A direct engine run** — load a manually crafted blueprint and execute it against bars/features
2. **Compile then backtest** — take research candidates, compile them to blueprints, and backtest the result

---

## Prerequisite

The market-data `run_id` must already have cleaned bars and features.

The engine reads from:

- `data/lake/runs/<run_id>/cleaned/...`
- `data/lake/runs/<run_id>/features/...`

If you do not have these, run the research pipeline first:

```bash
.venv/bin/python -m project.pipelines.run_all \
  --run_id <run_id> \
  --symbols BTCUSDT \
  --start 2022-11-01 \
  --end 2022-12-31 \
  --mode research
```

---

## Workflow A: Direct Engine Run

### Goal

Execute a strategy or DSL blueprint against bars/features and get ledger/PnL artifacts.

### Step 1. Prepare a blueprint JSON

Minimal example file: `/tmp/minimal_blueprint.json`

```json
{
  "id": "bp_test",
  "run_id": "single_hypothesis_btc_basis_disloc_run",
  "event_type": "BASIS_DISLOC",
  "candidate_id": "cand_1",
  "symbol_scope": {
    "mode": "single_symbol",
    "symbols": ["BTCUSDT"],
    "candidate_symbol": "BTCUSDT"
  },
  "direction": "short",
  "entry": {
    "triggers": ["basis_disloc_event"],
    "conditions": ["all"],
    "confirmations": [],
    "delay_bars": 0,
    "cooldown_bars": 0,
    "condition_logic": "all",
    "condition_nodes": [],
    "arm_bars": 0,
    "reentry_lockout_bars": 0
  },
  "exit": {
    "time_stop_bars": 12,
    "invalidation": {},
    "stop_type": "percent",
    "stop_value": 0.01,
    "target_type": "percent",
    "target_value": 0.02,
    "trailing_stop_type": "none",
    "trailing_stop_value": 0.0,
    "break_even_r": 0.0
  },
  "execution": {
    "fill_mode": "next_open",
    "allow_intrabar_exits": false,
    "priority_randomisation": true
  },
  "sizing": {
    "mode": "fixed_risk",
    "risk_per_trade": 0.01,
    "target_vol": null,
    "max_gross_leverage": 1.0,
    "max_position_scale": 1.0,
    "portfolio_risk_budget": 1.0,
    "symbol_risk_budget": 1.0
  },
  "overlays": [],
  "evaluation": {
    "min_trades": 1,
    "cost_model": {
      "fees_bps": 2.0,
      "slippage_bps": 2.0,
      "funding_included": true
    },
    "robustness_flags": {
      "oos_required": true,
      "multiplicity_required": true,
      "regime_stability_required": true
    }
  },
  "lineage": {
    "source_path": "manual",
    "compiler_version": "manual",
    "generated_at_utc": "2026-01-01T00:00:00Z"
  }
}
```

### Step 2. Run the engine

```bash
.venv/bin/python - <<'PY'
from pathlib import Path
import json
import pandas as pd

from project.core.config import get_data_root
from project.engine.runner import run_engine

data_root = get_data_root()
blueprint = json.loads(Path("/tmp/minimal_blueprint.json").read_text())

results = run_engine(
    run_id="single_hypothesis_btc_basis_disloc_run",
    symbols=["BTCUSDT"],
    strategies=["dsl_interpreter_v1__manual_test"],
    params={
        "allocator_mode": "heuristic",
        "max_portfolio_gross": 1.0,
        "max_symbol_gross": 1.0,
    },
    params_by_strategy={
        "dsl_interpreter_v1__manual_test": {
            "dsl_blueprint": blueprint,
            "event_feature_ffill_bars": 12,
        }
    },
    cost_bps=1.0,
    data_root=data_root,
    timeframe="5m",
    start_ts=pd.Timestamp("2022-11-01", tz="UTC"),
    end_ts=pd.Timestamp("2022-12-31", tz="UTC"),
)

print(results["engine_dir"])
print(results["metrics"]["portfolio"])
PY
```

### Step 3. Read engine artifacts

Look under: `data/runs/<engine_run_id>/engine/`

Important files:

- `metrics.json`
- `portfolio_returns.parquet`
- `strategy_returns_<strategy>.parquet`
- `strategy_trace_<strategy>.parquet`
- engine manifest

What to conclude:

- did the strategy actually generate positions
- what was the realized ledger/PnL path
- what did allocation and costs do
- do the traces match the intended entry/exit logic

---

## Workflow B: Compile Then Backtest

Use this when a research run has produced candidate rows worth converting into executable strategy form.

### Step 1. Run the research slice first

You need a completed research run with candidate artifacts.

Relevant research outputs live under:

- `data/reports/phase2/<run_id>/...`
- `data/runs/<run_id>/...`

### Step 2. Compile strategy blueprints

```bash
.venv/bin/python -m project.research.compile_strategy_blueprints \
  --run_id <run_id> \
  --symbols BTCUSDT
```

Check available flags:

```bash
.venv/bin/python -m project.research.compile_strategy_blueprints --help
```

Main compiler surface: [project/research/compile_strategy_blueprints.py](/home/irene/Edge/project/research/compile_strategy_blueprints.py)

### Step 3. Inspect emitted blueprint artifacts

The compiler writes under: `data/reports/strategy_blueprints/...`

One maintained example consumer expects:

- `data/reports/strategy_blueprints/multi_edge_portfolio/blueprints.jsonl`

Inspect the blueprint payload before backtesting. Check:

- `event_type`
- `direction`
- `entry.triggers`
- `entry.delay_bars`
- `exit.time_stop_bars`
- `exit.stop_value` / `exit.target_value`
- `execution.fill_mode`
- `lineage.run_id`

### Step 4. Backtest the compiled blueprint

```bash
.venv/bin/python - <<'PY'
from pathlib import Path
import json
import pandas as pd

from project.core.config import get_data_root
from project.engine.runner import run_engine

data_root = get_data_root()
blueprints_path = (
    data_root / "reports" / "strategy_blueprints" / "multi_edge_portfolio" / "blueprints.jsonl"
)

blueprints = []
with blueprints_path.open("r", encoding="utf-8") as fh:
    for line in fh:
        blueprints.append(json.loads(line))

params_by_strategy = {}
strategies = []
for i, bp in enumerate(blueprints):
    name = f"dsl_interpreter_v1__compiled_{i}"
    strategies.append(name)
    params_by_strategy[name] = {
        "dsl_blueprint": bp,
        "event_feature_ffill_bars": 12,
    }

results = run_engine(
    run_id="<your_run_id>",
    symbols=["BTCUSDT"],
    strategies=strategies,
    params={
        "allocator_mode": "heuristic",
        "max_portfolio_gross": 1.0,
        "max_symbol_gross": 1.0,
    },
    params_by_strategy=params_by_strategy,
    cost_bps=1.0,
    data_root=data_root,
    timeframe="5m",
    start_ts=pd.Timestamp("2022-11-01", tz="UTC"),
    end_ts=pd.Timestamp("2022-12-31", tz="UTC"),
)

print(results["engine_dir"])
print(results["metrics"]["portfolio"])
PY
```

### Step 5. Compare blueprint intent to engine traces

Read:

- the emitted blueprint JSON
- `strategy_trace_<strategy>.parquet`
- `strategy_returns_<strategy>.parquet`
- `portfolio_returns.parquet`

Verify:

- trigger columns in the blueprint exist in the merged feature frame
- interpreter generates positions on the bars you expect
- entry lag and fill mode behave as intended
- exits happen for the reasons you expect
- ledger PnL matches the position path

### Step 6. Diagnose if results look wrong

Problem usually lives in one of three places:

1. research-to-blueprint translation → [compile_strategy_blueprints.py](/home/irene/Edge/project/research/compile_strategy_blueprints.py)
2. DSL interpreter semantics → [interpreter.py](/home/irene/Edge/project/strategy/runtime/dsl_runtime/interpreter.py)
3. execution ledger / fill mechanics → [runner.py](/home/irene/Edge/project/engine/runner.py) / [pnl.py](/home/irene/Edge/project/engine/pnl.py)

---

## What Each Engine Path Proves

This workflow proves:

- whether a compiled blueprint is executable
- whether the engine produces a coherent ledger for it
- whether runtime traces match the intended strategy mechanics

This workflow does **not** by itself prove:

- that the original research claim was statistically sound
- that the compiled blueprint faithfully captured all research semantics

Those require both research-path artifact review **and** engine-path trace review.

---

## When To Use Which Path

| Question | Use |
|---|---|
| Is this bounded hypothesis statistically interesting? | Research path (`run_all` + phase-2 search) |
| What happens if I execute this strategy logic over bars? | Engine path (`run_engine`) |
| Does a promoted candidate actually work as a strategy? | Both — compile then backtest |

See [03_OPERATOR_WORKFLOW.md](/home/irene/Edge/docs/03_OPERATOR_WORKFLOW.md) for the full research-first workflow.
