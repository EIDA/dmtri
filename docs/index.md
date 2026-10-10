---
tags:
  - node-operator
---

# dmtri: Overview

`dmtri` is a command-line tool designed to trigger metadata and data refresh simulations across EIDA nodes using Ansible automation. It works across these components:

- `seedpsd`
- `wfcatalog`
- `availability`

It uses `.dmtri_jobs.json` per host to track async job state and integrates with `uv` and `ansible` for CLI automation.

## Source

<https://github.com/EIDA/dmtri>
