from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from project.pipelines import run_all


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="edge",
        description="Canonical CLI for the Edge operator and pipeline surfaces.",
    )
    subparsers = parser.add_subparsers(dest="command")

    operator_parser = subparsers.add_parser(
        "operator",
        help="Canonical operator workflow surface.",
    )
    operator_sub = operator_parser.add_subparsers(dest="operator_command")

    preflight_parser = operator_sub.add_parser(
        "preflight", help="Validate proposal, local data coverage, and writable outputs."
    )
    preflight_parser.add_argument("--proposal", required=True)
    preflight_parser.add_argument("--registry_root", default="project/configs/registries")
    preflight_parser.add_argument("--data_root", default=None)
    preflight_parser.add_argument("--out_dir", default=None)
    preflight_parser.add_argument("--json_output", default=None)

    for name, help_text in (
        ("plan", "Translate and validate a proposal without executing the run."),
        ("run", "Issue a proposal through the canonical operator path."),
        ("lint", "Validate a proposal and emit bounded-scope warnings."),
        ("explain", "Explain normalized proposal, compiled trigger space, and resolved experiment summary."),
    ):
        proposal_parser = operator_sub.add_parser(name, help=help_text)
        proposal_parser.add_argument("--proposal", required=True)
        proposal_parser.add_argument("--registry_root", default="project/configs/registries")
        proposal_parser.add_argument("--data_root", default=None)
        proposal_parser.add_argument("--run_id", default=None)
        proposal_parser.add_argument("--out_dir", default=None)
        proposal_parser.add_argument("--check", type=int, default=0)

    compare_parser = operator_sub.add_parser(
        "compare",
        help="Compare existing bounded runs across time slices and write a compact report.",
    )
    compare_parser.add_argument("--run_ids", required=True, help="Comma-separated run IDs to compare")
    compare_parser.add_argument("--program_id", default=None)
    compare_parser.add_argument("--data_root", default=None)

    regime_parser = operator_sub.add_parser(
        "regime-report",
        help="Build regime stability diagnostics for an existing run.",
    )
    regime_parser.add_argument("--run_id", required=True)
    regime_parser.add_argument("--data_root", default=None)

    diagnostics_parser = operator_sub.add_parser(
        "diagnose",
        help="Write structured negative-result diagnostics for an existing run.",
    )
    diagnostics_parser.add_argument("--run_id", required=True)
    diagnostics_parser.add_argument("--program_id", default=None)
    diagnostics_parser.add_argument("--data_root", default=None)

    campaign_parser = operator_sub.add_parser(
        "campaign",
        help="Run a bounded operator campaign from a campaign spec.",
    )
    campaign_sub = campaign_parser.add_subparsers(dest="campaign_command")
    campaign_start = campaign_sub.add_parser("start", help="Start or continue a campaign")
    campaign_start.add_argument("campaign_spec")
    campaign_start.add_argument("--data_root", default=None)
    campaign_start.add_argument("--plan_only", type=int, default=0)
    campaign_sub.required = True

    operator_sub.required = True

    pipeline_parser = subparsers.add_parser("pipeline", help="Pipeline commands")
    pipeline_sub = pipeline_parser.add_subparsers(dest="pipeline_command")
    pipeline_sub.add_parser("run-all", help="Run full pipeline")
    pipeline_sub.required = True

    ingest_parser = subparsers.add_parser("ingest", help="Ingest raw data from external exchanges")
    ingest_parser.add_argument("--run_id", required=True, help="Unique identifier for this run")
    ingest_parser.add_argument(
        "--symbols", required=True, help="Comma-separated list of symbols to ingest"
    )
    ingest_parser.add_argument("--start", required=True, help="Inclusive start date (YYYY-MM-DD)")
    ingest_parser.add_argument("--end", required=True, help="Inclusive end date (YYYY-MM-DD)")
    ingest_parser.add_argument(
        "--timeframe",
        default="1m",
        help="Timeframe to ingest, e.g. 1m, 5m. Only minute-based intervals are valid.",
    )
    ingest_parser.add_argument(
        "--out_root",
        default=None,
        help="Output root directory for ingested Parquet files. Defaults to data root",
    )
    ingest_parser.add_argument(
        "--concurrency", type=int, default=5, help="Number of concurrent downloads"
    )
    ingest_parser.add_argument("--max_retries", type=int, default=5)
    ingest_parser.add_argument("--retry_backoff_sec", type=float, default=2.0)
    ingest_parser.add_argument("--force", type=int, default=0)
    ingest_parser.add_argument("--log_path", default=None)

    subparsers.required = True
    return parser


def _default_out_dir(proposal_path: str | Path, run_id: str | None) -> Path:
    proposal_name = Path(proposal_path).stem or "proposal"
    suffix = run_id or proposal_name
    return Path("data") / "artifacts" / "operator" / suffix


def main() -> int:
    parser = _build_parser()
    args, unknown = parser.parse_known_args()

    if args.command == "operator":
        if args.operator_command == "preflight":
            from project.operator.preflight import run_preflight

            result = run_preflight(
                proposal_path=args.proposal,
                registry_root=args.registry_root,
                data_root=args.data_root,
                out_dir=args.out_dir,
                json_output=args.json_output,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0 if result["status"] != "block" else 1

        if args.operator_command in {"plan", "run"}:
            from project.research.agent_io.issue_proposal import issue_proposal

            plan_only = args.operator_command == "plan"
            result = issue_proposal(
                args.proposal,
                registry_root=Path(args.registry_root),
                data_root=Path(args.data_root) if args.data_root else None,
                run_id=args.run_id,
                plan_only=plan_only,
                dry_run=False,
                check=bool(args.check),
            )
            if args.out_dir:
                out_dir = Path(args.out_dir)
                out_dir.mkdir(parents=True, exist_ok=True)
                (out_dir / "operator_result.json").write_text(
                    json.dumps(result, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
            else:
                out_dir = _default_out_dir(args.proposal, args.run_id)
                out_dir.mkdir(parents=True, exist_ok=True)
                (out_dir / "operator_result.json").write_text(
                    json.dumps(result, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0 if int(result.get("returncode", 0)) == 0 else int(result["returncode"])

        if args.operator_command in {"lint", "explain"}:
            from project.operator.proposal_tools import explain_proposal, lint_proposal

            fn = explain_proposal if args.operator_command == "explain" else lint_proposal
            result = fn(
                proposal_path=args.proposal,
                registry_root=args.registry_root,
                data_root=args.data_root,
                out_dir=args.out_dir,
            )
            if args.out_dir:
                out_dir = Path(args.out_dir)
                out_dir.mkdir(parents=True, exist_ok=True)
                (out_dir / f"operator_{args.operator_command}.json").write_text(
                    json.dumps(result, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0 if result.get("status", "pass") != "block" else 1

    if args.command == "operator" and args.operator_command == "compare":
        from project.operator.stability import write_time_slice_report

        result = write_time_slice_report(
            run_ids=[part.strip() for part in str(args.run_ids).split(",") if part.strip()],
            program_id=args.program_id,
            data_root=Path(args.data_root) if args.data_root else None,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    if args.command == "operator" and args.operator_command == "regime-report":
        from project.operator.stability import write_regime_split_report

        result = write_regime_split_report(
            run_id=args.run_id,
            data_root=Path(args.data_root) if args.data_root else None,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    if args.command == "operator" and args.operator_command == "diagnose":
        from project.operator.stability import write_negative_result_diagnostics

        result = write_negative_result_diagnostics(
            run_id=args.run_id,
            program_id=args.program_id,
            data_root=Path(args.data_root) if args.data_root else None,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    if args.command == "operator" and args.operator_command == "campaign" and args.campaign_command == "start":
        from project.operator.campaign_engine import run_campaign

        result = run_campaign(
            campaign_spec_path=args.campaign_spec,
            data_root=Path(args.data_root) if args.data_root else None,
            plan_only=bool(args.plan_only),
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    if args.command == "pipeline" and args.pipeline_command == "run-all":
        sys.argv = ["pipelines/run_all.py"] + unknown
        return int(run_all.main())

    if args.command == "ingest":
        from project.pipelines.ingest import ingest_binance_um_ohlcv as _ingest_ohlcv

        ingest_argv = [
            "ingest_binance_um_ohlcv.py",
            f"--run_id={args.run_id}",
            f"--symbols={args.symbols}",
            f"--start={args.start}",
            f"--end={args.end}",
            f"--timeframe={args.timeframe}",
            f"--concurrency={args.concurrency}",
            f"--max_retries={args.max_retries}",
            f"--retry_backoff_sec={args.retry_backoff_sec}",
            f"--force={args.force}",
        ]
        if args.out_root:
            ingest_argv.append(f"--out_root={args.out_root}")
        if args.log_path:
            ingest_argv.append(f"--log_path={args.log_path}")
        ingest_argv.extend(unknown)
        orig_argv = list(sys.argv)
        sys.argv = ingest_argv
        try:
            return _ingest_ohlcv.main()
        finally:
            sys.argv = orig_argv

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
