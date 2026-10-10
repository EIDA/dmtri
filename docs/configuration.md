---
tags:
  - node-operator
---

# dmtri: Configuration

Once installed, set up your local configuration directory:

```bash
dmtri init
```

This creates a config folder (e.g., `~/.config/dmtri/` on Linux) with a template `hosts.ini` and all standard playbooks.

## Edit your Inventory

Use `nano` (or any text editor) to fill in your EIDA server details:

```bash
nano ~/.config/dmtri/hosts.ini
```

## PSD settings

`dmtri fix --psd` runs on the machine where seedpsd is installed. This is often a different machine. Add it to `hosts.ini`:

```ini
[seedpsd_nodes]
seedpsd.example.org ansible_user=qc

[seedpsd_nodes:vars]
# Where seedpsd is installed
seedpsd_dir=/home/qc/seedpsd
# Full path to the SDS archive (must start with /)
seedpsd_archive=/data/sds
# Optional: use several CPUs (off by default)
seedpsd_parallel=true
seedpsd_max_cpu=4
```

## Verify Connectivity

Check if your servers are reachable:

```bash
dmtri doctor
```

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
