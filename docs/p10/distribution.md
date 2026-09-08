<!-- SPDX-License-Identifier: Apache-2.0 -->

# P10 Digest-Bound Distribution Gate

The immutable P10 acceptance contract recorded the original local-only development
boundary. A later explicit operator authorization fixes one public repository, two GHCR
subjects, one branch workflow identity, GitHub Actions OIDC, and an independently
verifiable remote gate. This addendum does not modify that historical contract, merge
`main`, create a tag or Release, accept P10, or authorize P11.

## Fixed remote identity

```text
repository: jeremyliu1220/digital-colleagues
workflow: .github/workflows/ci.yml
workflow ref: refs/heads/codex/p10-mac-quickstart
runtime subject: ghcr.io/jeremyliu1220/digital-colleagues-runtime
Studio subject: ghcr.io/jeremyliu1220/digital-colleagues-studio
OIDC issuer: https://token.actions.githubusercontent.com
certificate identity: https://github.com/jeremyliu1220/digital-colleagues/.github/workflows/ci.yml@refs/heads/codex/p10-mac-quickstart
platforms: linux/amd64, linux/arm64
```

`distribution/p10/verification-policy.json` is the machine-readable lock. Its lifecycle is
exactly:

1. `authorized_pending`: fixed authority exists, but no digest or workflow-run result is
   accepted.
2. `published_pending_verification`: exact publication revision, run, subjects, and
   digests exist, but independent public verification is incomplete.
3. `passed`: both packages are public, anonymous exact-digest pulls work, and strict image,
   Cosign, and GitHub artifact-attestation verification passed.

Unknown, mixed, skipped, failed, private, tag-only, or synthetic substitution states fail
closed. The final candidate must contain only `passed`.

## One-time activation workflow

Normal `push` and `pull_request` events retain read-only, non-publishing P10 CI.
`pull_request_target` is forbidden. The temporary `workflow_dispatch` interface requires
`operation`, `confirm`, `candidate_sha`, `runtime_digest`, and `studio_digest`.

Publication runs only for the exact repository, branch ref, workflow SHA, operation
`publish`, and confirmation `PUBLISH-P10-CANDIDATE`. Only that job has:

```text
contents: read
packages: write
id-token: write
attestations: write
artifact-metadata: write
```

The verification job has `contents: read` only. It does not log in to GHCR and cannot
mint an OIDC token, push a package, generate an attestation, or mutate a registry.
Neither job uploads a workflow artifact, creates a Git tag or Release, or selects bytes
through a mutable tag.

All actions are pinned to immutable commits. The two Docker build steps disable automatic
provenance and SBOM output so each OCI index contains only `linux/amd64` and `linux/arm64`.
The only display/discovery tag is `sha-<full-40-character-publication-sha>`.
Execution always uses `subject@sha256:digest`.

Each image is processed in this order:

1. build and push its two-platform index;
2. sign the exact index digest with GitHub Actions OIDC and the
   `source_revision=<publication-sha>` annotation;
3. create GitHub build provenance for the untagged subject name and exact digest, with
   `push-to-registry: true`.

The runtime build context is the repository root with `Dockerfile.p10`. The Studio build
context is `studio` with `studio/Dockerfile.p10`. OCI source and revision labels bind the
public repository URL and exact publication SHA.

## Independent public verification

The repeatable final command is:

```bash
make p10-remote-distribution
```

It uses a task-owned empty Docker config and the exact locked public digests. It downloads
checksum-pinned GitHub CLI and Cosign binaries into an OS-temporary directory when they are
not already supplied by CI; it never commits a binary or requires a host installation.

For each subject it:

- runs `docker buildx imagetools inspect --raw`;
- verifies the index digest and the exact two-platform set;
- resolves and hashes both child manifests and configs, and resolves every layer;
- performs anonymous exact-digest pulls for both required platforms and the native Mac
  platform;
- runs Cosign with the exact certificate identity, exact OIDC issuer, ordinary claim
  checking, and exact `source_revision` annotation;
- runs `gh attestation verify oci://<subject>@<digest> -R
  jeremyliu1220/digital-colleagues` with exact signer workflow/digest, source ref/digest,
  certificate identity/issuer, SLSA provenance predicate, and GitHub-hosted-runner
  requirement.

The command then creates a checksum-bound bundle whose manifest uses the publication
source revision and the two exact GHCR digests. It executes three new Mac quickstarts from
three isolated temporary roots. Each trial checks task-owned containers, networks,
volumes, ports, API, worker, Studio, `status --json`, the internal network, and the
no-egress control, completes in less than 60 seconds, and leaves zero task-owned runtime
residue.

## Revision semantics and final lock

The publication source revision is the commit whose Dockerfiles and temporary workflow
built, signed, and attested the images. It remains fixed even after the branch advances.
The final evidence implementation revision is the later commit that records verified
digests/run identities and removes every publish/verify job and all remote write
permissions. `artifacts/p10/summary.json` records these as separate fields.

After successful verification the branch workflow is restored to read-only,
non-publishing CI. The historical activation commit remains reachable; it is never
amended or rewritten. Moving the branch tip prevents another dispatch for the old
publication source through the exact `candidate_sha == github.sha` guard.

## Claim boundary

Remote registry evidence is public distribution evidence, not a formal GitHub Release,
security certification, provider/live acceptance, production supply-chain assurance, or
production readiness. P10 remains a candidate awaiting independent acceptance. P11 stays
unauthorized.

## Official references checked

The fixed URLs, immutable action commits, checked-at timestamps, and observed contracts
are recorded in `provenance/p10-migration-receipt.json`. They cover Docker
multi-platform images, GHCR, GitHub artifact attestations and strict verification, Cosign
signing/verification, Application Support, and FileVault.
