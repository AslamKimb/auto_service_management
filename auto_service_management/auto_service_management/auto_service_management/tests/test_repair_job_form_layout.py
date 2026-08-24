import json
from pathlib import Path

import frappe
from frappe.tests import UnitTestCase

from auto_service_management.auto_service_management.doctype.repair_job.repair_job_dashboard import (
	get_data,
)

APP_ROOT = Path(__file__).parents[1]
REPAIR_JOB_JSON = APP_ROOT / "doctype" / "repair_job" / "repair_job.json"

EXPECTED_TABS = [
	("details_tab", "Details", 0),
	("services_tab", "Services", 0),
	("workshop_tab", "Workshop", 0),
	("billing_tab", "Billing", 0),
	("connections_tab", "Connections", 1),
]

EXPECTED_EXISTING_FIELDS = {
	"customer_section",
	"customer",
	"customer_vehicle",
	"column_break_customer",
	"registration_number",
	"vehicle_details",
	"job_card_snapshot",
	"repair_job_id_html",
	"odometer_in",
	"fuel_level",
	"job_section",
	"scope_revision",
	"job_status",
	"priority",
	"column_break_job",
	"promised_date",
	"column_break_job2",
	"project",
	"fleet_service_campaign",
	"quotation",
	"sales_order",
	"related_documents_section",
	"walkaround_inspection",
	"diagnosis_report",
	"customer_authorization",
	"quality_check",
	"gate_pass",
	"intake_notes_section",
	"column_break_related_documents",
	"customer_concern",
	"services_section",
	"services_help",
	"total_amount",
	"repair_job_services",
	"sales_invoices",
	"sales_orders",
	"payment_entries",
	"currency",
	"billing_section",
	"payment_status",
	"billing_components_html",
	"sales_orders_html",
	"material_requests_html",
	"column_break_billing",
	"odometer_out",
	"closure_section",
	"closed_on",
	"closed_by",
	"closure_type",
	"payment_total",
}

EXPECTED_TRANSACTIONS = [
	(
		"Workshop",
		[
			"Repair Job Service",
			"Walkaround Inspection",
			"Diagnosis Report",
			"Customer Authorization",
			"Quality Check",
			"Gate Pass",
			"Service History",
			"Repair Job Override",
			"Repair Job Log",
		],
	),
	(
		"Billing & Materials",
		["Sales Order", "Sales Invoice", "Payment Entry", "Material Request", "Quotation"],
	),
	("Context", ["Customer", "Customer Vehicle", "Project", "Fleet Service Campaign"]),
]

EXPECTED_INTERNAL_LINKS = {
	"Customer": "customer",
	"Customer Vehicle": "customer_vehicle",
	"Project": "project",
	"Fleet Service Campaign": "fleet_service_campaign",
	"Quotation": "quotation",
	"Sales Order": ["sales_orders", "sales_order"],
	"Sales Invoice": ["sales_invoices", "sales_invoice"],
	"Payment Entry": ["payment_entries", "payment_entry"],
	"Repair Job Service": ["repair_job_services", "repair_job_service"],
}


def _load_repair_job_definition():
	return json.loads(REPAIR_JOB_JSON.read_text(encoding="utf-8"))


class TestRepairJobFormLayoutContracts(UnitTestCase):
	def test_native_tabs_are_in_the_approved_order(self):
		definition = _load_repair_job_definition()
		tabs = [
			(field["fieldname"], field.get("label"), field.get("show_dashboard", 0))
			for field in definition["fields"]
			if field["fieldtype"] == "Tab Break"
		]

		self.assertEqual(tabs, EXPECTED_TABS)
		self.assertEqual(tabs[-1][0], "connections_tab")
		self.assertEqual(tabs[-1][2], 1)

	def test_existing_repair_job_fields_and_semantics_are_preserved(self):
		definition = _load_repair_job_definition()
		fields = {field["fieldname"]: field for field in definition["fields"]}

		self.assertTrue(EXPECTED_EXISTING_FIELDS.issubset(fields))
		self.assertEqual(fields["customer_vehicle"].get("reqd"), 1)
		self.assertEqual(fields["odometer_in"].get("reqd"), 1)
		self.assertEqual(fields["customer_concern"].get("reqd"), 1)
		self.assertEqual(fields["job_card_snapshot"].get("hidden"), 1)
		self.assertEqual(fields["job_card_snapshot"].get("read_only"), 1)
		self.assertEqual(fields["sales_orders"].get("read_only"), 1)
		self.assertEqual(fields["job_status"].get("default"), "Draft")

		for fieldname in ("registration_number", "vehicle_details", "project", "fleet_service_campaign"):
			with self.subTest(fieldname=fieldname):
				self.assertEqual(fields[fieldname].get("read_only"), 1)

		for fieldname in ("closed_on", "closed_by", "closure_type", "payment_total"):
			with self.subTest(fieldname=fieldname):
				self.assertEqual(fields[fieldname].get("read_only"), 1)

	def test_dashboard_declares_expected_native_connections(self):
		data = get_data()
		transactions = [(group["label"], group["items"]) for group in data["transactions"]]

		self.assertEqual(data["fieldname"], "repair_job")
		self.assertEqual(transactions, EXPECTED_TRANSACTIONS)
		self.assertEqual(data["internal_links"], EXPECTED_INTERNAL_LINKS)

		items = [item for _, group_items in transactions for item in group_items]
		self.assertEqual(len(items), len(set(items)))

	def test_live_meta_dashboard_matches_the_controller_contract(self):
		meta_data = frappe.get_meta("Repair Job").get_dashboard_data()
		controller_data = get_data()

		self.assertEqual(meta_data.get("fieldname"), controller_data["fieldname"])
		self.assertEqual(meta_data.get("transactions"), controller_data["transactions"])
		self.assertEqual(meta_data.get("internal_links"), controller_data["internal_links"])

	def test_native_link_counts_resolve_for_an_existing_repair_job(self):
		name = frappe.db.get_value("Repair Job", {}, "name")
		if not name:
			self.skipTest("No Repair Job fixture exists on this site")

		from frappe.desk.notifications import _get_linked_document_counts

		result = _get_linked_document_counts("Repair Job", name)
		self.assertIn("count", result)
		self.assertIn("internal_links_found", result["count"])
		self.assertIn("external_links_found", result["count"])
