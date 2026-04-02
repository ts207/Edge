from __future__ import annotations

from pathlib import Path
from subprocess import CompletedProcess, TimeoutExpired

from project.apps.chatgpt.handlers import invoke_codex_operator


def test_invoke_codex_operator_runs_codex_exec(monkeypatch, tmp_path: Path) -> None:
    calls: list[list[str]] = []
    snapshots = iter(
        [
            {"data_root": str(tmp_path), "recent_run_ids": [], "proposal_counts": {}},
            {"data_root": str(tmp_path), "recent_run_ids": ["run-9"], "proposal_counts": {"prog": 2}},
        ]
    )

    def fake_which(name: str) -> str | None:
        assert name == "codex"
        return "/usr/bin/codex"

    def fake_run(command, cwd, capture_output, text, check, timeout):
        calls.append(list(command))
        assert timeout == 90
        output_index = command.index("--output-last-message") + 1
        Path(command[output_index]).write_text("Codex completed task.\n", encoding="utf-8")
        return CompletedProcess(
            args=command,
            returncode=0,
            stdout=(
                '{"type":"thread.started","thread_id":"thread-123"}\n'
                '{"type":"item.completed","item":{"type":"agent_message","text":"fallback message"}}\n'
                '{"type":"turn.completed","usage":{"input_tokens":12,"output_tokens":4}}\n'
            ),
            stderr="",
        )

    monkeypatch.setattr("project.apps.chatgpt.handlers.shutil.which", fake_which)
    monkeypatch.setattr("project.apps.chatgpt.handlers.subprocess.run", fake_run)
    monkeypatch.setattr("project.apps.chatgpt.handlers._resolve_data_root", lambda _value: tmp_path)
    monkeypatch.setattr("project.apps.chatgpt.handlers._snapshot_operator_state", lambda _root: next(snapshots))
    monkeypatch.setattr(
        "project.apps.chatgpt.handlers._diff_operator_state",
        lambda before, after: {
            "data_root": str(tmp_path),
            "new_run_ids": ["run-9"],
            "proposal_memory_changes": [{"program_id": "prog", "before_count": 0, "after_count": 2, "delta": 2}],
            "dashboard_changed": True,
        },
    )

    result = invoke_codex_operator(
        task="Inspect the Edge operator surface.",
        sandbox="read-only",
        model="gpt-5-codex",
        profile="default",
        timeout_sec=90,
    )

    assert calls
    command = calls[0]
    assert command[:2] == ["/usr/bin/codex", "exec"]
    assert "--json" in command
    assert "--ephemeral" in command
    assert command[command.index("--sandbox") + 1] == "read-only"
    assert command[command.index("--model") + 1] == "gpt-5-codex"
    assert command[command.index("--profile") + 1] == "default"
    assert command[-1] == "Inspect the Edge operator surface."

    assert result["status"] == "success"
    assert result["timeout_sec"] == 90
    assert result["timed_out"] is False
    assert result["thread_id"] == "thread-123"
    assert result["final_message"] == "Codex completed task."
    assert result["usage"]["input_tokens"] == 12
    assert result["usage"]["output_tokens"] == 4
    assert result["post_run_probe"]["dashboard_changed"] is True
    assert result["post_run_probe"]["new_run_ids"] == ["run-9"]


def test_invoke_codex_operator_returns_partial_timeout_payload(monkeypatch, tmp_path: Path) -> None:
    snapshots = iter(
        [
            {"data_root": str(tmp_path), "recent_run_ids": [], "proposal_counts": {"prog": 1}},
            {"data_root": str(tmp_path), "recent_run_ids": ["run-timeout"], "proposal_counts": {"prog": 2}},
        ]
    )

    def fake_run(command, cwd, capture_output, text, check, timeout):
        assert timeout == 45
        output_index = command.index("--output-last-message") + 1
        Path(command[output_index]).write_text("Partial Codex result.\n", encoding="utf-8")
        raise TimeoutExpired(
            cmd=command,
            timeout=timeout,
            output=(
                '{"type":"thread.started","thread_id":"thread-timeout"}\n'
                '{"type":"item.completed","item":{"type":"agent_message","text":"still working"}}\n'
            ),
            stderr="partial stderr",
        )

    monkeypatch.setattr("project.apps.chatgpt.handlers.shutil.which", lambda _name: "/usr/bin/codex")
    monkeypatch.setattr("project.apps.chatgpt.handlers.subprocess.run", fake_run)
    monkeypatch.setattr("project.apps.chatgpt.handlers._resolve_data_root", lambda _value: tmp_path)
    monkeypatch.setattr("project.apps.chatgpt.handlers._snapshot_operator_state", lambda _root: next(snapshots))
    monkeypatch.setattr(
        "project.apps.chatgpt.handlers._diff_operator_state",
        lambda before, after: {
            "data_root": str(tmp_path),
            "new_run_ids": ["run-timeout"],
            "proposal_memory_changes": [{"program_id": "prog", "before_count": 1, "after_count": 2, "delta": 1}],
            "dashboard_changed": True,
        },
    )

    result = invoke_codex_operator(
        task="Repair artifacts.",
        sandbox="workspace-write",
        timeout_sec=45,
    )

    assert result["status"] == "timeout"
    assert result["exit_code"] is None
    assert result["timeout_sec"] == 45
    assert result["timed_out"] is True
    assert result["thread_id"] == "thread-timeout"
    assert result["final_message"] == "Partial Codex result."
    assert result["stderr"] == "partial stderr"
    assert result["event_types"] == ["thread.started", "item.completed"]
    assert result["post_run_probe"]["dashboard_changed"] is True
    assert result["post_run_probe"]["new_run_ids"] == ["run-timeout"]


def test_invoke_codex_operator_normalizes_missing_timeout(monkeypatch, tmp_path: Path) -> None:
    snapshots = iter(
        [
            {"data_root": str(tmp_path), "recent_run_ids": [], "proposal_counts": {}},
            {"data_root": str(tmp_path), "recent_run_ids": [], "proposal_counts": {}},
        ]
    )

    def fake_run(command, cwd, capture_output, text, check, timeout):
        assert timeout == 300
        output_index = command.index("--output-last-message") + 1
        Path(command[output_index]).write_text("", encoding="utf-8")
        return CompletedProcess(args=command, returncode=0, stdout="", stderr="")

    monkeypatch.setattr("project.apps.chatgpt.handlers.shutil.which", lambda _name: "/usr/bin/codex")
    monkeypatch.setattr("project.apps.chatgpt.handlers.subprocess.run", fake_run)
    monkeypatch.setattr("project.apps.chatgpt.handlers._resolve_data_root", lambda _value: tmp_path)
    monkeypatch.setattr("project.apps.chatgpt.handlers._snapshot_operator_state", lambda _root: next(snapshots))

    result = invoke_codex_operator(
        task="Repair the repo.",
        sandbox="workspace-write",
        timeout_sec=None,
    )

    assert result["status"] == "success"
    assert result["timeout_sec"] == 300


def test_invoke_codex_operator_reports_missing_cli(monkeypatch) -> None:
    monkeypatch.setattr("project.apps.chatgpt.handlers.shutil.which", lambda _name: None)

    try:
        invoke_codex_operator(task="noop")
    except RuntimeError as exc:
        assert "`codex` CLI" in str(exc)
    else:
        raise AssertionError("expected RuntimeError when codex CLI is missing")
