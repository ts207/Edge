from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

from project import PROJECT_ROOT
from project.io.utils import read_parquet
from project.scripts.generate_synthetic_crypto_regimes import generate_synthetic_crypto_run
from project.scripts.run_golden_workflow import load_workflow_config
from project.scripts.validate_synthetic_detector_truth import validate_detector_truth


def _default_config_path() -> Path:
    return PROJECT_ROOT / "configs" / "golden_synthetic_discovery.yaml"


def _run_pipeline(*, data_root: Path, argv: List[str]) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["BACKTEST_DATA_ROOT"] = str(data_root)
    env["BACKTEST_STRICT_RUN_SCOPED_READS"] = "1"
    return subprocess.run(
        [sys.executable, "-m", "project.pipelines.run_all", *argv],
        cwd=str(PROJECT_ROOT.parent),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def _candidate_summary(search_candidates_path: Path) -> Dict[str, Any]:
    if not search_candidates_path.exists() and not search_candidates_path.with_suffix(".csv").exists():
        return {"candidate_rows": 0, "candidate_event_types": []}
    frame = read_parquet(search_candidates_path if search_candidates_path.exists() else search_candidates_path.with_suffix(".csv"))
    return {
        "candidate_rows": int(len(frame)),
        "candidate_event_types": sorted(frame.get("event_type", pd.Series(dtype=str)).astype(str).unique().tolist()) if not frame.empty and "event_type" in frame.columns else [],
    }


def run_golden_synthetic_discovery(
    *,
    root: Path,
    config_path: Path,
    pipeline_runner=_run_pipeline,
) -> Dict[str, Any]:
    config = load_workflow_config(config_path)
    run_id = str(config.get("run_id", "golden_synthetic_discovery"))
    symbols = str(config.get("symbols", "BTCUSDT,ETHUSDT"))
    start_date = str(config.get("start_date", "2026-01-01"))
    end_date = str(config.get("end_date", "2026-02-28"))
    discovery_profile = str(config.get("discovery_profile", "synthetic"))
    phase2_gate_profile = str(config.get("phase2_gate_profile", "synthetic"))
    search_spec = str(config.get("search_spec", "synthetic_truth"))
    search_min_n = int(config.get("search_min_n", 8))
    volatility_profile = str(config.get("volatility_profile", "default"))
    noise_scale = float(config.get("noise_scale", 1.0))

    synthetic_manifest = generate_synthetic_crypto_run(
        run_id=run_id,
        start_date=start_date,
        end_date=end_date,
        data_root=root,
        symbols=[token.strip().upper() for token in symbols.split(",") if token.strip()],
        volatility_profile=volatility_profile,
        noise_scale=noise_scale,
    )
    preseeded_clean_root = root / "lake" / "runs" / run_id / "cleaned"
    if preseeded_clean_root.exists():
        shutil.rmtree(preseeded_clean_root)

    pipeline_args = [
        "--run_id", run_id,
        "--symbols", symbols,
        "--start", start_date,
        "--end", end_date,
        "--skip_ingest_ohlcv", "1",
        "--skip_ingest_funding", "1",
        "--skip_ingest_spot_ohlcv", "1",
        "--run_phase2_conditional", "1",
        "--phase2_event_type", "all",
        "--run_bridge_eval_phase2", "0",
        "--run_candidate_promotion", "0",
        "--run_recommendations_checklist", "0",
        "--run_strategy_builder", "0",
        "--run_strategy_blueprint_compiler", "0",
        "--run_profitable_selector", "0",
        "--run_interaction_lift", "0",
        "--run_promotion_audit", "0",
        "--run_edge_registry_update", "0",
        "--run_edge_candidate_universe", "0",
        "--run_discovery_quality_summary", "0",
        "--run_naive_entry_eval", "0",
        "--runtime_invariants_mode", "off",
        "--funding_scale", "decimal",
        "--discovery_profile", discovery_profile,
        "--phase2_gate_profile", phase2_gate_profile,
        "--search_spec", search_spec,
        "--search_min_n", str(search_min_n),
        "--config", "project/configs/pipeline.yaml",
    ]
    completed = pipeline_runner(data_root=root, argv=pipeline_args)
    if completed.returncode != 0:
        raise RuntimeError(
            "golden synthetic discovery pipeline failed\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )

    truth_map_path = Path(synthetic_manifest["truth_map_path"])
    truth_validation = validate_detector_truth(
        data_root=root,
        run_id=run_id,
        truth_map_path=truth_map_path,
    )
    search_diag_path = root / "reports" / "phase2" / run_id / "search_engine" / "phase2_diagnostics.json"
    search_diag = json.loads(search_diag_path.read_text(encoding="utf-8")) if search_diag_path.exists() else {}
    candidate_summary = _candidate_summary(root / "reports" / "phase2" / run_id / "search_engine" / "phase2_candidates.parquet")

    payload = {
        "workflow_id": str(config.get("workflow_id", "golden_synthetic_discovery_v1")),
        "config_path": str(config_path),
        "root": str(root),
        "run_id": run_id,
        "synthetic_manifest": synthetic_manifest,
        "pipeline": {
            "argv": pipeline_args,
            "returncode": int(completed.returncode),
        },
        "truth_validation": truth_validation,
        "search_engine_diagnostics": search_diag,
        "candidate_summary": candidate_summary,
        "required_outputs": list(config.get("required_outputs", [])),
    }
    out_path = root / "reliability" / "golden_synthetic_discovery_summary.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the canonical synthetic discovery workflow.")
    parser.add_argument("--root", default=None)
    parser.add_argument("--config", default=str(_default_config_path()))
    args = parser.parse_args(argv)

    root = Path(args.root) if args.root else (PROJECT_ROOT.parent / "artifacts" / "golden_synthetic_discovery")
    run_golden_synthetic_discovery(root=root, config_path=Path(args.config))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
