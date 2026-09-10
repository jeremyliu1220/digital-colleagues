<!-- SPDX-License-Identifier: Apache-2.0 -->

# Security Policy

## Supported status

Digital Colleagues is pre-release research software. **P8 passed independent acceptance
and was fast-forward merged from `codex/p8-release-readiness` to `main`.** The accepted P8
commit is `0bb80ab187932fbad42fbf665b8310987609a1f5`. The result is only a **v0.1 local
reference release candidate** for version `0.1.0`: no tag has been created, and nothing
has been published, uploaded, or formally released. It is not production-ready and
establishes no production security, high availability, enterprise IAM, real-provider
readiness, compliance, security certification, production hardening, or other excluded
capability. Human evaluation, live-provider evidence, and the unmeasured five-minute
target remain `not_evaluated`. Post-v0.1 S1–S4 and Self-initiated autonomy have not started
and do not start automatically. P0–P8 accepted artifacts, evidence, acceptance contracts,
receipts, and migrations remain historical and unchanged.

P10 is a Mac quickstart and distribution development candidate for a future v0.2
Public Pilot. It adds no package runtime, model/provider call, OAuth, connector, automatic
effect, Semantic Memory, Agent collaboration, or executable Skill. A separately authorized
one-time remote gate fixes the repository/ref/SHA, GHCR subjects, public visibility,
keyless signer/issuer/annotation, GitHub provenance, and final read-only workflow lock.
Wrong or incomplete remote evidence fails closed. See the
[v0.2 threat model](docs/security/v0.2-public-pilot-threat-model.md) and
[v0.2 privacy boundary](docs/security/v0.2-public-pilot-privacy-boundary.md). Their planned
controls are not evidence of live-provider security or production readiness.

P12 is a governance-only Public Pilot Continuity Rebaseline. It adds no runtime security
capability. Its accepted future boundary keeps HUMAN, MODEL, SERVICE, and
ExternalPartyReference identities disjoint; separates memory admission from lifecycle;
requires exact authority revalidation, mandatory checkpoints, ambiguity quarantine and
cursor-independent recovery; and assigns AutomaticEffectAuthorization only to P18.
These remain planned contracts until their owning P13-P20 gates pass.

P10 stores state and backups below Application Support with private modes, uses exact
digest image selection, binds ports only to loopback, gives Studio no secret mount, and
checks FileVault without changing it. The remote gate is public distribution evidence, not
proof of host, registry availability over time, supply-chain safety, production security,
privacy, encryption, or tenant isolation.

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
review. Local state, backups, rollback backups, and diagnostic bundles are unencrypted
operator-private data and must remain outside the public repository. Live receipts and
personal acceptance data remain outside the public repository.

For future live pilot work, Mac credentials require a FileVault check, secret directories
mode `0700`, credential files mode `0600`, and read-only service mounts. Keys/tokens are
forbidden from environment variables, SQLite, audit, backup, diagnostics, logs, errors,
command arguments, and public evidence. Always-on Linux requires an operator-provided
encrypted volume; without proven storage encryption, live readiness remains
`not_evaluated` or live mode is blocked. Do not submit credentials or live identifiers in
an issue, conversation, fixture, or repository file.
