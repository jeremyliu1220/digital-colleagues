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

The first publication attempt used source
`05e73ea23ac650edfae59fa409a770fdf967af3a`. Publication run
[`34202520699`](https://github.com/jeremyliu1220/digital-colleagues/actions/runs/34202520699)
created two public indexes, keyless signatures, and GitHub provenance attestations.
Read-only verification run
[`34206039435`](https://github.com/jeremyliu1220/digital-colleagues/actions/runs/34206039435)
verified those registry objects. Independent acceptance subsequently found that the source
contained a base-to-candidate change outside the immutable acceptance allowlist. That source,
both runs, runtime digest
`sha256:41567ba87a088944cf9a2c17b9b0f4359554c66b2ec1f6d52db46067e1ab9092`, and Studio
digest `sha256:b7dd4c2b35922ec31a9b38c15316283706a9aab0ffab2101a18f7bf106165f2e`
are retained as `superseded_contract_noncompliant_source`. They are not active release-lock
references and must not be selected by a final P10 bundle or execution path.

The scoped correction published the contract-compliant source
`62b226064d2597a4ca6a67f9f2c20a79a815732b` in publication run
[`34235760264`](https://github.com/jeremyliu1220/digital-colleagues/actions/runs/34235760264).
The active runtime index is
`sha256:a5bb41bdb85bf7b5a75dc79967e26943c098b024b64fdd345f5b4c6f4688991d`;
the active Studio index is
`sha256:7791d80d9fa464bbd1574601deba5a30ca6d980dab8c8275c24c117fae81e4c9`.
Read-only verification run
[`34237810474`](https://github.com/jeremyliu1220/digital-colleagues/actions/runs/34237810474)
passed all exact-digest checks. Its publication job was skipped. The immediately preceding
verification run
[`34236719816`](https://github.com/jeremyliu1220/digital-colleagues/actions/runs/34236719816)
failed closed before registry verification because the verifier rejected the legitimate
`published_pending_verification` lifecycle. The corrected verifier accepts only the exact
source and digest tuple already locked in policy; that failed run remains public and did
not republish, delete, or overwrite an artifact.

## Historical one-time activation workflow

The preserved activation history used the following controls. The final branch workflow
has removed `workflow_dispatch`, both remote jobs, and every package/OIDC/attestation
permission; normal `push` and `pull_request` events retain read-only, non-publishing P10 CI.
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

The verification job has `contents: read` and `attestations: read` only. It does not log
in to GHCR and cannot
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
- performs anonymous exact-digest pulls for both required platforms, removing only the
  just-pulled task reference between platform selections so classic Docker image stores
  cannot reuse a different platform under the same index digest, then retains one native
  exact-digest copy only for the timed `--pull never` quickstarts and removes it afterward;
- runs Cosign with the exact certificate identity, exact OIDC issuer, ordinary claim
  checking, and exact `source_revision` annotation;
- anonymously resolves the digest-derived OCI attestation index, hashes its exact subject
  index and Sigstore bundle, then runs `gh attestation verify <hashed-index> --bundle
  <hashed-bundle> -R jeremyliu1220/digital-colleagues` with exact signer digest, source
  ref/digest, certificate identity/issuer, SLSA provenance predicate, and
  GitHub-hosted-runner requirement. This offline verification path requires neither a
  GitHub API token nor registry credentials. The independent GitHub Actions run separately
  verified the required `oci://<subject>@<digest>` form against the GitHub attestation API.

For the superseded publication, the first verification attempt, run `34203006909`, failed
closed because mutually
exclusive GitHub CLI signer-policy flags were combined. Run `34204280131` then exposed a
missing read-only attestation permission. Run `34204837101` was retained as an
unclassified verifier failure; public stage classification in run `34205272328` isolated
the remaining failure to the anonymous pull. Docker's classic image store cannot retain
both variants under one multi-platform index, so the verifier now removes only its
task-pulled exact reference between platform pulls. Run `34206039435` passed all technical
remote checks, but that result cannot cure the source contract violation. No failed run
triggered package deletion or history rewriting.

The Mac rerun also rejected GitHub CLI's interactive OAuth request because its minimum
account scope exceeded this public read-only gate. The final verifier instead resolves the
digest-derived attestation artifact anonymously, verifies every OCI descriptor and hash,
and supplies the bundle to GitHub CLI offline. No CLI account token or GHCR credential is
required or recorded.

The command then creates a checksum-bound bundle whose manifest uses the publication
source revision and the two exact GHCR digests. It executes three new Mac quickstarts from
three isolated temporary roots. Each trial checks task-owned containers, networks,
volumes, ports, API, worker, Studio, `status --json`, the internal network, and the
no-egress control, completes in less than 60 seconds, and leaves zero task-owned runtime
residue.

## Revision semantics and final lock

The active publication source revision is the contract-compliant commit whose Dockerfiles
and temporary workflow built, signed, and attested the images. It remains fixed even after
the branch advances. Verification run `34237810474` is the only active correction
verification result; run `34236719816` remains a fail-closed historical result.
The final evidence implementation revision is the later commit that records verified
digests/run identities and removes every publish/verify job and all remote write
permissions. `artifacts/p10/summary.json` records these as separate fields.

After successful verification the branch workflow is restored to read-only,
non-publishing CI. The historical activation commit remains reachable; it is never
amended or rewritten. Moving the branch tip prevents another dispatch for the old
publication source through the exact `candidate_sha == github.sha` guard.

## Remote repository automation containment

The first push to the newly public repository caused the pre-existing
`.github/dependabot.yml` configuration to open nine unrequested version-update pull
requests. Publication remained disabled. The pull requests were later closed without
merge and their bot branches were deleted under separate owner authorization.

An attempted containment changed each `open-pull-requests-limit` from `5` to `0`, relying
on GitHub's documented per-ecosystem disable mechanism. Although operationally narrow, the
file is not one of the immutable P10 acceptance allowlist's 62 paths. The attempted gate,
test, documentation, and provenance exception therefore violated the fixed contract and
was rejected by independent acceptance. The final candidate restores
`.github/dependabot.yml` byte-for-byte to the accepted P9 base and the repository gate now
rejects any drift of that path as an extra changed path. If the restored configuration
opens another pull request, this P10 correction records and reports it; it does not create
another allowlist exception or claim authority to change the file.

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
