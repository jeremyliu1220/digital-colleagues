# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import time
import unittest
from collections import Counter
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from unittest import mock

from scripts.check_p12_historical_inventory import (
    ACCEPTED_GATE_IDS,
    CANONICAL_INVENTORY,
    EMBEDDED_DARWIN_ANCHORS,
    EXCLUDED_GATE_IDS,
    EXCLUDED_REASON_TOKENS,
    INCLUDED_GATE_IDS,
    ITEM_COUNTS,
    OBJECT_ORDER,
    OBJECT_RESULT_SCHEMA,
    OBJECT_TIMEOUTS,
    OPERATION_TIMEOUTS,
    HistoricalInventoryError,
    build_object_result,
    canonical_json,
    check_historical_inventory,
    excluded_platform_result,
    load_inventory,
    object_result_digest,
    validate_entrypoint_resolution,
    validate_inventory,
    validate_item_results,
    validate_object_result,
    validate_object_result_bytes,
    validate_predecessor_result,
)
from scripts.check_p12_repository import P12GateError
from scripts.run_p12_toolchain import (
    HISTORICAL_RESULT_MAX_BYTES,
    HistoricalTimeout,
    _bounded_result_bytes,
    _historical_process,
    _leaf_process,
    _operation_deadline,
    _remaining_timeout,
    _run_status,
    _structured_leaf_result,
    _structured_result_path,
    _verify_anchor,
    _verify_working_lock,
    run_ci,
)

ROOT = Path(__file__).resolve().parents[2]


def _copy() -> list[dict[str, Any]]:
    return list(deepcopy(CANONICAL_INVENTORY))


def _item(items: list[dict[str, Any]], gate_id: str) -> dict[str, Any]:
    return next(value for value in items if value["gate_id"] == gate_id)


def _passing_results() -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for item in CANONICAL_INVENTORY:
        item_type = item["item_type"]
        if item_type in {"setup", "included_acceptance_gate"}:
            result, exit_status = "passed", 0
        elif item_type == "evidence_anchor":
            result, exit_status = "identity_verified", None
        else:
            result, exit_status = "not_run_platform_excluded", None
        compact: dict[str, object] = {
            "exit_status": exit_status,
            "gate_id": item["gate_id"],
            "item_type": item_type,
            "result": result,
        }
        if item_type == "excluded_acceptance_gate":
            compact["embedded_anchor"] = deepcopy(item["embedded_anchor"])
            compact["platform_result"] = excluded_platform_result(item)
        results.append(compact)
    return results


def _inventory_digest() -> str:
    return f"sha256:{hashlib.sha256(canonical_json(CANONICAL_INVENTORY)).hexdigest()}"


def _passing_object_result(object_name: str) -> dict[str, object]:
    results = [
        result
        for item, result in zip(CANONICAL_INVENTORY, _passing_results(), strict=True)
        if item["object"] == object_name
    ]
    return build_object_result(
        object_name,
        inventory_digest=_inventory_digest(),
        ordered_item_results=results,
    )


class HistoricalInventoryTests(unittest.TestCase):
    def test_canonical_inventory_passes(self) -> None:
        self.assertEqual(load_inventory(ROOT), CANONICAL_INVENTORY)
        result = check_historical_inventory(ROOT)
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["total_item_count"], 151)
        self.assertRegex(str(result["inventory_sha256"]), r"^[0-9a-f]{64}$")

    def test_typed_counts_are_exact(self) -> None:
        counts = Counter(str(item["item_type"]) for item in CANONICAL_INVENTORY)
        self.assertEqual(counts["setup"], 5)
        self.assertEqual(counts["included_acceptance_gate"], 124)
        self.assertEqual(counts["evidence_anchor"], 17)
        self.assertEqual(counts["excluded_acceptance_gate"], 5)
        self.assertEqual(sum(counts.values()), ITEM_COUNTS["total"])

    def test_exact_five_platform_exclusions(self) -> None:
        excluded = [
            item for item in CANONICAL_INVENTORY if item["item_type"] == "excluded_acceptance_gate"
        ]
        self.assertEqual([item["gate_id"] for item in excluded], list(EXCLUDED_GATE_IDS))
        self.assertEqual(
            [i for i, item in enumerate(CANONICAL_INVENTORY, 1) if item in excluded],
            [64, 65, 101, 102, 103],
        )
        for item in excluded:
            with self.subTest(gate_id=item["gate_id"]):
                platform_result = excluded_platform_result(item)
                self.assertEqual(platform_result["replay_platform"], "ubuntu-24.04")
                self.assertEqual(
                    platform_result["ubuntu_historical_execution_status"], "not_proven"
                )
                self.assertEqual(platform_result["linux_public_pilot_readiness"], "blocked")
                self.assertEqual(platform_result["reason"], EXCLUDED_REASON_TOKENS[item["gate_id"]])

    def test_gate_set_difference_is_exact(self) -> None:
        difference = set(ACCEPTED_GATE_IDS) - set(INCLUDED_GATE_IDS)
        self.assertEqual(len(ACCEPTED_GATE_IDS), 129)
        self.assertEqual(len(set(ACCEPTED_GATE_IDS)), 129)
        self.assertEqual(len(INCLUDED_GATE_IDS), 124)
        self.assertEqual(difference, set(EXCLUDED_GATE_IDS))
        self.assertEqual(
            tuple(gate_id for gate_id in EXCLUDED_GATE_IDS if gate_id in difference),
            EXCLUDED_GATE_IDS,
        )

    def test_p8_bootstrap_is_setup_only(self) -> None:
        gate_ids = {str(item["gate_id"]) for item in CANONICAL_INVENTORY}
        self.assertNotIn("p8_bootstrap", gate_ids)
        setup = next(item for item in CANONICAL_INVENTORY if item["gate_id"] == "p8_setup")
        self.assertEqual(setup["item_type"], "setup")
        self.assertNotIn("p8_setup", ACCEPTED_GATE_IDS)

    def test_anchors_are_not_gate_results(self) -> None:
        anchors = [item for item in CANONICAL_INVENTORY if item["item_type"] == "evidence_anchor"]
        self.assertEqual(len(anchors), 17)
        self.assertTrue(all(item["command_kind"] == "identity_check" for item in anchors))
        self.assertTrue(all(item["expected"]["status"] == "identity_verified" for item in anchors))
        self.assertFalse({str(item["gate_id"]) for item in anchors} & set(ACCEPTED_GATE_IDS))
        _verify_anchor(ROOT, _item(_copy(), "p8_summary_anchor"))

    def test_per_object_resource_limits(self) -> None:
        setups = [item for item in CANONICAL_INVENTORY if item["item_type"] == "setup"]
        self.assertEqual([item["object"] for item in setups], list(OBJECT_ORDER))
        for item in setups:
            resources = item["resources"]
            self.assertEqual(resources["checkout_count"], 1)
            self.assertEqual(resources["python_environment_count"], 1)
            expected_locks = [f"{str(item['object']).lower()}_python_lock_anchor"]
            if item["object"] != "P9":
                expected_locks.append(f"{str(item['object']).lower()}_npm_lock_anchor")
            self.assertEqual(resources["lock_anchor_ids"], expected_locks)
            self.assertEqual(resources["object_timeout_seconds"], OBJECT_TIMEOUTS[item["object"]])
            self.assertEqual(resources["checkout_timeout_seconds"], 120)
            self.assertEqual(resources["venv_install_timeout_seconds"], 600)
            self.assertEqual(resources["npm_install_timeout_seconds"], 600)
        self.assertEqual(OPERATION_TIMEOUTS["executor"], 9900)
        for object_name in OBJECT_ORDER:
            with self.subTest(object_result=object_name):
                result = _passing_object_result(object_name)
                self.assertEqual(result["schema"], OBJECT_RESULT_SCHEMA)
                self.assertEqual(result["cleanup_residue_count"], 0)
                self.assertEqual(result["status"], "passed")
                digest = object_result_digest(result)
                self.assertRegex(digest, r"^sha256:[0-9a-f]{64}$")
                validated = validate_object_result(
                    result,
                    expected_object=object_name,
                    expected_inventory_digest=_inventory_digest(),
                    expected_digest=digest,
                    require_passed=True,
                )
                self.assertEqual(validated["status"], "passed")

        python_lock = _item(_copy(), "p8_python_lock_anchor")
        npm_lock = _item(_copy(), "p8_npm_lock_anchor")
        with TemporaryDirectory() as value:
            checkout = Path(value) / "checkout"
            git_environment = os.environ.copy()
            git_environment["GIT_NO_REPLACE_OBJECTS"] = "1"
            subprocess.run(
                [
                    "git",
                    "clone",
                    "--quiet",
                    "--shared",
                    "--no-checkout",
                    str(ROOT),
                    str(checkout),
                ],
                check=True,
                env=git_environment,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=30,
            )
            subprocess.run(
                ["git", "checkout", "--quiet", "--detach", str(python_lock["commit"])],
                check=True,
                cwd=checkout,
                env=git_environment,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=30,
            )
            for lock in (python_lock, npm_lock):
                _verify_working_lock(
                    checkout,
                    lock,
                    deadline=time.monotonic() + 30,
                    cleanup_deadline=time.monotonic() + 35,
                )

            lock_path = checkout / str(python_lock["expected"]["path"])
            original = lock_path.read_bytes()
            lock_path.write_bytes(original + b"\n")
            with self.assertRaises(P12GateError):
                _verify_working_lock(
                    checkout,
                    python_lock,
                    deadline=time.monotonic() + 30,
                    cleanup_deadline=time.monotonic() + 35,
                )
            lock_path.write_bytes(original)
            lock_path.chmod(0o755)
            with self.assertRaises(P12GateError):
                _verify_working_lock(
                    checkout,
                    python_lock,
                    deadline=time.monotonic() + 30,
                    cleanup_deadline=time.monotonic() + 35,
                )
            lock_path.unlink()
            lock_path.symlink_to(checkout / "pyproject.toml")
            with self.assertRaises(P12GateError):
                _verify_working_lock(
                    checkout,
                    python_lock,
                    deadline=time.monotonic() + 30,
                    cleanup_deadline=time.monotonic() + 35,
                )

    def test_cross_object_state_is_rejected(self) -> None:
        items = _copy()
        _item(items, "p9_repository")["resource_scope"] = "p8"
        with self.assertRaises(HistoricalInventoryError):
            validate_inventory(items, require_literal=False)

    def test_historical_subprocess_is_required(self) -> None:
        items = _copy()
        _item(items, "p10_repository")["command_kind"] = "in_process_import"
        with self.assertRaises(HistoricalInventoryError):
            validate_inventory(items, require_literal=False)

    def test_current_tree_module_shadowing_is_rejected(self) -> None:
        item = next(value for value in CANONICAL_INVENTORY if value["gate_id"] == "p8_repository")
        entrypoint = item["entrypoint"]
        with TemporaryDirectory() as temporary:
            checkout = Path(temporary) / "checkout"
            shadow = ROOT / str(entrypoint["path"])
            with self.assertRaises(HistoricalInventoryError):
                validate_entrypoint_resolution(
                    item,
                    checkout_root=checkout,
                    resolved_path=shadow,
                    resolved_blob=str(entrypoint["blob"]),
                )

    def test_module_blob_mismatch_is_rejected(self) -> None:
        item = next(
            value for value in CANONICAL_INVENTORY if value["gate_id"] == "p11_architecture"
        )
        entrypoint = item["entrypoint"]
        with TemporaryDirectory() as temporary:
            checkout = Path(temporary) / "checkout"
            resolved = checkout / str(entrypoint["path"])
            with self.assertRaises(HistoricalInventoryError):
                validate_entrypoint_resolution(
                    item,
                    checkout_root=checkout,
                    resolved_path=resolved,
                    resolved_blob="0" * 40,
                )

    def test_leaf_results_remain_individual(self) -> None:
        results = _passing_results()
        summary = validate_item_results(CANONICAL_INVENTORY, results)
        self.assertEqual(summary["item_result_count"], 151)
        self.assertEqual(summary["status"], "passed")
        with self.assertRaises(HistoricalInventoryError):
            validate_item_results(CANONICAL_INVENTORY, results[:-1])
        excluded_index = next(
            index
            for index, item in enumerate(CANONICAL_INVENTORY)
            if item["gate_id"] == "p10_quickstart"
        )
        for field in ("platform_result", "embedded_anchor"):
            with self.subTest(missing_excluded_field=field):
                malformed = deepcopy(results)
                del malformed[excluded_index][field]
                with self.assertRaises(HistoricalInventoryError):
                    validate_item_results(CANONICAL_INVENTORY, malformed)
        p10_result = _passing_object_result("P10")
        reordered = deepcopy(p10_result)
        ordered = reordered["ordered_item_results"]
        assert isinstance(ordered, list)
        ordered[0], ordered[1] = ordered[1], ordered[0]
        with self.assertRaises(HistoricalInventoryError):
            validate_object_result(
                reordered,
                expected_object="P10",
                expected_inventory_digest=_inventory_digest(),
            )

    def test_recursive_aggregate_is_rejected(self) -> None:
        items = _copy()
        _item(items, "p11r_architecture")["command"] = "make p11r-check"
        with self.assertRaises(HistoricalInventoryError):
            validate_inventory(items, require_literal=False)
        p8_result = _passing_object_result("P8")
        raw = canonical_json(p8_result)
        digest = object_result_digest(p8_result)
        parsed = validate_predecessor_result(
            "P9",
            object_result_bytes=raw,
            object_result_digest_value=digest,
            inventory_digest=_inventory_digest(),
        )
        self.assertEqual(parsed, p8_result)
        for current_object, bad_digest in (
            ("P8", digest),
            ("P9", "sha256:" + "0" * 64),
        ):
            with self.subTest(current_object=current_object):
                with self.assertRaises(HistoricalInventoryError):
                    validate_predecessor_result(
                        current_object,
                        object_result_bytes=raw,
                        object_result_digest_value=bad_digest,
                        inventory_digest=_inventory_digest(),
                    )
        with self.assertRaises(HistoricalInventoryError):
            validate_object_result_bytes(
                raw + b"\n",
                expected_object="P8",
                expected_inventory_digest=_inventory_digest(),
                expected_digest=digest,
                require_passed=True,
            )

    def test_object_cleanup_precedes_next_setup(self) -> None:
        items = _copy()
        _item(items, "p8_setup")["resources"]["cleanup_before_next_object"] = False
        with self.assertRaises(HistoricalInventoryError):
            validate_inventory(items, require_literal=False)

    def test_timeout_values_are_exact(self) -> None:
        items = _copy()
        _item(items, "p10_remote_distribution")["timeout_seconds"] = 1199
        with self.assertRaises(HistoricalInventoryError):
            validate_inventory(items)
        self.assertEqual(
            OBJECT_TIMEOUTS, {"P8": 2700, "P9": 900, "P10": 3000, "P11": 1800, "P11R": 1500}
        )
        with mock.patch("scripts.run_p12_toolchain.time.monotonic", return_value=100.0):
            self.assertEqual(
                _operation_deadline(500.0, 120, label="test operation"),
                220.0,
            )
            self.assertEqual(
                _remaining_timeout(250.0, 300, label="test operation"),
                150.0,
            )
            with self.assertRaises(HistoricalTimeout):
                _operation_deadline(100.0, 120, label="expired operation")
            with mock.patch(
                "scripts.run_p12_toolchain._leaf_process",
                return_value=(0, b"bounded"),
            ) as process:
                self.assertEqual(
                    _historical_process(
                        ["synthetic"],
                        cwd=ROOT,
                        environment=None,
                        deadline=220.0,
                        cleanup_deadline=500.0,
                        limit=120,
                        label="test operation",
                    ),
                    b"bounded",
                )
                self.assertEqual(process.call_args.kwargs["timeout"], 120.0)
                self.assertEqual(process.call_args.kwargs["cleanup_deadline"], 500.0)
            with self.assertRaises(P12GateError):
                _historical_process(
                    ["synthetic"],
                    cwd=ROOT,
                    environment=None,
                    deadline=220.0,
                    cleanup_deadline=219.0,
                    limit=120,
                    label="invalid cleanup deadline",
                )
        status, _ = _leaf_process(
            [sys.executable, "-c", "import time; time.sleep(60)"],
            cwd=ROOT,
            environment=os.environ.copy(),
            timeout=0.01,
            cleanup_deadline=time.monotonic() + 2.0,
        )
        self.assertEqual(status, 124)
        with TemporaryDirectory() as value:
            descendant_pid = Path(value) / "descendant.pid"
            status = _run_status(
                [
                    sys.executable,
                    "-c",
                    (
                        "import pathlib,subprocess,sys,time;"
                        "child=subprocess.Popen([sys.executable,'-c',"
                        "'import time;time.sleep(60)']);"
                        "pathlib.Path(sys.argv[1]).write_text(str(child.pid));"
                        "time.sleep(60)"
                    ),
                    str(descendant_pid),
                ],
                cwd=ROOT,
                timeout=1,
            )
            self.assertEqual(status, 124)
            self.assertTrue(descendant_pid.is_file())
            with self.assertRaises(ProcessLookupError):
                os.kill(int(descendant_pid.read_text(encoding="utf-8")), 0)
        with TemporaryDirectory() as value:
            output = Path(value) / "output"
            output.mkdir()
            result_path = output / "failed-unittest.json"
            item = {
                "command": "python tests --json-output <p8-temp>/failed-unittest.json",
                "expected": {"test_count": 7},
            }
            self.assertEqual(
                _structured_result_path(
                    item,
                    command_text=f"python tests --json-output {result_path}",
                    output_directory=output,
                ),
                result_path,
            )
            with self.assertRaises(P12GateError):
                _structured_result_path(
                    item,
                    command_text=(f"python tests --json-output {output / '..' / 'escaped.json'}"),
                    output_directory=output,
                )
            result_path.write_text(
                json.dumps(
                    {
                        "tests_run": 7,
                        "failures": 1,
                        "errors": 0,
                        "skipped": 0,
                        "gate_passed": False,
                    }
                ),
                encoding="utf-8",
            )
            structured = _structured_leaf_result(
                item,
                result_path,
                process_status=1,
                deadline=time.monotonic() + 5,
            )
            self.assertEqual(
                structured,
                {"tests_run": 7, "failures": 1, "errors": 0, "skipped": 0},
            )
            for invalid_gate_passed in (None, "false", 0):
                result_path.write_text(
                    json.dumps(
                        {
                            "tests_run": 7,
                            "failures": 1,
                            "errors": 0,
                            "skipped": 0,
                            "gate_passed": invalid_gate_passed,
                        }
                    ),
                    encoding="utf-8",
                )
                with self.subTest(gate_passed=invalid_gate_passed), self.assertRaises(P12GateError):
                    _structured_leaf_result(
                        item,
                        result_path,
                        process_status=1,
                        deadline=time.monotonic() + 5,
                    )
            regular_result = output / "regular.json"
            regular_result.write_text("{}", encoding="utf-8")
            symlink_result = output / "symlink.json"
            symlink_result.symlink_to(regular_result)
            with self.assertRaises(P12GateError):
                _bounded_result_bytes(symlink_result, deadline=time.monotonic() + 5)
            fifo_result = output / "fifo.json"
            os.mkfifo(fifo_result)
            with self.assertRaises(P12GateError):
                _bounded_result_bytes(fifo_result, deadline=time.monotonic() + 5)
            oversized_result = output / "oversized.json"
            with oversized_result.open("wb") as stream:
                stream.truncate(HISTORICAL_RESULT_MAX_BYTES + 1)
            with self.assertRaises(P12GateError):
                _bounded_result_bytes(oversized_result, deadline=time.monotonic() + 5)
        with (
            mock.patch(
                "scripts.run_p12_toolchain.run_current_ci",
                return_value={"mode": "ci", "status": "passed"},
            ),
            mock.patch(
                "scripts.run_p12_toolchain.run_portable_history",
                return_value={"status": "failed"},
            ),
        ):
            self.assertEqual(run_ci(ROOT, ROOT)["status"], "failed")

    def test_missing_gate_fails_closed(self) -> None:
        items = _copy()
        items.remove(_item(items, "p8_backup_restore"))
        with self.assertRaises(HistoricalInventoryError):
            validate_inventory(items, require_literal=False)

    def test_extra_exclusion_fails_closed(self) -> None:
        items = _copy()
        _item(items, "p8_backup_restore")["item_type"] = "excluded_acceptance_gate"
        with self.assertRaises(HistoricalInventoryError):
            validate_inventory(items, require_literal=False)

    def test_dynamic_membership_fails_closed(self) -> None:
        items = _copy()
        _item(items, "p9_repository")["gate_id"] = "p9_*"
        with self.assertRaises(HistoricalInventoryError):
            validate_inventory(items, require_literal=False)

    def test_entrypoint_identity_is_exact(self) -> None:
        gates = [
            item
            for item in CANONICAL_INVENTORY
            if item["item_type"] in {"included_acceptance_gate", "excluded_acceptance_gate"}
        ]
        self.assertEqual(len(gates), 129)
        self.assertEqual(sum(item["entrypoint"] is None for item in gates), 19)
        self.assertEqual(sum(item["entrypoint"] is not None for item in gates), 110)
        self.assertEqual(sum(item["entrypoint"] is None for item in CANONICAL_INVENTORY), 41)
        self.assertEqual(
            Counter(str(item["command_kind"]) for item in gates),
            Counter(
                {
                    "git": 3,
                    "npm_script": 20,
                    "predecessor_result": 4,
                    "python_function": 1,
                    "python_module": 12,
                    "python_script": 89,
                }
            ),
        )
        python_paths = {
            (str(item["object"]), str(item["entrypoint"]["path"]))
            for item in CANONICAL_INVENTORY
            if item["command_kind"] == "python_script"
        }
        function_units = [
            item for item in CANONICAL_INVENTORY if item["command_kind"] == "python_function"
        ]
        self.assertEqual(len(python_paths), 86)
        self.assertEqual([item["gate_id"] for item in function_units], ["p11_candidate_diff"])
        self.assertTrue(
            all(
                re.fullmatch(r"[0-9a-f]{40}", str(item["entrypoint"]["blob"]))
                for item in CANONICAL_INVENTORY
                if item["entrypoint"] is not None
            )
        )

    def test_five_embedded_darwin_anchors_are_platform_scoped(self) -> None:
        excluded = [
            item for item in CANONICAL_INVENTORY if item["item_type"] == "excluded_acceptance_gate"
        ]
        self.assertEqual(len(excluded), 5)
        self.assertEqual(len(EMBEDDED_DARWIN_ANCHORS), 5)
        for item in excluded:
            gate_id = str(item["gate_id"])
            with self.subTest(gate_id=gate_id):
                anchor = item["embedded_anchor"]
                self.assertEqual(anchor, EMBEDDED_DARWIN_ANCHORS[gate_id])
                self.assertEqual(anchor["anchor_platform"], "darwin")
                self.assertEqual(anchor["anchor_historical_status"], "passed")
                self.assertEqual(anchor["purpose"], "immutable_platform_scoped_identity_only")
                self.assertEqual(anchor["canonicalization"], "P12-CJ-1")
                self.assertRegex(str(anchor["canonical_sha256"]), r"^[0-9a-f]{64}$")
        p8_anchor = _item(_copy(), "p8_summary_anchor")
        self.assertEqual(p8_anchor["platform_scope"], "darwin_historical_evidence_identity")

    def test_linux_claim_laundering_fails_closed(self) -> None:
        for gate_id in EXCLUDED_GATE_IDS:
            with self.subTest(gate_id=gate_id):
                items = _copy()
                excluded = _item(items, gate_id)
                excluded["expected"]["ubuntu_historical_execution_status"] = "passed"
                with self.assertRaises(HistoricalInventoryError):
                    validate_inventory(items, require_literal=False)

    def test_zero_residue_is_required(self) -> None:
        items = _copy()
        setup = _item(items, "p11_setup")
        setup["resources"]["cleanup_residue_count"] = 1
        with self.assertRaises(HistoricalInventoryError):
            validate_inventory(items, require_literal=False)
        result = _passing_object_result("P11")
        result["cleanup_residue_count"] = 1
        with self.assertRaises(HistoricalInventoryError):
            validate_object_result(
                result,
                expected_object="P11",
                expected_inventory_digest=_inventory_digest(),
            )


if __name__ == "__main__":
    unittest.main()
