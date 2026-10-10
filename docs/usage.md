---
tags:
  - node-operator
---

# dmtri: Usage

## Run Refresh Jobs

Trigger refresh playbooks across your nodes:

```bash
dmtri refresh --network HL --station ATH --starttime 2024-01-01
```

## Track Job Status

Monitor the status of asynchronous jobs:

```bash
dmtri track
```

## Fix Inconsistencies

Automatically repair the inconsistencies found in an [`eida-consistency`](https://github.com/EIDA/eida-consistency) report. A report lists streams where the **availability** view and **dataselect** disagree; `dmtri fix` reads that report and, for each affected stream, re-runs the WFCatalog collector and rebuilds the availability view for the exact time window.

Point it at a report file or URL:

```bash
dmtri fix https://eida-oculus.orfeus-eu.org/consistency/NOA/2026/NOA_2026-06-07_140510.json
```

Fix only specific entries from the report (by their index):

```bash
dmtri fix report.json --index 2 --index 16
```

After a fix, the availability service keeps cached answers for ~20 minutes, so a stream may still look unfixed for a short while. Re-check once the cache expires — this only verifies, it changes nothing:

```bash
dmtri fix --verify-only report.json
```

### Prerequisite: the `eida-consistency` CLI

`dmtri fix` reads the report through [`eida-consistency`](https://github.com/EIDA/eida-consistency) (version **0.5.1 or newer**, for its `explore --json` output). If it isn't already on the machine, install it any one of these ways:

```bash
uv tool install eida-consistency     # recommended — puts it on your PATH
pipx install eida-consistency
pip install eida-consistency
```

You don't strictly have to install it: if `uv` is present, `dmtri fix` will run it on demand via `uvx eida-consistency`. And if it's installed somewhere off your `PATH`, point dmtri at it:

```bash
export DMTRI_EIDA_CONSISTENCY='/full/path/to/eida-consistency'
```

If it's missing (or too old), `dmtri fix` stops before touching anything and prints the exact install/upgrade command to run.

## Fix Missing PSDs

Sometimes a day has data but no PSD. `eida-consistency` finds these days. `dmtri fix --psd` makes the PSDs again.

You need `eida-consistency` **0.7.1 or newer**.

**1. Find the problems**

```bash
eida-consistency consistency --node NOA
```

This writes a report, for example `reports/noa_20261008.json`.

**2. Fix them**

```bash
dmtri fix reports/noa_20261008.json --psd
```

dmtri shows what it will do and asks `Proceed? (y/N)`. Type `y`.

**3. Check**

Wait 20 minutes, then:

```bash
eida-consistency rerun reports/noa_20261008.json
```

`RESOLVED` means fixed. `PERSISTS` means still broken. See [Troubleshooting](troubleshooting.md).

### What dmtri does

For each day without a PSD, dmtri takes that day, plus 15 days before and 15 days after. It runs one seedpsd command on those days:

```bash
seedpsd-cli data mseed --update --list <files>
```

dmtri never fixes a whole station at once, because that can take days. If a station has many more broken days, dmtri tells you:

```
  repaired : 7 window(s)
  skipped  : 2 window(s) (nothing in this archive to compute from)
  failed   : 0 window(s)

ℹ These channels have more broken days than the window covered.
  They need a backfill, not a repair:
    HP.EFP..HHZ  2919 missing + 0 invalid day(s) remain
```

To fill those days, run `seedpsd-cli data load` on the seedpsd machine when you have time.

### Options

| Option | What it does |
|---|---|
| `--psd` | Fix availability first, then PSDs |
| `--psd-only` | Fix PSDs only |
| `--psd-window 5` | Use 5 days before and after, instead of 15 |
| `--required-only` | Fix only days from 2024-01-01 on, when PSDs became required |
| `--no-confirm` | Start without asking |

## Operation Details

`dmtri` supports two main operations for both metadata and data: `refresh` and `clean`. These affect the following components:

### Refresh

- **Metadata**
    - `seedpsd`: Scans for new metadata.
    - `availability`: Refreshes the view in MongoDB.
- **Data**
    - Identifies data files in the archive for the specified epoch (by NSLC and time range).
        - `seedpsd`: Recalculates seedPSD for new files.
        - `wfcatalog`: Runs the collector on new data files.

### Clean

- **Metadata**
    - `seedpsd`: Removes the metadata entries.
    - `availability`: Refreshes the view in MongoDB.
- **Data**
    - Identifies data files in the archive for the specified epoch.
        - `seedpsd`: Removes associated seedPSD data (via CLI).
        - `wfcatalog`: Removes files using the `--delete` option in the collector.
