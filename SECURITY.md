# Security Policy

## Supported versions

Security fixes are applied to the latest released version of `dmtri` on PyPI.
Please upgrade to the newest release before reporting an issue.

## Reporting a vulnerability

Please **do not** open a public GitHub issue for security vulnerabilities.

Instead, report privately via GitHub's
[private vulnerability reporting](https://github.com/EIDA/dmtri/security/advisories/new)
(Security → Report a vulnerability). We aim to acknowledge reports within a few
working days and will coordinate a fix and disclosure timeline with you.

## Handling of credentials

`dmtri` orchestrates Ansible against EIDA nodes and therefore touches sensitive
material. Note that:

- Host credentials (SSH users/passwords, Mongo credentials) live in your local
  `hosts.ini`, created by `dmtri init` from a placeholder example. This file is
  **never** committed and is **not** bundled into the published package.
- Report values passed to `dmtri fix` are validated and rejected if they contain
  shell metacharacters, so untrusted report content cannot reach a playbook as
  an injected command.

If you believe any credential or sensitive path is exposed in the repository or
a published artifact, treat it as a vulnerability and report it privately as
described above.
