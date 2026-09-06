<!-- SPDX-License-Identifier: Apache-2.0 -->

# P1-P8 NOTICE and Candidate Attribution Review

Historical P1 record: No reviewed direct package required attribution in the source-only
scaffold, and future container or release distributions require a fresh review. The P8
review below is that fresh review; the P1 result is historical context, not a conclusion
about the P8 candidate.

## Hypothesis

The root `NOTICE` can remain the Digital Colleagues project notice for the exact P8
candidate if bundled third-party license texts are carried with the bundle that contains
those dependency bytes and no reviewed dependency requires an addition to the Apache NOTICE
file itself.

## Experiment

Review the exact `0.1.0` candidate artifact set; all 27 Python gate/runtime/build packages;
all 202 npm lock entries; the three npm production packages present in built Studio; the
Hatchling backend; three digest-pinned OCI bases; three commit-pinned GitHub Actions; and
the external release/operator tools. Compare exact versions, integrity/digest references,
declared licenses, whether bytes enter a candidate artifact, and the recorded attribution
treatment. Mechanically verify the root `LICENSE` and `NOTICE` against the accepted P7 base.

## Result and evidence

- The source archive contains project source, policy, tests, locks, and public documents;
  it contains no installed third-party package tree or milestone evidence artifact.
- The Python wheel contains Digital Colleagues code and project licensing metadata. Python
  dependencies remain package-manager requirements and are not vendored in the wheel.
- The built Studio contains React 19.2.8, React DOM 19.2.8, and Scheduler 0.27.0. All three
  declare MIT. The builder reads their installed `LICENSE` files and puts their full text in
  `THIRD_PARTY_LICENSES.txt` inside the Studio archive; missing text blocks the Gate.
- Development/build-only npm packages, GitHub Actions, and operator tools do not enter a
  candidate artifact as package trees.
- OCI images are local operational evidence, not P8 release artifacts and are not pushed or
  published. Their manifest-list digests are fixed, but this review does not claim a full
  legal census of every base-image OS package.
- The exact Node 24.15.0 build image and Corepack npm 11.12.1 are checked in host and
  container paths. The mutable `iproute2` installation was removed; the required route
  operation instead uses the version-asserted `ip` applet copied from the digest-pinned
  BusyBox 1.37.0 glibc image, which is explicitly inventoried as GPL-2.0-only.
- The generated deterministic inventory records 243 entries with no missing declared
  license, immutable reference, inclusion classification, or attribution treatment.

The root Apache-2.0 `LICENSE` is unchanged. No reviewed item for this exact candidate
requires third-party wording to be added to the project's root Apache `NOTICE`; dependency
license text that accompanies the bundled Studio bytes is kept inside the Studio artifact
instead.

## Decision and consequence

Keep the root `NOTICE` unchanged and require the Studio third-party license file as a
release artifact member. `make p8-supply-chain` compares the current `NOTICE` to the
accepted P7 base, and `make p8-release` checks the Studio license member and exact artifact
set.

This is a declared-metadata and artifact-treatment decision for an unpublished local
candidate, not legal advice or a general conclusion for a package registry, container
registry, hosted service, named-provider integration, or future dependency update. Any
unresolved license/source/attribution result must fail closed instead of changing or
waiving this decision silently.
