# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import io
import json
import stat
import unittest
import zipfile

from digital_colleagues.adapters.package.archive import validate_package_archive
from digital_colleagues.application.errors import ValidationError
from tests.p11.fixtures import digest, package_archive, valid_package


class ArchiveTests(unittest.TestCase):
    def test_exact_canonical_archive_is_valid(self) -> None:
        archive = package_archive()
        result = validate_package_archive(archive, expected_archive_digest=digest(archive))
        self.assertEqual(result.package.package_id, "fixture-agent")

    def test_wrong_expected_digest_fails_closed(self) -> None:
        with self.assertRaises(ValidationError):
            validate_package_archive(
                package_archive(), expected_archive_digest="sha256:" + "0" * 64
            )

    def test_traversal_member_fails_closed(self) -> None:
        with self.assertRaises(ValidationError):
            validate_package_archive(package_archive(member="../agent.json"))

    def test_absolute_and_backslash_paths_fail_closed(self) -> None:
        for member in ("/agent.json", "nested\\agent.json"):
            with self.subTest(member=member), self.assertRaises(ValidationError):
                validate_package_archive(package_archive(member=member))

    def test_deep_nesting_fails_closed(self) -> None:
        with self.assertRaises(ValidationError):
            validate_package_archive(package_archive(member="one/two/agent.json"))

    def test_additional_payload_fails_closed(self) -> None:
        with self.assertRaises(ValidationError):
            validate_package_archive(package_archive(extras=(("run.sh", b"exit 0"),)))

    def test_symlink_member_fails_closed(self) -> None:
        output = io.BytesIO()
        info = zipfile.ZipInfo("agent.json")
        info.create_system = 3
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        with zipfile.ZipFile(output, "w") as archive:
            archive.writestr(info, b"target")
        with self.assertRaises(ValidationError):
            validate_package_archive(output.getvalue())

    def test_fifo_and_device_members_fail_closed(self) -> None:
        for file_type in (stat.S_IFIFO, stat.S_IFCHR):
            output = io.BytesIO()
            info = zipfile.ZipInfo("agent.json")
            info.create_system = 3
            info.external_attr = (file_type | 0o600) << 16
            with zipfile.ZipFile(output, "w") as archive:
                archive.writestr(info, b"payload")
            with self.subTest(file_type=file_type), self.assertRaises(ValidationError):
                validate_package_archive(output.getvalue())

    def test_case_colliding_member_fails_closed(self) -> None:
        with self.assertRaises(ValidationError):
            validate_package_archive(package_archive(extras=(("Agent.JSON", b"{}"),)))

    def test_archive_bomb_ratio_fails_closed(self) -> None:
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("agent.json", b"0" * 100_000)
        with self.assertRaises(ValidationError):
            validate_package_archive(output.getvalue())

    def test_member_count_bound_is_enforced_before_payload_use(self) -> None:
        extras = tuple((f"payload-{index}.bin", b"x") for index in range(4))
        with self.assertRaises(ValidationError):
            validate_package_archive(package_archive(extras=extras))

    def test_member_comment_fails_closed(self) -> None:
        output = io.BytesIO()
        info = zipfile.ZipInfo("agent.json")
        info.comment = b"hidden"
        with zipfile.ZipFile(output, "w") as archive:
            archive.writestr(info, b"{}")
        with self.assertRaises(ValidationError):
            validate_package_archive(output.getvalue())

    def test_duplicate_json_key_fails_closed(self) -> None:
        encoded = json.dumps(valid_package(), separators=(",", ":"), sort_keys=True).encode()
        duplicate = encoded[:-1] + b',"schema":"dc-agent/v1"}'
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w") as archive:
            archive.writestr("agent.json", duplicate)
        with self.assertRaises(ValidationError):
            validate_package_archive(output.getvalue())

    def test_archive_comment_fails_closed(self) -> None:
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w") as archive:
            archive.comment = b"hidden"
            archive.writestr("agent.json", b"{}")
        with self.assertRaises(ValidationError):
            validate_package_archive(output.getvalue())

    def test_noncanonical_json_fails_closed(self) -> None:
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w") as archive:
            archive.writestr("agent.json", json.dumps(valid_package(), indent=2).encode())
        with self.assertRaises(ValidationError):
            validate_package_archive(output.getvalue())


if __name__ == "__main__":
    unittest.main()
