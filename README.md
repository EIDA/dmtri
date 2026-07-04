# dmtri

[![Run Tests](https://github.com/EIDA/dmtri/actions/workflows/pytest.yml/badge.svg)](https://github.com/EIDA/dmtri/actions/workflows/pytest.yml)
![Coverage](badges/coverage.svg)

`dmtri` is a command-line tool designed to trigger metadata and data refresh simulations across EIDA nodes using Ansible automation.

---
- `seedpsd` 
- `wfcatalog` 
- `availability` 

It uses `.dmtri_jobs.json` per host to track async job state and integrates with `uv` and `ansible` for CLI automation.

---

## Installation & Setup

### 1. Install or Run
You can run `dmtri` directly or install it as a tool:

#### Run without installing (via `uvx`)
```bash
uvx dmtri <command>
```

#### Install as a global tool
```bash
# Using uv (recommended)
uv tool install dmtri

# Using pip
pip install dmtri
```

### 2. Configure
Once installed, set up your local configuration directory:

```bash
dmtri init
```

This creates a config folder (e.g., `~/.config/dmtri/` on Linux) with a template `hosts.ini` and all standard playbooks.

#### Edit your Inventory
Use `nano` (or any text editor) to fill in your EIDA server details:

```bash
nano ~/.config/dmtri/hosts.ini
```

#### Verify Connectivity
Check if your servers are reachable:

```bash
dmtri doctor
```

---

## Usage

### Run Refresh Jobs
Trigger refresh playbooks across your nodes:

```bash
dmtri refresh --network HL --station ATH --starttime 2024-01-01
```

### Track Job Status
Monitor the status of asynchronous jobs:

```bash
dmtri track
```

### Fix Inconsistencies
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

#### Prerequisite: the `eida-consistency` CLI

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

---

## Customization

### Local Playbooks
`dmtri init` copies all playbooks to your config directory. You can edit them to change automation logic:

```bash
# Location: ~/.config/dmtri/playbooks/
nano ~/.config/dmtri/playbooks/refresh/availability_refresh.yml
```

`dmtri` prioritizes these local playbooks over the bundled defaults.

### Inventory Overrides
Override the inventory at runtime:

```bash
dmtri doctor --inventory ./my_custom_hosts.ini
```

---

## Operation Details

`dmtri` supports two main operations for both metadata and data: `refresh` and `clean`. These affect the following components:

#### 🔄 Refresh

- **Metadata**
  - `seedpsd`: Scans for new metadata.
  - `availability`: Refreshes the view in MongoDB.

- **Data**
  - Identifies data files in the archive for the specified epoch (by NSLC and time range).
    - `seedpsd`: Recalculates seedPSD for new files.
    - `wfcatalog`: Runs the collector on new data files.

#### 🧹 Clean

- **Metadata**
  - `seedpsd`: Removes the metadata entries.
  - `availability`: Refreshes the view in MongoDB.

- **Data**
  - Identifies data files in the archive for the specified epoch.
    - `seedpsd`: Removes associated seedPSD data (via CLI).
    - `wfcatalog`: Removes files using the `--delete` option in the collector.

---

## License

Copyright © 2026 EIDA (European Integrated Data Archive).

`dmtri` is free software: you can redistribute it and/or modify it under the terms of the
[GNU General Public License](LICENSE) as published by the Free Software Foundation, either
version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
See the [GNU General Public License](LICENSE) for more details.
