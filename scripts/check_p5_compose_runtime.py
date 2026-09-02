# SPDX-License-Identifier: Apache-2.0

"""Exercise isolated P5 Compose builder, policy, restart, fault, and cleanup paths."""

from __future__ import annotations

import argparse
import http.cookiejar
import json
import os
import platform
import secrets
import shutil
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.check_p4_compose_runtime import (
    ComposeRuntimeError,
    _cleanup,
    _compose,
    _container_ids,
    _now,
    _port,
    _request,
    _run,
    _wait_json,
    _wait_studio,
)


def _expect_status(
    opener: urllib.request.OpenerDirector,
    url: str,
    *,
    status: int,
    payload: dict[str, object],
    headers: dict[str, str],
) -> None:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, separators=(",", ":"), sort_keys=True).encode(),
        headers={"Accept": "application/json", "Content-Type": "application/json", **headers},
        method="POST",
    )
    try:
        opener.open(request, timeout=5)
    except urllib.error.HTTPError as exc:
        if exc.code == status:
            return
    except OSError as exc:
        raise ComposeRuntimeError("a fault-injection request did not return safely") from exc
    raise ComposeRuntimeError("a P5 stale fault did not return the expected refusal")


def _policy(wake_limit: int) -> dict[str, object]:
    return {
        "timezone": "UTC",
        "weekly_windows": [
            {"weekday": day, "start_minute": 0, "end_minute": 1440}
            for day in (
                "monday",
                "tuesday",
                "wednesday",
                "thursday",
                "friday",
                "saturday",
                "sunday",
            )
        ],
        "allowed_triggers": ["event", "timer"],
        "proactivity": "bounded",
        "notification": "enabled",
        "interruption": "allowed",
        "wake_limit": wake_limit,
        "wake_period": "day",
        "outside_hours": "defer",
        "stop_conditions": ["admin_stop", "budget_exhausted"],
        "escalation_conditions": ["budget_exhausted", "blocked_work"],
        "failure_limit": 3,
        "run_state": "active",
    }


def _update_body(
    draft: dict[str, Any],
    *,
    key: str,
    display_name: str,
    mission: str,
    wake_limit: int,
    policy_changes: dict[str, object] | None = None,
    policy_replacement: dict[str, object] | None = None,
) -> dict[str, object]:
    profile = cast(dict[str, Any], draft["proposed_profile"])
    mandate = cast(dict[str, Any], draft["proposed_mandate"])
    responsibilities = cast(list[dict[str, Any]], mandate["responsibilities"])
    capabilities = cast(list[dict[str, Any]], mandate["capabilities"])
    constraints = cast(list[dict[str, Any]], mandate["constraints"])
    boundaries = cast(list[dict[str, Any]], mandate["effect_boundaries"])
    policy = _policy(wake_limit)
    if policy_changes is not None:
        policy.update(policy_changes)
    if policy_replacement is not None:
        policy = policy_replacement
    return {
        "profile": {
            "display_name": display_name,
            "description": profile["description"],
            "presentation": profile["presentation"],
        },
        "mandate": {
            "mission": mission,
            "service_relationship": mandate["service_relationship"],
            "responsibilities": [
                {
                    "responsibility_id": item["responsibility_id"],
                    "description": item["description"],
                    "obligations": item["obligations"],
                    "completion_conditions": item["completion_conditions"],
                }
                for item in responsibilities
            ],
            "capabilities": [
                {"capability_id": item["capability_id"], "description": item["description"]}
                for item in capabilities
            ],
            "constraints": [
                {"constraint_id": item["constraint_id"], "description": item["description"]}
                for item in constraints
            ],
            "working_context": mandate["working_context"],
            "effect_boundaries": [
                {
                    "boundary_id": item["boundary_id"],
                    "effect_kind": item["effect_kind"],
                    "allowed_destination_kinds": item["allowed_destination_kinds"],
                    "allowed_actions": item["allowed_actions"],
                    "constraints": item["constraints"],
                    "human_approval_required": item["human_approval_required"],
                }
                for item in boundaries
            ],
        },
        "policy": policy,
        "expected_draft_revision": draft["revision"],
        "idempotency_key": key,
    }


def _create_update_review(
    opener: urllib.request.OpenerDirector,
    api: str,
    headers: dict[str, str],
    *,
    key: str,
    display_name: str,
    mission: str,
    wake_limit: int,
    policy_changes: dict[str, object] | None = None,
    policy_replacement: dict[str, object] | None = None,
) -> dict[str, Any]:
    created = _request(
        opener,
        api + "/colleagues/drafts",
        method="POST",
        headers=headers,
        payload={"idempotency_key": "create-" + key},
    )
    draft = cast(dict[str, Any], created["draft"])
    updated = _request(
        opener,
        api + f"/colleagues/drafts/{draft['draft_id']}",
        method="PUT",
        headers=headers,
        payload=_update_body(
            draft,
            key="update-" + key,
            display_name=display_name,
            mission=mission,
            wake_limit=wake_limit,
            policy_changes=policy_changes,
            policy_replacement=policy_replacement,
        ),
    )
    draft = cast(dict[str, Any], updated["draft"])
    reviewed = _request(
        opener,
        api + f"/colleagues/drafts/{draft['draft_id']}/review",
        method="POST",
        headers=headers,
        payload={
            "expected_draft_revision": draft["revision"],
            "idempotency_key": "review-" + key,
        },
    )
    return cast(dict[str, Any], reviewed["draft"])


def _confirmation(draft: dict[str, Any], key: str) -> dict[str, object]:
    return {
        "expected_draft_revision": draft["revision"],
        "expected_base_profile_revision": draft["base_profile_revision"],
        "expected_base_mandate_revision": draft["base_mandate_revision"],
        "expected_base_policy_revision": draft["base_policy_revision"],
        "expected_canonical_digest": draft["canonical_digest"],
        "idempotency_key": "confirm-" + key,
    }


def check_compose_runtime(root: Path) -> dict[str, object]:
    docker = shutil.which("docker")
    if docker is None:
        raise ComposeRuntimeError("Docker CLI is unavailable; P5 runtime remains not_evaluated")
    environment = os.environ.copy()
    api_port = _port()
    studio_port = _port()
    while studio_port == api_port:
        studio_port = _port()
    origin = f"http://127.0.0.1:{studio_port}"
    environment.update(
        {
            "DC_API_PORT": str(api_port),
            "DC_STUDIO_PORT": str(studio_port),
            "DC_EXPECTED_ORIGIN": origin,
        }
    )
    project = f"dc-p5-runtime-{os.getpid()}-{secrets.token_hex(4)}"
    started_at = _now()
    cleanup: dict[str, object] = {"passed": False}
    result: dict[str, object] | None = None
    try:
        server = _run(
            [docker, "version", "--format", "{{.Server.Version}}"],
            root=root,
            environment=environment,
        ).stdout.strip()
        compose_version = _run(
            [docker, "compose", "version", "--short"],
            root=root,
            environment=environment,
        ).stdout.strip()
        if not server or not compose_version:
            raise ComposeRuntimeError("Docker Engine or Compose version is unavailable")
        _compose(
            docker,
            project,
            ["up", "--build", "--detach", "api", "worker", "studio"],
            root=root,
            environment=environment,
        )
        jar = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
        api = f"http://127.0.0.1:{api_port}"
        _wait_json(opener, api + "/health")
        _wait_studio(origin)
        first_ids = _container_ids(docker, project, root=root, environment=environment)
        _compose(docker, project, ["build", "operator"], root=root, environment=environment)
        token = _compose(
            docker,
            project,
            ["run", "--rm", "--no-deps", "-T", "operator"],
            root=root,
            environment=environment,
        ).stdout.strip()
        if "\n" in token or len(token) < 32:
            raise ComposeRuntimeError("operator bootstrap retrieval returned an invalid shape")
        exchanged = _request(
            opener,
            api + "/auth/bootstrap/exchange",
            method="POST",
            payload={"token": token},
            headers={"Origin": origin},
        )
        csrf = exchanged.get("csrf_token")
        if not isinstance(csrf, str) or len(csrf) < 32:
            raise ComposeRuntimeError("bootstrap exchange did not return a CSRF binding")
        session_values = [cookie.value for cookie in jar if cookie.name == "dc_session"]
        if len(session_values) != 1:
            raise ComposeRuntimeError("bootstrap exchange did not create one session cookie")
        session_credential = session_values[0]
        if not isinstance(session_credential, str):
            raise ComposeRuntimeError("session cookie value was invalid")
        headers = {"Origin": origin, "X-CSRF-Token": csrf}
        _request(
            opener,
            api + "/colleagues",
            method="POST",
            headers=headers,
            payload={
                "display_name": "Runtime Atlas",
                "role_description": "Synthetic P5 Compose colleague",
                "service_relationship": "Serves the isolated runtime operator",
                "mission": "Complete one finite deterministic reference task",
                "timezone": "Asia/Taipei",
                "working_context": "Isolated synthetic Compose state",
                "working_hours": "free-form legacy display text",
                "working_style": "Direct and inspectable",
                "responsibilities": ["Own finite synthetic runtime work"],
                "capabilities": ["Propose a reference message"],
                "constraints": ["No external network"],
                "effect_kind": "reference_message",
                "destination_kind": "reference_channel",
                "action": "record_message",
                "effect_constraints": {"network": False},
                "idempotency_key": "compose-p5-colleague",
            },
        )
        recovered_session = _request(opener, api + "/auth/session")
        csrf = recovered_session.get("csrf_token")
        if not isinstance(csrf, str):
            raise ComposeRuntimeError("active colleague session lacked CSRF binding")
        headers = {"Origin": origin, "X-CSRF-Token": csrf}
        legacy = _request(opener, api + "/p5/studio/state")
        if legacy["active"]["policy_status"] != "legacy_unconfirmed":
            raise ComposeRuntimeError("legacy policy status was not explicit")
        initial = _create_update_review(
            opener,
            api,
            headers,
            key="initial-policy",
            display_name="Runtime Atlas P5",
            mission="Run only under exact typed P5 policy",
            wake_limit=4,
        )
        defaults_visible = bool(initial["explicit_defaults"])
        if not defaults_visible:
            raise ComposeRuntimeError("explicit P5 defaults disappeared from exact review")
        _request(
            opener,
            api + f"/colleagues/drafts/{initial['draft_id']}/confirm",
            method="POST",
            headers=headers,
            payload=_confirmation(initial, "initial-policy"),
        )
        draft_audit = _request(opener, api + f"/audit/{initial['correlation_id']}")
        draft_record_types = {item["record_type"] for item in draft_audit["records"]}
        if not {"colleague_draft", "draft_confirmation"}.issubset(draft_record_types):
            raise ComposeRuntimeError("P5 draft causal audit was incomplete")
        active = _request(opener, api + "/p5/studio/state")
        if (
            active["active"]["profile_revision"] != 2
            or active["active"]["mandate_revision"] != 2
            or active["active"]["policy_revision"] != 1
        ):
            raise ComposeRuntimeError("initial P5 exact revisions did not apply atomically")
        state = _request(opener, api + "/studio/state")
        responsibility_id = state["identity"]["mandate"]["responsibilities"][0]["responsibility_id"]
        work = _request(
            opener,
            api + "/work",
            method="POST",
            headers=headers,
            payload={
                "title": "P5 Compose policy work",
                "description": "Exercise revision binding and durable policy outcomes.",
                "responsibility_id": responsibility_id,
                "idempotency_key": "compose-p5-work",
            },
        )["work"]
        first_trigger = _request(
            opener,
            api + "/runtime/triggers",
            method="POST",
            headers=headers,
            payload={
                "work_id": work["work_id"],
                "trigger_class": "event",
                "deterministic_noop": False,
                "idempotency_key": "compose-old-proposal",
            },
        )
        if first_trigger.get("accepted") is not True:
            raise ComposeRuntimeError("typed policy refused the allowed Golden Path trigger")
        proposal_state = _wait_json(
            opener,
            api + "/studio/state",
            predicate=lambda value: bool(value.get("proposals")),
        )
        old_proposal = proposal_state["proposals"][0]

        winner = _create_update_review(
            opener,
            api,
            headers,
            key="winner",
            display_name="Runtime Atlas P5.1",
            mission="Use the winning exact policy revision",
            wake_limit=1,
        )
        loser = _create_update_review(
            opener,
            api,
            headers,
            key="loser",
            display_name="Never applied",
            mission="This concurrent draft must remain stale",
            wake_limit=3,
        )
        _request(
            opener,
            api + f"/colleagues/drafts/{winner['draft_id']}/confirm",
            method="POST",
            headers=headers,
            payload=_confirmation(winner, "winner"),
        )
        _expect_status(
            opener,
            api + f"/colleagues/drafts/{loser['draft_id']}/confirm",
            status=409,
            headers=headers,
            payload=_confirmation(loser, "loser"),
        )
        _expect_status(
            opener,
            api + f"/proposals/{old_proposal['proposal_id']}/decision",
            status=403,
            headers=headers,
            payload={
                "proposal_revision": old_proposal["revision"],
                "proposal_payload_digest": old_proposal["payload_digest"],
                "proposal_digest": old_proposal["proposal_digest"],
                "mandate_id": old_proposal["mandate_id"],
                "mandate_revision": old_proposal["mandate_revision"],
                "policy_id": old_proposal["policy_id"],
                "policy_revision": old_proposal["policy_revision"],
                "choice": "approve",
                "idempotency_key": "compose-stale-approval",
            },
        )
        _compose(
            docker,
            project,
            ["stop", "worker"],
            root=root,
            environment=environment,
        )
        proposals_before_queued_stop = len(
            _request(opener, api + "/studio/state").get("proposals", [])
        )
        allowed = _request(
            opener,
            api + "/runtime/triggers",
            method="POST",
            headers=headers,
            payload={
                "work_id": work["work_id"],
                "trigger_class": "timer",
                "deterministic_noop": False,
                "idempotency_key": "compose-budget-one",
            },
        )
        exhausted = _request(
            opener,
            api + "/runtime/triggers",
            method="POST",
            headers=headers,
            payload={
                "work_id": work["work_id"],
                "trigger_class": "event",
                "deterministic_noop": False,
                "idempotency_key": "compose-budget-two",
            },
        )
        if (
            allowed.get("accepted") is not True
            or exhausted.get("policy_outcome") != "budget_exhausted"
            or exhausted.get("escalation_id") is None
        ):
            raise ComposeRuntimeError("budget stop/escalation path was incomplete")
        policy_audit = _request(opener, api + f"/audit/{exhausted['correlation_id']}")
        policy_record_types = {item["record_type"] for item in policy_audit["records"]}
        if not {"policy_outcome", "policy_escalation"}.issubset(policy_record_types):
            raise ComposeRuntimeError("P5 policy refusal audit was incomplete")
        profile_only = _create_update_review(
            opener,
            api,
            headers,
            key="stopped-profile-only",
            display_name="Runtime Atlas remains stopped",
            mission="Use the winning exact policy revision",
            wake_limit=1,
            policy_replacement={},
        )
        profile_only_changes = [
            (item["section"], item["path"])
            for item in profile_only["diff"]
            if item["classification"] != "unchanged"
        ]
        if profile_only_changes != [("profile", "display_name")]:
            raise ComposeRuntimeError("profile-only stopped draft gained an authority change")
        profile_confirmation = _request(
            opener,
            api + f"/colleagues/drafts/{profile_only['draft_id']}/confirm",
            method="POST",
            headers=headers,
            payload=_confirmation(profile_only, "stopped-profile-only"),
        )
        profile_state = _request(opener, api + "/p5/studio/state")
        if (
            profile_confirmation["confirmation"]["policy_revision"] != 2
            or profile_state["runtime_policy"]["run_state"] != "stopped"
            or any(
                item.get("outcome") == "explicit_resume"
                for item in profile_state["runtime_policy"]["outcomes"]
            )
        ):
            raise ComposeRuntimeError("profile-only confirmation implicitly resumed runtime")
        before_restart = _request(opener, api + "/p5/studio/state")

        _compose(
            docker,
            project,
            ["stop", "api", "worker", "studio"],
            root=root,
            environment=environment,
        )
        _compose(
            docker,
            project,
            ["up", "--detach", "--force-recreate", "api", "worker", "studio"],
            root=root,
            environment=environment,
        )
        _wait_json(opener, api + "/health")
        _wait_studio(origin)
        second_ids = _container_ids(docker, project, root=root, environment=environment)
        if set(first_ids) & set(second_ids):
            raise ComposeRuntimeError("restart checkpoint did not create fresh containers")
        session = _request(opener, api + "/auth/session")
        csrf = session.get("csrf_token")
        if not isinstance(csrf, str):
            raise ComposeRuntimeError("restarted session lost its CSRF binding")
        headers = {"Origin": origin, "X-CSRF-Token": csrf}
        recovered = _request(opener, api + "/p5/studio/state")
        draft_states = {item["draft"]["state"] for item in recovered["drafts"]}
        if (
            recovered["active"] != before_restart["active"]
            or recovered["runtime_policy"]["budget_count"] != 1
            or recovered["runtime_policy"]["run_state"] != "stopped"
            or not recovered["runtime_policy"]["escalations"]
            or not {"confirmed", "stale"}.issubset(draft_states)
        ):
            raise ComposeRuntimeError(
                "P5 restart lost active, draft, counter, stop, or escalation state"
            )
        processed_queued = _request(
            opener,
            api + "/runtime/process",
            method="POST",
            headers=headers,
            payload={"idempotency_key": "compose-process-stopped-queued-wake"},
        )
        after_queued_stop = _wait_json(
            opener,
            api + "/p5/studio/state",
            predicate=lambda value: any(
                item.get("outcome") == "stopped"
                and item.get("stage") == "pre_wake"
                and item.get("policy_revision") == 2
                for item in value.get("runtime_policy", {}).get("outcomes", [])
            ),
        )
        stopped_outcomes = [
            item
            for item in after_queued_stop["runtime_policy"]["outcomes"]
            if item.get("outcome") == "stopped"
            and item.get("stage") == "pre_wake"
            and item.get("policy_revision") == 2
        ]
        if (
            processed_queued.get("decisions") not in {0, 1}
            or len(_request(opener, api + "/studio/state").get("proposals", []))
            != proposals_before_queued_stop
            or len(stopped_outcomes) != 1
        ):
            raise ComposeRuntimeError(
                "a restarted stopped queued wake was not retained as a governed proposal-free no-op"
            )
        queued_audit = _request(opener, api + f"/audit/{allowed['correlation_id']}")
        queued_types = {item["record_type"] for item in queued_audit["records"]}
        if "policy_outcome" not in queued_types or "effect_proposal" in queued_types:
            raise ComposeRuntimeError("stopped queued-wake causal history was incomplete")
        resume = _create_update_review(
            opener,
            api,
            headers,
            key="resume",
            display_name="Runtime Atlas P5.1",
            mission="Use the winning exact policy revision",
            wake_limit=2,
            policy_replacement={
                "wake_limit": 2,
                "run_state": "active",
                "explicit_resume": True,
            },
        )
        _request(
            opener,
            api + f"/colleagues/drafts/{resume['draft_id']}/confirm",
            method="POST",
            headers=headers,
            payload=_confirmation(resume, "resume"),
        )
        resumed = _request(opener, api + "/p5/studio/state")
        if (
            resumed["active"]["policy_revision"] != 3
            or resumed["runtime_policy"]["run_state"] != "active"
            or len(
                [
                    item
                    for item in resumed["runtime_policy"]["outcomes"]
                    if item.get("outcome") == "explicit_resume"
                    and item.get("stage") == "stop"
                    and item.get("policy_revision") == 3
                    and item.get("safe_projection", {}).get("previous_stop_reason")
                    == "budget_exhausted"
                ]
            )
            != 1
        ):
            raise ComposeRuntimeError("explicit revisioned resume did not apply")

        disallowed_policy = _create_update_review(
            opener,
            api,
            headers,
            key="control-disallowed",
            display_name="Runtime Atlas P5.1",
            mission="Use the winning exact policy revision",
            wake_limit=2,
            policy_changes={"allowed_triggers": ["timer"]},
        )
        _request(
            opener,
            api + f"/colleagues/drafts/{disallowed_policy['draft_id']}/confirm",
            method="POST",
            headers=headers,
            payload=_confirmation(disallowed_policy, "control-disallowed"),
        )
        disallowed = _request(
            opener,
            api + "/runtime/triggers",
            method="POST",
            headers=headers,
            payload={
                "work_id": work["work_id"],
                "trigger_class": "event",
                "deterministic_noop": False,
                "idempotency_key": "compose-disallowed",
            },
        )
        if disallowed.get("policy_outcome") != "disallowed_trigger":
            raise ComposeRuntimeError("disallowed trigger policy was not enforced")

        weekdays = (
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        )
        non_current_day = weekdays[(datetime.now(UTC).weekday() + 1) % 7]
        outside_policy = _create_update_review(
            opener,
            api,
            headers,
            key="control-outside",
            display_name="Runtime Atlas P5.1",
            mission="Use the winning exact policy revision",
            wake_limit=2,
            policy_changes={
                "weekly_windows": [
                    {"weekday": non_current_day, "start_minute": 0, "end_minute": 1440}
                ],
                "outside_hours": "defer",
            },
        )
        _request(
            opener,
            api + f"/colleagues/drafts/{outside_policy['draft_id']}/confirm",
            method="POST",
            headers=headers,
            payload=_confirmation(outside_policy, "control-outside"),
        )
        deferred = _request(
            opener,
            api + "/runtime/triggers",
            method="POST",
            headers=headers,
            payload={
                "work_id": work["work_id"],
                "trigger_class": "event",
                "deterministic_noop": False,
                "idempotency_key": "compose-outside",
            },
        )
        if deferred.get("policy_outcome") != "outside_hours_defer":
            raise ComposeRuntimeError("working-hours defer policy was not enforced")

        passive_policy = _create_update_review(
            opener,
            api,
            headers,
            key="control-proactivity",
            display_name="Runtime Atlas P5.1",
            mission="Use the winning exact policy revision",
            wake_limit=2,
            policy_changes={"proactivity": "disabled"},
        )
        _request(
            opener,
            api + f"/colleagues/drafts/{passive_policy['draft_id']}/confirm",
            method="POST",
            headers=headers,
            payload=_confirmation(passive_policy, "control-proactivity"),
        )
        passive = _request(
            opener,
            api + "/runtime/triggers",
            method="POST",
            headers=headers,
            payload={
                "work_id": work["work_id"],
                "trigger_class": "event",
                "deterministic_noop": False,
                "idempotency_key": "compose-proactivity",
            },
        )
        if passive.get("policy_outcome") != "proactivity_suppressed":
            raise ComposeRuntimeError("disabled proactivity policy was not enforced")

        interruption_policy = _create_update_review(
            opener,
            api,
            headers,
            key="control-interruption",
            display_name="Runtime Atlas P5.1",
            mission="Use the winning exact policy revision",
            wake_limit=2,
            policy_changes={"interruption": "never"},
        )
        _request(
            opener,
            api + f"/colleagues/drafts/{interruption_policy['draft_id']}/confirm",
            method="POST",
            headers=headers,
            payload=_confirmation(interruption_policy, "control-interruption"),
        )
        interrupted = _request(
            opener,
            api + "/runtime/triggers",
            method="POST",
            headers=headers,
            payload={
                "work_id": work["work_id"],
                "trigger_class": "event",
                "deterministic_noop": False,
                "idempotency_key": "compose-interruption",
            },
        )
        if interrupted.get("accepted") is not True:
            raise ComposeRuntimeError("interruption scenario did not enter the governed wake")
        _wait_json(
            opener,
            api + "/p5/studio/state",
            predicate=lambda value: any(
                item.get("outcome") == "interruption_suppressed"
                for item in value.get("runtime_policy", {}).get("outcomes", [])
            ),
        )

        dispatch_policy = _create_update_review(
            opener,
            api,
            headers,
            key="control-dispatch",
            display_name="Runtime Atlas P5.1",
            mission="Use the winning exact policy revision",
            wake_limit=2,
            policy_changes={"interruption": "allowed"},
        )
        dispatch_confirmation = _request(
            opener,
            api + f"/colleagues/drafts/{dispatch_policy['draft_id']}/confirm",
            method="POST",
            headers=headers,
            payload=_confirmation(dispatch_policy, "control-dispatch"),
        )
        active_policy_revision = dispatch_confirmation["confirmation"]["policy_revision"]
        dispatch_trigger = _request(
            opener,
            api + "/runtime/triggers",
            method="POST",
            headers=headers,
            payload={
                "work_id": work["work_id"],
                "trigger_class": "event",
                "deterministic_noop": False,
                "idempotency_key": "compose-dispatch",
            },
        )
        dispatch_state = _wait_json(
            opener,
            api + "/studio/state",
            predicate=lambda value: any(
                item.get("policy_revision") == active_policy_revision
                for item in value.get("proposals", [])
            ),
        )
        dispatch_proposal = next(
            item
            for item in dispatch_state["proposals"]
            if item["policy_revision"] == active_policy_revision
        )
        _request(
            opener,
            api + f"/proposals/{dispatch_proposal['proposal_id']}/decision",
            method="POST",
            headers=headers,
            payload={
                "proposal_revision": dispatch_proposal["revision"],
                "proposal_payload_digest": dispatch_proposal["payload_digest"],
                "proposal_digest": dispatch_proposal["proposal_digest"],
                "mandate_id": dispatch_proposal["mandate_id"],
                "mandate_revision": dispatch_proposal["mandate_revision"],
                "policy_id": dispatch_proposal["policy_id"],
                "policy_revision": dispatch_proposal["policy_revision"],
                "choice": "approve",
                "idempotency_key": "compose-dispatch-approval",
            },
        )
        dispatched_state = _wait_json(
            opener,
            api + "/studio/state",
            predicate=lambda value: any(
                item.get("correlation_id") == dispatch_trigger["correlation_id"]
                for item in value.get("results", [])
            ),
        )
        if not dispatched_state["results"]:
            raise ComposeRuntimeError("exact policy-bound dispatch did not finish")
        runtime_audit = _request(opener, api + f"/audit/{dispatch_trigger['correlation_id']}")
        runtime_types = {item["record_type"] for item in runtime_audit["records"]}
        expected_runtime_types = {
            "policy_outcome",
            "input_event",
            "wake_cycle",
            "decision",
            "effect_proposal",
            "human_approval",
            "effect_attempt",
            "action_result",
        }
        if not expected_runtime_types.issubset(runtime_types):
            raise ComposeRuntimeError("P5 runtime causal audit was incomplete")
        metric_readout = _request(opener, api + "/p5/evaluation/metrics")
        if (
            metric_readout.get("evidence_class") != "synthetic_offline"
            or metric_readout.get("policy_binding", {}).get("policy_revision")
            != active_policy_revision
        ):
            raise ComposeRuntimeError("P5 metric readout lacked exact active policy binding")
        final_policy_state = _request(opener, api + "/p5/studio/state")
        durable_outcomes = final_policy_state["runtime_policy"]["outcomes"]
        durable_refusals = [
            item
            for item in durable_outcomes
            if item.get("outcome") not in {"allowed", "explicit_resume"}
        ]
        refusal_readout = metric_readout.get("policy_refusals", {})
        expected_refusal_outcomes = {
            "budget_exhausted",
            "disallowed_trigger",
            "interruption_suppressed",
            "outside_hours_defer",
            "proactivity_suppressed",
            "stopped",
        }
        if (
            not any(item.get("outcome") == "explicit_resume" for item in durable_outcomes)
            or "explicit_resume" in refusal_readout.get("outcomes", [])
            or refusal_readout.get("count") != len(durable_refusals)
            or set(refusal_readout.get("outcomes", []))
            != {item.get("outcome") for item in durable_refusals}
            or not expected_refusal_outcomes.issubset(refusal_readout.get("outcomes", []))
        ):
            raise ComposeRuntimeError(
                "P5 metric readout misclassified durable refusals or explicit resume"
            )
        logs = _compose(
            docker,
            project,
            ["logs", "--no-color", "api", "worker", "studio"],
            root=root,
            environment=environment,
        )
        combined_logs = logs.stdout + logs.stderr
        if any(secret in combined_logs for secret in (token, session_credential, csrf)):
            raise ComposeRuntimeError("a plaintext credential appeared in service logs")
        _compose(
            docker,
            project,
            ["stop", "api", "worker", "studio"],
            root=root,
            environment=environment,
        )
        running = _compose(
            docker,
            project,
            ["ps", "--status", "running", "--quiet"],
            root=root,
            environment=environment,
        ).stdout.split()
        if running:
            raise ComposeRuntimeError("normal Compose stop left a service running")
        result = {
            "schema_version": 1,
            "gate": "p5_compose_runtime_clean",
            "status": "passed",
            "command": "python3 -B scripts/check_p5_compose_runtime.py .",
            "compose_project": project,
            "environment": {
                "api_host_port": api_port,
                "studio_host_port": studio_port,
                "published_bind": "127.0.0.1",
                "docker_server_version": server,
                "compose_version": compose_version,
                "host": platform.system().lower(),
            },
            "started_at": started_at,
            "fresh_containers_after_checkpoint": True,
            "draft_history_recovered": True,
            "policy_counter_recovered": True,
            "stale_draft_fault": "refused_409_and_persisted",
            "stale_proposal_fault": "refused_403_before_approval_dispatch",
            "budget_stop_escalation": "passed",
            "profile_only_stop_preservation_fault": "passed_without_policy_revision_or_resume",
            "queued_wake_after_stop_fault": "governed_noop_without_proposal_after_restart",
            "explicit_revisioned_resume": "passed",
            "typed_policy_controls": "working_hours_trigger_proactivity_interruption_passed",
            "policy_bound_dispatch": "passed",
            "safe_causal_audit": "passed",
            "explicit_defaults_visible": defaults_visible,
            "metric_readout": metric_readout,
            "credentials_absent_from_service_logs": True,
            "state_volume": "isolated_project_scoped_temporary_volume",
            "normal_stop": True,
            "evidence_class": "synthetic_offline",
        }
    finally:
        cleanup = _cleanup(docker, project, root=root, environment=environment)
    if not cleanup.get("passed"):
        raise ComposeRuntimeError("isolated P5 Compose cleanup was incomplete")
    if result is None:
        raise ComposeRuntimeError("the P5 Compose runtime result was not produced")
    result["ended_at"] = _now()
    result["cleanup"] = cleanup
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run actual P5 Compose runtime acceptance.")
    parser.add_argument("root", nargs="?", default=".")
    arguments = parser.parse_args(argv)
    try:
        result = check_compose_runtime(Path(arguments.root).resolve())
    except (OSError, ComposeRuntimeError) as exc:
        print(f"P5 Compose runtime check failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
