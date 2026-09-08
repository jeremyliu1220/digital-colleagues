<!-- SPDX-License-Identifier: Apache-2.0 -->

# P10 Mac Operations

These commands apply only to the provider-free deterministic local reference candidate.
They do not establish an always-on service, provider compatibility, encrypted-storage
effectiveness, production security, or production readiness.

## Prerequisites and private layout

Use macOS on `arm64` or `x86_64`, with Docker Desktop installed and its daemon running,
and an already downloaded, verified P10 bundle. Run commands from that bundle:

```bash
./dc doctor
./dc quickstart
./dc status
```

The default private root is `~/Library/Application Support/Digital Colleagues`. It contains
`state`, `secrets`, `backups`, `diagnostics`, `releases`, `config`, and rebuildable `cache`.
Directories are `0700`; private files are `0600`. Do not commit, attach, email, or upload
state, databases, backups, logs, diagnostics, release locks, or credentials.

`doctor` is read-only. FileVault `enabled` produces `encrypted_storage_ready`; off or
unknown blocks live readiness but does not block deterministic reference mode. P10 neither
changes FileVault nor accepts provider credentials. The shipped launcher accepts no
environment or command-line override for this classification; only read-only
`/usr/bin/fdesetup status` is authoritative. Probe substitution exists only in temporary
test harnesses.

## Lifecycle

`quickstart` verifies the bundle and environment, initializes the safe layout, starts
digest-bound prebuilt images without a build, and waits for API, worker, Studio, and
machine-readable status readiness. `up` repeats the safe start idempotently. `down` stops
the managed Compose project and preserves all private data. `status --json` returns only
finite service/version/maturity/schema/readiness classifications.

Human messages default to `en-US`; use `--locale zh-TW` or `--locale en-US`. `--json` is
stable and non-localized. Locale changes presentation only.

## Backup and restore

Create a WAL-consistent source-bound backup while services may be running:

```bash
./dc backup --backup local-backup.tar.gz
```

The new file is verified and mode `0600`; an existing file is never overwritten. Restore
requires services stopped and an exact confirmation:

```bash
./dc down
./dc restore --backup local-backup.tar.gz --confirm RESTORE-P10-STATE
```

Replacement first creates a verified rollback backup. Restore validates archive members,
sizes, digest, SQLite integrity, applied migration identity, schema compatibility, and
source binding. Destructive down migration is unsupported. As with P8, restoring older
bytes also restores older session/authority state, so sessions and pending approvals must
be revalidated through existing governance controls.

## Update and uninstall

`./dc update` still returns `remote_distribution_authorization_required`. The remote gate
authorizes one publication and verification cycle, not an update protocol or mutable
channel. A locked `passed` policy therefore permits verified quickstart consumption but
does not silently authorize download/switch/database-update behavior.

`./dc uninstall` stops only the managed project and clears rebuildable cache, preserving
state, secrets, backups, and release identity. Private data deletion requires all of:

```bash
./dc uninstall --purge-data \
  --verified-backup local-backup.tar.gz \
  --confirm DELETE-P10-DATA
```

The command verifies the backup, stopped-service state, exact managed-root identity, and
release identity before bounded deletion. It never follows a symlink or touches another
root. Automated purge tests use only OS-temporary managed roots.

## Failure categories

Failures use finite categories and exit codes: `2` invalid input, `3` host/precondition,
`4` distribution or identity verification, `5` concurrent invocation, `6` bounded runtime
failure, `7` destructive confirmation/backup requirement, and `8` missing remote
authorization. Output omits local paths, users, container IDs, environment, database
content, credentials, and raw Docker or exception output.
