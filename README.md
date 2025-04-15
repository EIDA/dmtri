# dmtri

[![Run Tests](https://github.com/EIDA/dmtri/actions/workflows/pytest.yml/badge.svg)](https://github.com/EIDA/dmtri/actions/workflows/pytest.yml)
![Coverage](badges/coverage.svg)

`dmtri` is a command-line tool designed to trigger metadata and data refresh simulations across EIDA FDSN nodes using Ansible automation.

---

## Installation

Clone the repository and set up the environment:

```bash
git clone https://github.com/EIDA/dmtri.git
cd dmtri
uv sync
```

---

## CLI Usage

```bash
uv run dmtri [command] [options]
```

### Commands

- `refresh`: Run a non-destructive seedpsd data/metadata refresh simulation
- `clean`: Simulate cleaning of outdated data/metadata

### Required Parameters

- `--starttime <timestamp>`  
  Start of the time range (ISO 8601 format, e.g., `2025-01-01T00:00:00`)

### Optional Parameters

- `--endtime <timestamp>`  
  End of the time range (default: current UTC time)

- `--network <codes>`  
  One or more FDSN network codes. Wildcards supported. Default: `"*"`

- `--station <codes>`  
  One or more FDSN station codes. Wildcards supported. Default: `"*"`

- `--location <codes>`  
  One or more FDSN location codes. Wildcards supported. Default: `"*"`

- `--channel <codes>`  
  One or more FDSN channel codes. Wildcards supported. Default: `"*"`

- `--type <data,metadata>`  
  Comma-separated values. Valid values: `data`, `metadata` (default: both)

- `--no-confirm`  
  Skips the confirmation prompt before running the playbook

---

## Examples

Refresh metadata and data for a specific station:

```bash
uv run dmtri refresh   --network HL   --station ATH   --starttime 2025-01-01T00:00:00   --endtime 2025-01-05T00:00:00
```

Clean data older than a given date:

```bash
uv run dmtri clean   --network HL   --station ATH   --starttime 2025-01-01T00:00:00
```

Suppress the execution plan confirmation:

```bash
uv run dmtri refresh --no-confirm ...
```

---

## Validation

The tool enforces several rules before execution:

- `--starttime` must be provided
- The time range cannot exceed 7 days without confirmation
- `--type` must include at least one valid value (`data`, `metadata`)

---

## Development

Run the CLI locally:

```bash
uv run dmtri --help
```

Run the test suite:

```bash
uv run pytest --cov=dmtri --cov-report=term-missing
```
