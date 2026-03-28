# Stabilization Baseline

Date: 2026-03-27
Branch: `codex/contract-stabilization`

## Command outcomes

| Command | Result | Notes |
| --- | --- | --- |
| `.venv/bin/python -m compileall -q project project/tests` | PASS | no output |
| `.venv/bin/python -m pytest project/tests/architecture -q` | PASS | `5 passed` |
| `.venv/bin/python -m pytest project/tests/live -q` | PASS | `59 passed` |
| `.venv/bin/python -m pytest project/tests/contracts -q` | PASS | `29 passed` |
| `.venv/bin/python -m pytest project/tests/reliability -q` | PASS | `4 passed` |
| `.venv/bin/python -m pytest project/tests/strategy -q` | PASS | `11 passed` |
| `.venv/bin/python -m project.reliability.cli_smoke --mode full --root /tmp/edge-smoke` | PASS | smoke summary emitted; `storage_mode=parquet` |
| `.venv/bin/python -m project.scripts.run_golden_workflow` | PASS | completed with no stderr |
| `.venv/bin/python -m project.scripts.run_golden_synthetic_discovery` | PASS | completed successfully; required ~436s timeout |
| `make minimum-green-gate` | FAIL | detector coverage artifacts drifted |

## Failure details

### `make minimum-green-gate`

The gate currently fails in the governance drift stage:

```text
PYTHONPATH=. /home/irene/Edge/.venv/bin/python project/scripts/detector_coverage_audit.py --md-out docs/generated/detector_coverage.md --json-out docs/generated/detector_coverage.json --check
detector coverage audit drift: docs/generated/detector_coverage.json
detector coverage audit drift: docs/generated/detector_coverage.md
make: *** [Makefile:66: minimum-green-gate] Error 1
```

The earlier `spec_qa_linter.py` step reports missing authored artifacts and runtime artifacts not statically checked, but it exits successfully and is not the failing condition in the baseline run.
