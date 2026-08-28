# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import dataclasses
import unittest
from datetime import datetime, timedelta, timezone

from digital_colleagues.core import (
    FrozenJsonObject,
    HumanRole,
    Namespace,
    NamespaceScope,
    Principal,
    PrincipalKind,
    datetime_from_z,
    datetime_to_z,
    to_canonical_json,
)
from digital_colleagues.core.errors import CoreInvariantError, NamespaceMismatchError
from tests.core.fixtures import T0, colleague_namespace, human_admin


class CommonAndPrincipalTests(unittest.TestCase):
    def test_nested_json_is_copied_and_deeply_immutable(self) -> None:
        mutable_values: list[object] = ["first", {"inner": [1, 2]}]
        source: dict[str, object] = {"items": mutable_values}

        frozen = FrozenJsonObject.from_mapping(source)
        mutable_values.append("later")
        nested = mutable_values[1]
        self.assertIsInstance(nested, dict)
        if isinstance(nested, dict):
            inner = nested["inner"]
            self.assertIsInstance(inner, list)
            if isinstance(inner, list):
                inner.append(3)

        self.assertEqual(
            to_canonical_json(frozen),
            '{"items":["first",{"inner":[1,2]}]}',
        )
        with self.assertRaises(TypeError):
            frozen["items"] = ()  # type: ignore[index]

    def test_frozen_dataclass_rejects_attribute_mutation(self) -> None:
        namespace = colleague_namespace()
        with self.assertRaises(dataclasses.FrozenInstanceError):
            namespace.tenant_id = "tenant-beta"  # type: ignore[misc]

    def test_mutable_set_cannot_enter_an_immutable_json_contract(self) -> None:
        with self.assertRaises(CoreInvariantError):
            FrozenJsonObject.from_mapping({"values": {"one", "two"}})

    def test_direct_json_constructor_also_deep_freezes_nested_lists(self) -> None:
        mutable = ["one"]
        frozen = FrozenJsonObject((("values", mutable),))
        mutable.append("two")
        self.assertEqual(to_canonical_json(frozen), '{"values":["one"]}')

    def test_dataclass_equality_and_serialization_are_deterministic(self) -> None:
        left = FrozenJsonObject.from_mapping({"second": [2, 3], "first": 1})
        right = FrozenJsonObject.from_mapping({"first": 1, "second": [2, 3]})
        self.assertEqual(left, right)
        self.assertEqual(to_canonical_json(left), to_canonical_json(right))

    def test_namespace_scope_is_explicit_and_exact(self) -> None:
        colleague = Namespace.colleague("tenant-alpha", "colleague-alpha")
        principal = Namespace.principal("tenant-alpha", "principal-alpha")
        self.assertEqual(colleague.scope, NamespaceScope.COLLEAGUE)
        self.assertEqual(principal.scope, NamespaceScope.PRINCIPAL)
        with self.assertRaises(NamespaceMismatchError):
            colleague.require_exact(principal)
        with self.assertRaises(NamespaceMismatchError):
            colleague.require_exact(Namespace.colleague("tenant-beta", "colleague-alpha"))

    def test_ids_are_explicit_strings(self) -> None:
        principal = human_admin()
        self.assertIs(type(principal.principal_id), str)
        self.assertIs(type(principal.namespace.tenant_id), str)
        with self.assertRaises(CoreInvariantError):
            Namespace.colleague("Tenant With Spaces", "colleague-alpha")

    def test_principal_kinds_are_disjoint_and_frozen(self) -> None:
        human = human_admin()
        model = Principal.model(tenant_id="tenant-alpha", principal_id="principal-model-a")
        service = Principal.service(tenant_id="tenant-alpha", principal_id="principal-service-a")
        self.assertEqual(
            {human.kind, model.kind, service.kind},
            {PrincipalKind.HUMAN, PrincipalKind.MODEL, PrincipalKind.SERVICE},
        )
        with self.assertRaises(dataclasses.FrozenInstanceError):
            model.kind = PrincipalKind.HUMAN  # type: ignore[misc]
        with self.assertRaises(CoreInvariantError):
            Principal(
                namespace=Namespace.principal("tenant-alpha", "principal-model-b"),
                principal_id="principal-model-b",
                kind=PrincipalKind.MODEL,
                roles=(HumanRole.TENANT_ADMIN,),
            )

    def test_only_canonical_human_roles_are_constructible(self) -> None:
        self.assertEqual(
            {role.value for role in HumanRole},
            {"tenant_admin", "colleague_user", "auditor"},
        )
        with self.assertRaises(CoreInvariantError):
            Principal(
                namespace=Namespace.principal("tenant-alpha", "principal-human-b"),
                principal_id="principal-human-b",
                kind=PrincipalKind.HUMAN,
                roles=("owner",),  # type: ignore[arg-type]
            )

    def test_utc_only_datetime_and_z_round_trip(self) -> None:
        encoded = datetime_to_z(T0)
        self.assertEqual(encoded, "2026-01-02T03:04:05.006000Z")
        self.assertEqual(datetime_from_z(encoded), T0)
        with self.assertRaises(CoreInvariantError):
            datetime_to_z(datetime(2026, 1, 2, 3, 4, 5))
        with self.assertRaises(CoreInvariantError):
            datetime_to_z(datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone(timedelta(hours=8))))
        with self.assertRaises(CoreInvariantError):
            datetime_from_z("2026-01-02T03:04:05+00:00")


if __name__ == "__main__":
    unittest.main()
