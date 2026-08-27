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

## P0 claim

A clean scan establishes only that the current files passed the encoded planning/public
boundary checks. It is not proof that a future product is private, secure, compliant, or
production-ready.
