from __future__ import annotations

from pathlib import Path
from typing import Any, Dict
from project import PROJECT_ROOT

import yaml

CORE_KEYS = {"event_type", "reports_dir", "events_file", "signal_column", "parameters"}
META_KEYS = {
    "active",
    "status",
    "description",
    "provenance",
    "deprecated",
    "kind",
    "version",
}


def _load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def build_unified_registry(repo_root: Path) -> Dict[str, Any]:
    spec_root = repo_root / "spec"
    events_root = spec_root / "events"

    canonical = _load_yaml(events_root / "canonical_event_registry.yaml")
    family_by_event: Dict[str, str] = {}
    for family, row in (canonical.get("families", {}) or {}).items():
        if not isinstance(row, dict):
            continue
        for event_type in row.get("events", []) or []:
            token = str(event_type).strip().upper()
            if token:
                family_by_event[token] = str(family).strip().upper()

    event_defaults = _load_yaml(events_root / "_defaults.yaml")
    event_family_defaults = _load_yaml(events_root / "_families.yaml")
    template_registry = _load_yaml(spec_root / "templates" / "event_template_registry.yaml")

    # Build event rows from per-event specs first.
    event_rows: Dict[str, Dict[str, Any]] = {}
    for spec_path in sorted(events_root.glob("*.yaml")):
        if spec_path.name.startswith("_") or spec_path.name == "canonical_event_registry.yaml":
            continue
        payload = _load_yaml(spec_path)
        if not payload:
            continue
        if bool(payload.get("deprecated", False)) or not bool(payload.get("active", True)):
            continue
        if payload.get("kind") in {
            "canonical_event_registry",
            "event_config_defaults",
            "event_family_defaults",
            "event_unified_registry",
        }:
            continue

        event_type = str(payload.get("event_type", "")).strip().upper()
        if not event_type:
            continue

        params = payload.get("parameters", {})
        if not isinstance(params, dict):
            params = {}

        legacy_top_level = {
            str(k): v for k, v in payload.items() if k not in CORE_KEYS and k not in META_KEYS
        }
        merged_event_params = dict(legacy_top_level)
        merged_event_params.update(params)

        event_rows[event_type] = {
            "canonical_family": family_by_event.get(event_type, event_type),
            "reports_dir": str(payload["reports_dir"]),
            "events_file": str(payload["events_file"]),
            "signal_column": str(payload["signal_column"]),
            "parameters": merged_event_params,
        }

    template_defaults = template_registry.get("defaults", {})
    if not isinstance(template_defaults, dict):
        template_defaults = {}
    template_families = template_registry.get("families", {})
    if not isinstance(template_families, dict):
        template_families = {}
    template_events = template_registry.get("events", {})
    if not isinstance(template_events, dict):
        template_events = {}

    for event_type, row in template_events.items():
        token = str(event_type).strip().upper()
        if not token or not isinstance(row, dict):
            continue
        if not bool(row.get("active", True)) or bool(row.get("deprecated", False)):
            if token in event_rows:
                del event_rows[token]
            continue
        base = event_rows.setdefault(
            token,
            {
                "canonical_family": str(
                    row.get("canonical_family", family_by_event.get(token, token))
                )
                .strip()
                .upper()
                or token,
                "reports_dir": "",
                "events_file": "",
                "signal_column": "",
                "parameters": {},
            },
        )
        if row.get("canonical_family"):
            base["canonical_family"] = str(row.get("canonical_family")).strip().upper()
        for key in (
            "templates",
            "horizons",
            "conditioning_cols",
            "max_candidates_per_run",
            "state_overrides",
        ):
            if key in row:
                base[key] = row.get(key)
        if "parameters" in row and isinstance(row["parameters"], dict):
            base.setdefault("parameters", {}).update(row["parameters"])
        if "synthetic_coverage" in row:
            base.setdefault("parameters", {})["synthetic_coverage"] = row["synthetic_coverage"]

    family_rows: Dict[str, Dict[str, Any]] = {}
    legacy_family_rows = event_family_defaults.get("families", {})
    if not isinstance(legacy_family_rows, dict):
        legacy_family_rows = {}

    all_families = set()
    all_families.update(str(k).strip().upper() for k in legacy_family_rows.keys())
    all_families.update(str(k).strip().upper() for k in template_families.keys())
    all_families.update(
        str(row.get("canonical_family", "")).strip().upper() for row in event_rows.values()
    )
    all_families.discard("")

    for family in sorted(all_families):
        legacy_row = legacy_family_rows.get(family, {})
        params = {}
        if isinstance(legacy_row, dict):
            raw = legacy_row.get("parameters", {})
            if isinstance(raw, dict):
                params = dict(raw)

        out: Dict[str, Any] = {"parameters": params}
        template_row = template_families.get(family, {})
        if isinstance(template_row, dict):
            for key in (
                "templates",
                "horizons",
                "conditioning_cols",
                "max_candidates_per_run",
            ):
                if key in template_row:
                    out[key] = template_row.get(key)
        family_rows[family] = out

    defaults = {
        "parameters": dict(
            event_defaults.get("parameters", {})
            if isinstance(event_defaults.get("parameters", {}), dict)
            else {}
        ),
        "templates": template_defaults.get("templates", []),
        "horizons": template_defaults.get("horizons", []),
        "conditioning_cols": template_defaults.get("conditioning_cols", []),
        "max_candidates_per_run": template_defaults.get("max_candidates_per_run", 1000),
    }

    return {
        "version": 1,
        "kind": "event_unified_registry",
        "metadata": {
            "status": "authoritative",
            "legacy_sources": {
                "event_defaults": "spec/events/_defaults.yaml",
                "event_family_defaults": "spec/events/_families.yaml",
                "event_specs_dir": "spec/events",
                "canonical_event_registry": "spec/events/canonical_event_registry.yaml",
                "template_registry": "spec/templates/event_template_registry.yaml",
            },
            "notes": (
                "Single event-centric schema for phase1+phase2 composition. "
                "Legacy specs retained for compatibility and drift checks."
            ),
        },
        "defaults": defaults,
        "families": family_rows,
        "events": {k: event_rows[k] for k in sorted(event_rows)},
    }


def main() -> int:
    repo_root = PROJECT_ROOT.parent
    unified = build_unified_registry(repo_root)
    out_path = repo_root / "spec" / "events" / "event_registry_unified.yaml"
    out_path.write_text(yaml.safe_dump(unified, sort_keys=False), encoding="utf-8")
    print(f"Wrote {out_path} with {len(unified.get('events', {}))} events")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
