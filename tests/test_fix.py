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


def test_get_fixes_verbose_streams_and_passes_flag(monkeypatch):
    """verbose=True adds --verbose to explore and streams (does not capture stderr)."""
    captured = {}

    def fake_run(cmd, **k):
        captured["cmd"] = cmd
        captured["kwargs"] = k
        return _fake_proc(stdout=json.dumps(_sample()))

    monkeypatch.setattr(fix, "_explore_base_cmd", lambda: ["eida-consistency"])
    monkeypatch.setattr(subprocess, "run", fake_run)
    fix.get_fixes("report.json", verbose=True)
    assert "--verbose" in captured["cmd"]
    # streaming mode captures stdout only, not capture_output
    assert captured["kwargs"].get("stdout") == subprocess.PIPE
    assert "capture_output" not in captured["kwargs"]


def test_get_fixes_non_verbose_omits_flag(monkeypatch):
    captured = {}

    def fake_run(cmd, **k):
        captured["cmd"] = cmd
        return _fake_proc(stdout=json.dumps(_sample()))

    monkeypatch.setattr(fix, "_explore_base_cmd", lambda: ["eida-consistency"])
    monkeypatch.setattr(subprocess, "run", fake_run)
    fix.get_fixes("report.json")
    assert "--verbose" not in captured["cmd"]


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


# --------------------------------------------------------------------------- #
# Unrecognised findings (explore ships on its own release cycle)
# --------------------------------------------------------------------------- #
def _psd_row(**over):
    row = {"network": "HL", "station": "ELEF", "location": "", "channel": "HHZ",
           "start": "2026-06-12", "end": "2026-06-12",
           "direction": "psd", "status": "actionable"}
    row.update(over)
    return row


def test_partition_collects_unknown_direction():
    parts = fix._partition(_result_with([_psd_row()]))
    assert parts["unhandled"] == [_psd_row()]
    assert parts["refresh"] == [] and parts["clean"] == []


def test_partition_collects_unknown_status():
    row = _psd_row(direction="refresh", status="needs-review")
    parts = fix._partition(_result_with([row]))
    assert parts["unhandled"] == [row]


def test_partition_leaves_unhandled_empty_for_known_rows():
    known = [
        {**_psd_row(), "direction": "refresh"},
        {**_psd_row(), "direction": "clean"},
        {**_psd_row(), "direction": None, "status": "fixed"},
        {**_psd_row(), "direction": None, "status": "transient"},
    ]
    assert fix._partition(_result_with(known))["unhandled"] == []


def test_run_fix_fails_loudly_on_unknown_direction(monkeypatch, capsys):
    """The whole point: never report success having silently ignored a finding."""
    monkeypatch.setattr(fix, "get_fixes", lambda *a, **k: _result_with([_psd_row()]))
    monkeypatch.setattr(fix, "run_hook",
                        lambda *a, **k: pytest.fail("no playbook should run"))
    rc = fix.run_fix("r", inventory=None, no_confirm=True)
    out = capsys.readouterr().out
    assert rc == 1                        # not 0 -- a caller can see this failed
    assert "does not understand" in out
    assert "'psd'" in out                 # the literal value that arrived
    assert "HL.ELEF..HHZ" in out          # and which stream it was about


def test_run_fix_still_repairs_known_rows_then_fails(monkeypatch, capsys):
    """Understood work is done first; the unknown rows only change the exit code."""
    good = {"network": "IV", "station": "MILZ", "location": "", "channel": "HHZ",
            "start": "2008-01-01", "end": "2008-02-01",
            "direction": "refresh", "status": "actionable"}
    monkeypatch.setattr(fix, "get_fixes", lambda *a, **k: _result_with([good, _psd_row()]))
    ran = []
    monkeypatch.setattr(fix, "run_hook",
                        lambda pb, vars, inventory=None, exit_on_error=True: ran.append(pb) or 0)
    rc = fix.run_fix("r", inventory=None, no_confirm=True)
    assert rc == 1
    assert len(ran) == 2                  # wfcatalog + availability still ran
    assert "1 rebuilt, 0 failed" in capsys.readouterr().out


def test_verify_only_fails_on_unhandled(monkeypatch, capsys):
    monkeypatch.setattr(fix, "get_fixes", lambda *a, **k: _result_with([_psd_row()]))
    rc = fix.run_verify_only("r", inventory=None)
    assert rc == 1
    assert "does not understand" in capsys.readouterr().out


# --------------------------------------------------------------------------- #
# PSD repair (dmtri fix --psd)
# --------------------------------------------------------------------------- #
def _row(net="HI", sta="SFL1", cha="HNN", loc="", day="2017-01-23",
         psd_consistent=False, required=False, index=1):
    return {"index": index, "network": net, "station": sta, "channel": cha,
            "location": loc, "starttime": f"{day}T01:57:38", "endtime": f"{day}T02:07:38",
            "psd_consistent": psd_consistent, "psd_required": required}


def _report(rows):
    return {"summary": {"node": "NOA"}, "results": rows}


def _use_report(monkeypatch, rows):
    monkeypatch.setattr(fix, "_load_report", lambda *a, **k: _report(rows))


def test_psd_findings_selects_only_real_gaps(monkeypatch):
    _use_report(monkeypatch, [
        _row(index=1, psd_consistent=False),
        _row(index=2, psd_consistent=True),     # has PSD
        _row(index=3, psd_consistent=None),     # skipped/orphan
    ])
    found = fix.psd_findings("r.json")
    assert [f["index"] for f in found] == [1]
    assert found[0]["day"] == "2017-01-23"


def test_psd_window_brackets_the_reported_day():
    w = fix.psd_windows([{"index": 1, "network": "HI", "station": "SFL1", "location": "",
                          "channel": "HNN", "day": "2017-01-23", "required": False}], 15)
    assert len(w) == 1
    assert w[0]["start"] == "2017-01-08"     # -15
    assert w[0]["end"] == "2017-02-07"       # +15
    assert w[0]["days"] == 31


def test_psd_windows_merge_when_they_overlap():
    """Two findings a week apart must not queue two overlapping plays."""
    findings = [
        {"index": 1, "network": "HI", "station": "SFL1", "location": "", "channel": "HNN",
         "day": "2017-01-23", "required": False},
        {"index": 2, "network": "HI", "station": "SFL1", "location": "", "channel": "HNN",
         "day": "2017-01-30", "required": False},
    ]
    w = fix.psd_windows(findings, 15)
    assert len(w) == 1
    assert w[0]["start"] == "2017-01-08" and w[0]["end"] == "2017-02-14"
    assert sorted(w[0]["indices"]) == [1, 2]


def test_psd_windows_keep_distant_findings_separate():
    findings = [
        {"index": 1, "network": "HI", "station": "SFL1", "location": "", "channel": "HNN",
         "day": "2017-01-23", "required": False},
        {"index": 2, "network": "HI", "station": "SFL1", "location": "", "channel": "HNN",
         "day": "2019-06-01", "required": False},
    ]
    assert len(fix.psd_windows(findings, 15)) == 2


def test_psd_windows_separate_per_channel():
    findings = [
        {"index": 1, "network": "HI", "station": "SFL1", "location": "", "channel": "HNN",
         "day": "2017-01-23", "required": False},
        {"index": 2, "network": "HI", "station": "SFL1", "location": "", "channel": "HNZ",
         "day": "2017-01-23", "required": False},
    ]
    assert len(fix.psd_windows(findings, 15)) == 2


def test_psd_to_vars_shape():
    w = {"network": "HI", "station": "SFL1", "location": "", "channel": "HNN",
         "start": "2017-01-08", "end": "2017-02-07", "days": 31, "indices": [1]}
    v = fix.psd_to_vars(w)
    assert v["network"] == ["HI"] and v["channel"] == ["HNN"]
    assert v["starttime"] == "2017-01-08T00:00:00"
    assert v["endtime"] == "2017-02-07T23:59:59"
    assert v["location"] == ""          # passed for /coverage; discovery ignores it


def test_run_psd_fix_no_findings_returns_0(monkeypatch, capsys):
    _use_report(monkeypatch, [_row(psd_consistent=True)])
    assert fix.run_psd_fix("r.json", inventory=None, no_confirm=True) == 0
    assert "No PSD findings" in capsys.readouterr().out


def test_run_psd_fix_runs_the_psd_playbook(monkeypatch, capsys):
    _use_report(monkeypatch, [_row()])
    called = []
    monkeypatch.setattr(fix, "run_hook",
                        lambda pb, vars, inventory=None, exit_on_error=True:
                            called.append((pb, vars)) or 0)
    rc = fix.run_psd_fix("r.json", inventory=None, no_confirm=True)
    assert rc == 0
    assert len(called) == 1
    assert called[0][0].name == "seedpsd_psd_repair.yml"
    assert called[0][1]["starttime"] == "2017-01-08T00:00:00"
    assert "repaired : 1 window(s)" in capsys.readouterr().out


def test_run_psd_fix_required_only_filters(monkeypatch, capsys):
    _use_report(monkeypatch, [_row(index=1, required=False),
                              _row(index=2, required=False, day="2019-01-01")])
    monkeypatch.setattr(fix, "run_hook",
                        lambda *a, **k: pytest.fail("nothing is required; should not run"))
    assert fix.run_psd_fix("r.json", inventory=None, required_only=True, no_confirm=True) == 0
    assert "none were psd_required" in capsys.readouterr().out


def test_run_psd_fix_rejects_unsafe_row_without_running(monkeypatch):
    _use_report(monkeypatch, [_row(sta="SFL1`reboot`")])
    monkeypatch.setattr(fix, "run_hook",
                        lambda *a, **k: pytest.fail("must not run on an unsafe value"))
    assert fix.run_psd_fix("r.json", inventory=None, no_confirm=True) == 1


def test_run_psd_fix_reports_failure_and_exits_nonzero(monkeypatch, capsys):
    _use_report(monkeypatch, [_row()])
    monkeypatch.setattr(fix, "run_hook",
                        lambda pb, vars, inventory=None, exit_on_error=True: 2)
    rc = fix.run_psd_fix("r.json", inventory=None, no_confirm=True)
    out = capsys.readouterr().out
    assert rc == 1
    assert "repaired : 0 window(s)" in out
    assert "failed   : 1 window(s)" in out
    assert "rc=2" in out


def test_explore_override_accepts_a_path_containing_spaces(monkeypatch, tmp_path):
    """A real drive path can contain a space; splitting on whitespace broke it."""
    exe = tmp_path / "OLD SSD" / "eida-consistency"
    exe.parent.mkdir(parents=True)
    exe.write_text("#!/bin/sh\n")
    monkeypatch.setenv("DMTRI_EIDA_CONSISTENCY", str(exe))
    assert fix._explore_base_cmd() == [str(exe)]


def test_explore_override_still_splits_a_command_line(monkeypatch):
    monkeypatch.setenv("DMTRI_EIDA_CONSISTENCY", "uvx eida-consistency")
    assert fix._explore_base_cmd() == ["uvx", "eida-consistency"]


def test_explore_override_honours_quoting(monkeypatch):
    monkeypatch.setenv("DMTRI_EIDA_CONSISTENCY", "'/opt/my tools/eida-consistency' --flag")
    assert fix._explore_base_cmd() == ["/opt/my tools/eida-consistency", "--flag"]


# --------------------------------------------------------------------------- #
# Outcome classification — a skip is not a repair, and rc=0 is not proof
# --------------------------------------------------------------------------- #
def _hook_writing(status: dict):
    """Fake run_hook that records a status the way the playbook would."""
    def _hook(pb, vars, inventory=None, exit_on_error=True):
        with open(vars["dmtri_status_file"], "w") as fh:
            json.dump(status, fh)
        return 0
    return _hook


def test_skip_is_not_counted_as_a_repair(monkeypatch, capsys):
    """A stream absent from the archive skips; reporting it as repaired was a lie."""
    _use_report(monkeypatch, [_row()])
    monkeypatch.setattr(fix, "run_hook", _hook_writing(
        {"outcome": "skipped", "reason": "no SDS files in /home/qc/iso_sds"}))
    rc = fix.run_psd_fix("r.json", inventory=None, no_confirm=True)
    out = capsys.readouterr().out
    assert rc == 0
    assert "repaired : 0 window(s)" in out
    assert "skipped  : 1 window(s)" in out
    assert "no SDS files" in out


def test_invalid_days_are_handled_by_the_window_pass(monkeypatch, capsys):
    """`data mseed --update` forces reprocessing, so invalid days need no second
    command -- the summary must not send the admin off to run update-dirty."""
    _use_report(monkeypatch, [_row()])
    calls = []

    def hook(playbook, vars, **kw):
        calls.append(vars)
        return _hook_writing(
            {"outcome": "repaired", "files": 31, "dirty_in_window": 12,
             "gap_dirty": 12, "remaining_missing": 0, "remaining_dirty": 0}
        )(playbook, vars, **kw)

    monkeypatch.setattr(fix, "run_hook", hook)
    fix.run_psd_fix("r.json", inventory=None, no_confirm=True)
    out = capsys.readouterr().out
    assert len(calls) == 1                      # one pass, no second playbook run
    assert "psd_dirty_repair" not in calls[0]
    assert "update-dirty" not in out



def test_rc0_without_a_status_is_flagged_unverified(monkeypatch, capsys):
    """1Y.GR12 exited 0 having written nothing; silence must not read as success."""
    _use_report(monkeypatch, [_row()])
    monkeypatch.setattr(fix, "run_hook",
                        lambda pb, vars, inventory=None, exit_on_error=True: 0)
    fix.run_psd_fix("r.json", inventory=None, no_confirm=True)
    out = capsys.readouterr().out
    assert "unverified" in out
    assert "recorded no status" in out


def test_remaining_gap_is_surfaced_as_backfill(monkeypatch, capsys):
    _use_report(monkeypatch, [_row()])
    monkeypatch.setattr(fix, "run_hook", _hook_writing(
        {"outcome": "repaired", "files": 31, "dirty_in_window": 0,
         "remaining_missing": 2290, "remaining_dirty": 7}))
    fix.run_psd_fix("r.json", inventory=None, no_confirm=True)
    out = capsys.readouterr().out
    assert "need a backfill" in out
    assert "2290 missing + 7 invalid" in out


def test_remaining_is_never_negative(monkeypatch, capsys):
    """The window can cover more days than are broken; -8 remaining was nonsense."""
    _use_report(monkeypatch, [_row()])
    monkeypatch.setattr(fix, "run_hook", _hook_writing(
        {"outcome": "repaired", "files": 31, "dirty_in_window": 0,
         "remaining_missing": 0, "remaining_dirty": 0}))
    fix.run_psd_fix("r.json", inventory=None, no_confirm=True)
    out = capsys.readouterr().out
    assert "-" not in out.split("summary")[1].split("Note:")[0].replace("–", "").replace("--", "")
    assert "need a backfill" not in out


# --- seedpsd's own skip reasons ----------------------------------------------
#
# seedpsd exits 0 and prints "Done." even when it skipped every file, so a
# window must not read as cleanly repaired when seedpsd said otherwise.

def test_seedpsd_skip_reasons_are_shown_verbatim(capsys):
    w = {"network": "MK", "station": "OTOV", "location": "00", "channel": "HHN",
         "start": "2023-09-15", "end": "2023-10-15", "days": 31, "indices": [0]}
    s = {"outcome": "repaired", "files": 31,
         "seedpsd_said": ["31 Unknown data source. Please update the metadata into SeedPSD and reprocess this file."]}
    fix._print_psd_summary([(w, s)])
    out = capsys.readouterr().out
    assert "1 where seedpsd skipped some data" in out
    assert "31 × Unknown data source" in out


def test_a_clean_repair_shows_no_skip_section(capsys):
    w = {"network": "HI", "station": "PYR2", "location": "", "channel": "HNZ",
         "start": "2016-12-11", "end": "2016-12-15", "days": 5, "indices": [0]}
    fix._print_psd_summary([(w, {"outcome": "repaired", "files": 5, "seedpsd_said": []})])
    out = capsys.readouterr().out
    assert "seedpsd skipped" not in out
