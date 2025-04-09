# dmtri
[![Run Tests](https://github.com/EIDA/dmtri/actions/workflows/pytest.yml/badge.svg)](https://github.com/EIDA/dmtri/actions/workflows/pytest.yml)
![Coverage](badges/coverage.svg)


Trigger metadata and data refresh workflows across EIDA FDSN nodes.


## Installation

Clone the repository:

```bash
git clone https://github.com/EIDA/dmtri.git
cd dmtri
```

Set up the environment:

```bash
uv sync
```

Run the CLI:

```bash
uv run dmtri refresh \\
  --network FR \\
  --station CIEL \\
  --starttime 2025-01-01T00:00:00
```

Make sure you have [uv](https://github.com/astral-sh/uv) installed.


## Configuration

Create a configuration file in:

```
~/.config/dmtri/config.toml
```

Example:

```toml
[endpoints]
NOA = "https://eida.gein.noa.gr"
GFZ = "https://geofon.gfz.de"
ODC = "https://orfeus-eu.org"
```


## Usage

Run the CLI using:

```bash
uv run dmtri refresh \
  --network FR \
  --station CIEL \
  --starttime 2025-01-01T00:00:00
```

Optional:

```bash
--endtime 2025-01-10T00:00:00
--type data,metadata
--config ./config.toml  # optional override
```

You must provide at least one of `--network` or `--station`.

## Development

Run tests:

```bash
uv run pytest
```
