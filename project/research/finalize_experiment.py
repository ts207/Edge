"""
Finalize Experiment Run.
Collects hypotheses evaluation results and appends to the program's tested ledger.
"""

import argparse
import json
import logging
from pathlib import Path
import sys

import pandas as pd
from project.core.config import get_data_root

_LOG = logging.getLogger(__name__)


def finalize_experiment(
    data_root: Path,
    program_id: str,
    run_id: str,
) -> None:
    exp_dir = data_root / "artifacts" / "experiments" / program_id / run_id
    if not exp_dir.exists():
        _LOG.error(f"Experiment directory not found: {exp_dir}")
        return

    # Load expanded hypotheses
    hyp_path = exp_dir / "expanded_hypotheses.parquet"
    if not hyp_path.exists():
        _LOG.error(f"Expanded hypotheses not found at: {hyp_path}")
        return
    hyps_df = pd.read_parquet(hyp_path)

    # Collect phase 2 candidate reports for this run
    all_results = []
    possible_roots = [
        data_root / "reports" / "phase2_discovery",
        data_root / "reports" / "phase2",
    ]

    for reports_root in possible_roots:
        if reports_root.exists():
            run_reports = reports_root / run_id
            if run_reports.exists():
                for p in run_reports.rglob("*.parquet"):
                    if "candidates" in p.name or "evaluated" in p.name:
                        try:
                            df = pd.read_parquet(p)
                            if not df.empty and (
                                "hypothesis_id" in df.columns or "candidate_id" in df.columns
                            ):
                                all_results.append(df)
                        except Exception as e:
                            _LOG.warning(f"Failed to read {p}: {e}")

    if not all_results:
        results_df = pd.DataFrame()
    else:
        results_df = pd.concat(all_results, ignore_index=True)

    # Robust ID matching
    from project.io.utils import write_parquet

    # Initialize merged_df with hyps
    merged_df = hyps_df.copy()
    merged_df["run_id"] = run_id
    finalized_at = pd.Timestamp.now(tz="UTC").isoformat()
    if "created_at" not in merged_df.columns:
        merged_df["created_at"] = finalized_at
    else:
        merged_df["created_at"] = merged_df["created_at"].fillna(finalized_at)

    if not results_df.empty:
        # Create unique evaluation map
        # We prefer hypothesis_id, fallback to candidate_id
        eval_map = {}

        for _, row in results_df.iterrows():
            hid = row.get("hypothesis_id")
            cid = row.get("candidate_id")

            # Helper to assign terminal status
            def get_status(r):
                # Try multiple names for expectancy
                exp = r.get("expectancy")
                if pd.isna(exp):
                    exp = r.get("mean_return_bps")
                if pd.isna(exp):
                    return "empty_sample"
                if r.get("sample_size", 0) < 5 and r.get("n_obs", 0) < 5:
                    return "insufficient_sample"
                return "evaluated"

            r_data = row.to_dict()
            r_data["eval_status"] = get_status(row)

            if hid and str(hid).startswith("hyp_"):
                eval_map[str(hid)] = r_data

            if cid:
                cid_str = str(cid)
                # Handle SYMBOL::prefix
                if "::" in cid_str:
                    cid_str = cid_str.split("::")[-1]

                if cid_str.startswith("hyp_") and cid_str not in eval_map:
                    eval_map[cid_str] = r_data

        # Apply to merged_df using record-based updates to prevent fragmentation
        updated_records = []
        for _, row in merged_df.iterrows():
            hid = row["hypothesis_id"]
            r_data = row.to_dict()

            if hid in eval_map:
                res = eval_map[hid]
                for k, v in res.items():
                    # Preserve original hypothesis_id if the result came from candidate_id matching
                    if k in ["hypothesis_id", "candidate_id"] and v != hid:
                        continue
                    if k not in r_data or pd.isna(r_data.get(k)):
                        r_data[k] = v

                # Ensure expectancy is populated from mean_return_bps if missing
                if pd.isna(r_data.get("expectancy")) and not pd.isna(r_data.get("mean_return_bps")):
                    r_data["expectancy"] = float(r_data["mean_return_bps"]) / 10000.0
            else:
                # Handle unsupported/missing
                t_type = row.get("trigger_type")
                if t_type == "transition":
                    r_data["eval_status"] = "unsupported_trigger_evaluator"
                elif (
                    t_type == "sequence"
                    and len(json.loads(row.get("trigger_payload", "{}")).get("events", [])) > 2
                ):
                    r_data["eval_status"] = "unsupported_trigger_evaluator"
                else:
                    r_data["eval_status"] = "not_executed_or_missing_data"

            updated_records.append(r_data)

        merged_df = pd.DataFrame.from_records(updated_records)
    else:
        merged_df["eval_status"] = "not_executed_or_missing_data"

    # Save evaluation results
    eval_df = merged_df[
        ~merged_df["eval_status"].isin(
            ["not_executed_or_missing_data", "unsupported_trigger_evaluator"]
        )
    ].copy()
    if not eval_df.empty:
        write_parquet(eval_df, exp_dir / "evaluation_results.parquet")

    # Append to tested ledger
    ledger_path = data_root / "artifacts" / "experiments" / program_id / "tested_ledger.parquet"
    if ledger_path.exists():
        try:
            ledger_df = pd.read_parquet(ledger_path)
            ledger_df = pd.concat([ledger_df, merged_df], ignore_index=True)
            ledger_df = ledger_df.drop_duplicates(subset=["hypothesis_id"], keep="last")
            write_parquet(ledger_df, ledger_path)
        except Exception as e:
            _LOG.error(f"Failed to update ledger: {e}")
            write_parquet(merged_df, ledger_path)
    else:
        ledger_path.parent.mkdir(parents=True, exist_ok=True)
        write_parquet(merged_df, ledger_path)

    # Summary
    summary = {
        "program_id": program_id,
        "run_id": run_id,
        "total_hypotheses": len(hyps_df),
        "evaluated_hypotheses": int((merged_df["eval_status"] == "evaluated").sum()),
        "passed_hypotheses": int(merged_df.get("gate_phase2_final", pd.Series([False])).sum())
        if "gate_phase2_final" in merged_df.columns
        else 0,
    }
    (exp_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    _LOG.info(f"Finalized experiment {program_id}/{run_id}. Ledger updated.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run_id", required=True)
    parser.add_argument("--program_id", required=True)
    parser.add_argument("--data_root", default=None)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    data_root = Path(args.data_root) if args.data_root else get_data_root()
    finalize_experiment(data_root, args.program_id, args.run_id)
    return 0


if __name__ == "__main__":
    sys.exit(main())
