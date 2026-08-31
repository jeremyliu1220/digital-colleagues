<!-- SPDX-License-Identifier: Apache-2.0 -->

# P4 Local Studio Golden Path

Status: development complete, awaiting independent acceptance.

This guide exercises the synthetic/offline P4 path. It does not use a real model, live
provider, account, external network effect, or production credential. Loopback publishing
reduces host exposure; it is not authentication, encryption, sandboxing, tenant isolation,
or a production-security control.

## Reference environment and prerequisites

The reference topology requires Docker Engine with Compose v2, an unused local Studio
port (default 4173), and an unused local API port (default 8000). Python 3.12+, Node.js
22.12+, npm, and Make are required for repository gates. Run commands from the repository
root. Use a unique Compose project name for each evidence attempt.

The automated fresh-instance smoke is:

```bash
PYTHONPATH=src python3 -B scripts/check_p4_golden_path.py
```

It creates a temporary SQLite file outside the repository, closes every first-instance
store and HTTP client, reconstructs them over the same file, and cleans the directory. It
proves flow and fresh-instance recovery only. It does not start containers or measure the
five-minute objective.

## Isolated Compose run

Choose a unique, non-personal project label and start the stack:

```bash
export DC_COMPOSE_PROJECT=p4-golden-synthetic
docker compose --project-name "$DC_COMPOSE_PROJECT" up --build --detach
docker compose --project-name "$DC_COMPOSE_PROJECT" ps
```

The named project owns its containers, network, and project-scoped `state` volume. The volume holds
the only `state.sqlite`. Do not map a repository directory to `/var/lib/digital-colleagues`.

Retrieve the bootstrap token once from a separate operator process:

```bash
docker compose --project-name "$DC_COMPOSE_PROJECT" run --rm operator
```

This one-shot process creates the token in memory, atomically stores and claims only its
digest in SQLite, and writes the plaintext only to the invoking operator terminal. No
plaintext handoff file exists in the volume, and API, worker, and Studio code has no
token-print path. Do not paste the token into chat, a file, shell
history, logs, fixtures, screenshots, or evidence. If it expires after ten minutes or the
operator command has already initialized it, stop the attempt, destroy the isolated volume,
and begin a clean attempt.

Open `http://127.0.0.1:4173`. The browser exchanges the token for an HttpOnly,
SameSite=Strict cookie. Local HTTP omits Secure; HTTPS mode enables it. The response also
provides the session-bound CSRF value used by Studio mutations. The server, not the
browser, creates the tenant, HUMAN `tenant_admin` principal, principal ID, session ID, and
active namespace.

## Manual path and restart checkpoint

The required human steps are:

1. Enter the one-time token and submit the bootstrap exchange.
2. Complete the initial-colleague builder. Review the descriptive Profile separately from
   the authoritative Mandate, exact revision 1, responsibilities, capabilities,
   constraints, initial working-hours data, and effect boundary before confirming.
3. Assign one finite synthetic work item to a listed responsibility.
4. Stop at the restart checkpoint. Do not create the trigger yet.

Restart every long-running service while preserving the volume:

```bash
docker compose --project-name "$DC_COMPOSE_PROJECT" restart api worker studio
docker compose --project-name "$DC_COMPOSE_PROJECT" ps
```

Reload Studio and confirm that identity, Mandate revision, finite work, and existing
history came from the recovered server state. Browser local/session storage is not used.

Then:

5. Create an Event or Timer trigger. A deterministic no-op path may be inspected
   separately; it must create no proposal and must not increase the AI-initiated numerator.
6. Run one bounded processing cycle and inspect wake reason, trigger class and identity,
   Agenda generation/handled generation, WakeCycle, Decision, correlation, causation,
   revisions, and safe UTC time.
7. Inspect the proposal inbox. Verify the exact proposal revision and both proposal and
   payload digests, safe projection, destination, action, effect boundary, Mandate
   ID/revision, actor, namespace, expiry, status, and causal source.
8. Approve or reject that exact immutable revision. A rejection is a successful governed
   outcome but does not create an EffectAttempt or ActionResult. To finish the reference
   ActionResult path, approve the proposal and run one more bounded processing cycle.
9. Open the audit view and inspect the safe chain from InputEvent through Agenda,
   WakeCycle, Decision, EffectProposal, HumanApprovalDecision, EffectAttempt, and
   ActionResult.

Success requires the authenticated path, durable recovery, exact approval, reference
ActionResult, and complete safe causal chain. Raw payloads and credentials must be absent
from the view and logs.

## Timing definition and claim limit

The five-minute objective starts immediately before the operator runs the one-time token
retrieval command. It ends when Studio displays the reference ActionResult and complete
causal audit chain after the documented restart. Image build/download time and prerequisite
installation are outside the interval; operator token entry, initial colleague confirmation,
work assignment, restart wait, trigger, proposal review, approval, and audit inspection are
inside it.

The repository automation does not drive or time those human steps. Therefore P4 records
the five-minute limit as **not evaluated**, not passed. An independent timed run must record
the environment, image state, start/end timestamps, elapsed time, exact human steps, any
retries, and evidence class. One measured environment cannot become a universal
performance promise.

## Cleanup and residue check

Normal stop and isolated cleanup are:

```bash
docker compose --project-name "$DC_COMPOSE_PROJECT" down --volumes --remove-orphans
docker compose --project-name "$DC_COMPOSE_PROJECT" ps --all
make p4-repository
python3 -B scripts/check_public_boundary.py .
```

Removing the named volume destroys the synthetic local state and cannot be undone. It is
appropriate only for the isolated project created for this run. The repository must not
contain SQLite/WAL/SHM files, logs, credentials, `dist`, coverage, or container residue.

## Evidence class and exclusions

This path yields synthetic/offline reference evidence only. It is not human-study or
live-provider evidence and does not prove colleague-experience improvement, five-minute
completion, production authentication, production security/privacy, compliance,
availability, distributed execution, or production readiness.
