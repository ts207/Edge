"""Shared test configuration and canonical path constants.

All tests must import path roots from here rather than computing
their own via parents[N] — that pattern is fragile and wrong across
different nesting depths.
"""
from __future__ import annotations

from pathlib import Path

# project/tests/conftest.py -> parents[0]=tests, parents[1]=project, parents[2]=EDGEE-main
REPO_ROOT: Path = Path(__file__).resolve().parents[2]
PROJECT_ROOT: Path = REPO_ROOT / "project"
SPEC_ROOT: Path = REPO_ROOT / "spec"
