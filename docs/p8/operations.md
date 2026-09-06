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
values, private payloads, and raw exceptions are not output. Every backup receives an
explicit source binding. A P8-state binding is the candidate release manifest. The P8
operator emits the first-release P7 binding from fixed, mechanically checked metadata; it
identifies accepted P7 version `0.0.0`, commit and tree, schema 7, and the exact migration
manifest while explicitly recording that no P7 release manifest existed.

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
  --source-binding /operator/private/rc/digital-colleagues-release-manifest-0.1.0.json \
  --migrations migrations
PYTHONPATH=src python3 -B -m digital_colleagues.operations verify-backup \
  --backup /operator/private/pre-upgrade.tar.gz \
  --source-binding /operator/private/rc/digital-colleagues-release-manifest-0.1.0.json \
  --migrations migrations
```

The versioned backup manifest binds backup format, release, source commit, schema and
migration versions, migration-manifest digest, database digest and size, UTC creation time,
and a random non-secret identifier. It contains no local path. Creating a backup refuses an
existing output rather than overwriting it.

## First release: accepted P7 to P8

P7 predates the release-manifest format. Do not fabricate or require a P7 release manifest.
Before any P8 API or worker starts against the state, verify that the running/source version
is the accepted P7 Git object `df47f8d075f7c0660ab5ed6035f8acfa3d3da4dc`, stop its
writers, and run the verified P8 operator tool against that state with the fixed descriptor:

```bash
umask 077
PYTHONPATH=src python3 -B -m digital_colleagues.operations \
  accepted-p7-source-binding > /operator/private/accepted-p7-source-binding.json
PYTHONPATH=src python3 -B -m digital_colleagues.operations backup \
  --database /operator/private/state.sqlite \
  --backup /operator/private/p7-pre-upgrade.tar.gz \
  --source-binding /operator/private/accepted-p7-source-binding.json \
  --migrations migrations
PYTHONPATH=src python3 -B -m digital_colleagues.operations verify-backup \
  --backup /operator/private/p7-pre-upgrade.tar.gz \
  --source-binding /operator/private/accepted-p7-source-binding.json \
  --migrations migrations
```

The descriptor is not a retroactive release artifact. It is a P8-authored, mechanically
checked transition binding to the immutable P7 Git object. Its migration digest must match
the supplied 001–007 files. An unknown P7 tree, version, schema, source descriptor, or
migration drift stops the transition.

## Upgrade

1. Verify candidate checksums, release manifest, supply-chain inventory, and archive
   allowlist.
2. Create and verify a pre-upgrade backup using the current source binding. For the first
   release use the exact P7 descriptor above; for later P8-state operations use the P8
   release manifest.
3. Stop API and worker writers normally. Keep the matching source code and source binding
   available.
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
  --backup-source-binding /operator/private/accepted-p7-source-binding.json \
  --current-source-binding /operator/private/rc/digital-colleagues-release-manifest-0.1.0.json \
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

For the first release, rollback is: stop P8, restore the verified P7-bound pre-upgrade
backup while creating a separately P8-bound rollback backup of the replaced state, then
start the exact accepted P7 Git object. P7 has no previous release manifest; its fixed
source descriptor supplies the required source/version/schema binding. For later releases,
start the matching previous code and release manifest. Destructive down-migration is
unsupported. Do not start newer code against restored older state and call that rollback.

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
