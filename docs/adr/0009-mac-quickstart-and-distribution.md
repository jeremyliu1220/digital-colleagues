<!-- SPDX-License-Identifier: Apache-2.0 -->

# ADR 0009: Mac Quickstart and Digest-Bound Distribution

- Status: Accepted for P10 development candidate
- Decision date: 2026-09-07
- Scope: P10 local distribution, operator interface, storage readiness, and i18n

## Context

The accepted P9 baseline plans a Public Pilot but distributes no v0.2 runtime. P10 must
make the deterministic reference stack usable from a downloaded bundle on an Apple silicon
or Intel Mac with Docker Desktop, without requiring host Python, Node, npm, Make, Git, a
provider credential, or a source build. Remote publication is not authorized.

## Decision

The distribution has two prebuilt OCI images: one non-root runtime image shared by API,
worker, and one-shot operator commands, and one Studio image. Each OCI index contains
exactly `linux/amd64` and `linux/arm64`. Docker bases and runtime selection use exact
digests. The image-only Compose file publishes only loopback ports, bind-mounts traceable
state, uses read-only roots and tmpfs, and gives Studio no secret mount.

The downloaded bundle contains `dc`, `compose.p10.yaml`, a rigid manifest, an operations
source binding, a verification policy, and checksums. `dc` parses JSON with the macOS
property-list utility and never executes or sources it. Mutations use an exact managed-root
identity, release identity, Compose identity, `umask 077`, safe modes, and a bounded
exclusive lock. Human output supports `zh-TW` and `en-US`; JSON keys/categories remain
stable and non-localized.

Private state lives under the user's Application Support directory in separate state,
secrets, backups, diagnostics, releases, config, and rebuildable cache directories.
FileVault is probed read-only. Off or unknown does not prevent provider-free deterministic
mode, but it blocks live readiness. P10 accepts and mounts no provider credential.

Studio text moves to parity-checked translation resources. Locale is presentation state;
it cannot change a route, payload, schema, role, authority, default, or validation rule.
FastAPI and package metadata use stable product terms and the development versions
`0.2.0.dev0`/`0.2.0-dev.0`. Existing milestone-named routes remain compatibility surfaces.

## Distribution authorization

Local OCI build, local layout verification, and isolated loopback runtime tests are
authorized. Remote push, package upload, signing, attestation generation, artifact upload,
tag, and Release creation are not. GHCR, registry signature, and registry attestation stay
`not_evaluated`; the remote distribution gate stays `authorization_required`.

## Consequences

- A source checkout is not needed by a bundle user and no build occurs during quickstart.
- Backup/restore reuse the accepted WAL-consistent P8 implementation through a strict P10
  source binding and an image-contained Python runtime.
- `update` refuses before switching while the authorized remote verification identity and
  evidence do not exist.
- P10 can become a local implementation candidate, but its full exit and P11 remain
  blocked on separately authorized, independently accepted remote distribution evidence.

## Scoped correction

The shipped launcher has no FileVault injection switch: only read-only
`/usr/bin/fdesetup status` can determine the production classification. Tests create any
probe substitute only inside an OS-temporary harness. API, worker, and Studio share one
explicit `internal: true` Compose network, while the operator remains `network_mode: none`.
A fixed ingress-only Nginx gateway, with no state, secrets, environment, or variable
destination, bridges that network to a separate loopback-published network. The runtime
Gate verifies the actual Docker network and compares a reachable gate-owned local control
endpoint with refused API, worker, and Studio connections; evidence derives the
external-egress count from those probes.

The release manifest has one rigid 18-field schema across the template, builder, Python
verifier, and shipped launcher. `source_timestamp` remains part of the private operations
source binding but is not a release-manifest field. Missing, extra, duplicate, unknown, or
wrong-type manifest fields fail closed.

## Rejected alternatives

- Mutable tags or `latest`: they do not bind executed bytes.
- Anonymous state volumes: they obscure operator-controlled persistence and backup scope.
- Credentials in environment or Compose interpolation: they cross unnecessary disclosure
  boundaries.
- Enabling FileVault: P10 has no authority to change host encryption or recovery state.
- Publishing from ordinary push CI: it exceeds current authorization and makes review
  timing ambiguous.
