# Changelog

All notable changes to `dmtri` are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.5] - 2026-07-04

### Added
- `dmtri fix --verbose` (`-v`) streams `eida-consistency explore` progress
  (per-query URLs) live instead of waiting silently.
- Continuous integration now runs the test suite on Python 3.9, 3.11, and 3.13.
- `[project.urls]` metadata (Homepage, Repository, Issues) so the PyPI page links
  back to the GitHub project.
- `CHANGELOG.md` and `SECURITY.md`.

### Changed
- `dmtri clean` now fails with a clear "not yet implemented" message instead of
  running empty placeholder playbooks. The subcommand remains visible in `--help`
  but is marked as not yet implemented.
- Minimum supported Python raised to **3.9** (3.8 is end-of-life and cannot build
  the package from source under the `setuptools>=77` requirement of the SPDX
  license metadata).

## [0.1.4] - 2026-07-04

### Fixed
- `tomllib` `ImportError` on Python 3.9/3.10 — now falls back to the `tomli`
  backport, which is installed conditionally for `python_version < "3.11"`.

### Added
- Tests for `run_init` bootstrap, `get_inventory_path` resolution priority,
  `_resolve_playbook` override precedence, bundled-playbook YAML validity, and
  the `get_version` pyproject fallback (coverage 82% → 91%).

## [0.1.3] - 2026-07-04

### Added
- `GPL-3.0-or-later` license (`LICENSE`), with PEP 639 SPDX metadata and a
  README license notice. Copyright © EIDA.

### Changed
- Replaced a hardcoded internal IP in the doctor tests with an RFC 5737
  documentation address, and removed developer home-directory paths from the
  bundled Ansible reference configs.
- Stopped tracking generated coverage artifacts (`.coverage`, `coverage.xml`).

[Unreleased]: https://github.com/EIDA/dmtri/compare/0.1.5...HEAD
[0.1.5]: https://github.com/EIDA/dmtri/compare/0.1.4...0.1.5
[0.1.4]: https://github.com/EIDA/dmtri/compare/0.1.3...0.1.4
[0.1.3]: https://github.com/EIDA/dmtri/compare/0.1.2...0.1.3
