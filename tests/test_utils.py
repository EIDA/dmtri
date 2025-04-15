import pytest
from argparse import Namespace, ArgumentParser
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from dmtri.utils import (
    get_version,
    maybe_warn_shell_globbing,
    validate_datetime_range,
    parse_datetime_args,
    validate_types,
    validate_and_normalize_args,
)


def test_get_version_reads_pyproject():
    version = get_version()
    assert isinstance(version, str)
    assert len(version) > 0


def test_parse_datetime_args_valid():
    args = Namespace(starttime="2025-01-01T00:00:00", endtime="2025-01-02T00:00:00")
    start, end = parse_datetime_args(args)
    assert start.isoformat().startswith("2025-01-01")
    assert end.isoformat().startswith("2025-01-02")


def test_parse_datetime_args_invalid():
    args = Namespace(starttime="not-a-date", endtime="2025-01-02T00:00:00")
    with pytest.raises(SystemExit):
        parse_datetime_args(args)


def test_validate_datetime_range_valid():
    now = datetime.now(timezone.utc)
    validate_datetime_range(now - timedelta(days=1), now)


def test_validate_datetime_range_future_start():
    now = datetime.now(timezone.utc)
    with pytest.raises(SystemExit):
        validate_datetime_range(now + timedelta(days=1), now)


def test_validate_datetime_range_end_before_start():
    now = datetime.now(timezone.utc)
    with pytest.raises(SystemExit):
        validate_datetime_range(now, now - timedelta(days=1))


@patch("builtins.input", return_value="n")
def test_validate_datetime_range_long_rejects_user(mock_input):
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=10)
    end = now
    with pytest.raises(SystemExit) as e:
        validate_datetime_range(start, end)
    assert e.value.code == 0


def test_validate_types_valid():
    args = Namespace(type="data,metadata")
    result = validate_types(args)
    assert result == ["data", "metadata"]


def test_validate_types_invalid():
    args = Namespace(type="banana")
    with pytest.raises(SystemExit):
        validate_types(args)


def test_warn_shell_globbing(tmp_path, monkeypatch):
    (tmp_path / "ATH").touch()
    (tmp_path / "GR").touch()
    monkeypatch.chdir(tmp_path)

    args = Namespace(network=["GR"], station=["ATH"])
    with pytest.raises(SystemExit):
        maybe_warn_shell_globbing(args)


@patch("builtins.input", return_value="y")
def test_validate_and_normalize_args_valid(mock_input):
    parser = ArgumentParser()
    args = Namespace(
        command="refresh",
        network=["GR"], station=["ATH"], location=["*"], channel=["*"],
        starttime="2025-01-01T00:00:00", endtime="2025-01-02T00:00:00",
        type="data"
    )
    start, end, types = validate_and_normalize_args(args, parser)
    assert start < end
    assert types == ["data"]


def test_validate_and_normalize_args_no_command():
    parser = ArgumentParser()
    args = Namespace(command=None)
    with pytest.raises(SystemExit):
        validate_and_normalize_args(args, parser)
def test_warn_shell_globbing_network(tmp_path, monkeypatch, capsys):
    (tmp_path / "GR").touch()
    monkeypatch.chdir(tmp_path)
    args = Namespace(station=["*"], network=["GR"])
    with pytest.raises(SystemExit):
        maybe_warn_shell_globbing(args)
    err = capsys.readouterr().err
    assert "--network appears to be expanded" in err
def test_validate_datetime_range_future_end(capsys):
    now = datetime.now(timezone.utc)
    future = now + timedelta(days=1)
    with pytest.raises(SystemExit):
        validate_datetime_range(now, future)
    err = capsys.readouterr().err
    assert "endtime cannot be in the future" in err.lower()
