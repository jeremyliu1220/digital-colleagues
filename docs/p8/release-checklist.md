<!-- SPDX-License-Identifier: Apache-2.0 -->

# P8 Release Candidate Checklist

P8 passed independent acceptance and was fast-forward merged from
`codex/p8-release-readiness` to `main`. The accepted P8 commit is
`0bb80ab187932fbad42fbf665b8310987609a1f5`. Historical P0–P8 artifacts, evidence,
acceptance contracts, receipts, and migrations remain unchanged. The accepted result is
only a **v0.1 local reference release candidate** for version `0.1.0`: no tag has been
created, and nothing has been published, uploaded, or formally released. It is not
production-ready and establishes no production security, high availability, enterprise
IAM, real-provider readiness,
compliance, or other excluded capability. Human evaluation, live-provider evidence, and
the unmeasured five-minute target remain `not_evaluated`. Post-v0.1 S1–S4 and Self-initiated
autonomy have not started and do not start automatically. This checklist remains unchecked
because this checkpoint hotfix performs no tag, publication, upload, or formal release.

## Source and history

- [ ] Release work starts from a clean `main` containing accepted P8 commit
  `0bb80ab187932fbad42fbf665b8310987609a1f5`, or an explicitly authorized descendant.
- [ ] The accepted P8 commit is an ancestor of HEAD; the fixed P8 development history remains
  anchored at merge-base `df47f8d075f7c0660ab5ed6035f8acfa3d3da4dc`.
- [ ] P0-P8 acceptance, evidence, artifacts, receipts, fingerprints, and migrations
  001-007 are unchanged; migration 008 is absent.
- [ ] Public-boundary scan reports zero exceptions and release archives contain no private
  state, backup, diagnostic, credential, log, cache, dependency tree, or build residue.

## Version, inventory, and attribution

- [ ] Python, package, lock, Studio, manifests, and docs all say `0.1.0`.
- [ ] Python packages are version- and hash-locked; npm entries have exact versions,
  integrity and declared license metadata.
- [ ] Docker base images use manifest-list digests; GitHub Actions use 40-character
  commits; no release-critical `latest` or mutable-only reference exists.
- [ ] Host and both Studio container builds execute Node 24.15.0 and integrity-pinned npm
  11.12.1 checks; no Dockerfile installs an uninventoried OS package.
- [ ] The P7 route guard uses the version-asserted BusyBox 1.37.0 `ip` applet from its exact
  OCI digest; no mutable `iproute2` package-manager install remains.
- [ ] Deterministically sorted SBOM covers Python, npm, Hatchling, OCI bases, Actions, and
  release/operator tools with inclusion and attribution treatment.
- [ ] Built Studio archive contains license texts for React, React DOM, and Scheduler.
- [ ] Root Apache-2.0 `LICENSE` and project `NOTICE` match their reviewed scope; unresolved
  license/source/attribution count is zero. This is metadata review, not legal advice.

## Candidate bytes

- [ ] Exactly six files from the P8 acceptance contract exist in an OS temporary output.
- [ ] Manifest binds source commit/timestamp, migrations, inputs, artifact sizes/digests,
  evidence classes, and claim exclusions.
- [ ] `SHA256SUMS` verifies the other five files.
- [ ] Two independent temporary builds have identical SHA-256 for all six files.
- [ ] OCI evidence is limited to immutable inputs, expected contents, and actual runtime;
  raw image byte reproducibility is not claimed.

## Operations and runtime

- [ ] Default Compose from the source archive selects deterministic intelligence and the
  reference channel; optional P7 HTTP adapters remain explicit opt-in.
- [ ] API/worker/Studio health and authenticated smoke flow succeed without an external
  provider call.
- [ ] Exact accepted P7 `0.0.0` code creates durable state and a source-bound backup before
  P8 starts; upgrade and rollback run mechanically without inventing a P7 release manifest.
- [ ] Synthetic durable identity, authority, finite work, Event/Timer, wake, Agenda,
  proposal, HUMAN approval, result, membership, and causal audit state exists.
- [ ] Live-WAL online backup verifies; post-backup state changes; stopped restore and fresh
  restart reproduce the backup instant.
- [ ] Diagnostics canaries are absent from stdout, stderr, bundle/archive bytes, and
  container logs.
- [ ] `cleanup` reports zero containers, networks, volumes, credentials, backups,
  diagnostics, extracted trees, and build workspaces.

## Mechanical gates and claims

- [ ] `git diff --check`, public boundary, every focused P8 target, full P8 unittest,
  `make check`, `make p8-compose-runtime`, and `make p8-golden` pass with zero failures,
  errors, skips, expected failures, or unexpected successes.
- [ ] The accepted P8 evidence summary remains byte-unchanged and no historical evidence
  writer is invoked.
- [ ] Final checks pass after the evidence commit and the worktree is clean.
- [ ] P8 remains accepted and merged but not tagged, published, uploaded, or formally
  released; human evaluation, live-provider evidence, production properties, and the
  unmeasured five-minute target remain `not_evaluated` or explicitly excluded.
