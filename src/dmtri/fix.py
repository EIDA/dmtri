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
import shutil
import subprocess
import sys
from datetime import date, timedelta

from dmtri.hooks.hooks import run_hook
from dmtri.paths import PLAYBOOK_WFCATALOG_REFRESH, PLAYBOOK_AVAILABILITY_REBUILD

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
        return override.split()
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
    return 0 if not still else 1


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
    return 0 if not bad else 1
