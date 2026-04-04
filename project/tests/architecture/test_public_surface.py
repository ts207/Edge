import os
from pathlib import Path
import subprocess

def test_makefile_exports_canonical_targets():
    """Verify Makefile provides the unified 4-stage interface explicitly."""
    repo_root = Path(__file__).parent.parent.parent.parent
    makefile_path = repo_root / "Makefile"
    assert makefile_path.exists(), "Makefile not found"
    content = makefile_path.read_text()
    
    assert "discover:" in content
    assert "validate:" in content
    assert "promote:" in content
    assert "deploy-paper:" in content

import sys

def test_deprecated_cli_commands():
    """Verify deprecated operator facade is still technically reachable but explicitly warns."""
    repo_root = Path(__file__).parent.parent.parent.parent
    result = subprocess.run(
        [sys.executable, "-m", "project.cli", "-h"],
        cwd=repo_root,
        capture_output=True,
        text=True
    )
    # The help block should announce deprecation prominently
    assert "DEPRECATED" in result.stdout or "DEPRECATED" in result.stderr
