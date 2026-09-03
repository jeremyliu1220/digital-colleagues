<!-- SPDX-License-Identifier: Apache-2.0 -->

# Public Provenance and Privacy Boundary

## Objective

The public project must be reconstructable from labeled, revision-pinned, repo-relative
records without revealing where a source checkout lives or copying personal or live
provider material.

## Allowed provenance fields

A source artifact records only:

- source label;
- Git revision;
- repository-relative source path;
- repository-relative destination;
- SHA-256 content digest;
- classification; and
- required transform.

Schema and policy versions may wrap those fields. Runtime source locations are ephemeral
process inputs and are never artifacts.

## Prohibited public material

- Local absolute paths or links to a local checkout.
- Email addresses or personal contact details.
- Personal colleague identifiers or names encoded as identifiers.
- Live provider, workspace, account, channel, conversation, or message identifiers.
- Bootstrap, enrollment, API, bot, session, or other credential material.
- Private keys, environment values, local databases, volumes, or logs.
- Live receipts, provider payloads, message bodies, or external acceptance evidence.
- Personal confirmation, acceptance, rating, or interview data.
- Raw parent-project evidence and current working-tree changes.

## Scanner policy

`provenance/scanner-policy.json` is versioned and contains named rule groups plus digests of
known private markers. Private marker values are not stored. The scanner also detects path,
contact, provider-identifier, credential, private-key, and structured live-evidence shapes.

`provenance/scanner-exceptions.json` is an exact exception ledger. An exception must name
one repository-relative file, one rule ID, the file's exact digest, a reason, and an
approving role. Directory globs, suffix-wide exclusions, generated-tree exclusions, and
unscoped rule suppression are invalid. P0 has no exceptions.

The scanner traverses every regular public-project file under the target root. It excludes
only the exact root `.git` administrative entry. A real root `.git/` directory is treated
as Git metadata. A root `.git` regular file is excluded only when a no-follow read confirms
one bounded line in `gitdir: POINTER` format, as used by Git worktrees. The pointer is never
followed, emitted, persisted, or included in an error. Malformed content, multiple lines,
a symlink, an oversized file, or any other special type fails closed.

Nested `.git` files and directories, `.github`, `.gitignore`, and all other similarly named
public paths remain in scope. A binary or undecodable public file fails closed unless a
future exact digest-bound exception is reviewed. The scanner reports repository-relative
public paths and rule IDs only, and its summary reports the count of exact digest-bound
exceptions actually applied.

## Error and output discipline

Tools accept a local `--source` location but replace all source-command errors with a
generic labeled failure. They do not print subprocess diagnostics that could contain the
location. Machine-readable output contains labels, revisions, counts, digests, and
repository-relative paths only.

## Live evidence separation

Live-provider and personal acceptance work belongs to a separate, non-public evidence
process. Reference receipts, deterministic fixtures, or synthetic confirmations cannot be
represented as live provider acceptance. Public release claims must name which evidence
class they use.

## P3 runtime and evidence boundary

P3 fixtures use only synthetic tenant, colleague, principal, work, destination, and content
values. The deterministic intelligence adapter and reference channel perform no network
access and accept no live account or provider configuration. SQLite files, WAL/SHM files,
logs, backups, and diagnostics are created only under OS temporary directories and are
forbidden from the public tree. Effect payload bytes may be present in the temporary local
state needed to dispatch the typed effect; public audit history, gate output, errors, and
evidence contain only digests or safe projections. The P3 parent fingerprints contain only
aggregate path-free fields and exclude exactly the repository-relative target subtree.

## Evidence claim

A clean scan plus P3/P4 synthetic tests establish only that the current files and encoded
reference paths passed their public-boundary checks. They do not prove that a future product
or real-provider deployment is private, secure, compliant, or production-ready.

## P4 credential and Studio boundary

P4 stores bootstrap and session credentials only as digests. The bootstrap plaintext is
created in memory and atomically claimed by the explicitly invoked one-shot operator
process; no plaintext handoff file exists, and API, worker, and Studio have no print path
for it. Browser state
uses an HttpOnly, SameSite=Strict cookie and does not use local storage as persistence.
Public tests generate transient synthetic values at runtime and public evidence records
only control results, counts, safe projections, and digests. An operator terminal,
unencrypted local volume, valid browser session, or same-user malware remains outside the
public-tree scanner's security guarantee.

P4 evaluation observations contain only stable namespaced opportunity/candidate IDs,
versioned source labels, integer judgments, safe causal references, and UTC observation
times. Rejected proposal candidates persist no candidate payload. Actual Compose runtime
evidence records only environment versions, a synthetic project label, timestamps,
checkpoint booleans, metric readouts, and cleanup counts; the operator token, session
credential, and CSRF value remain in process memory and are checked absent from service
logs and evidence output.

## P5 draft, policy, and evidence boundary

P5 public fixtures contain only synthetic colleague content. Draft audit stores the exact
canonical digest plus safe paths, classifications, revisions, lifecycle state, and default
sources; it does not copy private proposed payloads into causal history. Policy outcome and
escalation evidence contains typed outcomes, exact Mandate/policy revisions, safe summaries,
and digests. Budget rows contain only namespaced occurrence identities and counters.

The actual Compose Gate uses a unique project label, unused loopback ports, and a temporary
project-scoped volume, then verifies zero container, network, and volume residue. Bootstrap,
session, and CSRF plaintext stay process-local and are checked absent from service logs and
the P5 summary. Revision-bound synthetic/offline metrics do not represent human or live
provider observations and establish no colleague-experience improvement.

## P6 governance credential and export boundary

P6 enrollment and recovery plaintext may exist only in the invoked local operator process.
Browser-facing API responses, Studio state, worker context, SQLite, audit, logs, errors,
fixtures, and evidence receive no plaintext token, session credential, cookie, or CSRF
value. Persistence uses only purpose-framed credential digests; audit and evidence use safe
lifecycle identifiers and outcomes without credential digests.

Audit export requires an exact authorized namespace, explicit UTC range, allowlisted record
types, and bounded limit. Its versioned rows contain safe causal identifiers, revisions,
results, and required non-credential digests only. Private payloads, local absolute paths,
provider identifiers, raw diagnostics, secrets, and live/personal data are prohibited.

P6 public evidence remains synthetic/offline. It cannot be labeled human or live-provider
evidence and does not establish production privacy, security, compliance, tenant isolation,
or enterprise IAM. The P6 Gate has passed; those exclusions remain.

## P7 optional-adapter boundary

P7 public fixtures use synthetic tenant, colleague, work, destination, payload, and result
values against a controlled IP-loopback stub. The stub, its acknowledgements, and its
runtime receipts are synthetic/offline evidence, never live-provider evidence. Public
artifacts record human and live-provider evaluation as `not_evaluated`.

Optional credentials are opaque values created under an OS temporary directory for tests,
read only at the adapter composition edge, and removed during cleanup. Normal operation
prefers an operator-created Git-ignored read-only credential file. The public composition
root does not accept credential values through environment variables. Credentials and
credential paths are excluded from JSON bodies, SQLite, audit, API/Studio, exception text,
stdout/stderr, service logs, command arguments, and evidence.

Model requests contain only a minimal versioned namespace/work/agenda/allowed-boundary
projection. Session cookies, CSRF, bootstrap/enrollment/recovery values or digests, full
audit export, unrelated namespaces, local paths, and private governance material are never
sent. Channel requests contain the exact effect payload required for an already approved
dispatch; only safe classifications and irreversible digests return to durable
ActionResult/audit records. Raw adapter response bodies are not persisted or emitted.

URL validation rejects userinfo, query, fragment, redirect, non-HTTPS production endpoint,
and non-loopback test HTTP. Diagnostics expose only allowlisted categories, protocol/result
classifications, and digests. Provider/account/workspace/channel/conversation/message IDs,
live payloads, live receipts, real endpoints, and personal acceptance results remain
forbidden from the public tree. Live acceptance requires separate authorization and
non-public storage and cannot replace the P7 synthetic contract Gate.
