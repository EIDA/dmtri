# datacenter-change-trigger

A CLI tool to trigger metadata and data update workflows across EIDA datacenters.

This tool queries the FDSN Station web service using custom parameters and is designed to later integrate with systems like `seedpsd`, `wfcatalog`, and `availability` via hooks.

---

## 🚀 Usage

```bash
datacenter_change_trigger [COMMAND] [OPTIONS]
```

### Commands:
- `refresh` — trigger metadata/data actions
- `clean` — trigger cleanup actions
- `--reload-nodes` — update the node list from the EIDA routing service

### Common options:
- `--network`, `--station`, `--location`, `--channel`
- `--starttime`, `--endtime` (ISO or `YYYY-MM-DD`)
- `--type` (`data`, `metadata`, or both)

At least `--network` or `--station` must be specified.  
If the selected time range exceeds 7 days, a confirmation is required.

---

## 📦 Installation

Will be updated when uploaded to PyPI.

---

## 🗂️ Project URL

Issues and development happen at:  
[https://github.com/EIDA/datacenter-change-trigger](https://github.com/EIDA/datacenter-change-trigger)
