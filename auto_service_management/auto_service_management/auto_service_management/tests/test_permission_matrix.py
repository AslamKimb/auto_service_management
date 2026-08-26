from __future__ import annotations

import frappe
from frappe.desk.query_report import run as run_query_report
from frappe.tests import IntegrationTestCase

from auto_service_management.auto_service_management.integration.erpnext import component_mapping
from auto_service_management.auto_service_management.tests.test_controllers_integration import (
	_append_service_component,
	_create_job_service,
	_create_repair_job,
	_create_test_vehicle,
	_ensure_erpnext_basics,
	_get_or_create_customer,
)
from auto_service_management.auto_service_management.user_defaults import (
	WORKSHOP_DEFAULT_WORKSPACE,
	backfill_default_workspace_for_existing_users,
)
from auto_service_management.patches import phase25_system_manager_permissions

ROLE_MATRIX = {
	"Service Advisor": {
		"doctypes": {
			"Customer": "read",
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

ACTIVE_COMPONENT_CHILD_DOCTYPES = (
	"Repair Job Service Part",
	"Repair Job Service Labour",
	"Repair Job Service Consumable",
)

SYSTEM_MANAGER_PERMISSIONS = (
	"read",
	"write",
	"create",
	"delete",
	"submit",
	"cancel",
	"amend",
	"report",
	"export",
	"import",
	"share",
	"print",
	"email",
	"select",
)
SYSTEM_MANAGER_ROW_FIELDS = (*SYSTEM_MANAGER_PERMISSIONS, "if_owner")


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


def _effective_system_manager_permission_rows(doctype: str):
	custom_rows = frappe.get_all(
		"Custom DocPerm",
		filters={"parent": doctype, "role": "System Manager", "permlevel": 0},
		fields=["name", *SYSTEM_MANAGER_ROW_FIELDS],
		limit_page_length=0,
	)
	if custom_rows:
		return custom_rows
	return frappe.get_all(
		"DocPerm",
		filters={"parent": doctype, "role": "System Manager", "permlevel": 0},
		fields=["name", *SYSTEM_MANAGER_ROW_FIELDS],
		limit_page_length=0,
	)


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

	def test_parts_report_allows_parts_interpreter_and_denies_workshop_technician(self):
		matrix_job = frappe.get_doc("Repair Job", _create_repair_job(self.customer, self.vehicle))
		matrix_service = _create_job_service(matrix_job, service_name="Permission matrix components")
		_append_service_component(
			matrix_service,
			service_type="Part",
			description="Matrix part",
			quantity=1,
			rate=1,
		)
		_append_service_component(
			matrix_service,
			service_type="Consumable",
			description="Matrix consumable",
			quantity=1,
			rate=1,
		)

		for role, should_run in (("Parts Interpreter", True), ("Workshop Technician", False)):
			with self.subTest(role=role):
				user = _create_role_user(role)
				self.users_to_delete.append(user)
				frappe.set_user(user)

				if should_run:
					result = run_query_report("Jobs Waiting for Parts", filters={})
					self.assertIn("result", result)
					reported_descriptions = {row.get("description") for row in result["result"]}
					self.assertIn("Matrix part", reported_descriptions)
					self.assertIn("Matrix consumable", reported_descriptions)
				else:
					with self.assertRaises(frappe.PermissionError):
						run_query_report("Jobs Waiting for Parts", filters={})

	def test_parts_report_excludes_unpermitted_jobs_and_customers(self):
		suffix = frappe.generate_hash(length=6).upper()
		denied_customer = frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": f"Permission Matrix Denied {suffix}",
				"customer_group": "Commercial",
				"territory": "Uganda",
			}
		).insert(ignore_permissions=True)
		denied_vehicle = frappe.get_doc(
			{
				"doctype": "Customer Vehicle",
				"customer": denied_customer.name,
				"registration_number": f"PM-{suffix}",
				"vin_chassis_number": f"PMVIN-{suffix}",
				"engine_number": f"PMENG-{suffix}",
				"year_of_manufacture": 2022,
			}
		).insert(ignore_permissions=True)

		allowed_job = frappe.get_doc("Repair Job", _create_repair_job(self.customer, self.vehicle))
		denied_job = frappe.get_doc(
			"Repair Job", _create_repair_job(denied_customer.name, denied_vehicle.name)
		)
		same_customer_denied_job = frappe.get_doc(
			"Repair Job", _create_repair_job(self.customer, self.vehicle)
		)
		for job, label in (
			(allowed_job, "Allowed parts"),
			(denied_job, "Denied parts"),
			(same_customer_denied_job, "Same customer denied parts"),
		):
			service = _create_job_service(job, service_name=label)
			row = _append_service_component(
				service, service_type="Part", description=label, quantity=1, rate=1
			)
			if job is denied_job:
				# Deliberately corrupt the denormalized child link. The child query
				# must still honor the immediate Repair Job Service parent scope.
				frappe.db.set_value(row.doctype, row.name, "repair_job", allowed_job.name)

		user = _create_role_user("Parts Interpreter")
		self.users_to_delete.append(user)
		user_permission = frappe.get_doc(
			{
				"doctype": "User Permission",
				"user": user,
				"allow": "Repair Job",
				"for_value": allowed_job.name,
			}
		).insert(ignore_permissions=True)
		try:
			frappe.set_user(user)
			result = run_query_report("Jobs Waiting for Parts", filters={})["result"]
			reported_jobs = {row.get("repair_job") for row in result}
			self.assertIn(allowed_job.name, reported_jobs)
			self.assertNotIn(denied_job.name, reported_jobs)
			self.assertNotIn(same_customer_denied_job.name, reported_jobs)
			self.assertNotIn("Denied parts", {row.get("description") for row in result})
			# Other permitted fixtures may already have parts; the scope assertion is
			# specifically that this user's allowed job is visible and both
			# cross-customer and same-customer jobs are absent.
			self.assertTrue(all(row.get("repair_job") != denied_job.name for row in result))
		finally:
			frappe.set_user("Administrator")
			frappe.delete_doc("User Permission", user_permission.name, ignore_permissions=True, force=True)

	def test_system_manager_has_full_dms_and_erpnext_permissions(self):
		phase25_system_manager_permissions.execute()
		user = _create_role_user("System Manager")
		self.users_to_delete.append(user)

		for doctype in phase25_system_manager_permissions.all_doctypes():
			applicable_fields = phase25_system_manager_permissions._applicable_action_fields(doctype)
			for permtype in applicable_fields:
				with self.subTest(doctype=doctype, permtype=permtype):
					self.assertTrue(frappe.has_permission(doctype, permtype, user=user))
			rows = _effective_system_manager_permission_rows(doctype)
			self.assertTrue(rows)
			for row in rows:
				with self.subTest(doctype=doctype, row=row.name):
					for field in SYSTEM_MANAGER_PERMISSIONS:
						self.assertEqual(row.get(field), int(field in applicable_fields))
					self.assertEqual(row.get("if_owner"), 0)

		job = frappe.get_doc(
			{
				"doctype": "Repair Job",
				"customer": self.customer,
				"customer_vehicle": self.vehicle,
				"odometer_in": 1,
				"customer_concern": "Permission recovery test",
			}
		).insert(ignore_permissions=True)
		frappe.set_user(user)
		job.customer_concern = "System Manager can save this Repair Job"
		job.save()
		self.assertEqual(
			component_mapping.get_material_request_components(job.name)["repair_job"],
			job.name,
		)

	def test_workshop_roles_can_read_active_component_child_doctypes_with_parent_context(self):
		parent_map = {
			"Repair Job Service Part": "Repair Job Service",
			"Repair Job Service Labour": "Repair Job Service",
			"Repair Job Service Consumable": "Repair Job Service",
		}

		for role in ("Workshop Manager", "Service Advisor", "Parts Interpreter"):
			user = _create_role_user(role)
			self.users_to_delete.append(user)

			for doctype in ACTIVE_COMPONENT_CHILD_DOCTYPES:
				with self.subTest(role=role, doctype=doctype):
					self.assertTrue(
						frappe.has_permission(
							doctype,
							"read",
							user=user,
							parent_doctype=parent_map[doctype],
						)
					)
