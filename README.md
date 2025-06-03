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

## Quick Start

You can use `dmtri` in two ways, depending on your preference:

### Option 1: Using `uvx`

You can run commands using:

```bash
uvx dmtri <command> [options]

```

---

### Option 2: Global (Tool-based) — Ideal for global CLI use

```bash
uv tool install dmtri
```

This makes `dmtri` available globally:

```bash
dmtri <command> [options]

```

You can update it any time using:

```bash
uv tool upgrade dmtri
```

---

### 2. Configure inventory

Edit the file: `src/inventory/hosts.ini`

Example:

```ini
[seedpsd_nodes]
<SEEDPSD_HOST> ansible_user=<USER> ansible_ssh_pass="<PASSWORD>" ansible_connection=ssh ansible_become=false ansible_ssh_common_args='-o StrictHostKeyChecking=no'

[seedpsd_nodes:vars]
seedpsd_dir=/home/<USER>/seedpsd

[wf_catalogue]
<WFCATALOG_HOST> ansible_user=<USER> ansible_ssh_pass="<PASSWORD>" ansible_connection=ssh ansible_become=false ansible_ssh_common_args='-o StrictHostKeyChecking=no'

[wf_catalogue:vars]
collector_dir=/home/<USER>/Programs/wfcatalogue<VERSION>/wfcatalog/collector2

[ws_availability]
<AVAILABILITY_HOST> ansible_user=<USER> ansible_ssh_pass="<PASSWORD>" ansible_connection=ssh ansible_become=false ansible_ssh_common_args='-o StrictHostKeyChecking=no'

[ws_availability:vars]
availability_dir=/home/<USER>/Programs/ws-availability<VERSION>/views
mongo_user=<MONGO_USERNAME>
mongo_pass=<MONGO_PASSWORD>
mongo_authdb=<MONGO_DATABASE>

```

---

### 3. Run example jobs

By default, this command runs **all refresh playbooks** (seedpsd, wfcatalog, and availability):

```bash
uv run dmtri refresh -e "network=HL station=ATH starttime=2024-01-01T00:00:00 endtime=2024-01-02T00:00:00"
```

---

### 4. Track jobs across hosts

```bash
uv run dmtri track
```

Shows per-host job status:
```
Job ID: j123... Type: seedpsd  Station: ATH  Status: ✅ Finished
Job ID: manual-... Type: availability  Status: ✅ Manual (not tracked)
```

---

### 5. Troubleshooting with `dmtri doctor`

Check SSH connectivity to your configured hosts using:

```bash
uv run dmtri doctor
```

This uses the Ansible `ping` module to test access to all servers in your inventory.

#### Options

- `--verbose` — Show full output from each host

#### Example

```bash
uv run dmtri doctor --verbose
```

If no response is received, ensure:

- You're connected to the VPN (if applicable)
- SSH access is configured correctly in your inventory file
- Host IPs and credentials are reachable and valid

###  Operation Details

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
