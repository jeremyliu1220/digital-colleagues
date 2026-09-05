# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from digital_colleagues.adapters.channel.reference import ReferenceChannel
from digital_colleagues.adapters.http_json.channel import HttpJsonChannel
from digital_colleagues.adapters.http_json.configuration import (
    AdapterMode,
    HttpJsonSettings,
    load_adapter_selection,
)
from digital_colleagues.adapters.http_json.errors import AdapterFailure
from digital_colleagues.adapters.http_json.model import HttpJsonIntelligence
from digital_colleagues.adapters.intelligence.deterministic import DeterministicIntelligence
from digital_colleagues.adapters.sqlite.p6_store import SQLiteP6Store
from digital_colleagues.local.p7_adapters import build_selected_adapters
from digital_colleagues.local.runtime import build_local_runtime
from tests.p7.fixtures import credential_file, environment, settings


class P7ConfigurationTests(unittest.TestCase):
    def test_default_selection_is_deterministic_and_network_free(self) -> None:
        selection = load_adapter_selection({})
        self.assertEqual(selection.model_mode, AdapterMode.DETERMINISTIC)
        self.assertEqual(selection.channel_mode, AdapterMode.REFERENCE)
        intelligence, channel, composed = build_selected_adapters({})
        self.assertIsInstance(intelligence, DeterministicIntelligence)
        self.assertIsInstance(channel, ReferenceChannel)
        self.assertEqual(selection, composed)

    def test_explicit_loopback_selection_constructs_both_optional_adapters(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p7-config-") as temporary:
            credential = credential_file(Path(temporary))
            values = environment("http://127.0.0.1:47111/v1/adapter", credential)
            intelligence, channel, selection = build_selected_adapters(values)
            self.assertIsInstance(intelligence, HttpJsonIntelligence)
            self.assertIsInstance(channel, HttpJsonChannel)
            self.assertEqual(selection.model_mode, AdapterMode.HTTP_JSON_V1)
            self.assertNotIn(str(credential), repr(selection))
            self.assertNotIn("127.0.0.1", repr(selection))

    def test_unknown_modes_missing_fields_and_stray_network_settings_fail_closed(self) -> None:
        cases = (
            {"DC_MODEL_ADAPTER": "import.module.Class"},
            {"DC_CHANNEL_ADAPTER": "email"},
            {"DC_MODEL_ADAPTER": "http_json_v1"},
            {"DC_MODEL_ENDPOINT": "https://example.invalid/v1"},
            {"DC_P7_ALLOW_LOOPBACK_HTTP": "1"},
            {"DC_P7_UNRECOGNIZED": "1"},
        )
        for values in cases:
            with self.subTest(values=sorted(values)), self.assertRaises(AdapterFailure):
                load_adapter_selection(values)

    def test_url_userinfo_query_fragment_scheme_and_non_loopback_http_are_refused(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p7-url-") as temporary:
            credential = credential_file(Path(temporary))
            values = (
                "http://name:secret@127.0.0.1:8000/v1",
                "http://127.0.0.1:8000/v1?credential=value",
                "http://127.0.0.1:8000/v1#fragment",
                "file:///tmp/socket",
                "http://localhost:8000/v1",
                "http://192.0.2.1:8000/v1",
            )
            for endpoint in values:
                with self.subTest(endpoint=endpoint), self.assertRaises(AdapterFailure):
                    settings(endpoint, credential)

    def test_https_is_required_outside_explicit_loopback_tests(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p7-https-") as temporary:
            credential = credential_file(Path(temporary))
            accepted = HttpJsonSettings(
                endpoint="https://provider.invalid:443/v1/adapter",
                credential_file=credential,
                protocol_version="dc-http-json-v1",
                connect_timeout_seconds=1,
                read_timeout_seconds=2,
                total_timeout_seconds=3,
                maximum_request_bytes=4096,
                maximum_response_bytes=4096,
                maximum_pre_submit_retries=0,
            )
            self.assertEqual(accepted.parsed_endpoint.scheme, "https")
            with self.assertRaises(AdapterFailure):
                HttpJsonSettings(
                    endpoint="http://127.0.0.1:8000/v1/adapter",
                    credential_file=credential,
                    protocol_version="dc-http-json-v1",
                    connect_timeout_seconds=1,
                    read_timeout_seconds=2,
                    total_timeout_seconds=3,
                    maximum_request_bytes=4096,
                    maximum_response_bytes=4096,
                    maximum_pre_submit_retries=0,
                )

    def test_credential_must_be_regular_bounded_non_writable_file(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p7-secret-") as temporary:
            root = Path(temporary)
            writable = root / "writable"
            writable.write_text("synthetic", encoding="utf-8")
            writable.chmod(0o600)
            with self.assertRaises(AdapterFailure):
                settings("http://127.0.0.1:8000/v1", writable)
            target = credential_file(root)
            link = root / "link"
            link.symlink_to(target)
            with self.assertRaises(AdapterFailure):
                settings("http://127.0.0.1:8000/v1", link)
            target.chmod(0o600)
            configured = settings("http://127.0.0.1:8000/v1", credential_file(root))
            configured.credential_file.chmod(0o600)
            with self.assertRaises(AdapterFailure):
                configured.read_credential()

    def test_protocol_timeout_size_and_retry_bounds_are_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p7-bounds-") as temporary:
            credential = credential_file(Path(temporary))
            base = environment("http://127.0.0.1:8000/v1", credential)
            mutations = {
                "protocol": ("DC_MODEL_PROTOCOL", "v2"),
                "timeout": ("DC_P7_CONNECT_TIMEOUT_SECONDS", "0"),
                "total": ("DC_P7_TOTAL_TIMEOUT_SECONDS", "0.5"),
                "request": ("DC_P7_MAX_REQUEST_BYTES", "1"),
                "response": ("DC_P7_MAX_RESPONSE_BYTES", "2000000"),
                "retry": ("DC_P7_MAX_PRE_SUBMIT_RETRIES", "2"),
                "loopback": ("DC_P7_ALLOW_LOOPBACK_HTTP", "yes"),
            }
            for label, (key, value) in mutations.items():
                candidate = {**base, key: value}
                with self.subTest(label=label), self.assertRaises(AdapterFailure):
                    load_adapter_selection(candidate)

    def test_unused_adapter_settings_are_rejected_with_one_optional_adapter(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p7-unused-") as temporary:
            credential = credential_file(Path(temporary))
            base = environment("http://127.0.0.1:8000/v1", credential)
            model_only = {**base, "DC_CHANNEL_ADAPTER": "reference"}
            channel_only = {**base, "DC_MODEL_ADAPTER": "deterministic"}
            with self.assertRaises(AdapterFailure):
                load_adapter_selection(model_only)
            with self.assertRaises(AdapterFailure):
                load_adapter_selection(channel_only)

    def test_malformed_credential_fails_before_state_or_service_construction(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p7-early-") as temporary:
            root = Path(temporary)
            credential = root / "credential"
            credential.write_bytes(b"invalid\x00credential")
            credential.chmod(0o400)
            state = root / "state"
            values = environment("http://127.0.0.1:47111/v1/adapter", credential)
            with (
                patch(
                    "digital_colleagues.local.runtime.P6AuthenticationService"
                ) as service_constructor,
                self.assertRaises(AdapterFailure),
            ):
                build_local_runtime(state, adapter_environment=values)
            self.assertFalse(state.exists())
            service_constructor.assert_not_called()

    def test_later_service_construction_failure_closes_sqlite(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digital-colleagues-p7-close-") as temporary:
            state = Path(temporary) / "state"
            original_close = SQLiteP6Store.close
            with (
                patch(
                    "digital_colleagues.local.runtime.P6AuthenticationService",
                    side_effect=RuntimeError("synthetic construction failure"),
                ),
                patch.object(
                    SQLiteP6Store,
                    "close",
                    autospec=True,
                    side_effect=original_close,
                ) as close,
                self.assertRaisesRegex(RuntimeError, "synthetic construction failure"),
            ):
                build_local_runtime(state)
            close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
