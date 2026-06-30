from __future__ import annotations

import frappe
from frappe.desk.query_report import run as run_query_report
from frappe.tests import IntegrationTestCase

from auto_service_management.auto_service_management.tests.test_controllers_integration import (
	_create_test_vehicle,
	_ensure_erpnext_basics,
	_get_or_create_customer,
)
from auto_service_management.auto_service_management.user_defaults import (
	WORKSHOP_DEFAULT_WORKSPACE,
	backfill_default_workspace_for_existing_users,
)

ROLE_MATRIX = {
	"Service Advisor": {
		"doctypes": {
			"Customer Vehicle": "read",
			"Repair Job": "create",
			"Customer Authorization": "read",
		},
		"reports": ("Open Repair Jobs",),
	},
	"Workshop Manager": {
		"doctypes": {
			"Repair Job": "read",
			"Quality Check": "read",
		},
		"reports": ("Jobs by Status",),
	},
	"Parts Interpreter": {
		"doctypes": {
			"Repair Job": "read",
		},
		"reports": ("Jobs Waiting for Parts",),
	},
	"Cashier": {
		"doctypes": {
			"Sales Invoice": "read",
		},
		"reports": ("Jobs by Status",),
	},
	"Security Gate Officer": {
		"doctypes": {
			"Gate Pass": "read",
			"Service History": "read",
		},
		"reports": (),
	},
}


def _create_role_user(role: str, *, blank_default_workspace: bool = True) -> str:
	email = f"test.{frappe.scrub(role)}.{frappe.generate_hash(length=8)}@example.com"
	user = frappe.get_doc(
		{
			"doctype": "User",
			"email": email,
			"first_name": role,
			"enabled": 1,
			"send_welcome_email": 0,
			"user_type": "System User",
			"default_workspace": "" if blank_default_workspace else "Build",
			"roles": [{"role": "Desk User"}, {"role": role}],
		}
	)
	user.insert(ignore_permissions=True)
	return email


class TestPermissionMatrix(IntegrationTestCase):
	def setUp(self):
		_ensure_erpnext_basics()
		self.customer = _get_or_create_customer()
		self.vehicle = _create_test_vehicle(self.customer)
		self.original_user = frappe.session.user
		self.users_to_delete: list[str] = []

	def tearDown(self):
		frappe.set_user(self.original_user)
		for user in self.users_to_delete:
			if frappe.db.exists("User", user):
				frappe.delete_doc("User", user, ignore_permissions=True, force=1)
		frappe.db.rollback()

	def test_default_workspace_is_assigned_for_workshop_desk_roles_when_blank(self):
		for role in ROLE_MATRIX:
			with self.subTest(role=role):
				user = _create_role_user(role)
				self.users_to_delete.append(user)
				self.assertEqual(
					frappe.db.get_value("User", user, "default_workspace"),
					WORKSHOP_DEFAULT_WORKSPACE,
				)

	def test_existing_default_workspace_is_preserved(self):
		user = _create_role_user("Service Advisor", blank_default_workspace=False)
		self.users_to_delete.append(user)
		self.assertEqual(frappe.db.get_value("User", user, "default_workspace"), "Build")

	def test_default_workspace_backfill_updates_existing_blank_users(self):
		user = _create_role_user("Workshop Manager")
		self.users_to_delete.append(user)
		frappe.db.set_value("User", user, "default_workspace", "", update_modified=False)

		backfill_default_workspace_for_existing_users()

		self.assertEqual(
			frappe.db.get_value("User", user, "default_workspace"),
			WORKSHOP_DEFAULT_WORKSPACE,
		)

	def test_role_matrix_matches_phase6_workspace_contract(self):
		for role, expectations in ROLE_MATRIX.items():
			user = _create_role_user(role)
			self.users_to_delete.append(user)

			for doctype, permtype in expectations["doctypes"].items():
				with self.subTest(role=role, doctype=doctype, permtype=permtype):
					self.assertTrue(frappe.has_permission(doctype, permtype, user=user))

			frappe.set_user(user)
			for report_name in expectations["reports"]:
				with self.subTest(role=role, report=report_name):
					result = run_query_report(report_name, filters={})
					self.assertIn("result", result)
