from __future__ import annotations

from pathlib import Path

import pytest

from project.spec_validation.cli import run_all_validations
from project.spec_validation.search import validate_search_spec_doc


def test_validate_search_spec_rejects_unsupported_fields() -> None:
    with pytest.raises(ValueError, match="unsupported fields: cost_profiles"):
        validate_search_spec_doc(
            {
                "kind": "search_spec",
                "triggers": {"events": ["VOL_SHOCK"]},
                "templates": ["continuation"],
                "horizons": ["15m"],
                "directions": ["long"],
                "entry_lag": 1,
                "cost_profiles": ["standard"],
            },
            source="inline_search_spec",
        )


def test_validate_search_spec_rejects_zero_entry_lag() -> None:
    with pytest.raises(ValueError, match="must be >= 1"):
        validate_search_spec_doc(
            {
                "kind": "search_spec",
                "triggers": {"events": ["VOL_SHOCK"]},
                "templates": ["continuation"],
                "horizons": ["15m"],
                "directions": ["long"],
                "entry_lag": 0,
            },
            source="inline_search_spec",
        )


def test_spec_validation_cli_checks_real_search_specs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    search_dir = tmp_path / "search"
    search_dir.mkdir(parents=True, exist_ok=True)
    (search_dir / "search_valid.yaml").write_text(
        "\n".join(
            [
                "kind: search_spec",
                "triggers:",
                "  events:",
                "    - VOL_SHOCK",
                "templates: [continuation]",
                "horizons: [15m]",
                "directions: [long]",
                "entry_lag: 1",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (search_dir / "search_invalid.yaml").write_text(
        "\n".join(
            [
                "kind: search_spec",
                "triggers:",
                "  events:",
                "    - VOL_SHOCK",
                "templates: [continuation]",
                "horizons: [15m]",
                "directions: [long]",
                "entry_lag: 0",
                "",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr("project.spec_validation.cli.SEARCH_DIR", search_dir)

    assert run_all_validations() == 1
