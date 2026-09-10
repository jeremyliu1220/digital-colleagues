<!-- SPDX-License-Identifier: Apache-2.0 -->

# P11R Post-P11 Governance and CI Alignment Acceptance Contract

Status: fixed development contract. This file contains the complete Change Decision and
immutable acceptance contract for P11R. It is committed alone as the first P11R commit and
must remain byte-identical to that Git object. It must never be amended, rebased, squashed,
force-rewritten, weakened, or changed to fit implementation or CI results.

P11R is a narrow post-P11 governance and continuous-integration alignment. It is not a
Roadmap rebaseline, a P11 product correction, or P12. P11R may be described only as
**governance and CI alignment candidate complete; awaiting independent acceptance** after
every authorized development gate passes. Passing P11R never authorizes P12.

## Change Decision

### Context

P11 passed independent acceptance, final acceptance, fast-forward merge, and remote-main
verification at exact commit `7e5387f148f86b5c9b07820dd8b8f4e18e12dc38` and exact tree
`6d7c1b3053fefc1f3b14a4b39fde2d5adb641990`. Its acceptance-contract blob is
`85f2a91b85d3ec223d4f458199913a3eadbaabe9`, and its implementation tree digest is
`sha256:8bc5a7d431aae4fd1d46d94fd3af96f664b2f39d1b1d6ab679c50571ca8220e6`.

GitHub Actions run `34414627643` failed after the accepted P11 push because the current
workflow still invoked the historical `make p10-ci` target. The P10 compatibility checker
correctly limits the accepted P10 object to P10 metadata changes and therefore reported
`api_semantic_change_outside_metadata` when applied to legitimate accepted P11 API/runtime
changes. This is `post_merge_ci_configuration_drift`; it is not a P11 product defect or a
P11 acceptance failure.

The accepted P11 aggregate runner is also a historical development gate. Its test scope
includes the branch-bound test
`tests.p11.test_repository.RepositoryTests.test_repository_gate_accepts_exact_development_scope`,
and its repository checker requires the historical development branch and pre-merge ref
layout. It cannot be used unchanged as a current-tree P11R, pull-request, or main gate.

### Decision

Add a branch-independent current-tree CI entry while retaining every accepted P10 and P11
historical gate byte-identically. `make ci` delegates to a new `make p11-ci` current-tree
gate. The new gate uses an exact, literal inventory of current-tree-compatible P11 tests,
executes every listed test, and excludes only the one development-object-only test named in
this contract. It never invokes the accepted P11 runner's `--scope test` on P11R, a pull
request, or main.

The final P11R candidate gate separately materializes the exact accepted P11 object in an
OS temporary checkout with its contract-required branch and ref layout, and executes the
original complete P11 gate there. Current-tree regression evidence and accepted-object P11
evidence remain distinct.

GitHub Actions uses the repository `.nvmrc` as its Node version source. The exact Node
version is `24.15.0`, matching `studio/package.json` engine `>=24.15.0 <25`. Corepack uses
the exact integrity-qualified package-manager declaration from `studio/package.json`,
currently `npm@11.12.1+sha224.8b8077c959144afd9fbfc0f0a36ecf5b5375c7b1a202f32c0c06cdcb`.
P11R does not introduce a second Node or npm version source.

### Alternatives considered

1. Modify or relax the P10 compatibility checker: rejected because that would rewrite the
   meaning and reproducibility of accepted P10 evidence.
2. Run the accepted P11 aggregate or test scope directly on every current branch: rejected
   because it intentionally validates the historical `codex/p11-agent-packages` development
   identity and ref layout.
3. Skip or tolerate the branch-bound P11 test: rejected because skips, xfails, glob-based
   exclusions, failure capture, and threshold reduction can conceal regressions.
4. Add a literal branch-independent current-tree inventory and retain an exact-object P11
   replay as a separate final-candidate gate: accepted.

### Consequences

- Historical P10 and P11 gates remain reproducible on their exact accepted objects.
- Pull requests and main receive P11-aware regression coverage without pretending to be the
  original P11 development branch.
- Evidence has three independent test counts: accepted P11 exact-object, current-tree P11,
  and P11R governance tests.
- Current CI does not repeatedly execute retained-P10 or Compose work. The P11R final
  candidate performs one exact-object P11 replay, and main-push CI performs a separately
  bounded Compose smoke.
- Future milestones may replace the implementation behind `make ci` only through a new
  accepted contract; they do not modify historical targets.

### Non-goals

P11R adds no product/runtime capability, Studio product behavior, API or CLI behavior,
database schema, migration, package/image, dependency, provider, connector, Semantic
Memory, proactivity, Roadmap rebaseline, or P12 work. It creates no tag, Release,
publication, signature, or attestation.

### Compatibility and migration impact

Product/runtime source changes, Studio product-behavior changes, database-schema changes,
and migration-count changes are all exactly zero. Migrations remain exactly 001 through
008. All P0-P11 accepted commits, acceptance contracts, evidence, provenance, migrations,
and historical checker behavior remain byte-identical.

## Exact baseline, branch, ancestry, and commit boundary

- Exact P11R base: `7e5387f148f86b5c9b07820dd8b8f4e18e12dc38`.
- Exact base tree: `6d7c1b3053fefc1f3b14a4b39fde2d5adb641990`.
- Exact development branch: `codex/p11r-ci-alignment`.
- Work begins only from a clean `main` whose `HEAD`, local `main`, and `origin/main` equal
  the exact base, and only when the development branch does not already exist.
- This acceptance-contract commit is the first P11R commit, has the exact base as its sole
  parent, and changes only `docs/p11r/acceptance.md`. Its SHA becomes
  `P11R_ACCEPTANCE_COMMIT`.
- Every implementation and evidence commit descends from `P11R_ACCEPTANCE_COMMIT`. No merge
  commit is permitted in the base-to-candidate range.
- Implementation commits contain every required allowlisted change except
  `artifacts/p11r/summary.json`. That summary is committed alone as the final evidence
  commit after the committed implementation passes its authorized gates.
- Branch creation and this isolated contract commit do not authorize implementation,
  evidence, push, pull request, merge, tag, Release, publication, Roadmap rebaseline, or
  P12.

## Historical immutable boundary

Every base-to-candidate path outside the P11R allowlist is unchanged. In particular:

- `docs/p0` through `docs/p11`, `artifacts/p0` through `artifacts/p11`, P0-P11 provenance,
  fingerprints, source-rights records, source allowlists, and accepted P10 remote
  distribution identities remain byte-identical to the exact base;
- migrations `001` through `008` and `migrations/manifest.json` remain byte-identical and
  the migration count remains eight;
- accepted P10 and P11 runners, tests, Make targets, checkers, evidence writers, acceptance
  contracts, and evidence are not edited or redefined;
- existing protected P10 GHCR subjects and digests are not selected, overwritten,
  republished, retagged, or deleted; and
- no historical evidence writer is invoked.

The historical `make p10-ci` target and P10 compatibility checker may be executed only in
an OS temporary checkout of the exact accepted P10 object required by their fixed contract.
They are never executed directly on the P11R branch, a P11R pull request, or current main.

## Exact changed-file allowlist

The complete base-to-final-candidate changed path set is exactly these 15 paths:

```text
.github/workflows/ci.yml
Makefile
artifacts/p11r/summary.json
docs/p11r/acceptance.md
docs/p11r/operations.md
provenance/p11r-change-receipt.json
scripts/check_p11r_ci_policy.py
scripts/check_p11r_repository.py
scripts/check_p11r_provenance.py
scripts/collect_p11r_evidence.py
scripts/run_p11r_toolchain.py
tests/p11r/__init__.py
tests/p11r/test_ci_policy.py
tests/p11r/test_evidence_gate.py
tests/p11r/test_repository.py
```

A missing or additional path, rename, copy, delete, special file, symlink, staged change,
unstaged change, or untracked entry fails closed. `Makefile` may only add P11R/current-CI
targets and their `.PHONY` names. Every pre-existing recipe, including `p10-ci`,
`p11-test`, `p11-check`, `check`, and historical evidence targets, remains byte-identical.

## Node, npm, Python, and supply-chain contract

- `.nvmrc` is the sole Node version file and remains byte-identical with exact content
  `24.15.0`.
- `studio/package.json` remains byte-identical and requires Node `>=24.15.0 <25` plus the
  existing integrity-qualified npm declaration.
- GitHub Actions `actions/setup-node` uses `node-version-file: .nvmrc`; it does not contain
  a separate `node-version` value.
- The runner verifies `node --version` is exactly `v24.15.0` and `corepack npm --version`
  is exactly `11.12.1` before Studio work.
- Corepack remains enabled, and Studio installation uses the committed lock with
  `corepack npm ci --ignore-scripts --no-audit` in an OS temporary copy.
- Python uses an OS temporary virtual environment installed from
  `requirements/p8.lock` with `pip --require-hashes`. Repository-local virtualenvs,
  dependency trees, caches, coverage files, databases, and build residue are forbidden.
- P11R documents, workflow, tests, and evidence must report the same exact Node, engine,
  npm, lock, and action-pin identities. Any mismatch fails closed.

## Current CI architecture

`make p11-ci` is the branch-independent P11-aware gate, and `make ci` delegates to it.
Neither target changes the meaning of `make p11-test`, `make p11-check`, or `make check`.

The current-tree runner may import and reuse the accepted P8 hash-locked environment
helpers. It must not modify, copy and relax, monkey-patch, or redefine the accepted P11
runner. On P11R, pull requests, and main it must not invoke:

```text
python3 -B -m scripts.run_p11_toolchain --scope test
make p11-test
make p11-check
make check
scripts/check_p11_repository.py
tests.p11.test_repository.RepositoryTests.test_repository_gate_accepts_exact_development_scope
```

The branch-independent gate executes, with positive counts and zero failures, errors,
skips, expected failures, or unexpected successes:

1. Python Ruff lint and format check plus mypy over `src`, `scripts`, and `tests`;
2. the exact 100-test current-tree P11 regression inventory below;
3. all P11R governance/security tests with an exact discovered count recorded;
4. Studio lint, format check, typecheck, test, and build under exact Node/npm;
5. P11 architecture, migrations, compatibility, and Studio contract checkers;
6. P11R CI-policy and branch-independent scope/protected-history checks; and
7. the public-boundary and secret/private-data scan.

The runner loads every current-tree P11 test by its complete literal unittest ID. It uses
no glob, prefix, substring, regular expression, skip, xfail, failure suppression, or
minimum-count substitute. It verifies that the exact accepted P11 test inventory is the
union of the 100 current-tree IDs and the one development-object-only ID. Missing, renamed,
additional, duplicated, or unexpectedly excluded P11 tests fail closed.

## Exact current-tree P11 regression inventory

The following 100 tests are the complete branch-independent current-tree P11 suite:

```text
tests.p11.test_agent_package.AgentPackageTests.test_valid_schema_has_distinct_content_and_package_digests
tests.p11.test_agent_package.AgentPackageTests.test_canonical_serialization_is_stable
tests.p11.test_agent_package.AgentPackageTests.test_canonical_serialization_preserves_array_order
tests.p11.test_agent_package.AgentPackageTests.test_unknown_root_field_fails_closed
tests.p11.test_agent_package.AgentPackageTests.test_unknown_capability_fails_closed
tests.p11.test_agent_package.AgentPackageTests.test_noncanonical_version_fails_closed
tests.p11.test_agent_package.AgentPackageTests.test_unknown_schema_runtime_and_noninteger_schema_version_fail_closed
tests.p11.test_agent_package.AgentPackageTests.test_content_digest_mismatch_fails_closed
tests.p11.test_agent_package.AgentPackageTests.test_workflow_cycle_fails_closed
tests.p11.test_agent_package.AgentPackageTests.test_unreachable_workflow_node_fails_closed
tests.p11.test_agent_package.AgentPackageTests.test_unknown_predicate_fails_closed
tests.p11.test_agent_package.AgentPackageTests.test_unknown_step_and_effect_kind_fail_closed
tests.p11.test_agent_package.AgentPackageTests.test_workflow_node_and_depth_bounds_fail_closed
tests.p11.test_agent_package.AgentPackageTests.test_every_reconvergent_workflow_path_obeys_depth_bound
tests.p11.test_agent_package.AgentPackageTests.test_duplicate_capability_and_self_grant_fail_closed
tests.p11.test_agent_package.AgentPackageTests.test_prompt_like_code_remains_inert_text
tests.p11.test_agent_package.AgentPackageTests.test_invalid_unicode_fails_closed
tests.p11.test_agent_package.AgentPackageTests.test_locale_key_mismatch_fails_closed
tests.p11.test_api_cli.ApiCliTests.test_exact_api_v1_route_inventory_is_installed
tests.p11.test_api_cli.ApiCliTests.test_package_mutation_forbids_caller_authority_fields
tests.p11.test_api_cli.ApiCliTests.test_deployment_mutation_forbids_caller_role_and_actor
tests.p11.test_api_cli.ApiCliTests.test_console_entry_point_is_exactly_dc
tests.p11.test_api_cli.ApiCliTests.test_cli_authentication_uses_only_bounded_stdin_envelope
tests.p11.test_api_cli.ApiCliTests.test_cli_accepts_only_exact_ip_literal_loopback_origins
tests.p11.test_api_cli.ApiCliTests.test_cli_refuses_origin_rebinding_before_reading_credentials
tests.p11.test_api_cli.ApiCliTests.test_cli_redirect_refusal_never_forwards_credentials
tests.p11.test_api_cli.ApiCliTests.test_p11_role_matrix_is_fail_closed_for_management
tests.p11.test_api_cli.ApiCliTests.test_csrf_and_origin_are_required_for_p11_mutations
tests.p11.test_api_cli.ApiCliTests.test_selection_response_never_exposes_session_digests
tests.p11.test_archive.ArchiveTests.test_exact_canonical_archive_is_valid
tests.p11.test_archive.ArchiveTests.test_wrong_expected_digest_fails_closed
tests.p11.test_archive.ArchiveTests.test_traversal_member_fails_closed
tests.p11.test_archive.ArchiveTests.test_absolute_and_backslash_paths_fail_closed
tests.p11.test_archive.ArchiveTests.test_deep_nesting_fails_closed
tests.p11.test_archive.ArchiveTests.test_additional_payload_fails_closed
tests.p11.test_archive.ArchiveTests.test_symlink_member_fails_closed
tests.p11.test_archive.ArchiveTests.test_fifo_and_device_members_fail_closed
tests.p11.test_archive.ArchiveTests.test_case_colliding_member_fails_closed
tests.p11.test_archive.ArchiveTests.test_archive_bomb_ratio_fails_closed
tests.p11.test_archive.ArchiveTests.test_member_count_bound_is_enforced_before_payload_use
tests.p11.test_archive.ArchiveTests.test_member_comment_fails_closed
tests.p11.test_archive.ArchiveTests.test_duplicate_json_key_fails_closed
tests.p11.test_archive.ArchiveTests.test_archive_comment_fails_closed
tests.p11.test_archive.ArchiveTests.test_noncanonical_json_fails_closed
tests.p11.test_attestation.AttestationTests.test_policy_bound_offline_verification_succeeds
tests.p11.test_attestation.AttestationTests.test_wrong_subject_digest_fails_closed
tests.p11.test_attestation.AttestationTests.test_caller_digest_must_bind_the_exact_artifact_bytes
tests.p11.test_attestation.AttestationTests.test_wrong_certificate_policy_fields_fail_closed
tests.p11.test_attestation.AttestationTests.test_self_hosted_attestation_fails_closed
tests.p11.test_attestation.AttestationTests.test_malformed_output_fails_closed
tests.p11.test_attestation.AttestationTests.test_nonzero_cli_exit_fails_closed
tests.p11.test_attestation.AttestationTests.test_cli_timeout_fails_closed
tests.p11.test_attestation.AttestationTests.test_unavailable_verifier_never_downgrades
tests.p11.test_attestation.AttestationTests.test_non_github_source_rejects_partial_attestation_configuration
tests.p11.test_attestation.AttestationTests.test_verified_attestation_does_not_create_trust
tests.p11.test_attestation.AttestationTests.test_registration_replay_does_not_repeat_external_verification
tests.p11.test_attestation.AttestationTests.test_registration_replay_binds_bundle_and_every_policy_field_before_verification
tests.p11.test_evidence_gate.EvidenceGateTests.test_claim_and_status_are_exactly_one_candidate_vocabulary
tests.p11.test_evidence_gate.EvidenceGateTests.test_exclusions_keep_future_and_live_claims_out
tests.p11.test_evidence_gate.EvidenceGateTests.test_writer_creates_only_the_summary_path
tests.p11.test_evidence_gate.EvidenceGateTests.test_preconditions_refuse_dirty_implementation_tree
tests.p11.test_evidence_gate.EvidenceGateTests.test_prior_summary_identity_change_fails_closed
tests.p11.test_evidence_gate.EvidenceGateTests.test_retained_p10_result_is_exact_and_required
tests.p11.test_evidence_gate.EvidenceGateTests.test_candidate_range_diff_rejects_committed_trailing_whitespace
tests.p11.test_lifecycle.LifecycleTests.test_install_does_not_create_or_activate_deployment
tests.p11.test_lifecycle.LifecycleTests.test_register_trust_and_install_are_three_distinct_states
tests.p11.test_lifecycle.LifecycleTests.test_confirmation_leaves_deployment_in_draft
tests.p11.test_lifecycle.LifecycleTests.test_draft_review_and_confirmation_replay_exactly
tests.p11.test_lifecycle.LifecycleTests.test_distinct_activation_and_pause_transitions
tests.p11.test_lifecycle.LifecycleTests.test_illegal_draft_to_paused_transition_fails_closed
tests.p11.test_lifecycle.LifecycleTests.test_replay_rebinding_fails_closed
tests.p11.test_lifecycle.LifecycleTests.test_stale_revision_and_digest_fail_closed
tests.p11.test_lifecycle.LifecycleTests.test_revocation_blocks_active_exact_binding
tests.p11.test_lifecycle.LifecycleTests.test_only_active_deployment_is_runtime_eligible
tests.p11.test_lifecycle.LifecycleTests.test_upgrade_and_rollback_require_review_and_separate_activation
tests.p11.test_lifecycle.LifecycleTests.test_revoked_and_stale_rollback_targets_fail_closed
tests.p11.test_lifecycle.LifecycleTests.test_model_cannot_self_activate_and_namespaces_do_not_alias
tests.p11.test_lifecycle.LifecycleTests.test_lifecycle_audit_has_exact_actor_and_causality
tests.p11.test_lifecycle.LifecycleTests.test_selection_is_replay_safe_and_audited_in_its_transaction
tests.p11.test_lifecycle.LifecycleTests.test_tenth_succeeds_and_eleventh_is_audited_refusal
tests.p11.test_lifecycle.LifecycleTests.test_concurrent_activation_cannot_exceed_ten
tests.p11.test_migrations.MigrationTests.test_fresh_install_reaches_schema_eight_without_deployments
tests.p11.test_migrations.MigrationTests.test_named_active_limit_triggers_exist
tests.p11.test_migrations.MigrationTests.test_repeated_open_is_idempotent
tests.p11.test_migrations.MigrationTests.test_retained_manual_creation_receives_legacy_deployment_binding
tests.p11.test_migrations.MigrationTests.test_schema_seven_upgrade_preserves_legacy_manual_identity
tests.p11.test_migrations.MigrationTests.test_manifest_prefix_is_immutable
tests.p11.test_migrations.MigrationTests.test_active_slot_constraint_rejects_out_of_range_value
tests.p11.test_migrations.MigrationTests.test_active_limit_is_global_to_the_local_execution_host
tests.p11.test_migrations.MigrationTests.test_legacy_count_above_ten_aborts_migration_atomically
tests.p11.test_repository.RepositoryTests.test_acceptance_allowlist_has_exactly_fifty_nine_paths
tests.p11.test_repository.RepositoryTests.test_acceptance_commit_is_first_and_isolated
tests.p11.test_repository.RepositoryTests.test_historical_migrations_have_no_base_diff
tests.p11.test_repository.RepositoryTests.test_architecture_gate_rejects_application_adapter_import
tests.p11.test_studio.StudioTests.test_studio_gate_has_exact_locale_parity
tests.p11.test_studio.StudioTests.test_registry_has_live_result_announcement
tests.p11.test_studio.StudioTests.test_registry_keeps_permission_diff_visible
tests.p11.test_studio.StudioTests.test_registry_controls_have_disabled_busy_states
tests.p11.test_studio.StudioTests.test_registry_exposes_complete_separate_admin_workflow
tests.p11.test_studio.StudioTests.test_registry_displays_exact_attestation_review_fields
```

The sole development-object-only P11 test is:

```text
tests.p11.test_repository.RepositoryTests.test_repository_gate_accepts_exact_development_scope
```

This classification does not disable or weaken that test. It remains mandatory in the
accepted P11 exact-object suite.

## Accepted P11 exact-object replay

The P11R final candidate gate creates a new OS temporary checkout and establishes this
exact historical identity only inside that temporary checkout:

```text
accepted P11 HEAD: 7e5387f148f86b5c9b07820dd8b8f4e18e12dc38
branch: codex/p11-agent-packages
historical P11 base/main/origin-main: 4bef5629d450c6bb3940f606fc90194e008ee8fd
```

It then executes the original `make p11-check` without editing any accepted P11 file,
runner, test, checker, contract, evidence, or Git object. The run must report the complete
accepted P11 suite of exactly 101 tests with zero failures, errors, skips, expected
failures, or unexpected successes, and the original aggregate gate must pass. Temporary
paths and ref synthesis never enter the repository or evidence, and the checkout is removed
after the result is reduced to safe object IDs, counts, and finite status fields.

This exact-object replay occurs only in the P11R final candidate gate. It is not part of
pull-request or main current CI and does not rewrite accepted P11 evidence.

## GitHub Actions contract

The current workflow triggers only for pull requests targeting `main` and pushes to
`main`. It has only `permissions: contents: read`, uses immutable 40-hex action commits,
persists no checkout credentials, receives no secrets, requests no OIDC, and performs no
network write, package/image push, tag, Release, signature, attestation, or publication.
`pull_request_target`, `workflow_dispatch`, scheduled execution, and other events are
forbidden.

The common `current-ci` job runs `make ci` against the exact pull-request head SHA or exact
main push SHA. A `main-compose-smoke` job may run only after `current-ci` succeeds on a
push to `refs/heads/main`. Pull requests do not run Compose because P11R permits no product,
Studio-behavior, schema, migration, or deployment-topology change. The final P11R candidate
gate and merged-main push together retain bounded Compose coverage without recurring on
every pull request.

Workflow policy tests use a strict canonical policy and fail closed on unknown triggers,
permissions, actions, credentials, shell expressions, or publishing commands. They reject
write permissions, secret contexts, OIDC, mutable action references, persisted checkout
credentials, `git push`, tag/Release/package/image publication, signing/attestation,
historical P10/P11 aggregate commands on current trees, and a Compose job not restricted to
successful main pushes.

## P11R tests and evidence separation

P11R tests include positive and negative coverage for repository identity, exact allowlist,
immutable history, Makefile additive-only changes, current-test inventory equality, sole
development-only exclusion, Node/npm consistency, workflow triggers and permissions,
immutable action pins, credential persistence, secrets/OIDC/write denial, publishing-command
denial, current-CI command selection, Compose event restriction, evidence binding, and
fail-closed writer preconditions. Every test is named; the suite uses no skip or xfail.

Evidence records these as three separate objects and never sums or relabels them:

1. `accepted_p11_exact_object_suite`: exactly 101 tests, exact accepted P11 commit and
   historical branch identity, original aggregate command, and zero-exception counters;
2. `p11r_current_tree_p11_regression_suite`: exactly 100 literal tests, current candidate
   commit/tree, the sole excluded ID and reason, and zero-exception counters; and
3. `p11r_governance_suite`: the actual exact positive test count and full zero-exception
   counters for tests under `tests/p11r`.

The summary also records exact Node `24.15.0`, engine `>=24.15.0 <25`, npm `11.12.1`,
the integrity-qualified package-manager value, Python lock digest, action pins, all gate
commands/statuses, changed paths, protected-history identities, Compose result and residue,
CI run identity, read-only permission state, and zero secrets, OIDC, write permissions,
tags, Releases, package/image pushes, signatures, attestations, and publications.

Run `34414627643` is recorded only as the known post-merge CI configuration-drift baseline.
It must not be described as a P11 product regression or acceptance failure.

## Required gates and phased authorization

Implementation, candidate push/pull request, evidence generation, independent acceptance,
final acceptance, local fast-forward merge, and remote push each require a separate explicit
authorization.

The implementation phase will define repeatable P11R targets for:

```text
make p11r-test
make p11-ci
make ci
make p11r-compose-smoke
make p11r-check
make evidence-p11r
```

`make p11r-check` must include the current-tree gate, all P11R static and negative gates,
the accepted P11 exact-object replay, one bounded P11R candidate Compose smoke, public
boundary, committed diff validation, and cleanup. It must not invoke a historical evidence
writer. Evidence generation occurs only from a clean committed implementation and writes
only `artifacts/p11r/summary.json`; the final summary commit is followed by the complete
candidate gate again without rewriting the summary.

Independent acceptance binds one exact final candidate SHA/tree and verifies a successful
read-only, non-publishing pull-request run for that candidate. After separately authorized
fast-forward merge and remote push, a successful main `current-ci` and bounded Compose run
plus unchanged remote tags, Releases, packages/images, and protected P10 GHCR digests are
required for remote closeout. Those post-push results are reported externally and do not
rewrite accepted evidence.

## Stop conditions and final wording

Stop without cleanup, stash, reset, revert, rebase, force, contract modification, or scope
absorption if baseline, branch, ancestry, cleanliness, protected-history, Node/npm identity,
literal test inventory, exact-object replay, zero-exception test policy, workflow security,
public-boundary, no-publication, zero-product-change, or cleanup checks fail; an unlisted
path is needed; accepted P10/P11 behavior would need modification; a skip, xfail, glob,
failure suppression, threshold reduction, or fabricated result would be required; remote
write is needed without its phase authorization; or Roadmap rebaseline or P12 work is
needed.

After all separately authorized implementation and evidence gates pass, the exact
development conclusion is:

**P11R governance and CI alignment candidate complete; awaiting independent acceptance.**
