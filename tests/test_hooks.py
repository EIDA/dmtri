import pytest
from unittest.mock import patch, MagicMock
from dmtri.hooks.hooks import run_hook
from pathlib import Path


@patch("ansible_runner.run_command")
def test_run_hook_success(mock_runner, caplog, tmp_path):
    mock_runner.return_value = ("out", "err", 0)

    playbook = tmp_path / "test_playbook.yml"
    playbook.write_text("- hosts: all")

    vars = {
        "network": ["FR"],
        "station": ["CIEL"],
        "type": ["data"]
    }

    with caplog.at_level("INFO"):
        run_hook(playbook, vars)

    assert "Running:" in caplog.text
    assert "completed successfully" in caplog.text
    mock_runner.assert_called_once()


@patch("ansible_runner.run_command")
def test_run_hook_failure_exits(mock_runner, tmp_path):
    mock_runner.return_value = ("out", "err", 1)  # simulate failure

    playbook = tmp_path / "test_playbook.yml"
    playbook.write_text("- hosts: all")

    vars = {
        "network": ["FR"],
        "station": ["CIEL"]
    }

    with pytest.raises(SystemExit) as e:
        run_hook(playbook, vars)
    assert e.value.code == 1
    mock_runner.assert_called_once()


@patch("ansible_runner.run_command", return_value=("out", "err", 0))
def test_run_hook_builds_correct_cmd(mock_runner, tmp_path, caplog):
    playbook = tmp_path / "run.yml"
    playbook.write_text("- hosts: all")

    vars = {
        "network": ["FR"],
        "station": ["CIEL"],
    }

    with caplog.at_level("INFO"):
        run_hook(playbook, vars)

    expected_snippet = "-e network='FR' -e station='CIEL'"
    assert expected_snippet in caplog.text.replace(",", "")


# --- locating ansible-playbook -------------------------------------------
#
# `.venv/bin/dmtri` runs with the venv's interpreter but not its PATH, so a
# bare "ansible-playbook" is not found and every play dies before it starts.

def test_ansible_playbook_is_found_beside_the_interpreter(tmp_path, monkeypatch):
    from dmtri.hooks import hooks

    binary = tmp_path / "ansible-playbook"
    binary.write_text("#!/bin/sh\n")
    monkeypatch.setattr(hooks.sys, "executable", str(tmp_path / "python"))
    monkeypatch.setattr(hooks.shutil, "which", lambda _: "/usr/bin/ansible-playbook")

    assert hooks._ansible_playbook() == str(binary)


def test_ansible_playbook_falls_back_to_path(tmp_path, monkeypatch):
    from dmtri.hooks import hooks

    monkeypatch.setattr(hooks.sys, "executable", str(tmp_path / "python"))
    monkeypatch.setattr(hooks.shutil, "which", lambda _: "/usr/bin/ansible-playbook")

    assert hooks._ansible_playbook() == "/usr/bin/ansible-playbook"


def test_a_missing_ansible_is_reported_not_raised(tmp_path, monkeypatch, caplog):
    """A batch caller must get an rc it can report, not a FileNotFoundError."""
    from dmtri.hooks import hooks

    monkeypatch.setattr(hooks.sys, "executable", str(tmp_path / "python"))
    monkeypatch.setattr(hooks.shutil, "which", lambda _: None)

    playbook = tmp_path / "p.yml"
    playbook.write_text("- hosts: all")

    with caplog.at_level("ERROR"):
        rc = run_hook(playbook, {}, exit_on_error=False)

    assert rc == 127
    assert "ansible-playbook not found" in caplog.text


def test_a_missing_ansible_still_exits_for_single_shot_callers(tmp_path, monkeypatch):
    from dmtri.hooks import hooks

    monkeypatch.setattr(hooks.sys, "executable", str(tmp_path / "python"))
    monkeypatch.setattr(hooks.shutil, "which", lambda _: None)

    playbook = tmp_path / "p.yml"
    playbook.write_text("- hosts: all")

    with pytest.raises(SystemExit) as e:
        run_hook(playbook, {})
    assert e.value.code == 127
