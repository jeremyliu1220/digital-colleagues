<!-- SPDX-License-Identifier: Apache-2.0 -->

# P8 Release and Operational Readiness Acceptance Contract

Status: fixed development contract. P8 may be described only as **development complete,
awaiting independent acceptance** after every gate below passes. It may not be described as
accepted, published, tagged, production-ready, or a formal release before an independent
acceptance task and separately authorized version-management work. This contract is fixed
before P8 implementation and must not be deleted, weakened, or rewritten to fit results.

## Baseline, branch, and historical boundary

P8 starts on `codex/p8-release-readiness` from the independently accepted and fast-forward
merged P7 `main` baseline `df47f8d075f7c0660ab5ed6035f8acfa3d3da4dc`. That exact
commit is the merge-base of the P8 acceptance, implementation, and evidence commits.

P0-P7 acceptance records, Golden Paths, artifacts, evidence, provenance receipts,
fingerprints, and migrations 001-007 remain byte-unchanged from the fixed base. P8 must not
invoke a P0-P7 evidence writer, modify the parent research repository or its fingerprint,
or change the source allowlist's fixed parent revision. P8 adds no migration 008 and does
not modify migrations 001-007. Historical validation uses accepted Git objects and fixed
digests rather than rebuilding evidence.

P8 converges only the implemented v0.1 local reference scope. It adds no Semantic Memory,
Skill Learning or governed Skill runtime, shared knowledge, multi-person collaboration
platform, Self-initiated autonomy, arbitrary tool execution, enterprise IAM, OIDC, SSO,
SCIM, PostgreSQL, distributed store, high availability, multi-region operation, production
tenancy isolation, encryption at rest, compliance certification, named-provider support,
or real delivery.

## Version and release-candidate artifact boundary

The release-candidate version is exactly `0.1.0` in Python metadata, Studio metadata,
operator output, release manifests, and documentation. The P8 implementation must remove
the prior `0.0.0` scaffold metadata without weakening the historical P1-P7 gates; historical
checks evaluate their accepted commits or historical fixtures where version `0.0.0` was
part of the original meaning.

One build produces exactly these public files in an OS temporary output directory:

- `digital-colleagues-0.1.0-source.tar.gz`: a normalized allowlisted source archive from
  one clean commit, including the local Compose reference and its build inputs;
- `digital_colleagues-0.1.0-py3-none-any.whl`: the Python package wheel;
- `digital-colleagues-studio-0.1.0.tar.gz`: normalized built Studio static content;
- `digital-colleagues-sbom-0.1.0.json`: the deterministic machine-readable supply-chain
  inventory for the candidate;
- `digital-colleagues-release-manifest-0.1.0.json`: versioned bindings among the version,
  source commit, source timestamp, migration-manifest digest, artifact digests, build-input
  digests, evidence classes, and claim exclusions; and
- `SHA256SUMS`: sorted checksums for the other five files.

The manifest does not hash itself; `SHA256SUMS` hashes the manifest and the other four
content artifacts and does not hash itself. The source archive is the input for the
isolated Compose release path. The Studio archive is a deployable static output, while the
wheel is a Python distribution artifact. No package, archive, image, or checksum is
published by P8 development.

OCI images are operational test output, not P8 release artifacts. P8 does not claim raw
OCI image IDs or exported image archives are byte-for-byte reproducible. The image gate
instead verifies immutable base-image manifest digests, Dockerfile and lockfile digests,
the exact clean source commit, configured build inputs, required container content, and
runtime behavior. This narrower claim must remain explicit in evidence and documentation.

## Upgrade, backup, restore, and rollback contract

- Upgrade is a local operator sequence: verify the candidate manifest/checksums, stop
  writers, create and verify a pre-upgrade backup, start the candidate, apply only the
  existing checksummed migrations, and run health and authenticated smoke checks.
- Backup uses the SQLite online backup API to snapshot a live WAL database consistently;
  copying only `state.sqlite` is never represented as a valid backup. The snapshot passes
  SQLite integrity, migration-table, and manifest checks before packaging.
- A backup is a private versioned archive containing exactly `manifest.json` and
  `state.sqlite`. Its manifest binds backup-format version, release version, source commit,
  schema and migration versions, migration-manifest digest, database SHA-256, UTC creation
  time, and a random non-secret backup identifier. The archive and database are mode 0600
  and never enter Git, release artifacts, fixtures, stdout/stderr, logs, or P8 evidence.
- Restore reads no archive path through extraction APIs. It rejects special members,
  symlinks, path traversal, duplicate or unknown members, unsafe sizes, malformed or
  unknown format, digest mismatch, failed integrity, absent or inconsistent migration
  history, future schema, and migration-manifest incompatibility before changing state.
- Restore defaults to a new destination. Replacing existing state requires explicit
  offline confirmation and a distinct, verified rollback-backup destination. It creates
  that backup first and installs the verified database by a same-directory temporary file
  plus atomic replacement. It never silently overwrites state.
- Backup/restore tests compare durable required state after fresh reconstruction: complete
  namespace, colleague identity, Profile, Mandate and policy revisions, finite work,
  Event/Timer trigger, wake and Agenda state, proposals, HUMAN approvals, results, RBAC and
  memberships, and causal audit history.
- Restoring older state rolls back sessions, credential digests, membership/authority
  revisions, approval expiry reference state, and audit history to the backup instant.
  Operators must treat all restored sessions as untrusted, revoke/rotate them through the
  documented recovery path, re-check current membership and pending approvals, and retain
  the rollback backup privately for investigation. Restore is not an authorization bypass.
- A failed migration must roll back its schema and migration record in one SQLite
  transaction. A release rollback means stopping the candidate, restoring the verified
  pre-upgrade backup, and starting the matching previous code. Destructive down-migration
  is unsupported and must never be simulated or claimed.

## Diagnostics and redaction contract

The support-bundle command emits one bounded, versioned archive from an exact allowlist.
It may include release version and public commit, migration versions/checksum status,
non-sensitive Python/SQLite/platform classifications, health/Gate classifications, and
irreversible digests of safe causal identifiers. It includes no free-form log or audit
export.

It must reject or redact bootstrap, enrollment, recovery, session, CSRF, cookie, provider,
and adapter credentials or digests; credential paths; endpoints and URLs; request/response
bodies; private payloads; live receipts; personal data; SQLite or backup bytes; local
absolute paths, home paths, and user names; environment values; and unbounded exception or
subprocess text. Errors use a finite category and safe exit code.

Canary tests place credential-shaped values, private markers, and local paths in state,
environment, exception sources, and container-visible inputs, then scan stdout, stderr,
bundle members and bytes, release archives, and service logs. Any canary occurrence,
unknown field/member, unbounded output, or public-boundary exception fails P8.

## Supply-chain and NOTICE contract

The deterministic SBOM/inventory covers Python direct and transitive dependencies, Studio
direct and transitive dependencies, the Python build backend and release tools, Docker base
images, GitHub Actions, and external operator tools. Each applicable record carries name,
version, source class, immutable digest/reference, declared license, release-artifact
inclusion, and NOTICE/attribution treatment. Records are deterministically sorted.

The gate compares the inventory to `pyproject.toml`, Python release locks,
`studio/package-lock.json`, Dockerfiles, CI, and release scripts. Runtime/build dependencies
must be exact and content-hash pinned where downloaded; Docker bases and GitHub Actions must
use immutable digests/commits. `latest`, unpinned versions, mutable-only critical tags,
missing license metadata, unresolved source, unresolved required attribution, or inventory
drift fails closed.

The third-party inventory and NOTICE review must describe the actual source, wheel, built
Studio, and container verification boundaries. They record declared metadata and reviewed
attribution treatment without inventing legal conclusions. Root `LICENSE` is unchanged.
Root `NOTICE` changes only if evidence identifies an attribution that belongs there;
uncertainty blocks the release gate.

## Reproducibility contract

The release builder requires a clean repository whose HEAD descends from the fixed base and
P8 acceptance commit. It builds twice from the same commit in two independent OS temporary
workspaces using fixed inputs. It sets a source-commit-derived `SOURCE_DATE_EPOCH`, UTC,
`LC_ALL=C`, stable sorting, normalized gzip/tar/zip timestamps, regular-file modes, and
numeric owner/group zero. No build output or cache remains in the repository.

Every byte-level artifact named above, including both manifest copies and checksum files,
must have equal SHA-256 across the two builds. The builder must be runnable locally from
committed source and may not fetch an unpinned input. A mismatch reports only a finite
artifact/category and fails without writing a PASS summary.

## Public release and operational Golden Path

The fail-closed release Gate verifies repository/index/worktree state; base, merge-base,
acceptance and implementation ancestry; version consistency; zero-exception public scan;
SPDX, LICENSE, NOTICE and inventory status; immutable locks, images, and Actions; source
archive allowlist; forbidden credentials, databases, backups, logs, caches, dependency or
build residue, local paths, and private/live evidence; valid internal documentation links
and documented commands; scoped claims in README, SECURITY, development, Roadmap and the
capability matrix; deterministic defaults; explicit P7 adapter opt-in; candidate checksum
and manifest integrity; and isolated startup from the candidate source archive. Failure
must not produce a PASS result or evidence summary.

The actual P8 Golden Path must:

1. build the candidate from a clean source commit and validate its six-file set;
2. compare a second independent build byte-for-byte;
3. start default deterministic Compose from the extracted candidate without external
   provider access;
4. complete health and a basic authenticated smoke flow;
5. create a synthetic durable fixture covering identity, authority, work, runtime,
   approvals, results, membership, and causal audit;
6. take and verify an online SQLite backup;
7. make a safe, explicit state change, stop writers, restore, and restart;
8. prove the required durable state equals the backup instant;
9. create and scan the diagnostics bundle with canaries;
10. stop normally and prove zero remaining containers, networks, temporary volumes,
    backups, credentials, diagnostic bundles, extracted release trees, and build
    workspaces.

Docker or Compose not actually running is `not_evaluated` and blocks evidence and P8
completion. The Gate records a five-minute result only if an explicitly defined end-to-end
timer was actually measured; otherwise the five-minute target remains `not_evaluated`.
Human evaluation and live-provider evidence are always `not_evaluated` in public P8
evidence. Default operation makes zero external provider calls.

## Evidence class and claim boundary

P8 public tests and operational evidence are `synthetic_offline`; the local Docker runtime
is an actually executed synthetic/offline environment. SBOM license values are
`declared_metadata_review`, not legal advice. Human evaluation and live-provider acceptance
are `not_evaluated` and cannot be substituted by automated, model-reviewed, or synthetic
results.

Passing development gates supports only the statement **P8 development complete, awaiting
independent acceptance** and the candidate label **v0.1 local reference release candidate**.
It does not establish formal release/publication, production readiness, production
security/privacy, compliance, availability, enterprise identity, tenancy isolation,
named-provider compatibility, real delivery, pilot readiness, measured colleague-
experience improvement, or the five-minute target without actual timing evidence.

## Required repeatable gates

```bash
git diff --check
python3 -B scripts/check_public_boundary.py .
python3 -B scripts/check_p8_repository.py .
python3 -B scripts/check_p8_provenance.py .
python3 -B scripts/check_p8_operations.py .
PYTHONPATH=src python3 -B scripts/check_p8_backup_restore.py .
PYTHONPATH=src python3 -B scripts/check_p8_diagnostics.py .
python3 -B scripts/check_p8_supply_chain.py .
python3 -B scripts/check_p8_reproducibility.py .
python3 -B scripts/check_p8_release.py .
python3 -B scripts/check_p8_compose_runtime.py .
python3 -B scripts/check_p8_golden_path.py .
python3 -B scripts/run_p8_unittest_suite.py --start-directory tests --top-level-directory .
make check
make p8-compose-runtime
make p8-golden
```

Make targets are `p8-repository`, `p8-provenance`, `p8-operations`,
`p8-backup-restore`, `p8-diagnostics`, `p8-supply-chain`, `p8-reproducibility`,
`p8-release`, `p8-compose-runtime`, `p8-golden`, and `evidence-p8`. `make check` is the
complete P8 aggregate and retains every applicable P0-P7 regression without running a
historical evidence writer. CI runs the public non-publishing P8 aggregate; it never tags,
publishes, uploads a release artifact, or pushes an image.

All direct and aggregate test results require positive test counts where applicable and
exactly zero failures, errors, skips, expected failures, unexpected successes,
public-boundary exceptions, secret/private-data leaks, unexpected external egress, and
cleanup residue.

## Provenance, evidence, and stop conditions

The P8 provenance receipt covers every file changed from the fixed P7 base except the
generated P8 summary. Every entry is classified as new implementation based on public
documents and the accepted P7 implementation; transformed parent-source entries remain
zero.

Only after the acceptance and implementation commits exist, the tree is clean, all direct
and aggregate Gates pass, Docker is evaluated, both builds match, and cleanup is zero may
`make evidence-p8` atomically write `artifacts/p8/summary.json`. The writer rejects the
wrong branch/base/merge-base, dirty state, missing trusted commits, historical drift,
fabricated SHAs, missing/failed/skipped Gates, unsafe evidence, cleanup residue,
`not_evaluated` Docker runtime, or unsupported claims. Its public-tree digest excludes
exactly that summary.

Commit the summary alone and rerun every final Gate. Stop with a clean index/worktree on
`codex/p8-release-readiness`. Do not merge, push, tag, publish, release, rebase, squash,
amend, delete the branch, rewrite accepted history, or start post-v0.1 work.
