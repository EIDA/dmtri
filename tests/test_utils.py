import pytest
from dmtri.utils import parse_date_string, get_version,maybe_warn_shell_globbing,validate_datetime_range
from unittest.mock import patch
from datetime import datetime, timedelta, timezone




def test_parse_date_basic():
    assert parse_date_string("2025-01-01") == "2025-01-01T00:00:00"

def test_parse_date_end_flag_sets_time():
    assert parse_date_string("2025-01-01", end=True) == "2025-01-01T23:59:59"

def test_parse_iso8601():
    assert parse_date_string("2025-01-01T14:30:00") == "2025-01-01T14:30:00"

def test_parse_slash_format():
    assert parse_date_string("2025/01/01") == "2025-01-01T00:00:00"
    assert parse_date_string("2025/01/01 15:45:00") == "2025-01-01T15:45:00"

def test_parse_dot_format():
    assert parse_date_string("2025.01.01") == "2025-01-01T00:00:00"

def test_parse_invalid_date_raises():
    with pytest.raises(ValueError, match="Invalid date: 'not-a-date'"):
        parse_date_string("not-a-date")

def test_end_flag_only_applies_when_time_is_midnight():
    assert parse_date_string("2025-01-01T01:00:00", end=True) == "2025-01-01T01:00:00"

def test_get_version_reads_toml(monkeypatch, tmp_path):
    # Setup fake pyproject.toml
    project_root = tmp_path / "project"
    pyproject_path = project_root / "pyproject.toml"
    pyproject_path.parent.mkdir(parents=True, exist_ok=True)
    pyproject_path.write_text("""
[project]
name = "dmtri"
version = "9.9.9"
""")

    # Simulate file structure: project/src/datacenter_change_trigger/utils.py
    fake_utils_path = project_root / "src" / "dmtri" / "utils.py"
    fake_utils_path.parent.mkdir(parents=True, exist_ok=True)
    fake_utils_path.write_text("# mock utils.py file")

    # Patch __file__ to simulate we're inside the real package
    monkeypatch.setattr("dmtri.utils.__file__", str(fake_utils_path))

    assert get_version() == "9.9.9"


@patch("os.listdir", return_value=["README.md", "src"])
def test_globbing_on_station_triggers_exit(mock_listdir):
    # Simulates: --station * (shell expanded to filenames)
    class Args:
        station = ["README.md", "src"]
        network = ["FR"]
    with pytest.raises(SystemExit) as e:
        maybe_warn_shell_globbing(Args())
    assert e.value.code == 1
@patch("os.listdir", return_value=["README.md", "src"])
def test_globbing_on_network_triggers_exit(mock_listdir):
    # Simulates: --network * (shell expanded to filenames)
    class Args:
        station = ["CIEL"]
        network = ["src"]
    with pytest.raises(SystemExit) as e:
        maybe_warn_shell_globbing(Args())
    assert e.value.code == 1
def test_no_globbing_does_not_exit():
    class Args:
        station = ["CIEL"]
        network = ["FR"]
    with patch("os.listdir", return_value=["README.md", "src"]):
        # Should NOT raise anything
        maybe_warn_shell_globbing(Args())
def test_starttime_in_future_exits():
    now = datetime.now(timezone.utc)
    future = now + timedelta(days=1)
    with pytest.raises(SystemExit) as e:
        validate_datetime_range(future, future + timedelta(days=2))
    assert e.value.code == 1
def test_endtime_in_future_exits():
    now = datetime.now(timezone.utc)
    past = now - timedelta(days=1)
    future = now + timedelta(days=1)
    with pytest.raises(SystemExit) as e:
        validate_datetime_range(past, future)
    assert e.value.code == 1
def test_endtime_before_starttime_exits():
    t1 = datetime(2025, 1, 2, tzinfo=timezone.utc)
    t2 = datetime(2025, 1, 1, tzinfo=timezone.utc)
    with pytest.raises(SystemExit):
        validate_datetime_range(t1, t2)
