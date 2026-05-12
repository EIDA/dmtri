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
