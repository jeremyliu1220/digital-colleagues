<!-- SPDX-License-Identifier: Apache-2.0 -->

# P8 Release Candidate Checklist

This checklist creates an unpublished v0.1 local reference candidate. A checked list does
not mean P8 is independently accepted or that a Git tag, GitHub Release, package, image, or
formal release exists.

## Source and history

- [ ] HEAD is on `codex/p8-release-readiness`, clean, and has merge-base
  `df47f8d075f7c0660ab5ed6035f8acfa3d3da4dc`.
- [ ] Acceptance commit `eeb13ca643d5b512faab93e2e762ef4558dab688` and the committed
  implementation commit are ancestors.
- [ ] P0-P7 acceptance, evidence, artifacts, receipts, fingerprints, and migrations
  001-007 are unchanged; migration 008 is absent.
- [ ] Public-boundary scan reports zero exceptions and release archives contain no private
  state, backup, diagnostic, credential, log, cache, dependency tree, or build residue.

## Version, inventory, and attribution

- [ ] Python, package, lock, Studio, manifests, and docs all say `0.1.0`.
- [ ] Python packages are version- and hash-locked; npm entries have exact versions,
  integrity and declared license metadata.
- [ ] Docker base images use manifest-list digests; GitHub Actions use 40-character
  commits; no release-critical `latest` or mutable-only reference exists.
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
- [ ] Only after a clean implementation commit and all actual runtime checks pass,
  `make evidence-p8` writes the summary atomically and it is committed alone.
- [ ] Final checks pass after the evidence commit and the worktree is clean.
- [ ] Status is only “P8 development complete, awaiting independent acceptance”; human
  evaluation, live-provider acceptance, production properties, and an unmeasured
  five-minute target remain `not_evaluated` or explicitly excluded.
