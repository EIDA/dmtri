import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from dmtri import cli
import sys


def test_cli_version_flag(capsys):
    with pytest.raises(SystemExit):
        with patch("sys.argv", ["dmtri", "--version"]):
            cli.main()
    captured = capsys.readouterr()
    assert "version" in captured.out.lower()


def test_cli_no_command_prints_help(capsys):
    with pytest.raises(SystemExit) as e:
        with patch("sys.argv", ["dmtri"]):
            cli.main()
    assert e.value.code == 1
    captured = capsys.readouterr()
    assert "usage" in captured.out.lower()

@patch("dmtri.cli.run_hook")
def test_cli_refresh_no_confirm_runs(mock_run_hook):
    with patch("builtins.input", return_value="y"):
        args = [
            "dmtri", "refresh",
            "--network", "GR",
            "--station", "ATH",
            "--starttime", "2025-01-01T00:00:00",
            "--no-confirm"
        ]
        with patch("sys.argv", args):
            cli.main()

        assert mock_run_hook.call_count == 4


@patch("dmtri.cli.run_hook")
@patch("dmtri.cli.print_execution_plan")
def test_cli_refresh_with_confirm_runs(mock_print_plan, mock_run_hook):
    with patch("builtins.input", return_value="y"):
        args = [
            "dmtri", "refresh",
            "--network", "GR",
            "--station", "ATH",
            "--starttime", "2025-01-01T00:00:00"
        ]
        with patch("sys.argv", args):
            cli.main()

    assert mock_print_plan.call_count == 4
    assert mock_run_hook.call_count == 4



def test_cli_requires_starttime():
    args = ["dmtri", "refresh", "--network", "GR", "--station", "ATH"]
    with patch("sys.argv", args):
        with pytest.raises(SystemExit) as e:
            cli.main()
        assert e.value.code == 2  


def test_cli_invalid_date_format():
    args = ["dmtri", "refresh", "--network", "GR", "--station", "ATH", "--starttime", "bad-date"]
    with patch("sys.argv", args):
        with pytest.raises(SystemExit) as e:
            cli.main()
        assert e.value.code == 1


@patch("builtins.input", return_value="y")
def test_cli_invalid_type_rejected(mock_input):
    args = [
        "dmtri", "refresh",
        "--network", "GR", "--station", "ATH",
        "--starttime", "2025-01-01T00:00:00",
        "--endtime", "2025-04-01T00:00:00",  
        "--type", "test"
    ]
    with patch("sys.argv", args):
        with pytest.raises(SystemExit) as e:
            cli.main()
        assert e.value.code == 1



def test_cli_starttime_in_future_rejected():
    future = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    args = ["dmtri", "refresh", "--network", "GR", "--station", "ATH", "--starttime", future]
    with patch("sys.argv", args):
        with pytest.raises(SystemExit) as e:
            cli.main()
        assert e.value.code == 1


@patch("builtins.input", return_value="n")
def test_cli_user_aborts_on_long_range(mock_input, capsys):
    args = [
        "dmtri", "refresh",
        "--network", "GR",
        "--station", "ATH",
        "--starttime", "2025-01-01T00:00:00",
        "--endtime", "2025-01-20T00:00:00"
    ]
    with patch("sys.argv", args):
        with pytest.raises(SystemExit) as e:
            cli.main()
        assert e.value.code == 0

    out = capsys.readouterr().out
    assert "aborted by user" in out.lower()

@patch("dmtri.doctor.run_diagnostics")
def test_cli_doctor_runs(mock_run):
    with patch("sys.argv", ["dmtri", "doctor"]):
        cli.main()
        mock_run.assert_called_once_with(verbose=False)

@patch("dmtri.doctor.run_diagnostics")
def test_cli_doctor_verbose(mock_run):
    with patch("sys.argv", ["dmtri", "doctor", "--verbose"]):
        cli.main()
        mock_run.assert_called_once_with(verbose=True)
def test_cli_aborts_on_user_input(monkeypatch):
    test_args = [
        "dmtri", "refresh",
        "--network", "FR",
        "--starttime", "2024-01-01",
        "--endtime", "2024-01-02"
    ]
    monkeypatch.setattr(sys, "argv", test_args)

    with patch("builtins.input", return_value="n"):
        with pytest.raises(SystemExit) as excinfo:
            cli.main()
        assert excinfo.value.code == 0  # Means user aborted
@patch("builtins.input", return_value="y")  # Prevent blocking on input()
def test_cli_exits_if_no_playbook_for_command(mock_input, monkeypatch):
    test_args = [
        "dmtri", "refresh",
        "--network", "FR",
        "--starttime", "2024-01-01"
    ]
    monkeypatch.setattr(sys, "argv", test_args)

    # Temporarily remove any configured playbooks for 'refresh'
    from dmtri.cli import COMMAND_PLAYBOOKS
    original_playbooks = COMMAND_PLAYBOOKS.get("refresh")
    COMMAND_PLAYBOOKS["refresh"] = {}

    try:
        with pytest.raises(SystemExit) as e:
            cli.main()
        assert e.value.code == 1
    finally:
        # Restore after test
        COMMAND_PLAYBOOKS["refresh"] = original_playbooks
@patch("builtins.input", side_effect=["y", "n"])
@patch("dmtri.cli.print_execution_plan")
def test_cli_user_aborts_after_plan(mock_print_plan, mock_input, monkeypatch):
    args = [
        "dmtri", "refresh",
        "--network", "GR",
        "--station", "ATH",
        "--starttime", "2025-01-01T00:00:00"
    ]
    monkeypatch.setattr(sys, "argv", args)

    with pytest.raises(SystemExit) as e:
        cli.main()

    assert e.value.code == 0
