<!-- SPDX-License-Identifier: Apache-2.0 -->

# P11 local operations

Run `make p11-test` for the focused package, archive, attestation, migration, lifecycle,
API/CLI, Studio, and abuse suite. Run `make p11-check` for the retained exact-P10 object,
all P11 static and runtime gates, and isolated source-Compose restart/cleanup. `make check`
is the same aggregate P11 gate.

Local package inspection is non-mutating:

```bash
dc package-check inspect --archive PACKAGE.zip --expected-digest sha256:DIGEST
```

Authenticated remote commands read exactly one bounded JSON envelope from stdin:

```json
{"session_cookie":"VALUE","csrf_token":"VALUE"}
```

The values must never be placed in shell arguments, environment, logs, evidence, or issue
reports. GitHub Release registration additionally requires an operator-configured GitHub
CLI, trusted-root file, and offline bundle. Verification performs no login or network
write; unavailable or failed verification is terminal for that registration attempt.

Back up `state.sqlite` with the retained WAL-safe operation before migration. P11 has no
down migration. Rollback restores a verified schema-7 backup and matching code. Revoked,
paused, blocked, draft, and retired deployments do not execute. An activation refusal
`active_deployment_limit_reached` is expected when ten deployments already run on `local`.

`make evidence-p11` is permitted only from the clean committed implementation described
by the acceptance contract. It writes only `artifacts/p11/summary.json`. Do not push,
merge, tag, publish, create a Release, or begin P12.
