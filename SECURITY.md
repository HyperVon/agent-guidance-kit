# Security policy

## Supported versions

Security fixes apply to the current `main` development line and the latest
documented release. Older versions may not receive backports.

## Reporting a vulnerability

Report vulnerabilities through the repository's
[private GitHub Security Advisory flow][private-report]. Do not put live
credentials, exploit details, or private environment data in a public issue.

Include the affected revision, impact, minimal reproduction details, and any
known mitigation. The maintainer will acknowledge the report and coordinate a
fix and disclosure timeline through the private advisory.

## Scope

Security-sensitive areas include destination path validation, symlink handling,
conflict preflight, unintended overwrite, imported-content execution, secret
exposure, and instructions that could cause an agent to broaden its authority.

The bootstrap and validation tools are designed to run without network access
and must not read credentials, databases, logs, or application runtime state.

[private-report]: https://github.com/HyperVon/agent-guidance-kit/security/advisories/new
