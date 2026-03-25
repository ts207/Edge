from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import pytest

import project.research.compile_strategy_blueprints as compiler


@dataclass
class _StubContract:
    retail_profile_name: str = "capital_constrained"
    min_trade_count: int = 0
    min_tob_coverage: float = 0.0
    min_net_expectancy_bps: float = 0.0
    max_fee_plus_slippage_bps: float | None = None
    max_daily_turnover_multiple: float | None = None
    max_concurrent_positions: int | None = None
    target_account_size_usd: float | None = None
    capital_budget_usd: float | None = None
    effective_per_position_notional_cap_usd: float | None = None
    require_retail_viability: bool = True
    forbid_fallback_in_deploy_mode: bool = True

    def as_dict(self) -> dict[str, object]:
        return {
            "retail_profile_name": self.retail_profile_name,
            "require_retail_viability": bool(self.require_retail_viability),
            "forbid_fallback_in_deploy_mode": bool(self.forbid_fallback_in_deploy_mode),
        }


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_load_run_mode_reads_mode_alias(monkeypatch, tmp_path):
    monkeypatch.setattr(compiler, "DATA_ROOT", tmp_path)
    _write_json(
        tmp_path / "runs" / "run_mode_alias" / "run_manifest.json",
        {"mode": "Certification"},
    )
    assert compiler._load_run_mode("run_mode_alias") == "certification"


def test_enforce_deploy_mode_retail_viability_blocks_fallback_tracks():
    df = pd.DataFrame(
        [
            {
                "candidate_id": "cand_1",
                "gate_promo_retail_viability": "pass",
                "promotion_track": "fallback_only",
            }
        ]
    )
    with pytest.raises(ValueError, match="fallback policy violated"):
        compiler._enforce_deploy_mode_retail_viability(
            df,
            source_label="unit_test",
            run_mode="production",
            require_retail_viability=True,
            forbid_fallback_in_deploy_mode=True,
        )


def test_main_fails_closed_for_non_viable_promoted_candidates_in_deploy_mode(
    monkeypatch, tmp_path, capsys
):
    run_id = "run_deploy_gate"
    monkeypatch.setattr(compiler, "DATA_ROOT", tmp_path)
    monkeypatch.setattr(compiler, "_load_operator_registry", lambda: {"any": {}})
    monkeypatch.setattr(
        compiler,
        "resolve_objective_profile_contract",
        lambda **_: _StubContract(),
    )

    _write_json(
        tmp_path / "runs" / run_id / "run_manifest.json",
        {"run_mode": "production"},
    )
    _write_json(
        tmp_path / "runs" / run_id / "research_checklist" / "checklist.json",
        {"decision": "PROMOTE"},
    )

    promoted_path = tmp_path / "reports" / "promotions" / run_id / "promoted_candidates.csv"
    promoted_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {
                "candidate_id": "cand_1",
                "event_type": "VOL_SHOCK",
                "effective_lag_bars": 1,
                "condition": "all",
                "action": "long",
                "direction_rule": "long_only",
                "horizon": 5,
                "status": "PROMOTED",
                "promotion_track": "standard",
                "gate_promo_retail_viability": "fail",
            }
        ]
    ).to_csv(promoted_path, index=False)

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "compile_strategy_blueprints.py",
            "--run_id",
            run_id,
            "--symbols",
            "BTCUSDT",
            "--candidates_file",
            str(promoted_path),
            "--out_dir",
            str(tmp_path / "reports" / "strategy_blueprints" / run_id),
        ],
    )

    rc = compiler.main()
    assert rc == 1
    assert "Deploy-mode retail hard gate violated" in capsys.readouterr().err
