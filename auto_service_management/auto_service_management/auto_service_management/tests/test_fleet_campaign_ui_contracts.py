import json
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests import UnitTestCase

from auto_service_management.auto_service_management.doctype.fleet_service_campaign import (
	fleet_service_campaign,
)

APP_ROOT = Path(__file__).resolve().parents[2]
CAMPAIGN_ROOT = APP_ROOT / "auto_service_management" / "doctype" / "fleet_service_campaign"
CAMPAIGN_JS = CAMPAIGN_ROOT / "fleet_service_campaign.js"
CAMPAIGN_JSON = CAMPAIGN_ROOT / "fleet_service_campaign.json"
CAMPAIGN_DASHBOARD = CAMPAIGN_ROOT / "fleet_service_campaign_dashboard.py"
PROFORMA_TEMPLATE = APP_ROOT / "templates" / "includes" / "auto_service_print" / "proforma_invoice.html"


class TestFleetCampaignUIContracts(unittest.TestCase):
	def test_campaign_form_exposes_native_grouped_create_and_related_actions(self):
		source = CAMPAIGN_JS.read_text(encoding="utf-8")
		for label in (
			"Repair Job",
			"Proforma Invoice (Sales Order)",
			"Sales Invoice",
			"Related Documents",
		):
			self.assertIn(label, source)
		self.assertIn("frappe.model.open_mapped_doc", source)
		self.assertIn('frappe.model.can_create("Repair Job")', source)
		self.assertIn('frappe.model.can_create("Sales Order")', source)
		self.assertIn('frappe.model.can_create("Sales Invoice")', source)
		self.assertIn('frm.doc.status !== "Cancelled"', source)

	def test_campaign_selector_is_explicit_grouped_and_accessible(self):
		source = CAMPAIGN_JS.read_text(encoding="utf-8")
		self.assertIn("get_campaign_sales_order_components", source)
		self.assertIn("get_campaign_sales_invoice_components", source)
		self.assertIn("campaign-component-choice", source)
		self.assertIn("component_refs: JSON.stringify", source)
		self.assertIn("aria-label", source)
		self.assertIn("table-responsive", source)
		self.assertIn("Loading campaign components", source)
		self.assertIn("No eligible components", source)
		self.assertIn("Unable to load campaign components", source)

	def test_campaign_schema_has_live_sales_document_surfaces(self):
		fields = json.loads(CAMPAIGN_JSON.read_text(encoding="utf-8"))["fields"]
		by_name = {field.get("fieldname"): field for field in fields}
		self.assertEqual(by_name["sales_orders_html"]["fieldtype"], "HTML")
		self.assertEqual(by_name["sales_invoices_html"]["fieldtype"], "HTML")

	def test_campaign_dashboard_links_jobs_orders_and_invoices(self):
		source = CAMPAIGN_DASHBOARD.read_text(encoding="utf-8")
		self.assertIn('"fieldname": "fleet_service_campaign"', source)
		for doctype in ("Repair Job", "Sales Order", "Sales Invoice"):
			self.assertIn(f'"{doctype}"', source)

	def test_campaign_proforma_prints_campaign_and_per_line_source(self):
		template = PROFORMA_TEMPLATE.read_text(encoding="utf-8")
		self.assertIn("doc.fleet_service_campaign", template)
		self.assertIn("row.repair_job", template)
		self.assertIn("row.customer_vehicle", template)
		self.assertIn('print_title = "Proforma Invoice"', template)


class TestFleetCampaignDocumentSummary(UnitTestCase):
	def test_summary_rpc_is_resolvable_at_native_controller_path(self):
		method_path = (
			"auto_service_management.auto_service_management.doctype."
			"fleet_service_campaign.fleet_service_campaign.get_campaign_sales_document_summary"
		)
		self.assertIs(
			frappe.get_attr(method_path),
			fleet_service_campaign.get_campaign_sales_document_summary,
		)

	def test_summary_is_permission_scoped_and_separates_document_types(self):
		campaign = frappe._dict(name="FSC-1")
		campaign.check_permission = MagicMock()
		order = frappe._dict(name="SO-1", status="To Deliver and Bill")
		invoice = frappe._dict(name="SINV-1", status="Unpaid")
		with (
			patch.object(fleet_service_campaign.frappe, "get_doc", return_value=campaign),
			patch.object(fleet_service_campaign.frappe, "has_permission", return_value=True),
			patch.object(
				fleet_service_campaign.frappe,
				"get_list",
				side_effect=[[order], [invoice]],
			) as get_list,
		):
			result = fleet_service_campaign.get_campaign_sales_document_summary("FSC-1")

		campaign.check_permission.assert_called_once_with("read")
		self.assertEqual(result["sales_orders"], [order])
		self.assertEqual(result["sales_invoices"], [invoice])
		self.assertEqual(get_list.call_count, 2)
		for call in get_list.call_args_list:
			self.assertEqual(call.kwargs["filters"], {"fleet_service_campaign": "FSC-1"})

	def test_summary_does_not_query_or_disclose_unreadable_sales_documents(self):
		campaign = frappe._dict(name="FSC-1")
		campaign.check_permission = MagicMock()
		with (
			patch.object(fleet_service_campaign.frappe, "get_doc", return_value=campaign),
			patch.object(
				fleet_service_campaign.frappe,
				"has_permission",
				side_effect=lambda doctype, _ptype: doctype == "Sales Order",
			),
			patch.object(
				fleet_service_campaign.frappe,
				"get_list",
				return_value=[frappe._dict(name="SO-1")],
			) as get_list,
		):
			result = fleet_service_campaign.get_campaign_sales_document_summary("FSC-1")

		self.assertEqual([row.name for row in result["sales_orders"]], ["SO-1"])
		self.assertEqual(result["sales_invoices"], [])
		get_list.assert_called_once()
		self.assertEqual(get_list.call_args.args[0], "Sales Order")

	def test_campaign_mapping_wrappers_delegate_to_campaign_backend(self):
		target = frappe._dict(doctype="Sales Order")
		with patch.object(
			fleet_service_campaign,
			"map_campaign_sales_order",
			return_value=target,
		) as mapper:
			result = fleet_service_campaign.make_sales_order(
				"FSC-1",
				target_doc={"doctype": "Sales Order"},
				component_refs='[{"doctype":"Repair Job Service Part","name":"PART-1"}]',
			)

		self.assertIs(result, target)
		mapper.assert_called_once_with(
			"FSC-1",
			target_doc={"doctype": "Sales Order"},
			component_refs='[{"doctype":"Repair Job Service Part","name":"PART-1"}]',
		)

	def test_campaign_mapping_wrappers_read_open_mapped_doc_args(self):
		refs = '[{"doctype":"Repair Job Service Part","name":"PART-2"}]'
		original_args = getattr(frappe.flags, "args", None)
		frappe.flags.args = frappe._dict(component_refs=refs)
		try:
			with patch.object(
				fleet_service_campaign,
				"map_campaign_sales_invoice",
				return_value=frappe._dict(doctype="Sales Invoice"),
			) as mapper:
				fleet_service_campaign.make_sales_invoice("FSC-1")
		finally:
			frappe.flags.args = original_args

		mapper.assert_called_once_with("FSC-1", target_doc=None, component_refs=refs)


if __name__ == "__main__":
	unittest.main()
