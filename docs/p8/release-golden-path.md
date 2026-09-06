<!-- SPDX-License-Identifier: Apache-2.0 -->

# P8 Release and Operations Golden Path

This is an actually executed local Docker/Compose path using synthetic/offline data. It
contacts no external provider and publishes nothing. Docker unavailable is
`not_evaluated`, blocks evidence, and cannot be converted into a pass.

Run from a clean implementation commit:

```bash
make p8-reproducibility
make p8-compose-runtime
make p8-golden
```

The automated path creates all build workspaces, extracted source, Compose project names,
ports, volumes, credentials, backup archives, rollback backups, and diagnostic bundles
under OS temporary boundaries. It never writes release or private runtime bytes into the
repository.

The checkpoints are:

1. Build the exact six-file candidate twice from the same source commit and fixed inputs;
   validate each manifest/checksum/inventory and compare every SHA-256.
2. Extract only the validated allowlisted source archive and start its default Compose
   topology on unused loopback ports.
3. Verify API and Studio health, retrieve the one-time bootstrap value only in the operator
   process, exchange it, and complete a basic authenticated session flow.
4. Create a synthetic colleague, default revisioned policy, finite work, Timer no-op and
   Event wake, exact proposal, HUMAN approval, reference ActionResult, membership, and
   causal audit history.
5. While WAL writers are live, create and verify an online backup in a private mounted
   temporary directory. No database or backup bytes enter output or logs.
6. Apply a safe state mutation and prove the current state differs from the backup instant.
7. Stop API and worker, restore with explicit offline replacement and an automatic private
   rollback backup, restart fresh services, and prove identity, authority, policy, work,
   trigger/wake/Agenda, proposal/approval/result, membership, and causal state match the
   backup instant.
8. Generate an allowlisted support bundle while credential, private-payload, and local-path
   canaries exist only in the test boundary. Scan stdout, stderr, bundle, candidate archives,
   and service logs for zero canary disclosure.
9. Stop normally, bring the unique project down, and verify zero containers, networks,
   temporary volumes, credentials, backups, diagnostic bundles, extracted candidate trees,
   and build workspaces remain.

Evidence records the actual runtime versions, safe checkpoint classifications, counts, and
artifact digests only. It records human evaluation, live-provider evidence, and the
five-minute target as `not_evaluated`; the path does not claim production readiness,
security, privacy, availability, compliance, named-provider compatibility, or real
delivery.
