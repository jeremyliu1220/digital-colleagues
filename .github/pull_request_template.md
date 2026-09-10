<!-- SPDX-License-Identifier: Apache-2.0 -->

## Outcome

Describe the user or architecture outcome and active milestone.

## Evidence

- [ ] `make check`
- [ ] Relevant acceptance artifact updated
- [ ] Public-boundary scan passed with only reviewed exact exceptions
- [ ] Immutable acceptance commit/blob and exact implementation HEAD are identified
- [ ] Evidence authorization receipt is identified when evidence generation is authorized

## Boundaries

- [ ] No later-milestone product feature was introduced
- [ ] No private working-tree, personal, live-provider, or credential material was used
- [ ] New third-party material has origin, license, and notice review
- [ ] Documentation and claim limits match the implementation
- [ ] The change is inside the current milestone's exact changed-path allowlist
- [ ] Historical contracts, migrations, checkers, tests, evidence, and provenance are unchanged
- [ ] No tag, Release, package/image publication, signature, attestation, or remote mutation occurred without separate authorization
- [ ] P12 preserves `docs/p12/acceptance.md` byte-for-byte and does not create `artifacts/p12/summary.json` before evidence authorization
