import json
from pathlib import Path

from frappe.tests import UnitTestCase

from auto_service_management.auto_service_management.doctype.customer_lpo.customer_lpo_dashboard import (
	get_data as get_customer_lpo_dashboard_data,
)
from auto_service_management.auto_service_management.reporting.registry import (
	REPORT_DEFINITIONS,
)
from auto_service_management.auto_service_management.workspace_dashboard import (
	WORKSPACE_HUBS,
	WORKSPACE_REPORT_LINKS,
)

ROOT = Path(__file__).parents[1]


class TestCustomerLPOUIContracts(UnitTestCase):
	def test_native_lpo_tabs_and_child_table_are_present(self):
		meta = json.loads((ROOT / "doctype/customer_lpo/customer_lpo.json").read_text(encoding="utf-8"))
		fields = meta["fields"]
		tabs = [field["label"] for field in fields if field["fieldtype"] == "Tab Break"]
		self.assertEqual(tabs, ["Details", "Vehicles", "Financials", "Connections"])
		vehicle = next(field for field in fields if field["fieldname"] == "vehicle_rows")
		self.assertEqual(vehicle["options"], "Customer LPO Vehicle")

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

	def test_lpo_dashboard_override_accepts_frappe_data_keyword(self):
		data = get_customer_lpo_dashboard_data(data={})
		self.assertEqual(data["fieldname"], "customer_lpo")
		self.assertEqual(len(data["transactions"]), 2)

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
