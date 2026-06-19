import json
import subprocess
from types import SimpleNamespace

import pytest

import dmtri.fix as fix


# --------------------------------------------------------------------------- #
# get_fixes (subprocess + parsing)
# --------------------------------------------------------------------------- #
def _fake_proc(stdout="", stderr="", rc=0):
    return SimpleNamespace(stdout=stdout, stderr=stderr, returncode=rc)


def _sample(node="NOA", fixes=None):
    return {"schema_version": "1.0", "node": node, "report": "r", "fixes": fixes or []}


def test_get_fixes_parses_json(monkeypatch):
    payload = _sample(fixes=[{"index": 1, "network": "XX", "station": "STA",
                              "location": "00", "channel": "BHZ",
                              "start": "2008-01-01", "end": "2008-02-01",
                              "direction": "refresh", "status": "actionable"}])
    monkeypatch.setattr(fix, "_explore_base_cmd", lambda: ["eida-consistency"])
    monkeypatch.setattr(subprocess, "run",
                        lambda *a, **k: _fake_proc(stdout=json.dumps(payload)))
    result = fix.get_fixes("report.json")
    assert result["node"] == "NOA"
    assert result["fixes"][0]["channel"] == "BHZ"


def test_get_fixes_nonzero_exit_raises(monkeypatch):
    monkeypatch.setattr(fix, "_explore_base_cmd", lambda: ["eida-consistency"])
    monkeypatch.setattr(subprocess, "run",
                        lambda *a, **k: _fake_proc(stderr="boom", rc=3))
    with pytest.raises(RuntimeError, match="explore failed"):
        fix.get_fixes("report.json")


def test_get_fixes_too_old_gives_upgrade_hint(monkeypatch):
    """An eida-consistency that rejects --json yields an upgrade message, not a raw tail."""
    monkeypatch.setattr(fix, "_explore_base_cmd", lambda: ["eida-consistency"])
    monkeypatch.setattr(subprocess, "run",
                        lambda *a, **k: _fake_proc(stderr="Error: No such option: --json", rc=2))
    with pytest.raises(RuntimeError, match="too old.*explore --json"):
        fix.get_fixes("report.json")


def test_explore_base_cmd_missing_gives_install_hint(monkeypatch):
    """When eida-consistency and uvx are both absent, explain how to install."""
    monkeypatch.delenv("DMTRI_EIDA_CONSISTENCY", raising=False)
    monkeypatch.setattr(fix.shutil, "which", lambda name: None)
    with pytest.raises(RuntimeError, match="uv tool install eida-consistency"):
        fix._explore_base_cmd()


def test_explore_base_cmd_honors_override(monkeypatch):
    monkeypatch.setenv("DMTRI_EIDA_CONSISTENCY", "/opt/ec/eida-consistency")
    assert fix._explore_base_cmd() == ["/opt/ec/eida-consistency"]


def test_get_fixes_schema_mismatch_raises(monkeypatch):
    payload = {"schema_version": "2.0", "node": "N", "fixes": []}
    monkeypatch.setattr(fix, "_explore_base_cmd", lambda: ["eida-consistency"])
    monkeypatch.setattr(subprocess, "run",
                        lambda *a, **k: _fake_proc(stdout=json.dumps(payload)))
    with pytest.raises(RuntimeError, match="schema_version"):
        fix.get_fixes("report.json")


def test_get_fixes_tolerates_leading_noise(monkeypatch):
    payload = _sample()
    monkeypatch.setattr(fix, "_explore_base_cmd", lambda: ["eida-consistency"])
    monkeypatch.setattr(subprocess, "run",
                        lambda *a, **k: _fake_proc(stdout="warn\n" + json.dumps(payload)))
    assert fix.get_fixes("report.json")["node"] == "NOA"


# --------------------------------------------------------------------------- #
# fix_to_vars (date boundary + location mapping)
# --------------------------------------------------------------------------- #
def test_fix_to_vars_empty_location_and_end_boundary():
    f = {"network": "IV", "station": "MILZ", "location": "", "channel": "HHZ",
         "start": "2008-02-11", "end": "2008-05-02",
         "direction": "refresh", "status": "actionable"}
    wf, rb = fix.fix_to_vars(f)
    # avail-rebuild: empty location -> '--', end is exclusive (last day + 1)
    assert rb["loc"] == "--"
    assert rb["start"] == "2008-02-11"
    assert rb["end"] == "2008-05-03"
    # wfcatalog: empty location -> '*', covers full end day, data type
    assert wf["location"] == ["*"]
    assert wf["starttime"] == "2008-02-11T00:00:00"
    assert wf["endtime"] == "2008-05-02T23:59:59"
    assert wf["type"] == ["data"]


def test_fix_to_vars_explicit_location():
    f = {"network": "IV", "station": "AQU", "location": "00", "channel": "BHZ",
         "start": "2008-03-01", "end": "2008-03-01",
         "direction": "refresh", "status": "actionable"}
    wf, rb = fix.fix_to_vars(f)
    assert rb["loc"] == "00"
    assert rb["end"] == "2008-03-02"
    assert wf["location"] == ["00"]


# --------------------------------------------------------------------------- #
# _partition (filtering + dedup)
# --------------------------------------------------------------------------- #
def test_partition_splits_and_dedups():
    base = {"network": "IV", "station": "MILZ", "location": "", "channel": "HHZ",
            "start": "2008-01-01", "end": "2008-02-01"}
    result = _result_with([
        {**base, "direction": "refresh", "status": "actionable"},
        {**base, "direction": "refresh", "status": "actionable"},  # dup
        {**base, "channel": "HHN", "direction": "clean", "status": "actionable"},
        {**base, "channel": "HHE", "direction": "refresh", "status": "fixed"},
        {**base, "channel": "BHZ", "direction": "refresh", "status": "transient"},
    ])
    parts = fix._partition(result)
    assert len(parts["refresh"]) == 1   # deduped
    assert len(parts["clean"]) == 1
    assert len(parts["fixed"]) == 1
    assert len(parts["transient"]) == 1


def _result_with(fixes):
    return {"schema_version": "1.0", "node": "NOA", "fixes": fixes}


# --------------------------------------------------------------------------- #
# run_verify_only
# --------------------------------------------------------------------------- #
def test_verify_only_all_fixed_returns_0(monkeypatch, capsys):
    monkeypatch.setattr(fix, "get_fixes", lambda *a, **k: _result_with([
        {"network": "IV", "station": "MILZ", "location": "", "channel": "HHZ",
         "start": "2008-01-01", "end": "2008-02-01",
         "direction": "refresh", "status": "fixed"},
    ]))
    assert fix.run_verify_only("r", inventory=None) == 0
    assert "1 fixed" in capsys.readouterr().out


def test_verify_only_still_inconsistent_returns_1(monkeypatch):
    monkeypatch.setattr(fix, "get_fixes", lambda *a, **k: _result_with([
        {"network": "IV", "station": "MILZ", "location": "", "channel": "HHZ",
         "start": "2008-01-01", "end": "2008-02-01",
         "direction": "refresh", "status": "actionable"},
    ]))
    assert fix.run_verify_only("r", inventory=None) == 1


# --------------------------------------------------------------------------- #
# run_fix (chain ordering + continue-on-error)
# --------------------------------------------------------------------------- #
def test_run_fix_runs_chain_in_order(monkeypatch):
    f = {"network": "IV", "station": "MILZ", "location": "", "channel": "HHZ",
         "start": "2008-01-01", "end": "2008-02-01",
         "direction": "refresh", "status": "actionable"}
    monkeypatch.setattr(fix, "get_fixes", lambda *a, **k: _result_with([f]))
    calls = []

    def fake_hook(pb, vars, inventory=None, exit_on_error=True):
        calls.append(pb)
        return 0
    monkeypatch.setattr(fix, "run_hook", fake_hook)

    rc = fix.run_fix("r", inventory=None, no_confirm=True)
    assert rc == 0
    assert calls == [fix.PLAYBOOK_WFCATALOG_REFRESH, fix.PLAYBOOK_AVAILABILITY_REBUILD]


def test_run_fix_skips_rebuild_when_wfcatalog_fails(monkeypatch):
    f = {"network": "IV", "station": "MILZ", "location": "", "channel": "HHZ",
         "start": "2008-01-01", "end": "2008-02-01",
         "direction": "refresh", "status": "actionable"}
    monkeypatch.setattr(fix, "get_fixes", lambda *a, **k: _result_with([f]))
    calls = []

    def fake_hook(pb, vars, inventory=None, exit_on_error=True):
        calls.append(pb)
        return 2 if pb == fix.PLAYBOOK_WFCATALOG_REFRESH else 0
    monkeypatch.setattr(fix, "run_hook", fake_hook)

    rc = fix.run_fix("r", inventory=None, no_confirm=True)
    assert rc == 1                                   # a failure -> nonzero
    assert calls == [fix.PLAYBOOK_WFCATALOG_REFRESH]  # rebuild skipped


def test_run_fix_no_targets_returns_0(monkeypatch):
    monkeypatch.setattr(fix, "get_fixes", lambda *a, **k: _result_with([]))
    assert fix.run_fix("r", inventory=None, no_confirm=True) == 0


# --------------------------------------------------------------------------- #
# security: injection-laced report values must never reach a playbook
# --------------------------------------------------------------------------- #
def test_validate_fix_rejects_shell_metacharacters():
    bad = {"network": "IV", "station": "X; rm -rf /", "location": "", "channel": "HHZ",
           "start": "2008-01-01", "end": "2008-02-01"}
    with pytest.raises(ValueError, match="unsafe station"):
        fix._validate_fix(bad)


@pytest.mark.parametrize("field,value", [
    ("channel", "HHZ$(touch pwned)"),
    ("network", "IV`whoami`"),
    ("start", "2008-01-01; echo x"),
    ("location", "0123456789"),  # too long
])
def test_validate_fix_rejects_various(field, value):
    f = {"network": "IV", "station": "STA", "location": "", "channel": "HHZ",
         "start": "2008-01-01", "end": "2008-02-01"}
    f[field] = value
    with pytest.raises(ValueError):
        fix._validate_fix(f)


def test_run_fix_rejects_malicious_row_without_running_playbooks(monkeypatch):
    evil = {"network": "IV", "station": "MILZ`reboot`", "location": "", "channel": "HHZ",
            "start": "2008-01-01", "end": "2008-02-01",
            "direction": "refresh", "status": "actionable"}
    monkeypatch.setattr(fix, "get_fixes", lambda *a, **k: _result_with([evil]))
    calls = []
    monkeypatch.setattr(fix, "run_hook",
                        lambda pb, vars, inventory=None, exit_on_error=True: calls.append(pb) or 0)
    rc = fix.run_fix("r", inventory=None, no_confirm=True)
    assert rc == 1           # recorded as failed
    assert calls == []       # no playbook ever ran for the unsafe row
