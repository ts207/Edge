"""
Campaign Controller: Orchestrates autonomous research sequences.
"""
import argparse
import hashlib
import json
import logging
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import pandas as pd
import yaml

from project.core.config import get_data_root
from project.pipelines.research.experiment_engine import build_experiment_plan, RegistryBundle

_LOG = logging.getLogger(__name__)

@dataclass
class CampaignConfig:
    program_id: str
    max_runs: int = 5
    max_hypotheses_total: int = 5000
    max_consecutive_no_signal: int = 2
    halt_on_empty_share: float = 0.8
    halt_on_unsupported_share: float = 0.5
    
@dataclass
class CampaignSummary:
    program_id: str
    total_runs: int = 0
    total_generated: int = 0
    total_evaluated: int = 0
    total_empty_sample: int = 0
    total_insufficient_sample: int = 0
    total_unsupported: int = 0
    total_skipped: int = 0
    top_hypotheses: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_json(self) -> str:
        return json.dumps(self.__dict__, indent=2)

class CampaignController:
    def __init__(self, config: CampaignConfig, data_root: Path, registry_root: Path):
        self.config = config
        self.data_root = data_root
        self.registry_root = registry_root
        self.campaign_dir = data_root / "artifacts" / "experiments" / config.program_id
        self.campaign_dir.mkdir(parents=True, exist_ok=True)
        self.ledger_path = self.campaign_dir / "tested_ledger.parquet"
        self.summary_path = self.campaign_dir / "campaign_summary.json"
        self.frontier_path = self.campaign_dir / "search_frontier.json"
        self.registries = RegistryBundle(registry_root)

    def run_campaign(self):
        _LOG.info(f"Starting campaign: {self.config.program_id}")
        
        for run_idx in range(self.config.max_runs):
            _LOG.info(f"Iteration {run_idx + 1}/{self.config.max_runs}")
            
            # 1. Propose next search slice
            request_dict = self._propose_next_request()
            if not request_dict:
                _LOG.info("No more search frontier. Campaign complete.")
                break
                
            # 2. Write experiment config
            run_id = f"run_{run_idx + 1}_{hashlib.md5(json.dumps(request_dict).encode()).hexdigest()[:8]}"
            config_path = self.campaign_dir / f"{run_id}_config.yaml"
            config_path.write_text(yaml.dump(request_dict))
            
            # 3. Build plan (validates)
            try:
                plan = build_experiment_plan(config_path, self.registry_root, out_dir=self.campaign_dir / run_id)
            except Exception as e:
                _LOG.error(f"Failed to build plan for {run_id}: {e}")
                continue
                
            # 4. Run pipeline
            self._execute_pipeline(config_path, run_id)
            
            # 5. Update summary and check halts
            summary = self._update_campaign_stats()
            if self._should_halt(summary):
                _LOG.warning("Halt criteria met. Ending campaign.")
                break
                
        _LOG.info(f"Campaign {self.config.program_id} finished.")

    def _propose_next_request(self) -> Optional[Dict[str, Any]]:
        # This is the "brain" of the controller.
        # For Phase 1, we implement a simple progressive search through EVENT families.
        
        tested_ids = set()
        tested_events: Set[str] = set()
        if self.ledger_path.exists():
            df = pd.read_parquet(self.ledger_path)
            tested_ids = set(df["hypothesis_id"].unique())
            if "trigger_payload" in df.columns:
                def _event_id_from_payload(payload: object) -> Optional[str]:
                    try:
                        parsed = json.loads(str(payload))
                    except Exception:
                        return None
                    if not isinstance(parsed, dict):
                        return None
                    event_id = str(parsed.get("event_id", "")).strip()
                    return event_id or None

                tested_events = {
                    event_id
                    for event_id in df["trigger_payload"].apply(_event_id_from_payload).dropna().astype(str)
                    if event_id
                }
            
        # Get all legal events from registry
        events = self.registries.events.get("events", {})
        available_events = [eid for eid, meta in events.items() if meta.get("enabled", True)]
        
        # Simple strategy: find 3 events we haven't tested yet
        # (In a real system, this would be much more sophisticated)
        to_test = []
        for eid in available_events:
            if eid in tested_events:
                continue
            to_test.append(eid)
            if len(to_test) >= 3: break
            
        if not to_test:
            return None
            
        return {
            "program_id": self.config.program_id,
            "run_mode": "research",
            "description": f"Autonomous run {self.config.program_id}",
            "instrument_scope": {
                "instrument_classes": ["crypto"],
                "symbols": ["BTCUSDT"],
                "timeframe": "5m",
                "start": "2024-01-01",
                "end": "2024-01-05"
            },
            "trigger_space": {
                "allowed_trigger_types": ["EVENT"],
                "events": {"include": to_test}
            },
            "templates": {"include": ["continuation"]},
            "evaluation": {
                "horizons_bars": [12, 24],
                "directions": ["long", "short"],
                "entry_lags": [0]
            },
            "contexts": {"include": {}},
            "search_control": {
                "max_hypotheses_total": 1000,
                "max_hypotheses_per_template": 500,
                "max_hypotheses_per_event_family": 500
            },
            "promotion": {"enabled": False}
        }

    def _execute_pipeline(self, config_path: Path, run_id: str):
        _LOG.info(f"Executing pipeline for {run_id}...")
        cmd = [
            sys.executable, "-m", "project.pipelines.run_all",
            "--mode", "research",
            "--run_id", run_id,
            "--experiment_config", str(config_path),
            "--registry_root", str(self.registry_root)
        ]
        _LOG.info(f"Command: {' '.join(cmd)}")
        subprocess.run(cmd, check=True, cwd=str(Path.cwd()))

    def _update_campaign_stats(self) -> CampaignSummary:
        if not self.ledger_path.exists():
            return CampaignSummary(self.config.program_id)
            
        df = pd.read_parquet(self.ledger_path)
        
        summary = CampaignSummary(
            program_id=self.config.program_id,
            total_runs=len(df["run_id"].unique()),
            total_generated=len(df),
            total_evaluated=len(df[df["eval_status"] == "evaluated"]),
            total_empty_sample=len(df[df["eval_status"] == "empty_sample"]),
            total_insufficient_sample=len(df[df["eval_status"] == "insufficient_sample"]),
            total_unsupported=len(df[df["eval_status"] == "unsupported_trigger_evaluator"]),
            total_skipped=len(df[df["eval_status"] == "not_executed_or_missing_data"]),
        )
        
        # Get top 5 hypotheses by expectancy
        if not df.empty and "expectancy" in df.columns:
            top = df[df["eval_status"] == "evaluated"].sort_values("expectancy", ascending=False).head(5)
            summary.top_hypotheses = top.to_dict(orient="records")
            
        self.summary_path.write_text(summary.to_json())
        
        # Update frontier
        self._update_frontier(df)
        
        return summary

    def _update_frontier(self, ledger_df: pd.DataFrame):
        # Build simple frontier of untested events
        events = self.registries.events.get("events", {})
        enabled_events = [eid for eid, meta in events.items() if meta.get("enabled", True)]
        
        tested_events = set()
        failed_events = set()
        
        if not ledger_df.empty:
            # Note: trigger_payload is JSON in the ledger
            def get_eid(payload):
                try:
                    p = json.loads(payload)
                    return p.get("event_id")
                except: return None
            
            ledger_df["eid"] = ledger_df["trigger_payload"].apply(get_eid)
            tested_events = set(ledger_df["eid"].dropna().unique())
            
            # Repeated failures (empty sample or insufficient)
            fail_counts = ledger_df[ledger_df["eval_status"].isin(["empty_sample", "insufficient_sample"])].groupby("eid").size()
            failed_events = set(fail_counts[fail_counts >= 3].index)

        frontier = {
            "untested_events": sorted(list(set(enabled_events) - tested_events)),
            "exhausted_events": sorted(list(failed_events)),
            "partially_explored_families": self._get_partial_families(tested_events)
        }
        self.frontier_path.write_text(json.dumps(frontier, indent=2))

    def _get_partial_families(self, tested_events: Set[str]) -> Dict[str, float]:
        events = self.registries.events.get("events", {})
        families = {}
        for eid, meta in events.items():
            fam = meta.get("family", "unknown")
            if fam not in families: families[fam] = {"total": 0, "tested": 0}
            families[fam]["total"] += 1
            if eid in tested_events: families[fam]["tested"] += 1
            
        return {f: stats["tested"]/stats["total"] for f, stats in families.items() if 0 < stats["tested"] < stats["total"]}

    def _should_halt(self, summary: CampaignSummary) -> bool:
        if summary.total_generated == 0: return False
        
        empty_share = summary.total_empty_sample / summary.total_generated
        if empty_share > self.config.halt_on_empty_share:
            _LOG.warning(f"High empty sample share: {empty_share:.2%}")
            return True
            
        unsupported_share = summary.total_unsupported / summary.total_generated
        if unsupported_share > self.config.halt_on_unsupported_share:
            _LOG.warning(f"High unsupported trigger share: {unsupported_share:.2%}")
            return True
            
        return False

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--program_id", required=True)
    parser.add_argument("--max_runs", type=int, default=3)
    parser.add_argument("--registry_root", default="project/configs/registries")
    args = parser.parse_args()
    
    data_root = get_data_root()
    config = CampaignConfig(program_id=args.program_id, max_runs=args.max_runs)
    controller = CampaignController(config, data_root, Path(args.registry_root))
    controller.run_campaign()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
