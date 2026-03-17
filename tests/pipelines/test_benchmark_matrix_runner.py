from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2] / "project"

def _load_runner_module():
    script_path = PROJECT_ROOT / "scripts" / "run_benchmark_matrix.py"
    spec = importlib.util.spec_from_file_location("run_benchmark_matrix", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module

def test_benchmark_matrix_dry_run_writes_manifest(tmp_path, monkeypatch):
    module = _load_runner_module()
    data_root = tmp_path / "data"
    out_dir = data_root / "reports" / "perf_matrix"
    matrix_path = tmp_path / "matrix.yaml"
    matrix_path.write_text(
        "version: 1\n"
        "matrix_id: unit_matrix\n"
        "defaults:\n"
        "  mode: research\n"
        "  flags:\n"
        "    run_hypothesis_generator: 0\n"
        "runs:\n"
        "  - run_id: unit_run_1\n"
        "    symbols: BTCUSDT\n"
        "    start: 2024-01-01\n"
        "    end: 2024-01-02\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(module, "DATA_ROOT", data_root)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_benchmark_matrix.py",
            "--matrix",
            str(matrix_path),
            "--out_dir",
            str(out_dir),
        ],
    )
    rc = module.main()
    assert rc == 0

    manifest_path = out_dir / "matrix_manifest.json"
    assert manifest_path.exists()
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert payload["matrix_id"] == "unit_matrix"
    assert payload["execute"] is False
    assert payload["results"][0]["status"] == "dry_run"
    assert "--run_id" in payload["results"][0]["command"]
    assert "unit_run_1" in payload["results"][0]["command"]

def test_benchmark_matrix_execute_records_success(tmp_path, monkeypatch):
    module = _load_runner_module()
    data_root = tmp_path / "data"
    out_dir = data_root / "reports" / "perf_matrix_exec"
    matrix_path = tmp_path / "matrix_exec.yaml"
    matrix_path.write_text(
        "version: 1\n"
        "matrix_id: exec_matrix\n"
        "runs:\n"
        "  - run_id: exec_run_1\n"
        "    symbols: BTCUSDT\n"
        "    start: 2024-01-01\n"
        "    end: 2024-01-02\n",
        encoding="utf-8",
    )

    fake_run_all = tmp_path / "fake_run_all.py"
    fake_run_all.write_text("raise SystemExit(0)\n", encoding="utf-8")

    monkeypatch.setattr(module, "DATA_ROOT", data_root)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_benchmark_matrix.py",
            "--matrix",
            str(matrix_path),
            "--run_all",
            str(fake_run_all),
            "--python",
            sys.executable,
            "--execute",
            "1",
            "--out_dir",
            str(out_dir),
        ],
    )
    rc = module.main()
    assert rc == 0

    payload = json.loads((out_dir / "matrix_manifest.json").read_text(encoding="utf-8"))
    assert payload["execute"] is True
    assert payload["results"][0]["status"] == "success"
    assert payload["results"][0]["returncode"] == 0
