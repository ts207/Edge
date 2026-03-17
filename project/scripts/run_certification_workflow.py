from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable

import pandas as pd

from project import PROJECT_ROOT
from project.live.health_checks import (
    DataHealthMonitor,
    build_runtime_certification_manifest,
)
from project.live.state import LiveStateStore
from project.runtime.invariants import run_runtime_postflight_audit
from project.io.runtime_adapter import read_raw_event_rows
from project.scripts.run_golden_workflow import run_golden_workflow
from project.spec_registry import load_yaml_path


def _default_config_path() -> Path:
    return PROJECT_ROOT / "configs" / "golden_certification.yaml"


def load_certification_config(path: Path) -> Dict[str, Any]:
    payload = load_yaml_path(path) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"Certification workflow config must be a mapping: {path}")
    return dict(payload)


def _materialize_runtime_events(*, root: Path, run_id: str) -> Path:
    events_dir = root / "events" / run_id
    events_dir.mkdir(parents=True, exist_ok=True)
    events_path = events_dir / "events.csv"
    base = pd.Timestamp("2024-01-01T00:00:00Z")
    rows = [
        {
            "event_id": "cert_evt_0001",
            "event_type": "VOL_SHOCK",
            "symbol": "BTCUSDT",
            "lane_id": "alpha_5s",
            "source_id": "VOL_SHOCK:BTCUSDT",
            "source_seq": 1,
            "enter_ts": int(base.value // 1000),
            "detected_ts": int((base + pd.Timedelta(seconds=2)).value // 1000),
        },
        {
            "event_id": "cert_evt_0002",
            "event_type": "VOL_SHOCK",
            "symbol": "ETHUSDT",
            "lane_id": "alpha_5s",
            "source_id": "VOL_SHOCK:ETHUSDT",
            "source_seq": 2,
            "enter_ts": int((base + pd.Timedelta(seconds=5)).value // 1000),
            "detected_ts": int((base + pd.Timedelta(seconds=6)).value // 1000),
        },
    ]
    pd.DataFrame(rows).to_csv(events_path, index=False)
    return events_path


def _build_health_report(
    *,
    stale_threshold_sec: float,
    streams: Iterable[Dict[str, Any]],
) -> Dict[str, Any]:
    monitor = DataHealthMonitor(stale_threshold_sec=stale_threshold_sec)
    for item in streams:
        symbol = str(item.get("symbol", "")).strip()
        stream = str(item.get("stream", "")).strip()
        if symbol and stream:
            monitor.on_event(symbol, stream)
    return monitor.check_health()


def _fallback_replay_digest(path: Path) -> str:
    if not path.exists():
        return ""
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return f"sha256:{digest}"


def _materialize_live_state_snapshot(*, root: Path, config: Dict[str, Any]) -> Path:
    relpath = Path(str(config.get("live_state_snapshot_path", "reliability/live_state.json")))
    snapshot_path = relpath if relpath.is_absolute() else root / relpath
    store = LiveStateStore(snapshot_path=snapshot_path)
    store.update_from_exchange_snapshot(
        {
            "wallet_balance": float(config.get("wallet_balance", 100000.0)),
            "margin_balance": float(config.get("margin_balance", 100000.0)),
            "positions": list(config.get("live_positions", [])),
        }
    )
    return snapshot_path


def run_certification_workflow(*, root: Path, config_path: Path) -> Dict[str, Any]:
    config = load_certification_config(config_path)
    workflow_config = Path(
        str(
            config.get(
                "golden_workflow_config",
                PROJECT_ROOT / "configs" / "golden_workflow.yaml",
            )
        )
    )
    if not workflow_config.is_absolute():
        workflow_config = PROJECT_ROOT.parent / workflow_config

    golden_payload = run_golden_workflow(root=root, config_path=workflow_config)
    run_id = str(config.get("runtime_run_id", golden_payload["summary"].get("run_id", "smoke_run")))
    events_path = _materialize_runtime_events(root=root, run_id=run_id)

    raw_rows, source_path = read_raw_event_rows(data_root=root, run_id=run_id)
    events_df = pd.DataFrame(raw_rows) if raw_rows else None

    postflight_audit = run_runtime_postflight_audit(
        data_root=root,
        run_id=run_id,
        events_df=events_df,
        source_path=source_path,
        repo_root=PROJECT_ROOT,
        determinism_replay_checks=True,
    )
    health_report = _build_health_report(
        stale_threshold_sec=float(config.get("stale_threshold_sec", 60.0)),
        streams=list(config.get("freshness_streams", [])),
    )
    replay_digest = str(postflight_audit.get("replay_digest", "")).strip()
    if not replay_digest:
        replay_digest = _fallback_replay_digest(events_path)
    live_state_snapshot_path = _materialize_live_state_snapshot(root=root, config=config)
    certification_manifest = build_runtime_certification_manifest(
        postflight_audit=postflight_audit,
        health_report=health_report,
        kill_switch_status={"is_active": False, "reason": None, "message": ""},
        oms_lineage=dict(config.get("oms_lineage", {})),
        replay_status={
            "status": str(postflight_audit.get("determinism_status", postflight_audit.get("status", "unknown"))),
            "replay_digest": replay_digest,
        },
        live_state_status={
            "snapshot_path": str(live_state_snapshot_path),
            "auto_persist_enabled": True,
        },
    )

    reliability_dir = root / "reliability"
    reliability_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = reliability_dir / "runtime_certification_manifest.json"
    manifest_path.write_text(
        json.dumps(certification_manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    payload = {
        "workflow_id": str(config.get("workflow_id", "golden_certification_v1")),
        "config_path": str(config_path),
        "root": str(root),
        "runtime_run_id": run_id,
        "events_path": str(events_path),
        "live_state_snapshot_path": str(live_state_snapshot_path),
        "required_outputs": list(config.get("required_outputs", [])),
        "golden_workflow": golden_payload,
        "runtime_certification_manifest_path": str(manifest_path),
        "runtime_certification": certification_manifest,
    }
    summary_path = reliability_dir / "golden_certification_summary.json"
    summary_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the certification-grade golden workflow."
    )
    parser.add_argument(
        "--root",
        default=None,
        help="Output root for generated certification artifacts.",
    )
    parser.add_argument(
        "--config",
        default=str(_default_config_path()),
        help="Certification workflow config YAML path.",
    )
    args = parser.parse_args(argv)

    root = (
        Path(args.root)
        if args.root
        else (PROJECT_ROOT.parent / "artifacts" / "golden_certification")
    )
    run_certification_workflow(root=root, config_path=Path(args.config))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
