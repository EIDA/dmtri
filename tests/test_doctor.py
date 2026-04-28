import pytest
from unittest.mock import patch, MagicMock
from dmtri import doctor


@patch("ansible_runner.run")
def test_run_diagnostics_all_ok(mock_run, caplog):
    mock_event = {"event": "runner_on_ok", "event_data": {"host": "10.0.0.248"}}
    mock_run.return_value.events = [mock_event]

    with caplog.at_level("INFO"):
        doctor.run_diagnostics(verbose=False)

    assert "[OK] 10.0.0.248" in caplog.text



@patch("ansible_runner.run")
def test_run_diagnostics_unreachable(mock_run, caplog):
    mock_event = {"event": "runner_on_unreachable", "event_data": {"host": "10.0.0.248"}}
    mock_run.return_value.events = [mock_event]

    doctor.run_diagnostics(verbose=False)

    out = caplog.text
    assert "[UNREACHABLE] 10.0.0.248" in out


@patch("ansible_runner.run")
def test_run_diagnostics_no_response(mock_run, caplog):
    mock_run.return_value.events = []

    doctor.run_diagnostics(verbose=False)

    out = caplog.text
    assert "No responses received" in out
@patch("ansible_runner.run")
def test_run_diagnostics_skips_non_dict_and_missing_host(mock_run, caplog):
    # Non-dict event
    bad_event1 = "not a dict"

    # Event without host
    bad_event2 = {"event": "runner_on_ok", "event_data": {}}

    # Good event for sanity check
    good_event = {"event": "runner_on_ok", "event_data": {"host": "10.0.0.248"}}

    mock_run.return_value.events = [bad_event1, bad_event2, good_event]

    with caplog.at_level("INFO"):
        doctor.run_diagnostics(verbose=False)

    assert "[OK] 10.0.0.248" in caplog.text
