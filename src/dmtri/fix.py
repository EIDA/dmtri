"""`dmtri fix` — automated repair of inconsistencies from an eida-consistency report.

Flow:
  1. Shell out to `eida-consistency explore --json <report>` to get structured fixes
     (NSLC + true window + direction + status).
  2. Keep the actionable, refresh-direction fixes (v1 is refresh-only; the clean
     direction — phantom availability records — needs deletion logic we don't have yet).
  3. For each fix, run the repair chain on the existing playbook/SSH machinery:
        wfcatalog_refresh (NSLC + range)  ->  availability_rebuild (docker exec avail-rebuild)
     continue-on-error: a failed stream is recorded and skipped, not fatal; the
     availability rebuild is skipped for a stream whose wfcatalog step failed.
  4. Report, and remind that the live /availability service caches answers for
     ~20 min, so confirmation should come from `dmtri fix --verify-only` later.

The availability rebuild reads from WFCatalog and is idempotent, so re-runs are safe.
"""
from __future__ import annotations  # keep modern type hints lazy (dmtri floor is 3.8)

import json
import os
import re
import shlex
import shutil
import subprocess
import tempfile
import sys
from datetime import date, timedelta

from dmtri.hooks.hooks import run_hook
from dmtri.paths import (PLAYBOOK_WFCATALOG_REFRESH, PLAYBOOK_AVAILABILITY_REBUILD,
                         PLAYBOOK_SEEDPSD_PSD_REPAIR)

# Major schema version of `explore --json` we understand. Minor bumps are additive.
SUPPORTED_SCHEMA_MAJOR = "1"


# --------------------------------------------------------------------------- #
# Talking to eida-consistency
# --------------------------------------------------------------------------- #
def _explore_base_cmd() -> list[str]:
    """Locate the eida-consistency CLI.

    Order: $DMTRI_EIDA_CONSISTENCY override -> `eida-consistency` on PATH ->
    `uvx eida-consistency`. Raises a helpful error if none is available.
    """
    override = os.environ.get("DMTRI_EIDA_CONSISTENCY")
    if override:
        # A plain path is used verbatim -- splitting on whitespace would tear a
        # path containing a space (e.g. "/mnt/c/OLD SSD/.../eida-consistency")
        # in half. Anything else is a command line ("uvx eida-consistency"), so
        # shlex honours quoting instead of naive whitespace splitting.
        if os.path.isfile(override):
            return [override]
        return shlex.split(override)
    if shutil.which("eida-consistency"):
        return ["eida-consistency"]
    if shutil.which("uvx"):
        return ["uvx", "eida-consistency"]
    raise RuntimeError(
        "`dmtri fix` needs the eida-consistency CLI, which was not found on this machine.\n"
        "  Install it (pick one):\n"
        "    uv tool install eida-consistency     # recommended — puts it on your PATH\n"
        "    pipx install eida-consistency\n"
        "    pip install eida-consistency\n"
        "  Or just make `uv` available and dmtri will run it on demand via `uvx` (no install).\n"
        "  Already installed elsewhere? Point dmtri at it:\n"
        "    export DMTRI_EIDA_CONSISTENCY='/full/path/to/eida-consistency'"
    )


def get_fixes(report: str, days: int | None = None,
              indices: list[int] | None = None, verbose: bool = False) -> dict:
    """Run `eida-consistency explore --json` and return the parsed result dict.

    With ``verbose=True`` we ask explore for its per-query log (``--verbose``) and
    let that progress stream straight to our stderr instead of capturing it, so the
    user can watch the exploration happen. stdout is still captured either way
    (it must stay pure JSON for parsing).

    Raises RuntimeError on a non-zero exit, unparseable output, or an
    incompatible schema major version.
    """
    cmd = _explore_base_cmd() + ["explore", "--json", report]
    if verbose:
        cmd += ["--verbose"]
    if days is not None:
        cmd += ["--days", str(days)]
    for i in indices or []:
        cmd += ["--index", str(i)]

    # explore re-probes every inconsistent stream against the live node, so it can
    # run for minutes. We capture its output (stdout must stay pure JSON), which
    # means the user sees nothing while it works — tell them it's running so the
    # silent wait doesn't look like a hang.
    print(f"⏳ Running eida-consistency explore on {report} …", file=sys.stderr, flush=True)
    print("   (re-checking each stream against the live node; this can take a few minutes)",
          file=sys.stderr, flush=True)
    if verbose:
        # Stream explore's progress (stderr) live; still capture stdout for JSON.
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, text=True)
    else:
        proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        # In verbose mode stderr already went to the terminal, so it is not on the
        # proc object — fall back to whatever leaked onto stdout.
        combined = (proc.stderr or "") + (proc.stdout or "")
        # An eida-consistency too old to know `--json` rejects the flag with a
        # "No such option: --json" usage error. Turn that into an upgrade hint
        # instead of a cryptic argparse/click tail.
        if "--json" in combined and "no such option" in combined.lower():
            raise RuntimeError(
                "eida-consistency is installed but too old: it does not support "
                "`explore --json` (needed by `dmtri fix`, available since 0.5.1).\n"
                "  Upgrade it (pick one):\n"
                "    uv tool upgrade eida-consistency\n"
                "    pipx upgrade eida-consistency\n"
                "    pip install -U eida-consistency"
            )
        tail = combined.strip().splitlines()[-5:]
        raise RuntimeError(
            "eida-consistency explore failed (exit "
            f"{proc.returncode}):\n  " + "\n  ".join(tail)
        )

    out = proc.stdout
    try:
        # stdout is pure JSON (eida-consistency logs/progress go to stderr); fall
        # back to the first '{' in case anything leaks in front of it.
        result = json.loads(out[out.index("{"):]) if "{" in out else json.loads(out)
    except (ValueError, json.JSONDecodeError) as e:
        raise RuntimeError(f"could not parse explore --json output: {e}")

    version = str(result.get("schema_version", ""))
    if version.split(".")[0] != SUPPORTED_SCHEMA_MAJOR:
        raise RuntimeError(
            f"explore --json schema_version {version!r} is incompatible with this "
            f"dmtri (expects {SUPPORTED_SCHEMA_MAJOR}.x). Update dmtri or eida-consistency."
        )
    print(f"✓ explore finished — {len(result.get('fixes', []))} fix candidate(s) "
          f"for node {result.get('node', '?')}", file=sys.stderr, flush=True)
    return result


# --------------------------------------------------------------------------- #
# Fix -> playbook variables
# --------------------------------------------------------------------------- #
# Fix values come from a report fetched over a URL (untrusted input) and are
# forwarded into Ansible playbooks that shell out (docker exec / find). Validate
# them at the source against strict allow-lists so nothing shell-special can reach
# a command line. FDSN codes are short alphanumerics (+ wildcards/-/_); dates ISO.
_CODE_RE = re.compile(r"^[A-Za-z0-9*?_-]{1,8}$")   # network / station / channel
_LOC_RE = re.compile(r"^[A-Za-z0-9*?_-]{0,8}$")    # location (may be empty)
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _validate_fix(f: dict) -> None:
    """Raise ValueError if any field would be unsafe to pass to a playbook."""
    for k in ("network", "station", "channel"):
        if not _CODE_RE.match(str(f.get(k, ""))):
            raise ValueError(f"unsafe {k}={f.get(k)!r}")
    if not _LOC_RE.match(str(f.get("location", ""))):
        raise ValueError(f"unsafe location={f.get('location')!r}")
    for k in ("start", "end"):
        if not _DATE_RE.match(str(f.get(k, ""))):
            raise ValueError(f"unsafe {k}={f.get(k)!r}")


def _end_exclusive(end: str) -> str:
    """avail-rebuild's --end is exclusive (te <= end). explore reports the last
    *broken* day inclusively, so pass the day after it."""
    y, m, d = (int(x) for x in end.split("-"))
    return (date(y, m, d) + timedelta(days=1)).isoformat()


def fix_to_vars(fix: dict) -> tuple[dict, dict]:
    """Map one fix record to (wfcatalog_refresh vars, availability_rebuild vars)."""
    net, sta, cha = fix["network"], fix["station"], fix["channel"]
    loc = fix["location"]
    start, end = fix["start"], fix["end"]

    wfcatalog_vars = {
        "network": [net],
        "station": [sta],
        # wfcatalog discovery is largely location-agnostic; empty location -> '*'.
        "location": [loc or "*"],
        "channel": [cha],
        "starttime": f"{start}T00:00:00",
        "endtime": f"{end}T23:59:59",
        "type": ["data"],
    }
    rebuild_vars = {
        "net": net,
        "sta": sta,
        # avail-rebuild spells the empty location as '--'.
        "loc": "--" if loc == "" else loc,
        "cha": cha,
        "start": start,
        "end": _end_exclusive(end),
    }
    return wfcatalog_vars, rebuild_vars


def _dedup(fixes: list[dict]) -> list[dict]:
    seen, out = set(), []
    for f in fixes:
        key = (f["network"], f["station"], f["location"], f["channel"], f["start"], f["end"])
        if key not in seen:
            seen.add(key)
            out.append(f)
    return out


def _label(f: dict) -> str:
    return f"{f['network']}.{f['station']}.{f['location']}.{f['channel']}  {f['start']} -> {f['end']}"


# The direction/status values this dmtri knows how to act on. explore is a
# separate program on its own release cycle, so it can start emitting values we
# have never heard of without any dmtri release -- see _partition's "unhandled".
KNOWN_DIRECTIONS = ("refresh", "clean")
KNOWN_STATUSES = ("actionable", "fixed", "transient")


def _is_handled(f: dict) -> bool:
    """True if this row lands in one of the buckets _partition builds."""
    status = f.get("status")
    if status in ("fixed", "transient"):
        return True
    if status == "actionable":
        return f.get("direction") in KNOWN_DIRECTIONS
    return False


def _loose_label(f: dict) -> str:
    """Label a row we did not recognise -- fields we rely on may be absent."""
    nslc = ".".join(str(f.get(k, "?")) for k in
                    ("network", "station", "location", "channel"))
    return f"{nslc}  {f.get('start', '?')} -> {f.get('end', '?')}"


def _report_unhandled(rows: list) -> None:
    """Print findings this dmtri could not place, with their literal values.

    explore prints a suggested `uvx dmtri ...` line in its human summary, but
    that never reaches the JSON we parse -- so we print the same facts it is
    built from (stream and window) and let the operator take it from there.
    """
    groups: dict = {}
    for f in rows:
        groups.setdefault((f.get("direction"), f.get("status")), []).append(f)
    print("\n" + "=" * 50)
    print(f" {len(rows)} finding(s) this dmtri does not understand")
    print("=" * 50)
    for (direction, status), items in sorted(groups.items(), key=lambda kv: str(kv[0])):
        print(f"  direction={direction!r} status={status!r}  ({len(items)} row(s))")
        for f in items:
            print(f"    {_loose_label(f)}")
    print(f"\n  This dmtri handles direction: {', '.join(KNOWN_DIRECTIONS)}"
          f"; status: {', '.join(KNOWN_STATUSES)}.")
    print("  Your eida-consistency is newer than this dmtri -- upgrade dmtri,")
    print("  or repair the streams above by hand.")


# --------------------------------------------------------------------------- #
# Commands
# --------------------------------------------------------------------------- #
def _partition(result: dict) -> dict:
    fixes = result.get("fixes", [])
    actionable = [f for f in fixes if f.get("status") == "actionable"]
    return {
        "refresh": _dedup([f for f in actionable if f.get("direction") == "refresh"]),
        "clean": [f for f in actionable if f.get("direction") == "clean"],
        "fixed": [f for f in fixes if f.get("status") == "fixed"],
        "transient": [f for f in fixes if f.get("status") == "transient"],
        # Anything matching none of the above. Without this the row would simply
        # vanish and we would report success having ignored it.
        "unhandled": [f for f in fixes if not _is_handled(f)],
        "node": result.get("node", "?"),
    }


def run_verify_only(report: str, inventory, days=None, indices=None, verbose=False) -> int:
    """Re-probe via explore --json and report which rows are now fixed. No playbooks.

    Returns 0 if nothing remains actionable (all healed), else 1.
    """
    parts = _partition(get_fixes(report, days, indices, verbose=verbose))
    still = parts["refresh"] + parts["clean"]
    print(f"\nVerify ({parts['node']}): "
          f"{len(parts['fixed'])} fixed, {len(still)} still inconsistent, "
          f"{len(parts['transient'])} transient.")
    for f in parts["fixed"]:
        print(f"  ✓ fixed   {f['network']}.{f['station']}.{f['location']}.{f['channel']}")
    for f in still:
        print(f"  ✗ still   {_label(f)}")
    if parts["unhandled"]:
        _report_unhandled(parts["unhandled"])
    return 0 if not still and not parts["unhandled"] else 1


def run_fix(report: str, inventory, days=None, indices=None,
            no_confirm=False, debug=False, verbose=False) -> int:
    """Drive the repair chain for every actionable refresh-direction fix."""
    parts = _partition(get_fixes(report, days, indices, verbose=verbose))
    targets = parts["refresh"]

    if parts["clean"]:
        print(f"Note: {len(parts['clean'])} clean-direction inconsistency(ies) "
              "skipped (not supported yet — refresh-only).")
    if parts["fixed"]:
        print(f"Note: {len(parts['fixed'])} row(s) already consistent — nothing to do.")

    if not targets:
        print("No actionable refresh-direction fixes. Nothing to run.")
        if parts["unhandled"]:
            _report_unhandled(parts["unhandled"])
            return 1
        return 0

    print(f"\ndmtri fix ({parts['node']}) — {len(targets)} stream(s) to repair:")
    for f in targets:
        print(f"  - {_label(f)}")
    print("\n  Each: (1) wfcatalog_refresh on wf_catalogue, "
          "(2) availability_rebuild on ws_availability.")

    if not no_confirm:
        if input("\nProceed? (y/N): ").strip().lower() != "y":
            print("Aborted by user.")
            return 0

    results = []  # (fix, ok, reason)
    for f in targets:
        try:
            _validate_fix(f)            # never forward untrusted/unsafe values to a playbook
        except ValueError as e:
            print(f"\n=== {_label(f)} ===\n  REJECTED: {e}")
            results.append((f, False, f"rejected ({e})"))
            continue
        wf_vars, rb_vars = fix_to_vars(f)
        print(f"\n=== {_label(f)} ===")
        rc1 = run_hook(PLAYBOOK_WFCATALOG_REFRESH, wf_vars, inventory=inventory, exit_on_error=False)
        if rc1 != 0:
            results.append((f, False, f"wfcatalog rc={rc1} (availability rebuild skipped)"))
            continue
        rc2 = run_hook(PLAYBOOK_AVAILABILITY_REBUILD, rb_vars, inventory=inventory, exit_on_error=False)
        if rc2 != 0:
            results.append((f, False, f"avail-rebuild rc={rc2}"))
        else:
            results.append((f, True, ""))

    ok = [r for r in results if r[1]]
    bad = [r for r in results if not r[1]]
    print("\n" + "=" * 50)
    print(f" dmtri fix summary: {len(ok)} rebuilt, {len(bad)} failed")
    print("=" * 50)
    for f, _, reason in bad:
        print(f"  ✗ {_label(f)}  -- {reason}")
    if ok:
        print("\nℹ The availability service caches answers for ~20 min, so these")
        print("  may still show as 'not available' until the cache expires.")
        print(f"  Confirm later with:  dmtri fix --verify-only <report>")
    if parts["unhandled"]:
        _report_unhandled(parts["unhandled"])
    return 0 if not bad and not parts["unhandled"] else 1


# --------------------------------------------------------------------------- #
# PSD repair  (`dmtri fix --psd`)
#
# PSD findings are read STRAIGHT FROM THE REPORT, not via `explore --json`.
# explore only walks availability-vs-dataselect disagreements, so a PSD-only
# finding never reaches it -- and does not need to: /coverage is queried over the
# whole UTC day, so the verdict is already day-final and there is no boundary to
# explore. Reading the report keeps this half independent of eida-consistency.
#
# The repair is deliberately BOUNDED. Gaps on a real archive run to thousands of
# days per channel (23-59% of a channel's history, measured on NOA), so repairing
# "the whole gap" would mean hours per finding. Instead we repair a window and
# the playbook reports how much remains, so a bounded fix never reads as a
# finished one and the operator can schedule a proper backfill.
# --------------------------------------------------------------------------- #
DEFAULT_PSD_WINDOW_DAYS = 15

# Measured on the NOA seedpsd host: ~11.4 s per day-file single-threaded. Used
# only to warn before a long run; `seedpsd_parallel` on the host makes it ~5x
# faster, but that is an inventory setting dmtri cannot see from here.
_SECONDS_PER_DAY_FILE = 11.4


def _load_report(report: str) -> dict:
    """Load a consistency report from a local path or an http(s) URL."""
    if report.startswith(("http://", "https://")):
        import requests
        resp = requests.get(report, timeout=30)
        resp.raise_for_status()
        return resp.json()
    with open(report) as fh:
        return json.load(fh)


def psd_findings(report: str) -> list:
    """Report rows meaning 'data present for this day, but no valid PSD'."""
    rows = []
    for r in _load_report(report).get("results", []):
        if r.get("psd_consistent") is not False:
            continue
        rows.append({
            "index": r.get("index"),
            "network": r.get("network"),
            "station": r.get("station"),
            "location": r.get("location", "") or "",
            "channel": r.get("channel"),
            "day": str(r.get("starttime", ""))[:10],
            "required": bool(r.get("psd_required")),
        })
    return rows


def psd_windows(findings: list, window_days: int = DEFAULT_PSD_WINDOW_DAYS) -> list:
    """Collapse findings into one repair window per channel.

    Two findings on the same channel a fortnight apart would otherwise queue
    overlapping windows and recompute the same day-files twice, so touching
    windows are merged.
    """
    by_channel: dict = {}
    for f in findings:
        if not f["day"]:
            continue
        key = (f["network"], f["station"], f["location"], f["channel"])
        by_channel.setdefault(key, []).append(f)

    windows = []
    for (net, sta, loc, cha), items in sorted(by_channel.items(), key=lambda kv: str(kv[0])):
        spans = []
        for f in sorted(items, key=lambda x: x["day"]):
            day = date.fromisoformat(f["day"])
            lo, hi = day - timedelta(days=window_days), day + timedelta(days=window_days)
            if spans and lo <= spans[-1][1] + timedelta(days=1):
                prev_lo, prev_hi, idxs = spans[-1]
                spans[-1] = (prev_lo, max(prev_hi, hi), idxs + [f["index"]])
            else:
                spans.append((lo, hi, [f["index"]]))
        for lo, hi, idxs in spans:
            windows.append({
                "network": net, "station": sta, "location": loc, "channel": cha,
                "start": lo.isoformat(), "end": hi.isoformat(),
                "days": (hi - lo).days + 1, "indices": idxs,
            })
    return windows


def psd_to_vars(window: dict, status_file: str = None) -> dict:
    """Map a repair window to seedpsd_psd_repair variables.

    `location` is passed for the /coverage query only -- the SDS layout has no
    location directory, so file discovery still matches on
    network/station/channel/day and picks up every location for that channel.
    Broader than the finding, and harmless: recomputing a valid day rewrites an
    identical record.

    `dmtri_status_file` is a path on THIS machine that the play writes its
    outcome to. Without it the caller only sees rc, and rc=0 does not mean
    repaired -- a window with no data skips, and a window of invalid days can
    leave everything untouched.
    """
    v = {
        "network": [window["network"]],
        "station": [window["station"]],
        "channel": [window["channel"]],
        "location": window.get("location", "") or "",
        "starttime": f"{window['start']}T00:00:00",
        "endtime": f"{window['end']}T23:59:59",
    }
    if status_file:
        v["dmtri_status_file"] = status_file
    return v


def _psd_label(w: dict) -> str:
    return (f"{w['network']}.{w['station']}.{w['location']}.{w['channel']}  "
            f"{w['start']} -> {w['end']}  ({w['days']}d)")


def _estimate(total_days: int) -> str:
    minutes = total_days * _SECONDS_PER_DAY_FILE / 60.0
    if minutes < 1:
        return "<1 min"
    if minutes < 90:
        return f"~{minutes:.0f} min"
    return f"~{minutes / 60.0:.1f} h"


def run_psd_fix(report: str, inventory, window_days: int = DEFAULT_PSD_WINDOW_DAYS,
                required_only: bool = False, no_confirm: bool = False) -> int:
    """Repair a bounded day window around every 'data present, no PSD' finding."""
    findings = psd_findings(report)
    skipped_informational = 0
    if required_only:
        before = len(findings)
        findings = [f for f in findings if f["required"]]
        skipped_informational = before - len(findings)

    if not findings:
        print("\nNo PSD findings to repair"
              f"{' (none were psd_required)' if skipped_informational else ''}.")
        return 0

    windows = psd_windows(findings, window_days)
    total_days = sum(w["days"] for w in windows)

    print(f"\ndmtri fix --psd — {len(findings)} finding(s) in "
          f"{len(windows)} repair window(s), +-{window_days} days:")
    for w in windows:
        print(f"  - {_psd_label(w)}")
    if skipped_informational:
        print(f"\n  Note: {skipped_informational} informational (pre-2024) finding(s) "
              "skipped by --required-only.")
    print(f"\n  Up to {total_days} day-file(s): {_estimate(total_days)} if the host runs "
          "single-threaded,")
    print("  substantially less with seedpsd_parallel enabled in the inventory.")
    print("  Each window reports its own gap, and anything seedpsd skipped.")

    if not no_confirm:
        if input("\nProceed? (y/N): ").strip().lower() != "y":
            print("Aborted by user.")
            return 0

    results = []
    status_dir = tempfile.mkdtemp(prefix="dmtri-psd-")
    try:
        for i, w in enumerate(windows):
            try:
                _validate_fix(w)   # report values reach an Ansible command line
            except ValueError as e:
                print(f"\n=== {_psd_label(w)} ===\n  REJECTED: {e}")
                results.append((w, {"outcome": "rejected", "reason": str(e)}))
                continue
            print(f"\n=== {_psd_label(w)} ===")
            sf = os.path.join(status_dir, f"w{i}.json")
            rc = run_hook(PLAYBOOK_SEEDPSD_PSD_REPAIR, psd_to_vars(w, sf),
                          inventory=inventory, exit_on_error=False)
            results.append((w, _read_status(sf, rc)))
    finally:
        shutil.rmtree(status_dir, ignore_errors=True)

    return _print_psd_summary(results)


def _read_status(path: str, rc: int) -> dict:
    """What the play recorded, falling back to rc if it wrote nothing.

    A play that died before writing leaves no file; treat that as a failure
    rather than silently assuming the rc told the whole story.
    """
    try:
        with open(path) as fh:
            st = json.load(fh)
        st.setdefault("outcome", "repaired" if rc == 0 else "failed")
        return st
    except (OSError, ValueError):
        return {"outcome": "repaired" if rc == 0 else "failed",
                "reason": "play wrote no status" if rc == 0 else f"rc={rc}",
                "unverified": rc == 0}


def _print_psd_summary(results: list) -> int:
    """Report each outcome as what it was. A skip is not a repair."""
    def of(kind):
        return [(w, s) for w, s in results if s.get("outcome") == kind]

    repaired, skipped = of("repaired"), of("skipped")
    failed = of("failed") + of("rejected")
    unverified = [(w, s) for w, s in repaired if s.get("unverified")]

    print("\n" + "=" * 50)
    print(" dmtri fix --psd summary")
    print("=" * 50)
    with_skips = sum(1 for _, s in repaired if s.get("seedpsd_said"))
    print(f"  repaired : {len(repaired)} window(s)"
          f"{f' — {with_skips} where seedpsd skipped some data (see below)' if with_skips else ''}")
    print(f"  skipped  : {len(skipped)} window(s) (nothing in this archive to compute from)")
    print(f"  failed   : {len(failed)} window(s)")

    for w, s in skipped:
        print(f"\n  – skipped {_psd_label(w)}\n      {s.get('reason', 'no files')}")
    for w, s in failed:
        print(f"\n  ✗ failed  {_psd_label(w)}\n      {s.get('reason', 'see output above')}")
    # seedpsd exits 0 even when it skipped every file, so rc alone overstates
    # what was repaired. Show its own reasons, verbatim.
    for w, s in [(w, s) for w, s in repaired if s.get("seedpsd_said")]:
        print(f"\n  ⚠ seedpsd skipped some data in {_psd_label(w)}:")
        for line in s["seedpsd_said"]:
            count, _, reason = line.partition(" ")
            print(f"      {count:>5} × {reason}")
    for w, s in unverified:
        print(f"\n  ? unverified {_psd_label(w)}\n      "
              "the play exited 0 but recorded no status — treat as unconfirmed")

    backlog = [(w, s) for w, s in repaired
               if s.get("remaining_missing", 0) or s.get("remaining_dirty", 0)]
    if backlog:
        print("\nℹ These channels have more broken days than the window covered.")
        print("  They need a backfill, not a repair:")
        for w, s in backlog:
            print(f"    {w['network']}.{w['station']}.{w['location']}.{w['channel']}  "
                  f"{s.get('remaining_missing', 0)} missing + "
                  f"{s.get('remaining_dirty', 0)} invalid day(s) remain")
        print("    seedpsd-cli data load --network <N> --station <S> "
              "--channel <C> --year <Y> --parallel")

    print("\n  Note: rc=0 from the playbook is not proof a day is now covered."
          "\n  Confirm with:  eida-consistency rerun <report>")
    return 0 if not failed else 1
