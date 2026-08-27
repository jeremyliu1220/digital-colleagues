<!-- SPDX-License-Identifier: Apache-2.0 -->

# Provenance Procedure

## Principles

1. Identify the source by a public label, never by a local location.
2. Read only the approved fixed Git revision.
3. Select individual files with a versioned allowlist.
4. Verify source bytes against SHA-256 before any transformation.
5. Record a repository-relative destination, classification, and required transform.
6. Perform rights and third-party notice review before writing migrated content.
7. De-identify and adapt architecture before adding the destination file.
8. Run the public-boundary scanner and milestone tests.
9. Preserve the evidence as counts and digests without source checkout locations.

## P0 commands

```bash
python3 scripts/verify_source_allowlist.py --source SOURCE_CHECKOUT --revision dea9a9accc82fbedd35deb7117dcb5173223cf44
python3 scripts/check_public_boundary.py .
```

The first command reads Git objects only and copies nothing. `SOURCE_CHECKOUT` is runtime
input. It is never saved or echoed, including on failure.

## Fingerprint scope

Because the new target is intentionally nested inside the parent working tree, the
pre-existing parent state is fingerprinted with exactly one pathspec exclusion: the
authorized `digital-colleagues` target subtree. Status, tracked diff, index diff, and the
path/type/mode/content state of every existing untracked or ignored entry are hashed.
Only aggregate counts and digests are emitted: no entry path, content, link target, or
source location is returned, including in errors. Matching before and after values mean no
pre-existing parent-source state changed. The full parent status is expected to contain
the untracked target subtree.

## Future migration receipt

A later migration receipt may contain only the allowed source fields plus transformation
tool version, destination digest, reviewer role, and gate result. It must not contain
source checkout locations, author contact data, live provider values, personal acceptance,
or raw command output.
