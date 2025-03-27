from datetime import datetime, timedelta, timezone
import pytest
from unittest.mock import patch
from datacenter_change_trigger import cli

def test_cli_version_flag(capsys):
    with pytest.raises(SystemExit):
        with patch("sys.argv", ["datacenter_change_trigger", "--version"]):
            cli.main()
    captured = capsys.readouterr()
    assert "version" in captured.out.lower()

def test_cli_no_command_prints_help(capsys):
    with pytest.raises(SystemExit) as e:
        with patch("sys.argv", ["datacenter_change_trigger"]):
            cli.main()
    assert e.value.code == 1
    captured = capsys.readouterr()
    assert "usage" in captured.out.lower()

@patch("datacenter_change_trigger.cli.query.query_node")
@patch("datacenter_change_trigger.cli.load_config", return_value={"endpoints": {"main": "https://test.endpoint"}})
@patch("builtins.input", return_value="y")
def test_cli_refresh_runs_query(mock_input, mock_config, mock_query_node, capsys):
    mock_query_node.return_value = ("url", "endpoint", "result")
    args = [
        "datacenter_change_trigger", "refresh",
        "--network", "FR", "--station", "CIEL",
        "--starttime", "2025-01-01T00:00:00",
        "--endtime", "2025-01-15T00:00:00",
        "--config", "./config.toml"
    ]
    with patch("sys.argv", args):
        cli.main()
    out = capsys.readouterr().out
    assert "query url" in out.lower()

@patch("datacenter_change_trigger.cli.query.query_node")
@patch("datacenter_change_trigger.cli.load_config", return_value={"endpoints": {"main": "https://test.endpoint"}})
@patch("builtins.input", return_value="n")
def test_cli_aborts_if_user_declines_long_range(mock_input, mock_config, mock_query_node, capsys):
    args = [
        "datacenter_change_trigger", "refresh",
        "--network", "FR", "--station", "CIEL",
        "--starttime", "2025-01-01T00:00:00",
        "--endtime", "2025-02-01T00:00:00"
    ]
    with patch("sys.argv", args):
        with pytest.raises(SystemExit) as e:
            cli.main()
        assert e.value.code == 0
    out = capsys.readouterr().out
    assert "aborted by user" in out.lower()
    assert not mock_query_node.called

@patch("datacenter_change_trigger.cli.query.query_node")
@patch("datacenter_change_trigger.cli.load_config", return_value={"endpoints": {"main": "https://test.endpoint"}})
def test_cli_short_range_runs_without_prompt(mock_config, mock_query_node, capsys):
    mock_query_node.return_value = ("url", "endpoint", "result")
    args = [
        "datacenter_change_trigger", "refresh",
        "--network", "FR", "--station", "CIEL",
        "--starttime", "2025-01-01T00:00:00",
        "--endtime", "2025-01-02T00:00:00"
    ]
    with patch("sys.argv", args):
        cli.main()
    out = capsys.readouterr().out
    assert "query url" in out.lower()

def test_cli_rejects_all_wildcard():
    args = [
        "datacenter_change_trigger", "refresh",
        "--network", "*", "--station", "*",
        "--starttime", "2025-01-01T00:00:00"
    ]
    with patch("sys.argv", args):
        with pytest.raises(SystemExit) as e:
            cli.main()
        assert e.value.code == 1

@patch("builtins.input", return_value="y")
def test_cli_invalid_type_rejected(mock_input):
    args = [
        "datacenter_change_trigger", "refresh",
        "--network", "FR", "--station", "CIEL",
        "--starttime", "2025-01-01T00:00:00",
        "--type", "banana"
    ]
    with patch("sys.argv", args):
        with pytest.raises(SystemExit) as e:
            cli.main()
        assert e.value.code == 1

@patch("datacenter_change_trigger.cli.query.query_node", return_value=None)
@patch("datacenter_change_trigger.cli.load_config", return_value={"endpoints": {"main": "https://test"}})
@patch("builtins.input", return_value="y")
def test_cli_handles_empty_query_result(mock_input, mock_config, mock_query):
    args = [
        "datacenter_change_trigger", "refresh",
        "--network", "FR", "--station", "CIEL",
        "--starttime", "2025-01-01T00:00:00",
        "--endtime", "2025-01-15T00:00:00"
    ]
    with patch("sys.argv", args):
        with pytest.raises(SystemExit) as e:
            cli.main()
        assert e.value.code == 1

def test_cli_requires_starttime():
    args = [
        "datacenter_change_trigger", "refresh",
        "--network", "FR", "--station", "CIEL"
    ]
    with patch("sys.argv", args):
        with pytest.raises(SystemExit) as e:
            cli.main()
        assert e.value.code == 2  # argparse error code

def test_cli_invalid_date_format():
    args = [
        "datacenter_change_trigger", "refresh",
        "--network", "FR", "--station", "CIEL",
        "--starttime", "not-a-date"
    ]
    with patch("sys.argv", args):
        with pytest.raises(SystemExit) as e:
            cli.main()
        assert e.value.code == 1

@patch("shutil.copy", side_effect=Exception("copy failed"))
@patch("datacenter_change_trigger.cli.load_config", return_value={"endpoints": {"main": "https://test"}})
@patch("builtins.input", return_value="y")
def test_cli_warns_if_config_copy_fails(mock_input, mock_config, mock_copy, capsys):
    args = [
        "datacenter_change_trigger", "refresh",
        "--config", "bad.toml",
        "--network", "FR", "--station", "CIEL",
        "--starttime", "2025-01-01T00:00:00",
        "--endtime", "2025-01-15T00:00:00"
    ]
    with patch("sys.argv", args):
        with pytest.raises(SystemExit):
            cli.main()
    err = capsys.readouterr().err
    assert "warning: failed to save config file" in err.lower()

@patch("datacenter_change_trigger.cli.load_config", side_effect=ValueError("Mock config error"))
@patch("builtins.input", return_value="y")
def test_cli_invalid_config_file(mock_input, mock_config):
    args = [
        "datacenter_change_trigger", "refresh",
        "--network", "FR", "--station", "CIEL",
        "--starttime", "2025-01-01T00:00:00",
        "--config", "bad.toml"
    ]
    with patch("sys.argv", args):
        with pytest.raises(SystemExit) as e:
            cli.main()
        assert e.value.code == 1
def test_cli_starttime_in_future_rejected():
    future_date = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    args = [
        "datacenter_change_trigger", "refresh",
        "--network", "FR",
        "--station", "CIEL",
        "--starttime", future_date
    ]
    with patch("sys.argv", args):
        with pytest.raises(SystemExit) as e:
            cli.main()
        assert e.value.code == 1
