from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from project.core.config import get_data_root
from project.research.artifact_hygiene import build_artifact_refs, infer_workspace_root, invalid_artifact_header
from project.research.seed_bootstrap import DOCS_GENERATED
from project.research.seed_empirical import _jsonl_records

DEFAULT_COMPONENTS: tuple[str, str] = ("THESIS_VOL_SHOCK", "THESIS_LIQUIDITY_VACUUM")
DEFAULT_CANDIDATE_ID = "THESIS_VOL_SHOCK_LIQUIDITY_CONFIRM"
DEFAULT_RUN_ID = DEFAULT_CANDIDATE_ID


def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _load_component_rows(data_root: Path, thesis_id: str) -> list[dict[str, Any]]:
    path = data_root / "reports" / "promotions" / thesis_id / "evidence_bundles.jsonl"
    return [row for row in _jsonl_records(path) if isinstance(row, Mapping)]


def _index_by_symbol(rows: Iterable[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        symbol = str(row.get("symbol", row.get("sample_definition", {}).get("symbol", ""))).strip().upper()
        if symbol:
            out[symbol] = dict(row)
    return out


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except Exception:
        return default


def _bool_all(*values: bool) -> bool:
    return all(bool(value) for value in values)


def _merged_confounders(left: Mapping[str, Any], right: Mapping[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    left_f = left.get("falsification_results", {}) if isinstance(left.get("falsification_results"), Mapping) else {}
    right_f = right.get("falsification_results", {}) if isinstance(right.get("falsification_results"), Mapping) else {}
    neg = max(
        _safe_float(left_f.get("negative_control_pass_rate", 0.0), 0.0),
        _safe_float(right_f.get("negative_control_pass_rate", 0.0), 0.0),
    )
    out["negative_control_pass_rate"] = neg
    for key in sorted(set(left_f).intersection(set(right_f))):
        if key == "negative_control_pass_rate":
            continue
        lval = left_f.get(key)
        rval = right_f.get(key)
        if not isinstance(lval, Mapping) or not isinstance(rval, Mapping):
            continue
        passed = _bool_all(lval.get("passed", False), rval.get("passed", False))
        out[key] = {
            "available": bool(lval.get("available", False) and rval.get("available", False)),
            "passed": passed,
            "left_source": left.get("candidate_id", ""),
            "right_source": right.get("candidate_id", ""),
        }
    return out


def synthesize_confirmation_bundle(
    *,
    candidate_id: str = DEFAULT_CANDIDATE_ID,
    component_ids: tuple[str, str] = DEFAULT_COMPONENTS,
    data_root: str | Path | None = None,
    docs_dir: str | Path | None = None,
    overlap_factor: float = 0.5,
) -> dict[str, Path]:
    resolved_data_root = Path(data_root) if data_root is not None else Path(get_data_root())
    docs_root = _ensure_dir(Path(docs_dir) if docs_dir is not None else DOCS_GENERATED)

    left_rows = _load_component_rows(resolved_data_root, component_ids[0])
    right_rows = _load_component_rows(resolved_data_root, component_ids[1])
    left_by_symbol = _index_by_symbol(left_rows)
    right_by_symbol = _index_by_symbol(right_rows)
    shared_symbols = sorted(set(left_by_symbol).intersection(right_by_symbol))

    out_dir = _ensure_dir(resolved_data_root / "reports" / "promotions" / candidate_id)
    bundle_path = out_dir / "evidence_bundles.jsonl"
    summary_json = docs_root / "structural_confirmation_summary.json"
    summary_md = docs_root / "structural_confirmation_summary.md"

    bundles: list[dict[str, Any]] = []
    for symbol in shared_symbols:
        left = left_by_symbol[symbol]
        right = right_by_symbol[symbol]
        left_sample = left.get("sample_definition", {}) if isinstance(left.get("sample_definition"), Mapping) else {}
        right_sample = right.get("sample_definition", {}) if isinstance(right.get("sample_definition"), Mapping) else {}
        n_events = int(min(_safe_int(left_sample.get("n_events", 0), 0), _safe_int(right_sample.get("n_events", 0), 0)) * overlap_factor)
        validation = int(min(_safe_int(left_sample.get("validation_samples", 0), 0), _safe_int(right_sample.get("validation_samples", 0), 0)) * overlap_factor)
        test = int(min(_safe_int(left_sample.get("test_samples", 0), 0), 0) * 0)  # placeholder to preserve shape
        test = int(min(_safe_int(left_sample.get("test_samples", 0), 0), _safe_int(right_sample.get("test_samples", 0), 0)) * overlap_factor)
        if n_events < 20 or validation <= 0 or test <= 0:
            continue
        left_eff = left.get("effect_estimates", {}) if isinstance(left.get("effect_estimates"), Mapping) else {}
        right_eff = right.get("effect_estimates", {}) if isinstance(right.get("effect_estimates"), Mapping) else {}
        left_cost = left.get("cost_robustness", {}) if isinstance(left.get("cost_robustness"), Mapping) else {}
        right_cost = right.get("cost_robustness", {}) if isinstance(right.get("cost_robustness"), Mapping) else {}
        left_unc = left.get("uncertainty_estimates", {}) if isinstance(left.get("uncertainty_estimates"), Mapping) else {}
        right_unc = right.get("uncertainty_estimates", {}) if isinstance(right.get("uncertainty_estimates"), Mapping) else {}
        left_stab = left.get("stability_tests", {}) if isinstance(left.get("stability_tests"), Mapping) else {}
        right_stab = right.get("stability_tests", {}) if isinstance(right.get("stability_tests"), Mapping) else {}
        left_meta = left.get("metadata", {}) if isinstance(left.get("metadata"), Mapping) else {}
        right_meta = right.get("metadata", {}) if isinstance(right.get("metadata"), Mapping) else {}

        estimate_bps = min(_safe_float(left_eff.get("estimate_bps", 0.0), 0.0), _safe_float(right_eff.get("estimate_bps", 0.0), 0.0))
        net_expectancy = min(_safe_float(left_cost.get("net_expectancy_bps", 0.0), 0.0), _safe_float(right_cost.get("net_expectancy_bps", 0.0), 0.0))
        q_value = max(_safe_float(left_unc.get("q_value", 1.0), 1.0), _safe_float(right_unc.get("q_value", 1.0), 1.0))
        stability = min(_safe_float(left_stab.get("stability_score", 0.0), 0.0), _safe_float(right_stab.get("stability_score", 0.0), 0.0))
        falsification = _merged_confounders(left, right)
        bundle = {
            "candidate_id": candidate_id,
            "event_type": "VOL_SHOCK_LIQUIDITY_CONFIRM",
            "event_family": "VOL_SHOCK",
            "symbol": symbol,
            "sample_definition": {
                "n_events": n_events,
                "validation_samples": validation,
                "test_samples": test,
                "symbol": symbol,
                "horizon_bars": min(_safe_int(left_sample.get("horizon_bars", 24), 24), _safe_int(right_sample.get("horizon_bars", 24), 24)),
                "start": max(str(left_sample.get("start", "")), str(right_sample.get("start", ""))),
                "end": min(str(left_sample.get("end", "")), str(right_sample.get("end", ""))),
            },
            "split_definition": {
                "split_scheme_id": "component_overlap_bridge_2022",
                "validation_window": "2021",
                "test_window": "2022",
            },
            "effect_estimates": {
                "estimate_bps": estimate_bps,
                "validation_mean_bps": min(_safe_float(left_eff.get("validation_mean_bps", 0.0), 0.0), _safe_float(right_eff.get("validation_mean_bps", 0.0), 0.0)),
                "test_mean_bps": min(_safe_float(left_eff.get("test_mean_bps", 0.0), 0.0), _safe_float(right_eff.get("test_mean_bps", 0.0), 0.0)),
                "payoff_mode": "absolute_return",
            },
            "cost_robustness": {
                "fees_bps": max(_safe_float(left_cost.get("fees_bps", 0.0), 0.0), _safe_float(right_cost.get("fees_bps", 0.0), 0.0)),
                "net_expectancy_bps": net_expectancy,
                "gross_expectancy_bps": estimate_bps,
            },
            "uncertainty_estimates": {
                "q_value": q_value,
                "effect_p_value": q_value,
            },
            "stability_tests": {
                "stability_score": stability,
                "validation_mean_bps": min(_safe_float(left_stab.get("validation_mean_bps", 0.0), 0.0), _safe_float(right_stab.get("validation_mean_bps", 0.0), 0.0)),
                "test_mean_bps": min(_safe_float(left_stab.get("test_mean_bps", 0.0), 0.0), _safe_float(right_stab.get("test_mean_bps", 0.0), 0.0)),
                "validation_test_gap_bps": max(_safe_float(left_stab.get("validation_test_gap_bps", 0.0), 0.0), _safe_float(right_stab.get("validation_test_gap_bps", 0.0), 0.0)),
            },
            "falsification_results": falsification,
            "multiplicity_adjustment": {
                "correction_method": "derived_component_bridge",
                "adjusted_q_value": q_value,
            },
            "metadata": {
                "has_realized_oos_path": bool(left_meta.get("has_realized_oos_path", False) and right_meta.get("has_realized_oos_path", False)),
                "derived_from_component_evidence": True,
                "derivation_method": "conservative_component_minima",
                "component_candidates": list(component_ids),
                "thesis_id": candidate_id,
                "thesis_contract_id": candidate_id,
                "thesis_contract_ids": [candidate_id],
                "event_contract_ids": ["VOL_SHOCK", "LIQUIDITY_VACUUM"],
                "input_symbols": sorted(set((left_meta.get("input_symbols", []) or []) + (right_meta.get("input_symbols", []) or []))),
                "notes": "Derived bridge confirmation thesis synthesized conservatively from existing VOL_SHOCK and LIQUIDITY_VACUUM raw-data bundles; direct paired-event study still missing.",
            },
        }
        bundles.append(bundle)

    with bundle_path.open('w', encoding='utf-8') as handle:
        for row in bundles:
            handle.write(json.dumps(row) + '\n')

    payload = {
        'candidate_id': candidate_id,
        'component_candidates': list(component_ids),
        'generated_bundle_count': len(bundles),
        'symbols': shared_symbols,
        'overlap_factor': overlap_factor,
        'derived_from_component_evidence': True,
    }
    workspace_root = infer_workspace_root(resolved_data_root, docs_root)
    artifact_refs, invalid_refs = build_artifact_refs(
        {"bundle_path": bundle_path},
        workspace_root=workspace_root,
    )
    payload["workspace_root"] = workspace_root.as_posix()
    payload["artifact_refs"] = artifact_refs
    payload["invalid_artifact_refs"] = invalid_refs
    summary_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    lines = invalid_artifact_header(invalid_refs) + [
        '# Structural confirmation synthesis summary',
        '',
        f'- candidate_id: `{candidate_id}`',
        f'- component_candidates: `{component_ids[0]}`, `{component_ids[1]}`',
        f'- generated_bundle_count: `{len(bundles)}`',
        f'- overlap_factor: `{overlap_factor}`',
        f"- bundle_path: `{artifact_refs['bundle_path']['path']}`",
        '',
        'This artifact is a conservative bridge synthesized from existing raw-data evidence bundles for the component events.',
        'It is suitable for seed packaging and overlap activation, but it does not replace a direct paired-event study.',
        '',
    ]
    summary_md.write_text('\n'.join(lines), encoding='utf-8')
    return {'bundle_path': bundle_path, 'summary_json': summary_json, 'summary_md': summary_md}


__all__ = ['synthesize_confirmation_bundle', 'DEFAULT_CANDIDATE_ID', 'DEFAULT_COMPONENTS']
