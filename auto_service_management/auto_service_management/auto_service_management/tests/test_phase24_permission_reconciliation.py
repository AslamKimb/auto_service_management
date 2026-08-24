from __future__ import annotations

import unittest
from unittest.mock import patch

import frappe

from auto_service_management.patches import phase24_reconcile_custom_permissions as phase24


class TestPhase24PermissionReconciliation(unittest.TestCase):
	def test_only_conflicting_template_target_roles_are_removed(self):
		custom_rows = [
			frappe._dict(name="cashier-grant", role="Cashier", permlevel=0, read=1),
			frappe._dict(name="advisor-override", role="Service Advisor", permlevel=0, read=1, write=0),
			frappe._dict(
				name="regional-reviewer-constraint",
				role="Regional Template Reviewer",
				permlevel=0,
				read=1,
				if_owner=1,
			),
			frappe._dict(
				name="advisor-field-level-constraint",
				role="Service Advisor",
				permlevel=1,
				read=1,
				if_owner=1,
			),
		]
		deleted = []

		def get_all(doctype, **kwargs):
			if doctype == "DocType":
				return ["Repair Job Service Template"]
			if doctype == "Custom DocPerm":
				return custom_rows
			if doctype == "DocPerm":
				return []
			raise AssertionError(doctype)

		with (
			patch.object(phase24.frappe, "get_all", side_effect=get_all),
			patch.object(
				phase24.frappe,
				"delete_doc",
				side_effect=lambda _doctype, name, **_kwargs: deleted.append(name),
			),
			patch.object(phase24, "copy_perms"),
			patch.object(phase24.frappe, "clear_cache"),
		):
			phase24.execute()

		self.assertEqual(deleted, ["cashier-grant", "advisor-override"])

	def test_reconcile_deletes_duplicate_custom_perm_and_preserves_constraints(self):
		custom_rows = [
			frappe._dict(
				name="duplicate-row",
				role="Workshop Manager",
				permlevel=0,
				read=1,
				write=1,
			),
			frappe._dict(
				name="restricted-row",
				role="Service Advisor",
				permlevel=0,
				read=1,
				write=0,
				if_owner=1,
			),
		]
		standard_rows = [
			frappe._dict(role="Workshop Manager", permlevel=0, read=1, write=1),
			frappe._dict(role="Service Advisor", permlevel=0, read=1, write=1, if_owner=0),
		]
		deleted = []

		def get_all(doctype, **kwargs):
			if doctype == "DocType":
				return ["Repair Job"]
			if doctype == "Custom DocPerm":
				return custom_rows
			if doctype == "DocPerm":
				return standard_rows
			raise AssertionError(doctype)

		def delete_doc(_doctype, name, **_kwargs):
			deleted.append(name)

		with (
			patch.object(phase24.frappe, "get_all", side_effect=get_all),
			patch.object(phase24.frappe, "delete_doc", side_effect=delete_doc),
			patch.object(phase24, "copy_perms"),
			patch.object(phase24.frappe, "clear_cache"),
		):
			phase24.execute()

		self.assertEqual(deleted, ["duplicate-row"])

	def test_permission_value_comparison_includes_owner_constraint(self):
		standard = frappe._dict(read=1, write=1, if_owner=0)
		custom = frappe._dict(read=1, write=1, if_owner=1)

		self.assertNotEqual(phase24._permission_values(custom), phase24._permission_values(standard))


if __name__ == "__main__":
	unittest.main()
