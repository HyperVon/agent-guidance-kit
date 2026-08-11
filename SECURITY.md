# Security policy

## Supported versions

This project is in pre-v1 development. Security fixes apply to the current main
development line.

## Reporting a vulnerability

Once the public repository is available, report vulnerabilities through its
private GitHub Security Advisory flow. Do not put live credentials, exploit
details, or private environment data in a public issue.

## Scope

Security-sensitive areas include destination path validation, symlink handling,
conflict preflight, unintended overwrite, imported-content execution, secret
exposure, and instructions that could cause an agent to broaden its authority.

The bootstrap and validation tools are designed to run without network access
and must not read credentials, databases, logs, or application runtime state.
