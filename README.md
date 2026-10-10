# dmtri

[![Run Tests](https://github.com/EIDA/dmtri/actions/workflows/pytest.yml/badge.svg)](https://github.com/EIDA/dmtri/actions/workflows/pytest.yml)
![Coverage](badges/coverage.svg)

`dmtri` is a command-line tool designed to trigger metadata and data refresh simulations across EIDA nodes using Ansible automation. It works across these components:

- `seedpsd`
- `wfcatalog`
- `availability`

It uses `.dmtri_jobs.json` per host to track async job state and integrates with `uv` and `ansible` for CLI automation.

## Documentation

The full documentation lives in [`docs/`](docs/):

- [Overview](docs/index.md)
- [Install](docs/install.md)
- [Usage](docs/usage.md) — refresh jobs, tracking, fixing inconsistencies, fixing missing PSDs
- [Configuration](docs/configuration.md) — inventory, PSD settings, customization
- [Troubleshooting](docs/troubleshooting.md)

## License

Copyright © 2026 EIDA (European Integrated Data Archive).

`dmtri` is free software: you can redistribute it and/or modify it under the terms of the
[GNU General Public License](LICENSE) as published by the Free Software Foundation, either
version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
See the [GNU General Public License](LICENSE) for more details.
