import inspect
import json
from pathlib import Path

import frappe
from frappe.tests import UnitTestCase

MODULE_ROOT = Path(__file__).parents[1]
APP_ROOT = Path(__file__).parents[2]


class TestPhase10ServiceBillingContracts(UnitTestCase):
	def test_active_service_components_exclude_subcontracted_services(self):
		service = _doctype_fields("repair_job_service")
		template = _doctype_fields("repair_service_template")

		self.assertNotIn("subcontracted_services", service)
		self.assertNotIn("subcontracted_services", template)
		self.assertEqual(service["legacy_subcontracted_services"]["hidden"], 1)
		self.assertEqual(service["legacy_subcontracted_services"]["read_only"], 1)
		self.assertEqual(template["legacy_subcontracted_services"]["hidden"], 1)
		self.assertEqual(template["legacy_subcontracted_services"]["read_only"], 1)

	def test_component_iterator_supports_only_service_status_filter(self):
		from auto_service_management.auto_service_management.doctype.repair_job_service.repair_job_service import (
			iter_repair_job_components,
		)

		self.assertIn("service_statuses", inspect.signature(iter_repair_job_components).parameters)
		self.assertNotIn("statuses", inspect.signature(iter_repair_job_components).parameters)

	def test_active_component_tables_do_not_have_status_fields(self):
		for folder in (
			"repair_job_service_part",
			"repair_job_service_consumable",
			"repair_job_service_labour",
		):
			self.assertNotIn("status", _doctype_fields(folder))

	def test_server_totals_use_stock_discounts_and_labour_billing_fields(self):
		service = frappe.get_doc(
			{
				"doctype": "Repair Job Service",
				"currency": "UGX",
				"parts": [
					{
						"billable": 1,
						"quantity": 2,
						"rate": 100,
						"discount_percentage": 10,
						"cost_rate": 40,
					}
				],
				"consumables": [
					{
						"billable": 0,
						"quantity": 5,
						"rate": 20,
						"cost_rate": 5,
					}
				],
				"labour": [
					{
						"billable": 1,
						"hours": 3,
						"billing_hours": 2,
						"billing_rate": 60,
						"costing_rate": 30,
					}
				],
			}
		)

		service.calculate_totals()

		self.assertEqual(service.total_amount, 300)
		self.assertEqual(service.cost_total, 195)
		self.assertEqual(service.gross_margin, 105)

	def test_parent_trace_fields_are_fixture_owned(self):
		fixture = json.loads((APP_ROOT / "fixtures" / "custom_field.json").read_text(encoding="utf-8"))
		names = {row["name"] for row in fixture}

		self.assertIn("Sales Invoice-repair_job", names)
		self.assertIn("Material Request-repair_job", names)

	def test_erpnext_forms_load_get_items_from_scripts(self):
		hooks = (APP_ROOT / "hooks.py").read_text(encoding="utf-8")

		self.assertIn('"Sales Invoice": "public/js/sales_invoice.js"', hooks)
		self.assertIn('"Material Request": "public/js/material_request.js"', hooks)
		self.assertTrue((APP_ROOT / "public" / "js" / "sales_invoice.js").is_file())
		self.assertTrue((APP_ROOT / "public" / "js" / "material_request.js").is_file())

	def test_mapping_methods_are_typed_and_post_only(self):
		from auto_service_management.auto_service_management.doctype.repair_job import repair_job
		from auto_service_management.auto_service_management.doctype.repair_job_service import (
			repair_job_service,
		)

		for method in (
			repair_job.make_sales_invoice,
			repair_job.make_material_request,
			repair_job_service.make_sales_invoice,
			repair_job_service.make_material_request,
		):
			self.assertTrue(method.__annotations__)
			self.assertEqual(frappe.allowed_http_methods_for_whitelisted_func[method], ["POST"])

	def test_document_lifecycle_hooks_are_registered(self):
		hooks = (APP_ROOT / "hooks.py").read_text(encoding="utf-8")

		for doctype in ("Sales Invoice", "Material Request"):
			self.assertIn(f'"{doctype}": {{', hooks)
		for event in ("validate", "on_update", "on_submit", "on_cancel", "on_trash"):
			self.assertIn(f'"{event}":', hooks)

	def test_live_total_script_recalculates_all_active_tables(self):
		script = (MODULE_ROOT / "doctype" / "repair_job_service" / "repair_job_service.js").read_text(
			encoding="utf-8"
		)

		self.assertIn("calculate_service_totals", script)
		for fieldname in ("parts_remove", "consumables_remove", "labour_remove"):
			self.assertIn(fieldname, script)


def _doctype_fields(folder):
	path = MODULE_ROOT / "doctype" / folder / f"{folder}.json"
	doctype = json.loads(path.read_text(encoding="utf-8"))
	return {field["fieldname"]: field for field in doctype["fields"]}
