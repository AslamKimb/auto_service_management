import json
from pathlib import Path

import frappe
from frappe.tests import IntegrationTestCase, UnitTestCase

from auto_service_management.auto_service_management.doctype.customer_lpo.customer_lpo_dashboard import (
	get_data as get_customer_lpo_dashboard_data,
)
from auto_service_management.auto_service_management.doctype.customer_lpo_vehicle.customer_lpo_vehicle import (
	normalize_registration_number,
)
from auto_service_management.auto_service_management.integration import customer_lpo_workflow
from auto_service_management.auto_service_management.reporting.registry import (
	REPORT_DEFINITIONS,
)
from auto_service_management.auto_service_management.workspace_dashboard import (
	WORKSPACE_HUBS,
	WORKSPACE_REPORT_LINKS,
)

ROOT = Path(__file__).parents[1]
CONNECTION_ITEMS = [
	"Fleet Service Campaign",
	"Repair Job",
	"Customer Vehicle",
	"Sales Order",
	"Sales Invoice",
	"Customer LPO Amendment",
]


class TestCustomerLPOUIContracts(UnitTestCase):
	def test_native_lpo_tabs_and_child_table_are_present(self):
		meta = json.loads((ROOT / "doctype/customer_lpo/customer_lpo.json").read_text(encoding="utf-8"))
		fields = meta["fields"]
		tabs = [field["label"] for field in fields if field["fieldtype"] == "Tab Break"]
		self.assertEqual(tabs, ["Details", "Vehicles", "Financials", "Connections"])
		vehicle = next(field for field in fields if field["fieldname"] == "vehicle_rows")
		self.assertEqual(vehicle["options"], "Customer LPO Vehicle")

	def test_lpo_vehicle_row_uses_customer_vehicle_as_the_single_required_identity(self):
		meta = json.loads(
			(ROOT / "doctype/customer_lpo_vehicle/customer_lpo_vehicle.json").read_text(encoding="utf-8")
		)
		fields = {field["fieldname"]: field for field in meta["fields"]}

		self.assertEqual(fields["customer_vehicle"].get("reqd"), 1)
		self.assertFalse(fields["registration_number"].get("reqd", 0))
		self.assertEqual(fields["registration_number"].get("read_only"), 1)
		self.assertEqual(
			fields["registration_number"].get("fetch_from"),
			"customer_vehicle.registration_number",
		)

	def test_lpo_actions_use_native_controller_and_post_mutations(self):
		source = (ROOT / "../public/js/customer_lpo.js").resolve().read_text(encoding="utf-8")
		self.assertIn("Preview CSV", source)
		self.assertIn("Import Vehicles", source)
		self.assertIn("Add Amendment", source)
		self.assertIn('fieldtype: "Attach"', source)
		self.assertIn("file_url", source)
		self.assertIn("Create Campaign & Jobs", source)
		self.assertIn('type: "POST"', source)
		self.assertIn("make_sales_invoice", source)
		self.assertIn('frm.set_query("customer_vehicle", "vehicle_rows"', source)
		self.assertNotIn("Resolve Vehicles", source)
		self.assertNotIn("Create Missing Vehicles", source)
		self.assertNotIn("resolve_vehicle_rows", source)

	def test_lpo_dashboard_override_accepts_frappe_data_keyword(self):
		data = get_customer_lpo_dashboard_data(data={})
		self.assertEqual(data["fieldname"], "customer_lpo")
		self.assertEqual(len(data["transactions"]), 2)
		self.assertEqual(
			data["internal_links"],
			{"Customer Vehicle": ["vehicle_rows", "customer_vehicle"]},
		)

	def test_lpo_reports_and_fleet_workspace_links_are_registered(self):
		self.assertIn("Customer LPO Utilization", REPORT_DEFINITIONS)
		self.assertIn("Customer LPO Vehicle Progress", REPORT_DEFINITIONS)
		self.assertIn("Customer LPO", [row["label"] for row in WORKSPACE_HUBS["Fleet & History"]["links"]])
		self.assertIn("Cashier", WORKSPACE_HUBS["Fleet & History"]["roles"])
		self.assertIn("Customer LPO Utilization", WORKSPACE_REPORT_LINKS)
		for report_path in (
			ROOT / "report/customer_lpo_utilization/customer_lpo_utilization.json",
			ROOT / "report/customer_lpo_vehicle_progress/customer_lpo_vehicle_progress.json",
		):
			roles = {row["role"] for row in json.loads(report_path.read_text(encoding="utf-8"))["roles"]}
			self.assertIn("Auto Service Admin", roles)

	def test_lpo_print_formats_are_app_owned(self):
		fulfilment = json.loads(
			(
				ROOT / "print_format/customer_lpo_fulfilment_summary/customer_lpo_fulfilment_summary.json"
			).read_text(encoding="utf-8")
		)
		invoice = json.loads(
			(ROOT / "print_format/customer_lpo_invoice/customer_lpo_invoice.json").read_text(encoding="utf-8")
		)
		self.assertEqual(fulfilment["doc_type"], "Customer LPO")
		self.assertEqual(invoice["doc_type"], "Sales Invoice")
		self.assertIn("customer_lpo_invoice", invoice["html"])


class TestCustomerLPOConnectionsIntegration(IntegrationTestCase):
	def test_native_connections_resolve_customer_vehicle_through_the_lpo_child_table(self):
		company = frappe.db.get_value("Company", {}, "name")
		customer = frappe.db.get_value("Customer", {}, "name")
		currency = frappe.db.get_value("Company", company, "default_currency") if company else None
		if not company or not customer or not currency:
			self.skipTest("Company, Customer, and currency fixtures are required")

		suffix = frappe.generate_hash(length=8).upper()
		vehicle = frappe.get_doc(
			{
				"doctype": "Customer Vehicle",
				"customer": customer,
				"registration_number": f"LPO-CONN-{suffix}",
			}
		).insert(ignore_permissions=True)
		lpo = frappe.get_doc(
			{
				"doctype": "Customer LPO",
				"company": company,
				"customer": customer,
				"lpo_number": f"CONNECTION-{suffix}",
				"issue_date": "2026-08-27",
				"expiry_date": "2026-12-31",
				"currency": currency,
				"ceiling_basis": "Tax Inclusive",
				"authorized_amount": 1000,
				"vehicle_rows": [
					{
						"customer_vehicle": vehicle.name,
						"registration_number": vehicle.registration_number,
					}
				],
			}
		).insert(ignore_permissions=True)

		from frappe.desk.notifications import _get_linked_document_counts

		result = _get_linked_document_counts("Customer LPO", lpo.name, CONNECTION_ITEMS)
		vehicle_link = next(
			row
			for row in result["count"]["internal_links_found"]
			if row["doctype"] == "Customer Vehicle"
		)
		self.assertEqual(vehicle_link["names"], [vehicle.name])
		self.assertEqual(vehicle_link["count"], 1)

		imported_vehicle = frappe.get_doc(
			{
				"doctype": "Customer Vehicle",
				"customer": customer,
				"registration_number": f"LPO-CSV-{suffix}",
			}
		).insert(ignore_permissions=True)
		imported_registration = frappe.db.get_value(
			"Customer Vehicle", imported_vehicle.name, "registration_number"
		)
		result = customer_lpo_workflow.import_vehicle_csv(
			lpo.name,
			rows=[{"registration_number": imported_registration}],
		)
		lpo.reload()
		self.assertEqual(result["imported"], 1)
		self.assertEqual(lpo.vehicle_rows[-1].customer_vehicle, imported_vehicle.name)
		self.assertEqual(
			lpo.vehicle_rows[-1].registration_number,
			normalize_registration_number(imported_registration),
		)
