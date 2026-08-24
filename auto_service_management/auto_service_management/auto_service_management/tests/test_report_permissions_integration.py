from __future__ import annotations

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import now_datetime

from auto_service_management.auto_service_management.reporting.runner import run_report
from auto_service_management.auto_service_management.tests.test_controllers_integration import (
	_create_repair_job,
	_create_test_vehicle,
	_ensure_erpnext_basics,
	_get_or_create_customer,
)


class TestReportPermissionsIntegration(IntegrationTestCase):
	def setUp(self):
		self.original_user = frappe.session.user
		_ensure_erpnext_basics()
		customer = _get_or_create_customer()
		vehicle = _create_test_vehicle(customer)
		self.role = f"G4 Report Role {frappe.generate_hash(length=8)}"
		self.report_role = f"G4 Report Execute Role {frappe.generate_hash(length=8)}"
		self.user = f"g4.report.{frappe.generate_hash(length=8)}@example.com"
		for role in (self.role, self.report_role):
			frappe.get_doc(
				{
					"doctype": "Role",
					"role_name": role,
					"desk_access": 1,
				}
			).insert(ignore_permissions=True)
		frappe.get_doc(
			{
				"doctype": "User",
				"email": self.user,
				"first_name": "G4 Report User",
				"enabled": 1,
				"send_welcome_email": 0,
				"user_type": "System User",
				"roles": [{"role": self.role}, {"role": self.report_role}],
			}
		).insert(ignore_permissions=True)

		self.owned_job = _create_repair_job(customer, vehicle)
		self.other_job = _create_repair_job(customer, vehicle)
		frappe.db.set_value("Repair Job", self.owned_job, "owner", self.user, update_modified=False)
		self._insert_invoice_row(self.owned_job, 101)
		self._insert_invoice_row(self.other_job, 202)

	def tearDown(self):
		frappe.set_user(self.original_user)
		frappe.clear_cache()
		frappe.db.rollback()

	def _insert_invoice_row(self, repair_job: str, amount: int):
		row = frappe.get_doc(
			{
				"doctype": "Repair Job Invoice Row",
				"parent": repair_job,
				"parenttype": "Repair Job",
				"parentfield": "sales_invoices",
				"repair_job": repair_job,
				"customer": frappe.db.get_value("Repair Job", repair_job, "customer"),
				"job_status": "Closed",
				"closed_on": now_datetime(),
				"grand_total": amount,
				"paid_amount": 0,
				"outstanding_amount": amount,
				"payment_status": "Unpaid",
			}
		)
		row.flags.ignore_links = True
		row.insert(ignore_permissions=True)

	def _grant(self, *, read=0, select=0, report=0):
		if read or select:
			frappe.get_doc(
				{
					"doctype": "Custom DocPerm",
					"parent": "Repair Job",
					"parenttype": "DocType",
					"parentfield": "permissions",
					"role": self.role,
					"permlevel": 0,
					"read": read,
					"select": select,
					"if_owner": 1,
				}
			).insert(ignore_permissions=True)
		if report:
			frappe.get_doc(
				{
					"doctype": "Custom DocPerm",
					"parent": "Repair Job",
					"parenttype": "DocType",
					"parentfield": "permissions",
					"role": self.report_role,
					"permlevel": 0,
					"read": 0,
					"select": 0,
					"report": 1,
				}
			).insert(ignore_permissions=True)
		frappe.clear_cache()
		frappe.set_user(self.user)

	def test_read_and_report_returns_only_rows_from_permitted_parents(self):
		self._grant(read=1, report=1)

		_columns, rows = run_report("Corporate Credit Releases", {})

		self.assertEqual({row.repair_job for row in rows}, {self.owned_job})

	def test_report_only_is_denied(self):
		self._grant(report=1)

		with self.assertRaises(frappe.PermissionError):
			run_report("Corporate Credit Releases", {})

	def test_read_only_is_denied(self):
		self._grant(read=1)

		with self.assertRaises(frappe.PermissionError):
			run_report("Corporate Credit Releases", {})

	def test_user_without_report_or_data_permission_is_denied(self):
		frappe.clear_cache()
		frappe.set_user(self.user)

		with self.assertRaises(frappe.PermissionError):
			run_report("Corporate Credit Releases", {})
