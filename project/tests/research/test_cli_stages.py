import subprocess
import sys

def test_cli_help():
    cmds = ["discover", "validate", "promote", "deploy"]
    for cmd in cmds:
        result = subprocess.run(
            [sys.executable, "project/cli.py", cmd, "--help"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert cmd in result.stdout

def test_legacy_deprecation_warning():
    result = subprocess.run(
        [sys.executable, "project/cli.py", "operator", "preflight", "--proposal", "fake.yaml"],
        capture_output=True,
        text=True
    )
    # It might fail because fake.yaml doesn't exist, but it should still print warning to stderr
    assert "WARNING: 'operator preflight' is deprecated" in result.stderr
