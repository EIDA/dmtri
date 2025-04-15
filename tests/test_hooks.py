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
