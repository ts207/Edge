# BTC Data Foundation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Ingest 3 years of BTCUSDT Binance UM futures historical data (OHLCV 5m, funding rates, mark price 5m, open interest) into the pipeline data lake so the research campaign can run.

**Architecture:** All four ingest scripts already exist under `project/pipelines/ingest/`. They pull from the public `data.binance.vision` archive — no API key required for historical data. Each script writes partitioned Parquet files and emits a manifest. The gate check reads those manifests and validates row counts and completeness.

**Tech Stack:** Python 3.11, pandas, pyarrow, requests, aiohttp. The project uses a local `.venv` with pinned deps in `pyproject.toml`.

---

### Task 1: Install the virtual environment

**Files:**
- No files to edit — just shell setup

**Step 1: Create the venv and install the package**

```bash
cd /home/tstuv/workspace/trading/EDGEE
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -e .
```

**Step 2: Verify the install worked**

```bash
.venv/bin/python -c "import project.pipelines.run_all; print('OK')"
```

Expected output: `OK`

If you see import errors, check `pyproject.toml` for missing deps and install them manually.

**Step 3: Verify the query tool works**

```bash
.venv/bin/python -m project.research.knowledge.query knobs
```

Expected: prints available knob names without error.

---

### Task 2: Ingest BTCUSDT UM OHLCV 5m (2022–2024)

**Files:**
- Script: `project/pipelines/ingest/ingest_binance_um_ohlcv.py`
- Output: `data/lake/raw/binance/perp/BTCUSDT/ohlcv_5m/year=*/month=*/`
- Manifest: written to stdout + auto-tracked by the script

**Step 1: Run the ingest**

```bash
cd /home/tstuv/workspace/trading/EDGEE
.venv/bin/python -m project.pipelines.ingest.ingest_binance_um_ohlcv \
  --run_id btc_data_foundation \
  --symbols BTCUSDT \
  --start 2022-01-01 \
  --end 2024-12-31 \
  --timeframe 5m \
  --force 0
```

Expected: downloads ~36 monthly zip archives, writes ~36 parquet partitions. Each partition covers one month. Final log line should say `status: success`.

If a month is missing from the archive it will fall back to daily archives automatically.

**Step 2: Spot-check the output**

```bash
.venv/bin/python - <<'EOF'
import pandas as pd
from pathlib import Path
files = sorted(Path("data/lake/raw/binance/perp/BTCUSDT/ohlcv_5m").rglob("*.parquet"))
print(f"Partitions: {len(files)}")
df = pd.read_parquet(files[0])
print(df.dtypes)
print(df.head(3))
print(f"Total rows first partition: {len(df)}")
EOF
```

Expected: ~36 partitions, columns `[timestamp, open, high, low, close, volume, symbol, source]`, ~8928 rows per month (31 days × 24h × 12 bars).

---

### Task 3: Ingest BTCUSDT funding rates (2022–2024)

**Files:**
- Script: `project/pipelines/ingest/ingest_binance_um_funding.py`
- Output: `data/lake/raw/binance/perp/BTCUSDT/funding/year=*/month=*/`

**Step 1: Run the ingest**

```bash
cd /home/tstuv/workspace/trading/EDGEE
.venv/bin/python -m project.pipelines.ingest.ingest_binance_um_funding \
  --run_id btc_data_foundation \
  --symbols BTCUSDT \
  --start 2022-01-01 \
  --end 2024-12-31 \
  --use_api_fallback 1 \
  --force 0
```

Expected: ~36 monthly partitions. Funding settles 3× per day (00:00, 08:00, 16:00 UTC), so ~1095 records per year, ~3285 total. Final status: `success`.

**Step 2: Verify completeness**

```bash
.venv/bin/python - <<'EOF'
import pandas as pd
from pathlib import Path
files = sorted(Path("data/lake/raw/binance/perp/BTCUSDT/funding").rglob("*.parquet"))
print(f"Partitions: {len(files)}")
frames = [pd.read_parquet(f) for f in files]
df = pd.concat(frames).sort_values("timestamp")
print(f"Total funding records: {len(df)}")
print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
print(f"Missing 8h slots: {df['timestamp'].diff().dropna().gt(pd.Timedelta(hours=8)).sum()}")
EOF
```

Expected: ~3285 records, 0 or very few missing 8h slots (gaps may exist during exchange outages).

---

### Task 4: Ingest BTCUSDT mark price 5m (2022–2024)

**Files:**
- Script: `project/pipelines/ingest/ingest_binance_um_mark_price_5m.py`
- Output: `data/lake/raw/binance/perp/BTCUSDT/mark_price_5m/year=*/month=*/`

**Step 1: Run the ingest**

```bash
cd /home/tstuv/workspace/trading/EDGEE
.venv/bin/python -m project.pipelines.ingest.ingest_binance_um_mark_price_5m \
  --run_id btc_data_foundation \
  --symbols BTCUSDT \
  --start 2022-01-01 \
  --end 2024-12-31 \
  --force 0
```

Expected: ~36 monthly partitions, same bar count as OHLCV 5m. Status: `success`.

**Step 2: Quick row count check**

```bash
.venv/bin/python - <<'EOF'
import pandas as pd
from pathlib import Path
files = sorted(Path("data/lake/raw/binance/perp/BTCUSDT/mark_price_5m").rglob("*.parquet"))
print(f"Partitions: {len(files)}")
total = sum(len(pd.read_parquet(f)) for f in files)
print(f"Total rows: {total}")
EOF
```

Expected: roughly equal to OHLCV 5m row count.

---

### Task 5: Ingest BTCUSDT open interest history (2022–2024)

**Files:**
- Script: `project/pipelines/ingest/ingest_binance_um_open_interest_hist.py`
- Output: `data/lake/raw/binance/perp/BTCUSDT/open_interest/year=*/month=*/`

**Step 1: Run the ingest**

```bash
cd /home/tstuv/workspace/trading/EDGEE
.venv/bin/python -m project.pipelines.ingest.ingest_binance_um_open_interest_hist \
  --run_id btc_data_foundation \
  --symbols BTCUSDT \
  --start 2022-01-01 \
  --end 2024-12-31 \
  --period 5m \
  --force 0
```

Expected: ~36 monthly partitions. OI history from `data.binance.vision` goes back to mid-2020. Status: `success`.

**Step 2: Spot-check**

```bash
.venv/bin/python - <<'EOF'
import pandas as pd
from pathlib import Path
files = sorted(Path("data/lake/raw/binance/perp/BTCUSDT/open_interest").rglob("*.parquet"))
print(f"Partitions: {len(files)}")
df = pd.read_parquet(files[0])
print(df.dtypes)
print(df.head(3))
EOF
```

---

### Task 6: Gate check — validate all four data streams

Before moving to the research campaign, confirm all data streams are present and internally consistent.

**Step 1: Run date-range alignment check**

```bash
.venv/bin/python - <<'EOF'
import pandas as pd
from pathlib import Path

streams = {
    "ohlcv_5m": "data/lake/raw/binance/perp/BTCUSDT/ohlcv_5m",
    "funding": "data/lake/raw/binance/perp/BTCUSDT/funding",
    "mark_price_5m": "data/lake/raw/binance/perp/BTCUSDT/mark_price_5m",
    "open_interest": "data/lake/raw/binance/perp/BTCUSDT/open_interest",
}

for name, path in streams.items():
    files = sorted(Path(path).rglob("*.parquet"))
    if not files:
        print(f"MISSING: {name}")
        continue
    frames = [pd.read_parquet(f) for f in files]
    df = pd.concat(frames).sort_values("timestamp")
    print(f"{name}: {len(df)} rows | {df['timestamp'].min().date()} → {df['timestamp'].max().date()}")
EOF
```

Expected output (approximate):
```
ohlcv_5m:      315000+ rows | 2022-01-01 → 2024-12-31
funding:         3285 rows  | 2022-01-01 → 2024-12-31
mark_price_5m: 315000+ rows | 2022-01-01 → 2024-12-31
open_interest: 315000+ rows | 2022-01-01 → 2024-12-31
```

**Gate:** All four streams present, all cover 2022-01-01 to 2024-12-31 (within a day). If any are missing or grossly short, re-run the relevant ingest task with `--force 1`.

**Step 2: If gate passes, write a note**

```bash
cat > data/artifacts/btc_data_foundation_gate.txt <<'EOF'
btc_data_foundation gate: PASS
date: $(date -u +%Y-%m-%dT%H:%M:%SZ)
streams: ohlcv_5m, funding, mark_price_5m, open_interest
symbol: BTCUSDT
range: 2022-01-01 to 2024-12-31
next: proceed to research campaign (Section 2)
EOF
```

---

## Next Step

Once the gate passes, proceed to the research campaign plan:
`docs/plans/2026-03-16-btc-funding-disloc-campaign.md` (to be written after Section 2 design is approved).
