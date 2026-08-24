from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import frappe
from frappe.tests import UnitTestCase

from auto_service_management.auto_service_management.doctype.repair_job_service import repair_job_service
from auto_service_management.auto_service_management.reporting.control_definitions import CONTROL_REPORTS
from auto_service_management.auto_service_management.reporting.runner import run_report
from auto_service_management.auto_service_management.reporting.workshop_definitions import WORKSHOP_REPORTS

MODULE_ROOT = Path(__file__).resolve().parents[1]


class _PermissionProbe(SimpleNamespace):
	def check_permission(self, permission):
		self.checked_permission = permission


class TestPermissionRegressions(UnitTestCase):
	def test_invoice_row_reports_use_native_child_parent_context_without_get_all(self):
		for report_name in ("Corporate Credit Releases", "Repair Revenue by Period"):
			for permissions in (
				{"read": True, "select": False, "report": True},
				{"read": False, "select": True, "report": True},
			):
				with self.subTest(report=report_name, permissions=permissions):
					definition = CONTROL_REPORTS[report_name]
					self.assertEqual(definition.parent_field, "repair_job")
					self.assertEqual(definition.permission_parent_doctype, "Repair Job")
					row_with_stale_link = {
						"parent": "RJ-ACTUAL-PARENT",
						"repair_job": "RJ-STALE-LINK",
					}
					with (
						patch(
							"auto_service_management.auto_service_management.reporting.runner.frappe.has_permission",
							side_effect=lambda _doctype, ptype: permissions[ptype],
						),
						patch(
							"auto_service_management.auto_service_management.reporting.runner.frappe.get_list",
							return_value=[row_with_stale_link],
						) as get_list,
						patch(
							"auto_service_management.auto_service_management.reporting.runner.frappe.get_all"
						) as get_all,
					):
						_columns, rows = run_report(report_name, {})

					get_list.assert_called_once()
					call = get_list.call_args
					self.assertEqual(call.args[0], "Repair Job Invoice Row")
					self.assertEqual(call.kwargs["parent_doctype"], "Repair Job")
					self.assertNotIn("repair_job", call.kwargs["filters"])
					self.assertEqual(rows, [row_with_stale_link])
					get_all.assert_not_called()

	def test_report_requires_report_and_parent_data_permission(self):
		for permissions in (
			{"read": False, "select": False, "report": True},
			{"read": True, "select": False, "report": False},
			{"read": False, "select": False, "report": False},
		):
			with self.subTest(permissions=permissions):
				with (
					patch(
						"auto_service_management.auto_service_management.reporting.runner.frappe.has_permission",
						side_effect=lambda _doctype, ptype: permissions[ptype],
					),
					patch(
						"auto_service_management.auto_service_management.reporting.runner.frappe.get_list"
					) as get_list,
				):
					with self.assertRaises(frappe.PermissionError):
						run_report("Corporate Credit Releases", {})

				invoice_row_calls = [
					call
					for call in get_list.call_args_list
					if call.args and call.args[0] == "Repair Job Invoice Row"
				]
				self.assertEqual(invoice_row_calls, [])

	def test_all_repair_job_child_reports_use_native_parent_context(self):
		for report_name, definition in WORKSHOP_REPORTS.items():
			if definition.parent_field == "repair_job":
				with self.subTest(report=report_name):
					self.assertEqual(definition.permission_parent_doctype, "Repair Job")

	def test_active_component_children_declare_select_for_v16_queries(self):
		for folder in (
			"repair_job_service_part",
			"repair_job_service_consumable",
			"repair_job_service_labour",
		):
			path = MODULE_ROOT / "doctype" / folder / f"{folder}.json"
			permissions = json.loads(path.read_text(encoding="utf-8"))["permissions"]
			for row in permissions:
				with self.subTest(doctype=folder, role=row["role"]):
					self.assertEqual(row.get("select"), 1)

	def test_v16_child_select_patch_is_registered(self):
		patches = (MODULE_ROOT.parent / "patches.txt").read_text(encoding="utf-8")
		self.assertIn("auto_service_management.patches.phase28_v16_child_select_permissions", patches)

	def test_version_audit_query_is_not_treated_as_a_child_table(self):
		with (
			patch(
				"auto_service_management.auto_service_management.reporting.runner.frappe.has_permission",
				return_value=True,
			),
			patch(
				"auto_service_management.auto_service_management.reporting.runner.frappe.get_list",
				return_value=[],
			) as get_list,
		):
			run_report("Discount and Price Change Audit", {})

		get_list.assert_called_once()
		call = get_list.call_args
		self.assertEqual(call.args[0], "Version")
		self.assertNotIn("parent_doctype", call.kwargs)

	def test_template_role_matrix_is_exact_and_does_not_grant_cashier_or_security(self):
		path = MODULE_ROOT / "doctype" / "repair_job_service_template" / "repair_job_service_template.json"
		permissions = {
			row["role"]: {key for key, value in row.items() if key != "role" and value == 1}
			for row in json.loads(path.read_text(encoding="utf-8"))["permissions"]
		}

		self.assertTrue({"read", "write", "create"}.issubset(permissions["Workshop Manager"]))
		self.assertTrue({"read", "write", "create"}.issubset(permissions["Service Advisor"]))
		self.assertEqual(permissions["Workshop Technician"], {"read"})
		self.assertEqual(permissions["Parts Interpreter"], {"read", "report"})
		self.assertNotIn("Cashier", permissions)
		self.assertNotIn("Security Gate Officer", permissions)

	def test_template_picker_checks_read_permission_and_uses_permission_aware_query(self):
		job = _PermissionProbe(customer_vehicle="VEH-1")
		has_permission = Mock(return_value=True)
		get_list = Mock(return_value=[])
		fake_frappe = SimpleNamespace(
			get_doc=lambda *_args: job,
			has_permission=has_permission,
			get_list=get_list,
			db=SimpleNamespace(
				get_value=lambda *_args, **_kwargs: frappe._dict(make="Toyota", model="Toyota - Prado")
			),
			_dict=frappe._dict,
		)

		with patch.object(repair_job_service, "frappe", fake_frappe):
			self.assertEqual(repair_job_service.get_compatible_repair_job_service_templates("RJ-1"), [])

		self.assertEqual(job.checked_permission, "read")
		has_permission.assert_called_once_with("Repair Job Service Template", "read", throw=True)
		get_list.assert_called_once()

	def test_template_actions_are_hidden_when_target_permissions_are_missing(self):
		job_js = (MODULE_ROOT / "doctype" / "repair_job" / "repair_job.js").read_text(encoding="utf-8")
		service_js = (MODULE_ROOT / "doctype" / "repair_job_service" / "repair_job_service.js").read_text(
			encoding="utf-8"
		)
		template_js = (
			MODULE_ROOT / "doctype" / "repair_job_service_template" / "repair_job_service_template.js"
		).read_text(encoding="utf-8")

		self.assertIn('frappe.model.can_read("Repair Job Service Template")', job_js)
		self.assertIn('frappe.model.can_create("Repair Job Service")', job_js)
		self.assertIn('frappe.model.can_create("Repair Job Service Template")', service_js)
		self.assertIn('frappe.model.can_create("Repair Job Service")', template_js)

	def test_template_child_number_cards_declare_parent_document_type(self):
		for card_folder in (
			"repair_job_service_template_parts",
			"repair_job_service_template_labour",
			"repair_job_service_template_consumables",
		):
			with self.subTest(card=card_folder):
				path = MODULE_ROOT / "number_card" / card_folder / f"{card_folder}.json"
				card = json.loads(path.read_text(encoding="utf-8"))
				self.assertEqual(card["parent_document_type"], "Repair Job Service Template")
