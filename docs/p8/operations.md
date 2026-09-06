<!-- SPDX-License-Identifier: Apache-2.0 -->

# P8 Local Operations

These procedures apply only to the v0.1 local reference candidate. They do not establish
production readiness, availability, encrypted storage, enterprise identity, or a support
service. Run them as the local operator who controls the Compose project and private state.

## Private-data boundary

`state.sqlite`, its WAL and SHM files, every backup, rollback backup, and diagnostic bundle
are operator-private. They can contain identities, membership and authority revisions,
sessions and credential digests, work, approvals, effects, and causal history. Keep the
containing directory mode `0700` and each generated file mode `0600`. Do not commit, attach
to a public issue, place in release artifacts, print, email, or upload these files. Encrypt
storage and transport outside this project if the operator's risk assessment requires it;
v0.1 does not provide encryption at rest. Secure deletion on SSD, snapshots, backups, and
container storage depends on the operator's platform and is not guaranteed by `unlink`.

The tools emit only finite status/category JSON. Paths, database contents, credential
values, private payloads, and raw exceptions are not output. Keep the release manifest
beside the candidate: backup and restore use it to bind release `0.1.0`, the public source
commit, and the exact migration manifest.

## Verify a release candidate

From a clean committed source tree with the P8 locked tools installed:

```bash
python3 -B scripts/build_p8_release.py --output /operator/private/rc
python3 -B scripts/check_p8_release.py .
python3 -B scripts/check_p8_reproducibility.py .
```

The output directory must be new or empty. Verify `SHA256SUMS` and
`digital-colleagues-release-manifest-0.1.0.json` before starting the candidate. P8 builds
but does not publish, tag, upload, or push any file or image.

## Consistent online backup

Do not copy only `state.sqlite`: WAL may contain committed pages absent from that file. The
backup command uses the SQLite online backup API while writers may be running, checks the
copied database, verifies migration identity/checksums, and packages exactly
`manifest.json` plus `state.sqlite` as a private archive.

```bash
umask 077
PYTHONPATH=src python3 -B -m digital_colleagues.operations backup \
  --database /operator/private/state.sqlite \
  --backup /operator/private/pre-upgrade.tar.gz \
  --release-manifest /operator/private/rc/digital-colleagues-release-manifest-0.1.0.json \
  --migrations migrations
PYTHONPATH=src python3 -B -m digital_colleagues.operations verify-backup \
  --backup /operator/private/pre-upgrade.tar.gz \
  --release-manifest /operator/private/rc/digital-colleagues-release-manifest-0.1.0.json \
  --migrations migrations
```

The versioned backup manifest binds backup format, release, source commit, schema and
migration versions, migration-manifest digest, database digest and size, UTC creation time,
and a random non-secret identifier. It contains no local path. Creating a backup refuses an
existing output rather than overwriting it.

## Upgrade

1. Verify candidate checksums, release manifest, supply-chain inventory, and archive
   allowlist.
2. Create and verify a pre-upgrade backup using the current matching release manifest.
3. Stop API and worker writers normally. Keep the pre-upgrade code and manifest available.
4. Start the candidate source archive through default Compose. The store applies only
   migrations 001-007 and checks every immutable checksum; P8 adds no migration 008.
5. Verify `/health`, exchange a local bootstrap/session only if required, and perform the
   documented authenticated smoke read. Re-check current membership and pending approvals.

A migration failure rolls back the migration SQL and its `schema_migrations` record in the
same transaction. It does not trigger an automatic restore.

## Restore and release rollback

Restore must run with API and worker stopped. Restoring to a new database is the default.
Replacing state requires both `--replace` and `--offline-confirmed`, plus a distinct path
for an automatically verified rollback backup:

```bash
PYTHONPATH=src python3 -B -m digital_colleagues.operations restore \
  --backup /operator/private/pre-upgrade.tar.gz \
  --database /operator/private/state.sqlite \
  --release-manifest /operator/private/rc/digital-colleagues-release-manifest-0.1.0.json \
  --migrations migrations \
  --replace \
  --offline-confirmed \
  --rollback-backup /operator/private/pre-restore-rollback.tar.gz
```

Restore validates the archive type and exact member list without generic extraction,
rejects path traversal and symlink/hardlink/special entries, bounds sizes, verifies database
digest and integrity, refuses future schema or incompatible migration history/manifest, and
then uses a same-directory temporary file plus atomic replacement. It never silently
overwrites existing state.

Release rollback is: stop the candidate, restore the verified pre-upgrade backup, and start
the matching previous code and manifest. Destructive down-migration is unsupported. Do not
start newer code against restored older state and call that rollback.

Restoring older bytes also rolls session state, credential digests, approval expiry state,
membership and authority revisions, and audit history back to that instant. Treat all
restored sessions as untrusted: use the authorized recovery flow to revoke/rotate sessions,
re-check current HUMAN memberships and roles, and re-review every pending approval before
dispatch. A restore is not proof that old authority remains appropriate.

## Redacted diagnostics

```bash
PYTHONPATH=src python3 -B -m digital_colleagues.operations diagnostics \
  --database /operator/private/state.sqlite \
  --output /operator/private/support-bundle.tar.gz \
  --release-manifest /operator/private/rc/digital-colleagues-release-manifest-0.1.0.json \
  --migrations migrations \
  --causal-id correlation-synthetic
```

The mode-`0600` archive contains only `diagnostics.json`: release version/public commit,
verified schema/migration status, coarse Python/SQLite/platform versions, finite health
classifications, and purpose-framed SHA-256 values for at most 16 supplied safe causal
identifiers. It never includes state/backup bytes, raw logs or audit exports, environment
values, local paths, user names, endpoints/URLs, cookies, CSRF, session/bootstrap/
enrollment/recovery/adapter credentials or digests, request/response bodies, private
payloads, live receipts, or personal data. Inspect it locally before any separately
authorized disclosure, then apply the same protected retention and deletion policy as a
backup.
