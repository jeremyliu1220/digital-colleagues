<!-- SPDX-License-Identifier: Apache-2.0 -->

# Security Policy

## Supported status

Digital Colleagues is pre-release research software. P1 is a repository scaffold with no
runtime. No version is production-supported, and no security, compliance, availability,
or enterprise-isolation claim is made.

## Reporting a vulnerability

Use the repository host's **private vulnerability reporting** feature when it is available.
Do not place exploit details, credentials, personal information, provider identifiers, or
private environment data in a public issue.

If private reporting is not enabled, open a minimal public issue requesting a private
maintainer contact path. Include no vulnerability details. Repository maintainers must
enable a private reporting path before publication or accepting security reports.

Maintainers will acknowledge a private report, assess affected scope, coordinate a fix and
disclosure when warranted, and record only sanitized public evidence. Response timing is a
best-effort goal until a later release defines supported versions and service levels.

## Security boundary

The current threat model is in `docs/security/threat-model.md`. Loopback binding, local
tokens, deterministic adapters, or a clean boundary scan are not substitutes for security
review. Live receipts and personal acceptance data remain outside the public repository.
