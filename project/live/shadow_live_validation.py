from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np
import pandas as pd

from project.core.config import get_data_root
from project.live.contracts.live_trade_context import LiveTradeContext
from project.live.decision import decide_trade_intent
from project.live.thesis_store import ThesisStore
from project.research.artifact_hygiene import build_artifact_refs, infer_workspace_root, invalid_artifact_header
from project.research.thesis_evidence_runner import (
    DOCS_DIR,
    _liquidation_cascade_events,
    _liquidity_vacuum_events,
    _load_raw_dataset,
    _policy_specs,
    _vol_shock_events,
)

DEFAULT_WINDOW_DAYS = 14
DEFAULT_CONTEXT_WINDOW_BARS = 3
DEFAULT_RUN_ID = "block_g_shadow_live_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _active_events_in_window(event_masks: Mapping[str, pd.Series], idx: int, window_bars: int) -> list[str]:
    lo = max(0, idx - window_bars)
    active: list[str] = []
    for event_id, mask in event_masks.items():
        if bool(mask.iloc[lo: idx + 1].any()):
            active.append(event_id)
    return active


def _current_bar_events(event_masks: Mapping[str, pd.Series], idx: int) -> list[str]:
    return [event_id for event_id, mask in event_masks.items() if bool(mask.iloc[idx])]


def _approx_execution_features(bars: pd.DataFrame, idx: int) -> dict[str, float]:
    row = bars.iloc[idx]
    close = float(pd.to_numeric(pd.Series([row.get("close")]), errors="coerce").iloc[0] or 0.0)
    high = float(pd.to_numeric(pd.Series([row.get("high")]), errors="coerce").iloc[0] or close)
    low = float(pd.to_numeric(pd.Series([row.get("low")]), errors="coerce").iloc[0] or close)
    quote_volume = float(pd.to_numeric(pd.Series([row.get("quote_volume", row.get("volume", 0.0))]), errors="coerce").iloc[0] or 0.0)
    volume = pd.to_numeric(bars["volume"], errors="coerce")
    median_volume = float(volume.shift(1).rolling(72, min_periods=12).median().iloc[idx] or 0.0)
    spread_bps = max(0.5, min(20.0, ((high - low) / max(close, 1e-9)) * 10_000.0 * 0.08))
    depth_usd = max(0.0, quote_volume * 0.05)
    tob_coverage = max(0.2, min(1.0, quote_volume / max(median_volume * max(close, 1.0), 1.0)))
    return {
        "spread_bps": spread_bps,
        "depth_usd": depth_usd,
        "tob_coverage": tob_coverage,
    }


def _contexts_for_symbol(
    *,
    symbol: str,
    data_root: Path,
    start_time: pd.Timestamp,
    context_window_bars: int,
) -> list[LiveTradeContext]:
    specs = {spec.candidate_id: spec for spec in _policy_specs(None)}
    bars = _load_raw_dataset(symbol, "ohlcv_5m", data_root=data_root)
    if bars.empty:
        return []
    funding = _load_raw_dataset(symbol, "funding", data_root=data_root)
    open_interest = _load_raw_dataset(symbol, "open_interest", data_root=data_root)
    event_masks: dict[str, pd.Series] = {
        "VOL_SHOCK": _vol_shock_events(bars, specs["THESIS_VOL_SHOCK"].params),
        "LIQUIDITY_VACUUM": _liquidity_vacuum_events(bars, specs["THESIS_LIQUIDITY_VACUUM"].params),
    }
    if funding.empty or open_interest.empty:
        event_masks["LIQUIDATION_CASCADE"] = pd.Series(False, index=bars.index, dtype=bool)
    else:
        event_masks["LIQUIDATION_CASCADE"] = _liquidation_cascade_events(
            bars,
            funding,
            open_interest,
            specs["THESIS_LIQUIDATION_CASCADE"].params,
        )

    close = pd.to_numeric(bars["close"], errors="coerce")
    realized_vol = np.sqrt(np.log(close / close.shift(1)).pow(2).rolling(12, min_periods=12).mean())
    vol_median = float(realized_vol.median()) if realized_vol.notna().any() else 0.0

    contexts: list[LiveTradeContext] = []
    symbol_mask = bars["timestamp"] >= start_time
    for idx in np.flatnonzero(symbol_mask.to_numpy(dtype=bool)):
        current_events = _current_bar_events(event_masks, idx)
        active_events = _active_events_in_window(event_masks, idx, context_window_bars)
        if not current_events and len(active_events) < 2:
            continue
        current_event_id = current_events[0] if current_events else active_events[0]
        rv_value = float(realized_vol.iloc[idx]) if pd.notna(realized_vol.iloc[idx]) else None
        live_features = {
            **_approx_execution_features(bars, idx),
            "realized_vol": rv_value,
        }
        contexts.append(
            LiveTradeContext(
                timestamp=str(bars.iloc[idx]["timestamp"]),
                symbol=symbol,
                timeframe="5m",
                primary_event_id=current_event_id,
                event_family=current_event_id,
                canonical_regime=(
                    "HIGH_VOL" if rv_value is not None and rv_value >= vol_median else "LOW_VOL"
                ),
                event_side="both",
                live_features=live_features,
                regime_snapshot={
                    "canonical_regime": "HIGH_VOL" if rv_value is not None and rv_value >= vol_median else "LOW_VOL"
                },
                execution_env={"runtime_mode": "monitor_only"},
                portfolio_state={},
                active_event_families=active_events,
                active_event_ids=active_events,
                active_episode_ids=[],
                contradiction_event_families=[],
                contradiction_event_ids=[],
                episode_snapshot={},
            )
        )
    return contexts


def _trace_row(context: LiveTradeContext, outcome: Any) -> dict[str, Any]:
    retrieved = []
    matched_clauses: list[str] = []
    missing_confirmations: list[str] = []
    contradictions: list[str] = []
    invalidators: list[str] = []
    overlap_groups: list[str] = []
    for match in outcome.ranked_matches:
        overlap_group = str(match.thesis.governance.overlap_group_id or "")
        if overlap_group and overlap_group not in overlap_groups:
            overlap_groups.append(overlap_group)
        matched_clauses.extend(match.reasons_for)
        missing_confirmations.extend(item for item in match.reasons_against if item.startswith("confirmation_missing:"))
        contradictions.extend(item for item in match.reasons_against if item.startswith("contradiction_event:"))
        invalidators.extend(item for item in match.reasons_against if item == "invalidation_triggered")
        retrieved.append(
            {
                "thesis_id": match.thesis.thesis_id,
                "promotion_class": match.thesis.promotion_class,
                "eligibility_passed": bool(match.eligibility_passed),
                "support_score": float(match.support_score),
                "contradiction_penalty": float(match.contradiction_penalty),
                "overlap_group_id": overlap_group,
                "reasons_for": list(match.reasons_for),
                "reasons_against": list(match.reasons_against),
            }
        )
    top_metadata = dict(outcome.trade_intent.metadata or {})
    explanation_complete = bool(
        retrieved
        and (outcome.trade_intent.reasons_for or outcome.trade_intent.reasons_against)
        and top_metadata.get("overlap_group_id", "")
    )
    suppression_reason = ""
    if outcome.trade_intent.action == "reject":
        suppression_reason = ";".join(outcome.trade_intent.reasons_against)
    elif missing_confirmations:
        suppression_reason = ";".join(sorted(set(missing_confirmations)))
    return {
        "timestamp": context.timestamp,
        "symbol": context.symbol,
        "timeframe": context.timeframe,
        "primary_event_id": str(context.primary_event_id or context.event_family),
        "canonical_regime": str(
            context.canonical_regime or context.regime_snapshot.get("canonical_regime", "")
        ),
        "active_event_ids": list(context.active_event_ids),
        "compat_event_family": str(context.event_family),
        "compat_active_event_families": list(context.active_event_families),
        "active_episodes": list(context.active_episode_ids),
        "retrieved_theses": retrieved,
        "matched_clauses": sorted(set(matched_clauses)),
        "missing_confirmations": sorted(set(missing_confirmations)),
        "contradictions": sorted(set(contradictions)),
        "invalidators": sorted(set(invalidators)),
        "overlap_group_diagnostics": {
            "active_overlap_group_ids": overlap_groups,
            "top_overlap_group_id": str(top_metadata.get("overlap_group_id", "")),
            "top_thesis_id": outcome.trade_intent.thesis_id,
        },
        "action_chosen": outcome.trade_intent.action,
        "suppression_reason": suppression_reason,
        "explanation_complete": explanation_complete,
    }


def run_shadow_live_thesis_validation(
    *,
    thesis_store_path: str | Path,
    data_root: str | Path | None = None,
    out_dir: str | Path | None = None,
    docs_dir: str | Path | None = None,
    run_id: str = DEFAULT_RUN_ID,
    symbols: Iterable[str] = ("BTCUSDT", "ETHUSDT"),
    window_days: int = DEFAULT_WINDOW_DAYS,
    context_window_bars: int = DEFAULT_CONTEXT_WINDOW_BARS,
) -> dict[str, Path]:
    thesis_store = ThesisStore.from_path(thesis_store_path)
    resolved_data_root = Path(data_root) if data_root is not None else Path(get_data_root())
    report_dir = _ensure_dir(Path(out_dir) if out_dir is not None else resolved_data_root / "reports" / "shadow_live" / run_id)
    resolved_docs = _ensure_dir(Path(docs_dir) if docs_dir is not None else DOCS_DIR)

    max_ts: pd.Timestamp | None = None
    for symbol in symbols:
        bars = _load_raw_dataset(symbol, "ohlcv_5m", data_root=resolved_data_root)
        if bars.empty:
            continue
        candidate = bars["timestamp"].max()
        if max_ts is None or candidate > max_ts:
            max_ts = candidate
    if max_ts is None:
        raise ValueError("Shadow live validation requires raw bar data for at least one symbol")
    start_time = max_ts - pd.Timedelta(days=int(window_days))

    contexts: list[LiveTradeContext] = []
    for symbol in symbols:
        contexts.extend(
            _contexts_for_symbol(
                symbol=symbol,
                data_root=resolved_data_root,
                start_time=start_time,
                context_window_bars=int(context_window_bars),
            )
        )
    contexts.sort(key=lambda item: (item.timestamp, item.symbol))

    trace_rows: list[dict[str, Any]] = []
    action_counts: Counter[str] = Counter()
    chosen_theses: Counter[str] = Counter()
    confirm_thesis_ids = {thesis.thesis_id for thesis in thesis_store.active_theses() if str(thesis.governance.operational_role or '').strip().lower() == 'confirm'}
    confirmation_stats_by_id: dict[str, Counter[str]] = {thesis_id: Counter() for thesis_id in sorted(confirm_thesis_ids)}
    silent_match_count = 0
    unexplained_hold_count = 0
    overlap_metadata_missing = 0
    for context in contexts:
        outcome = decide_trade_intent(context=context, thesis_store=thesis_store, include_pending=False)
        row = _trace_row(context, outcome)
        trace_rows.append(row)
        action_counts[row["action_chosen"]] += 1
        if outcome.trade_intent.thesis_id:
            chosen_theses[outcome.trade_intent.thesis_id] += 1
        if not row["matched_clauses"]:
            silent_match_count += 1
        if row["action_chosen"] == "watch" and not row["suppression_reason"]:
            unexplained_hold_count += 1
        if not row["overlap_group_diagnostics"].get("top_overlap_group_id"):
            overlap_metadata_missing += 1
        for retrieved in row["retrieved_theses"]:
            thesis_id = str(retrieved.get("thesis_id", "")).strip()
            if thesis_id not in confirmation_stats_by_id:
                continue
            stats = confirmation_stats_by_id[thesis_id]
            stats["retrieved_cycles"] += 1
            if retrieved["eligibility_passed"]:
                stats["eligible_cycles"] += 1
            if any(reason.startswith("confirmation_match:") for reason in retrieved["reasons_for"]):
                stats["confirmation_match_cycles"] += 1
            if any(reason.startswith("confirmation_missing:") for reason in retrieved["reasons_against"]):
                stats["confirmation_missing_cycles"] += 1
            if row["overlap_group_diagnostics"].get("top_thesis_id") == thesis_id:
                stats["top_ranked_cycles"] += 1

    trace_path = report_dir / "shadow_live_thesis_trace.jsonl"
    with trace_path.open("w", encoding="utf-8") as handle:
        for row in trace_rows:
            handle.write(json.dumps(row) + "\n")

    confirmation_payload_by_id = {
        thesis_id: {
            "retrieved_cycles": int(stats.get("retrieved_cycles", 0)),
            "eligible_cycles": int(stats.get("eligible_cycles", 0)),
            "confirmation_match_cycles": int(stats.get("confirmation_match_cycles", 0)),
            "confirmation_missing_cycles": int(stats.get("confirmation_missing_cycles", 0)),
            "top_ranked_cycles": int(stats.get("top_ranked_cycles", 0)),
        }
        for thesis_id, stats in confirmation_stats_by_id.items()
    }
    aggregate_confirmation_payload = {
        key: int(sum(payload.get(key, 0) for payload in confirmation_payload_by_id.values()))
        for key in ("retrieved_cycles", "eligible_cycles", "confirmation_match_cycles", "confirmation_missing_cycles", "top_ranked_cycles")
    }

    summary_payload = {
        "run_id": run_id,
        "generated_at_utc": _utc_now(),
        "window": {
            "start": str(start_time),
            "end": str(max_ts),
            "window_days": int(window_days),
            "context_window_bars": int(context_window_bars),
        },
        "symbols": list(symbols),
        "contexts_evaluated": len(trace_rows),
        "action_counts": dict(action_counts),
        "chosen_thesis_counts": dict(chosen_theses),
        "confirmation_thesis_stats": aggregate_confirmation_payload,
        "confirmation_thesis_stats_by_id": confirmation_payload_by_id,
        "quality_checks": {
            "silent_match_count": silent_match_count,
            "unexplained_hold_count": unexplained_hold_count,
            "overlap_metadata_missing_count": overlap_metadata_missing,
            "no_silent_thesis_matches": silent_match_count == 0,
            "no_unexplained_holds": unexplained_hold_count == 0,
            "overlap_metadata_visible_consistently": overlap_metadata_missing == 0,
        },
    }
    workspace_root = infer_workspace_root(resolved_data_root, resolved_docs, report_dir)
    artifact_refs, invalid_refs = build_artifact_refs(
        {
            "trace": trace_path,
        },
        workspace_root=workspace_root,
    )
    summary_payload["workspace_root"] = workspace_root.as_posix()
    summary_payload["artifact_refs"] = artifact_refs
    summary_payload["invalid_artifact_refs"] = invalid_refs
    summary_json = report_dir / "shadow_live_thesis_summary.json"
    summary_md = report_dir / "shadow_live_thesis_summary.md"
    summary_json.write_text(json.dumps(summary_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = invalid_artifact_header(invalid_refs) + [
        "# Shadow live thesis summary",
        "",
        f"- run_id: `{run_id}`",
        f"- contexts_evaluated: `{len(trace_rows)}`",
        f"- window: `{start_time}` -> `{max_ts}`",
        f"- symbols: `{', '.join(symbols)}`",
        f"- trace_path: `{artifact_refs['trace']['path']}`",
        "",
        "## Action counts",
        "",
    ]
    for action, count in sorted(action_counts.items()):
        lines.append(f"- `{action}`: `{count}`")
    lines.extend([
        "",
        "## Confirmation thesis diagnostics",
        "",
        f"- retrieved_cycles: `{aggregate_confirmation_payload['retrieved_cycles']}`",
        f"- eligible_cycles: `{aggregate_confirmation_payload['eligible_cycles']}`",
        f"- confirmation_match_cycles: `{aggregate_confirmation_payload['confirmation_match_cycles']}`",
        f"- confirmation_missing_cycles: `{aggregate_confirmation_payload['confirmation_missing_cycles']}`",
        f"- top_ranked_cycles: `{aggregate_confirmation_payload['top_ranked_cycles']}`",
        "",
        "## Confirmation thesis breakdown",
        "",
    ])
    for thesis_id, payload in confirmation_payload_by_id.items():
        lines.append(
            f"- `{thesis_id}` — retrieved `{payload['retrieved_cycles']}`, matches `{payload['confirmation_match_cycles']}`, missing `{payload['confirmation_missing_cycles']}`, top-ranked `{payload['top_ranked_cycles']}`"
        )
    lines.extend([
        "",
        "## Quality checks",
        "",
        f"- no_silent_thesis_matches: `{summary_payload['quality_checks']['no_silent_thesis_matches']}`",
        f"- no_unexplained_holds: `{summary_payload['quality_checks']['no_unexplained_holds']}`",
        f"- overlap_metadata_visible_consistently: `{summary_payload['quality_checks']['overlap_metadata_visible_consistently']}`",
        "",
    ])
    summary_md.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

    artifact_refs, invalid_refs = build_artifact_refs(
        {
            "trace": trace_path,
            "summary_json": summary_json,
            "summary_md": summary_md,
        },
        workspace_root=workspace_root,
    )
    summary_payload["artifact_refs"] = artifact_refs
    summary_payload["invalid_artifact_refs"] = invalid_refs
    summary_json.write_text(json.dumps(summary_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary_md.write_text(
        "\n".join(invalid_artifact_header(invalid_refs) + lines[len(invalid_artifact_header(invalid_refs)):]).rstrip() + "\n",
        encoding="utf-8",
    )

    docs_summary_json = resolved_docs / "shadow_live_thesis_summary.json"
    docs_summary_md = resolved_docs / "shadow_live_thesis_summary.md"
    docs_summary_json.write_text(json.dumps(summary_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    docs_summary_md.write_text(summary_md.read_text(encoding="utf-8"), encoding="utf-8")
    return {
        "trace": trace_path,
        "summary_json": summary_json,
        "summary_md": summary_md,
        "docs_summary_json": docs_summary_json,
        "docs_summary_md": docs_summary_md,
    }


__all__ = ["run_shadow_live_thesis_validation", "DEFAULT_RUN_ID"]
