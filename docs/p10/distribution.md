<!-- SPDX-License-Identifier: Apache-2.0 -->

# P10 Local Distribution Contract

P10 produces a local-only multi-platform implementation candidate. No GHCR package,
signature, attestation, download, tag, upload, or Release exists or is authorized.

## Bundle and image topology

`scripts/build_p10_candidate.py --build-oci` exports separate runtime and Studio OCI
layouts. Each root index must resolve exactly one `linux/amd64` and one `linux/arm64`
manifest. Every referenced config and layer is present and content-addressed. Runtime
contains Python code and migrations; Studio contains the built static application. Both
carry product/version/revision/license/source labels. The runtime default is non-root.

The bundle builder accepts only two explicit `name@sha256:...` references and emits:

```text
SHA256SUMS
compose.p10.yaml
dc
manifest.json
operations-source-binding.json
verification-policy.json
```

`manifest.json` binds the product, versions, maturity, source revision, platforms, schema
1-7, exact runtime/Studio image references, Compose identity, and remote authorization
states. `SHA256SUMS` covers the manifest and every other bundle member except the checksum
file itself. A bundle is rejected on an unexpected member, mode, checksum, identity,
mutable image, unresolved template field, or any missing, extra, duplicate, unknown, or
wrong-type manifest field. `source_timestamp` belongs only to the operations source binding
and is not part of this fixed release-manifest schema.

API, worker, and Studio use one explicit internal Compose network. The operator retains
`network_mode: none`. A fixed ingress-only Nginx gateway with no private mount, environment,
or variable destination provides loopback API and Studio forwarding. The actual runtime
and quickstart Gates verify the Docker network and use a bounded gate-owned host-loopback
endpoint with a reachable external-route control before requiring API, worker, and Studio
probes to fail. They do not contact the public Internet.

## Official references checked

Checked at: `2026-09-07T15:12:21Z`.

| Official URL | Observed contract used by P10 |
| --- | --- |
| https://docs.docker.com/build/building/multi-platform/ | A multi-platform image is a manifest list pointing to per-platform manifests; `--platform` selects targets; Docker Desktop supports emulation and current containerd image stores support manifest lists. |
| https://docs.github.com/en/actions/concepts/security/artifact-attestations | Attestations bind an artifact to source/build provenance, require verification to provide benefit, and are not a guarantee that an artifact is secure. |
| https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations | Container attestation generation needs `id-token: write`, `attestations: write`, and `packages: write`; subject name is fully qualified without a tag and subject digest is `sha256:`. |
| https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry | GHCR uses package permissions and supports exact digest pulls; upload requires write authority. |
| https://docs.sigstore.dev/cosign/signing/signing_with_containers/ | Container signing attaches signature material to a registry subject and therefore is a remote state-changing action. |
| https://developer.apple.com/documentation/foundation/url/applicationsupportdirectory | Application Support is the platform location for application-owned support data. |
| https://support.apple.com/en-gb/guide/deployment/dep0a2cb7686/web | FileVault protects startup-volume data and its enablement/recovery lifecycle is an administrative security operation, not a quickstart side effect. |

## Future GHCR activation contract

Activation requires a separate authorization fixing the public owner/repository, two
package subject names, build workflow identity, signer identity, exact subject digests,
visibility, permissions, signature policy, attestation policy, verification commands, and
private/public evidence treatment. Only then may a workflow receive the required write
permissions or execute a push/sign/attest step.

Until that change is independently accepted:

```text
ghcr_publication: not_evaluated
registry_image_signature: not_evaluated
registry_attestation: not_evaluated
remote_distribution_gate: authorization_required
```

Synthetic/offline fixtures exercise rejection only and can never satisfy a remote gate.
