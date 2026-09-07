<!-- SPDX-License-Identifier: Apache-2.0 -->

# P10 Mac Quickstart and Distribution Acceptance Contract

Status: fixed development contract. This file is the complete, immutable contract for
P10 development. It must be committed alone as the first P10 commit and remain
byte-identical to that Git object. The commit must never be amended, rebased, squashed,
force-rewritten, or changed to fit implementation results.

P10 may be described only as **implementation candidate complete; authorized remote
distribution gate pending independent acceptance** after every authorized local gate in
this contract passes. It may not be described as fully accepted, merged, published,
released, downloadable from GHCR, live-provider validated, production-secure, or
production-ready. P11 remains unauthorized.

## Exact baseline, branch, ancestry, and first commit

- Exact P10 base and accepted P9 ancestor:
  `11aa240af8db2ca515325dc059b1a77f7badc874`.
- Required accepted P8 ancestor: `0bb80ab187932fbad42fbf665b8310987609a1f5`.
- Exact development branch: `codex/p10-mac-quickstart`.
- Work begins only from a clean `main` whose `HEAD` and `main` both equal the exact P10
  base, with an empty index, worktree, and untracked set; migrations 001-007 plus the
  manifest are the only migrations; migration 008 is absent; and retained P9 `make check`
  passes.
- This file is the first P10 change and its isolated commit becomes
  `P10_ACCEPTANCE_COMMIT`. Every implementation and evidence commit descends from it.
- The implementation commit is a later clean commit containing every implementation path
  except `artifacts/p10/summary.json`. The final evidence commit contains only that
  summary and is never treated as an implementation change.

## Historical immutable boundary

P0-P9 accepted history is immutable. Every acceptance record, artifact, evidence file,
receipt, fingerprint, fixed provenance record, and milestone-specific historical record
under `docs/p0` through `docs/p9` and `artifacts/p0` through `artifacts/p9` remains
byte-identical to the exact base. Historical evidence writers are never invoked.

Migrations `001_initial.sql` through `007_governance_hardening.sql` and
`migrations/manifest.json` remain byte-identical to the exact base. Migration 008 and every
other new migration are absent. Existing namespace, identity, authority, approval,
persistence, replay, effect, and audit semantics remain unchanged. The accepted P8
`0.1.0` release artifacts and evidence are neither edited nor regenerated.

Living top-level documents named in the allowlist may receive current P10 status and
boundary text; that does not reinterpret or replace a historical acceptance record.

## Exact changed-file allowlist

The complete base-to-final-candidate changed path set must equal this explicit allowlist.
No glob or directory shorthand is implied. A missing or additional path, rename, copy,
type change, traversal, symlink, hardlink, device, socket, FIFO, staged change, unstaged
change, or untracked entry fails closed.

```text
.github/workflows/ci.yml
Dockerfile.p10
Dockerfile.p10.dockerignore
Makefile
README.md
SECURITY.md
SUPPORT.md
compose.p10.yaml
dc
distribution/p10/release-manifest.template.json
distribution/p10/verification-policy.json
docs/adr/0009-mac-quickstart-and-distribution.md
docs/architecture/target-architecture.md
docs/development.md
docs/p10/acceptance.md
docs/p10/compatibility.md
docs/p10/distribution.md
docs/p10/operations.md
docs/roadmap.md
docs/security/privacy-boundary.md
docs/security/threat-model.md
provenance/p10-migration-receipt.json
pyproject.toml
scripts/build_p10_candidate.py
scripts/check_p10_compatibility.py
scripts/check_p10_compose_runtime.py
scripts/check_p10_distribution.py
scripts/check_p10_evidence.py
scripts/check_p10_i18n.py
scripts/check_p10_operations.py
scripts/check_p10_provenance.py
scripts/check_p10_quickstart.py
scripts/check_p10_repository.py
scripts/check_p10_reproducibility.py
scripts/check_p10_security.py
scripts/collect_p10_evidence.py
scripts/p10_gate_support.py
scripts/run_p10_toolchain.py
src/digital_colleagues/__init__.py
src/digital_colleagues/api/app.py
src/digital_colleagues/api/p4_app.py
src/digital_colleagues/local/runtime.py
studio/Dockerfile.p10
studio/package-lock.json
studio/package.json
studio/src/App.test.tsx
studio/src/App.tsx
studio/src/i18n.ts
studio/src/locales/en-US.ts
studio/src/locales/zh-TW.ts
studio/src/studioContract.ts
tests/p10/__init__.py
tests/p10/fixtures.py
tests/p10/test_compatibility.py
tests/p10/test_distribution.py
tests/p10/test_evidence_gate.py
tests/p10/test_i18n.py
tests/p10/test_operations.py
tests/p10/test_repository.py
tests/p10/test_reproducibility.py
tests/p10/test_security.py
artifacts/p10/summary.json
```

Only P10 documents, ADR, provenance, gates, tests, static/synthetic evidence, the root
launcher, image-only topology, P10 Dockerfiles, distribution manifests/policy, local
operator/distribution code, Studio translations and necessary UI changes, stable product
metadata, non-publishing CI verification, and current-status documentation are authorized.
If any other file becomes necessary, work stops for a contract conflict; this contract is
not modified.

## Product and version contract

- Product name: `Digital Colleagues`.
- Python/PEP 440 version: `0.2.0.dev0`.
- Studio/SemVer and display version: `0.2.0-dev.0`.
- Maturity: `Public Pilot development candidate`.
- FastAPI title: `Digital Colleagues Local API`.
- Python package metadata is the canonical runtime product source. A mechanical gate must
  prove the required PEP 440-to-SemVer mapping and exact agreement across Python, Studio,
  API, OCI labels, Compose, and the generated distribution manifest.
- Studio user-visible copy contains no P3/P4/P5/P6/P7 milestone branding, no “P6 local
  governance control plane,” no “P6 under verification,” and no “P7 optional adapters.”
  Historical Python symbols, compatibility routes, and historical documents need not be
  renamed.
- User-visible maturity must not claim P10 acceptance, RC, formal release, publication,
  production security, or production readiness.

## P10 capability and exclusion boundary

P10 implements only Mac Quickstart and Distribution, a local prebuilt multi-platform OCI
candidate, the `./dc` interface, macOS Application Support layout, FileVault/secret-file
readiness, `zh-TW`/`en-US` translation keys, stable product/API metadata, retained route
compatibility, actual deterministic Mac quickstart timing, and P10 governance/evidence.

P10 implements no AgentPackage schema/parser/install/Catalog/trust lifecycle; no
ColleagueDeployment registry or multi-Agent behavior; no OpenAI/model gateway; no
Microsoft OAuth/Graph/Outlook/Teams/Planner/SharePoint integration; no ExternalConnection,
ConnectorGrant, or AutomaticEffectAuthorization runtime; no provider credential setup; no
Semantic Memory, embeddings, shared knowledge, Agent collaboration or messaging; no
executable Skill/plugin/browser automation; no always-on or 72-hour profile; and no HA,
enterprise IAM, production tenancy, compliance, or production-readiness claim.

## Distribution and image contract

- P10 has separate runtime and Studio images. Runtime is shared by API, worker, and
  one-shot operator commands.
- Each local OCI candidate has exactly `linux/amd64` and `linux/arm64` manifests beneath
  one OCI index. Configs and layers exist and match every declared digest.
- Docker bases are exact manifest digests. Images have stable product, development
  version, source revision, Apache-2.0 license, and source-identity OCI labels without a
  local path or private identifier. Runtime remains non-root and installs no uninventoryed
  OS package.
- `compose.p10.yaml` is image-only: it has no `build` key, uses only verified
  `name@sha256:...` references supplied from an exact release lock, binds published ports
  to loopback, bind-mounts traceable state, uses read-only roots and tmpfs, and never mounts
  secrets into Studio. Mutable tags and `latest` never select runtime bytes.
- Local gates build OCI layouts or use an isolated synthetic loopback registry. They do
  not push remotely. Native Mac architecture must actually start; the other architecture
  receives complete OCI/static contract verification. Quickstart performs no build.
- The downloaded bundle contains a rigid JSON release manifest, verification policy,
  checksums, `dc`, and image-only Compose. The launcher parses data without `eval` or
  sourcing untrusted content. Manifest and checksums bind every bundle member and exact
  image digest.
- Tags are display/discovery metadata only. Execution selection always uses a digest.

## GHCR, signature, and attestation authorization boundary

The official references checked for the P10 contract are Docker multi-platform build
documentation, GitHub artifact-attestation concepts and how-to documentation, GitHub
Container registry documentation, Sigstore container-signing documentation, Apple
Application Support documentation, and Apple FileVault deployment documentation. The
implementation provenance records their exact URLs, a UTC checked-at time, and the
observed contract.

GitHub documentation requires write authority to publish a container and generate a
registry attestation, including `packages: write`, `id-token: write`, and
`attestations: write`; the attestation binds an untagged fully qualified subject name to an
exact `sha256:` subject digest. Verification is required and an attestation is provenance,
not a safety verdict. GHCR supports digest-pinned pulls. Cosign signing/attachment changes
registry state and requires separate authorization.

This task authorizes none of those writes and has no fixed public repository/package
identity. CI therefore has read-only permissions, never uploads an artifact, and never
publishes on push. Docker push, package upload, tag, Release creation, GitHub attestation
generation, registry cosign signing, `packages: write`, `id-token: write`,
`attestations: write`, and `upload-artifact` are forbidden.

Local fixtures may test signatures and attestations only as `synthetic_offline`. They
must reject unresolved, unsigned, unattested, digest-mismatched, wrong-repository,
wrong-workflow, wrong-signer, and synthetic-as-remote candidates. Unless a later explicit
authorization exists, evidence is fixed to:

```text
ghcr_publication: not_evaluated
registry_image_signature: not_evaluated
registry_attestation: not_evaluated
remote_distribution_gate: authorization_required
```

These states do not block a local implementation candidate, but they block a complete P10
exit, a public-download claim, and P11.

## `./dc` operator contract

The host prerequisites are only macOS, a running Docker Desktop, the downloaded P10
bundle, the standard macOS shell/system tools, and supported `arm64` or `x86_64`. The
launcher must not require host Python, Node, npm, Make, Git, jq, or provider credentials.
It supports `doctor`, `quickstart`, `up`, `down`, `status`, `backup`, `restore`, `update`,
and `uninstall`.

Every command supports human `zh-TW` and `en-US` output and stable non-localized `--json`
output. An explicit locale is validated; unknown locale safely uses `en-US` or fails
closed without changing behavior, authority, defaults, paths, or payloads. Errors map to a
finite stable category and exit code.

Output never includes a secret/token/cookie/credential, environment dump, SQLite content,
container ID, user name, local absolute path, raw exception, or unbounded Docker output.
The launcher uses no `eval`, does not execute a manifest, and does not source unverified
key/value data. It never recursively deletes an unresolved glob, `$HOME`, `~`, `/`, the
workspace root, or an unverified root. Every mutation verifies exact managed-root, release,
and Compose-project identity; uses a bounded exclusive lock; is idempotent; and fails
closed under concurrency.

`doctor` is read-only and checks macOS/architecture, Docker CLI/Compose/daemon and minimum
versions, release manifest/checksums, digest-only image references, ports, creatable
Application Support parent, existing directory/file modes, and FileVault. FileVault off or
unknown never becomes live-ready.

`quickstart` starts a monotonic timer at invocation, performs required doctor checks,
creates only secure non-secret layout/config, uses prebuilt digest-bound images, starts
API/worker/Studio, waits to a finite deadline, and ends only after API, worker, Studio, and
`status --json` are ready. Failure stops resources started by that invocation and returns a
finite error. FileVault off does not block deterministic reference mode but keeps live
readiness blocked/not-evaluated. It accepts no provider credential.

`up` uses only the verified release lock and image-only Compose, never builds or updates,
and never creates schema 008. `down` normally stops services and preserves state, secrets,
backups, and release lock. `status` returns only finite health, version, maturity, schema,
and readiness categories.

`backup` and `restore` reuse P8 WAL-consistent, source-bound semantics. A backup is
verified and mode `0600`. Restore requires stopped services, compatible source binding,
explicit confirmation, and refuses overwrite or destructive down migration.

`update` verifies a candidate manifest/checksums/digests/signature/attestation before
switching, creates and verifies a pre-update backup, and refuses production-style update
while remote attestation authority is absent. A health failure may select only the
previous verified release lock/Compose choice; it never blindly changes database bytes.

`uninstall` normally removes only P10-managed containers and rebuildable cache, preserving
state, secrets, backups, and release lock. Data purge is a distinct option with an exact
confirmation, stopped services, exact-root proof, and a verified backup. Purge tests use
only OS temporary roots and cannot affect any path outside the managed root.

## macOS filesystem, FileVault, and secret contract

The default root is `~/Library/Application Support/Digital Colleagues`, resolved without
printing or persisting the user or absolute host path. It separates `state`, `secrets`,
`backups`, `diagnostics`, `releases`, `config`, and rebuildable `cache`/temporary data.
Managed root and all private directories use mode `0700`; credentials, backups, databases,
locks containing release identity, and other private files use mode `0600`. Creation uses
`umask 077`. Runtime state is an explicit bind mount, not an anonymous volume.

Secrets never enter environment, Compose interpolation, command arguments, SQLite, audit,
backup metadata, diagnostics, stdout/stderr, logs, public evidence, or Studio state. A
secret file is read-only mounted only to an explicitly necessary service; the deterministic
P10 reference mode needs none. Studio has no secret mount.

The production FileVault probe uses only the trusted macOS system tool and performs no
state change. Its probe is injectable only through an explicit test boundary. P10 never
enables/disables FileVault, changes a recovery key, or requests a password. Enabled means
`encrypted_storage_ready`; off and unknown mean blocked/not-evaluated. Public evidence
records only contract-test classifications, never the actual host state.

## Studio i18n contract

All user-visible navigation, bootstrap, builder, work, wake, proposal, audit, governance,
notice, empty/loading/error, maturity, and security-boundary text comes from translation
resources rather than remaining centralized as literals in `App.tsx`. No new runtime
dependency is introduced.

`zh-TW` and `en-US` key sets are exactly equal; all values are non-empty strings; all
interpolation placeholder names are identical per key. Missing, extra, blank, wrong-type,
or placeholder-mismatched translations fail build/test. Unknown locale safely selects
`en-US`. Browser preference is presentation state only and never server authority.
Locale cannot alter schema, canonical role, principal kind, authority, effect, permission,
default, validation, API route, method, or payload. Keyboard, focus, ARIA, and existing
security explanations remain present. P10 adds no Catalog/package localization.

## API metadata and compatibility contract

`src/digital_colleagues/local/runtime.py`, `src/digital_colleagues/api/app.py`, and
`src/digital_colleagues/api/p4_app.py` use the stable title and canonical development
version. Existing `/p5`, `/p6`, authentication, governance, and all other accepted routes,
methods, schemas, status codes, authorization, CSRF, replay, namespace, and persistence
semantics remain present and unchanged. P10 adds no empty `/api/v1` endpoint.

The compatibility inventory fixes the exact retained route/method/schema surface. New
future public APIs use stable terms under `/api/v1`; alias, deprecation, or removal needs a
later independent contract. Studio may call retained compatibility paths without exposing
milestone language to users.

## Actual Mac quickstart measurement

The gate runs on actual macOS with Docker Desktop/daemon, a prebuilt distribution
candidate, a clean OS-temporary managed root, unique loopback ports, and no provider
credential. No build occurs inside the timed interval.

The gate performs at least three independent clean trials using a monotonic clock. Each
starts immediately before `./dc quickstart`; each ends only after API healthy, worker
ready, Studio HTTP ready, and `./dc status --json` says ready. Every trial is below 300
seconds. The evidence records durations, maximum, median, platform class, and bounded
precondition classifications, but no hostname, user name, absolute path, IP, container ID,
or private machine data.

A failure, skip, timeout, partial health, stale process, port conflict, source build,
mutable image, unsafe cleanup, runtime residue, or unexpected external egress fails the
gate. Results prove only the local deterministic reference quickstart. First external
Agent timing, OpenAI/Microsoft 365, live-provider usefulness, always-on operation, and
production readiness remain excluded. The remote GHCR pull path is `not_evaluated`.

## Required gates and negative coverage

The P10 gates are repository, provenance, distribution, quickstart, security/FileVault/
filesystem, operations CLI, i18n, metadata/compatibility, Compose runtime,
reproducibility, evidence, and aggregate toolchain. Tests cover at least:

- wrong base/branch/ancestry; dirty staged/unstaged/untracked state; contract mutation;
  P0-P9 drift; migration drift/008; allowlist missing/extra/rename/copy/traversal/symlink/
  special-file bypass; and forbidden P11+ product/runtime changes;
- mutable/latest/missing-platform/digest-mismatched images; unsigned/unattested remote or
  synthetic-as-remote candidate; wrong repository/workflow/signer; and workflows with
  publication actions or write permissions;
- quickstart build/timeout/partial-health/stale-process/port-conflict/concurrency; unsafe
  root or purge; FileVault off/unknown promoted to live-ready; wrong modes; secret leakage
  or excessive mounts; and unsafe backup/restore/update/uninstall behavior;
- missing/extra/blank/wrong-type/placeholder-mismatched translations, unknown locale, or
  locale-dependent authority/schema/API payload;
- user-visible milestone branding, milestone FastAPI metadata, retained route or semantic
  drift, migration 008, provider/OAuth/connector/AgentPackage/multi-Agent/memory/plugin
  behavior, and evidence written after failure/skip/dirty/uncommitted input or containing
  private material.

Every necessary gate has positive test/check counts and exactly zero failures, errors,
skips, expected failures, unexpected successes, historical drift, secret leaks, unsafe
paths, runtime residue, or unexpected external egress. Docker or actual-Mac gates cannot
be replaced by mocks and still pass.

Repeatable commands include:

```bash
git status --short --branch
git diff --check
python3 -B scripts/check_public_boundary.py .
python3 -B scripts/check_p10_repository.py .
python3 -B scripts/check_p10_provenance.py .
python3 -B scripts/check_p10_distribution.py .
python3 -B scripts/check_p10_security.py .
python3 -B scripts/check_p10_operations.py .
python3 -B scripts/check_p10_i18n.py .
python3 -B scripts/check_p10_compatibility.py .
python3 -B scripts/check_p10_reproducibility.py .
PYTHONPATH=src python3 -B -m unittest discover -s tests/p10 -t . -v
make p10-compose-runtime
make p10-quickstart
make p10-check
make check
```

`scripts/run_p10_toolchain.py` creates an isolated OS-temporary clone from Git object
`11aa240af8db2ca515325dc059b1a77f7badc874`, runs retained P9 `make check` at that exact
object, and only then runs current P10 gates. It never calls a historical evidence writer,
never reads the parent research working tree, fails closed, and redacts temporary paths
from all output and errors.

## Provenance and evidence contract

The P10 receipt states that source basis is accepted P9 implementation, this P10 contract,
and the listed official public documentation; parent research working tree read is false;
source/transformed migration counts are zero; and every allowlisted implementation path
except the final summary has a classification and implementation basis. No local path or
private identifier is recorded.

The evidence writer runs only on the exact branch after the acceptance and implementation
commits exist, this contract is immutable, tree/index are clean, all required local gates
pass with no skip, P0-P9 history and migrations are unchanged, migration 008 is absent,
there is no forbidden capability/private material, and three actual timings are valid.
Evidence is never written on failure.

`artifacts/p10/summary.json` records schema/milestone/base/acceptance/implementation/branch/
tree identity, versions, changed-path count, historical and migration counts, capability
boundary, direct and aggregate results, test count/IDs, three durations/maximum/median,
platform set/native result, i18n parity/key count, route compatibility, secret canary and
cleanup counts, evidence classes, exclusions, and remote authorization states.

Its only candidate claim is `p10_mac_quickstart_distribution_candidate`. It must say the
local deterministic quickstart candidate and local multi-platform OCI contract passed,
while GHCR publication/signature/attestation are `not_evaluated`, the complete P10 exit is
pending authorized remote distribution verification, and P11 remains unauthorized.

Evidence classes are limited to `static`, `synthetic_offline`, `local_oci`,
`local_mac_runtime`, and `not_evaluated`. Evidence never claims public release/download,
real registry signature/attestation, provider compatibility, first-Agent timing, live or
human acceptance, always-on behavior, production security/privacy/readiness, HA,
enterprise IAM, compliance, or P11+ capability.

## Completion and stop conditions

Implementation commits are logically separated and never contain the final summary.
After implementation is committed and clean, all gates run; only then may the summary be
generated and committed alone. All final gates rerun from that final candidate.

Stop immediately without reset, stash, revert, rebase, contract modification, or scope
absorption if baseline/branch/history/migration invariants fail; a non-allowlisted file is
needed; P11+ behavior or real credentials/private data become necessary; publication,
upload, push, tag, Release, remote signing, or write permission is needed; official
documentation conflicts with the contract; the five-minute gate cannot be honestly
measured on its defined prerequisites; secrets cannot remain outside environment/
arguments/logs; or a gate could pass only by skip, mock substitution, or weaker criteria.

After every authorized local gate passes, the exact completion wording is:

**P10 implementation candidate complete; authorized remote distribution gate pending
independent acceptance.**

The branch remains clean and unmerged. No push, tag, publication, upload, Release, remote
change, or P11 work occurs.
