from __future__ import annotations

import importlib
from pathlib import Path

import pytest


def test_pipeline_compat_package_removed() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    assert not (repo_root / "project" / "pipelines" / "compat").exists()


def test_research_compat_package_removed() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    compat_root = repo_root / "project" / "research" / "compat"
    assert not compat_root.exists()
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("project.research.compat")


def test_strategy_compat_packages_removed() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    for rel_path, module_name in (
        ("project/strategy_dsl", "project.strategy_dsl"),
        ("project/strategy_templates", "project.strategy_templates"),
    ):
        compat_root = repo_root / rel_path
        assert not compat_root.exists()
        with pytest.raises(ModuleNotFoundError):
            importlib.import_module(module_name)


def test_dead_files_and_um_wrapper_scripts_removed() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    removed_paths = (
        repo_root / "project" / "scripts" / "no_op.py",
        repo_root / "project" / "pipelines" / "research" / "no_op.py",
        repo_root / "project" / "pipelines" / "ingest" / "ingest_binance_um_ohlcv_1m.py",
        repo_root / "project" / "pipelines" / "ingest" / "ingest_binance_um_ohlcv_5m.py",
        repo_root / "tests" / "test_phase2_fallback_canaries.py",
    )
    for path in removed_paths:
        assert not path.exists(), f"legacy surface still exists: {path.relative_to(repo_root)}"
