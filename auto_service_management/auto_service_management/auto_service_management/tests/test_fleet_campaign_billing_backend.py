from unittest.mock import patch

import frappe
from frappe.handler import is_valid_http_method
from frappe.tests import UnitTestCase

from auto_service_management.auto_service_management import custom_fields
from auto_service_management.auto_service_management.integration import sales_order_mapping
from auto_service_management.auto_service_management.integration.erpnext import (
	component_mapping,
	document_sync,
)


class _Target:
	def __init__(self, doctype):
		self.doctype = doctype
		self.docstatus = 0
		self.name = None
		self.items = []
		self.values = {}

	def get(self, fieldname):
		if fieldname == "items":
			return self.items
		return self.values.get(fieldname)

	def set(self, fieldname, value):
		self.values[fieldname] = value
		setattr(self, fieldname, value)

	def append(self, fieldname, value):
		assert fieldname == "items"
		self.items.append(value)

	def is_new(self):
		return True

	def run_method(self, _method):
		return None


class _Row(dict):
	def get(self, key, default=None):
		return super().get(key, default)

	def set(self, key, value):
		self[key] = value


class TestFleetCampaignBillingBackend(UnitTestCase):
	def _complete_trace(self, repair_job="RJ-1", suffix="1"):
		return frappe._dict(
			repair_job=repair_job,
			customer_vehicle=f"VEH-{suffix}",
			repair_job_service=f"RJS-{suffix}",
			repair_component_doctype="Repair Job Service Part",
			repair_component_row=f"PART-{suffix}",
			project=f"PROJ-{suffix}",
		)

	def _authoritative_trace(self):
		return frappe._dict(
			repair_job="RJ-1",
			customer_vehicle="VEH-1",
			repair_job_service="RJS-1",
			repair_component_doctype="Repair Job Service Part",
			repair_component_row="PART-1",
			project="PROJ-1",
			sales_order=None,
			sales_order_item=None,
			sales_invoice=None,
			sales_invoice_item=None,
		)

	def _campaign_sales_doc(self, doctype="Sales Order"):
		return frappe._dict(
			doctype=doctype,
			name=None,
			fleet_service_campaign="FSC-1",
			repair_job=None,
			repair_job_service=None,
			project=None,
			customer="CUST-1",
			items=[self._complete_trace()],
		)

	def test_campaign_mappers_are_live_post_only_whitelisted_methods(self):
		for method in (
			component_mapping.map_campaign_sales_order,
			component_mapping.map_campaign_sales_invoice,
		):
			with self.subTest(method=method.__name__):
				self.assertIn(method, frappe.whitelisted)
				self.assertEqual(frappe.allowed_http_methods_for_whitelisted_func[method], ["POST"])
				original_request = getattr(frappe.local, "request", None)
				frappe.local.request = frappe._dict(method="GET")
				try:
					with self.assertRaises(frappe.PermissionError):
						is_valid_http_method(method)
				finally:
					frappe.local.request = original_request

	def test_sales_documents_include_campaign_parent_trace_fields(self):
		fields = custom_fields.get_trace_custom_fields()
		self.assertEqual(
			{row["fieldname"] for row in fields["Sales Order"]},
			{"repair_job", "repair_job_service", "fleet_service_campaign", "customer_lpo"},
		)
		self.assertEqual(
			{row["fieldname"] for row in fields["Sales Invoice"]},
			{"repair_job", "fleet_service_campaign", "customer_lpo"},
		)

	def test_campaign_scope_accepts_multiple_linked_jobs_and_clears_single_job_parent(self):
		doc = frappe._dict(
			fleet_service_campaign="FSC-1",
			repair_job=None,
			customer="CUST-1",
			items=[self._complete_trace("RJ-1", "1"), self._complete_trace("RJ-2", "2")],
		)
		campaign = frappe._dict(name="FSC-1", customer="CUST-1")
		jobs = {
			"RJ-1": frappe._dict(name="RJ-1", customer="CUST-1", fleet_service_campaign="FSC-1"),
			"RJ-2": frappe._dict(name="RJ-2", customer="CUST-1", fleet_service_campaign="FSC-1"),
		}

		def get_doc(doctype, name):
			return campaign if doctype == "Fleet Service Campaign" else jobs[name]

		with (
			patch.object(document_sync.frappe, "get_doc", side_effect=get_doc),
			patch.object(document_sync, "_validate_campaign_component_authority"),
		):
			result = document_sync._validate_sales_document_scope(doc)

		self.assertEqual({job.name for job in result}, {"RJ-1", "RJ-2"})
		self.assertIsNone(doc.repair_job)

	def test_campaign_scope_rejects_unlinked_job(self):
		doc = frappe._dict(
			fleet_service_campaign="FSC-1",
			repair_job=None,
			customer="CUST-1",
			items=[self._complete_trace("RJ-2", "2")],
		)
		campaign = frappe._dict(name="FSC-1", customer="CUST-1")
		job = frappe._dict(name="RJ-2", customer="CUST-1", fleet_service_campaign="FSC-OTHER")
		with (
			patch.object(document_sync.frappe, "get_doc", side_effect=[campaign, job]),
			patch.object(document_sync, "_validate_campaign_component_authority"),
			self.assertRaisesRegex(frappe.ValidationError, "does not belong"),
		):
			document_sync._validate_sales_document_scope(doc)

	def test_campaign_scope_rejects_fully_untraced_item(self):
		doc = frappe._dict(
			fleet_service_campaign="FSC-1",
			repair_job=None,
			customer="CUST-1",
			items=[frappe._dict(item_code="ITEM-1", qty=1)],
		)
		with self.assertRaisesRegex(frappe.ValidationError, "missing campaign trace fields"):
			document_sync._validate_sales_document_scope(doc)

	def test_campaign_scope_rejects_partial_trace_item(self):
		row = self._complete_trace()
		row.project = None
		doc = frappe._dict(
			fleet_service_campaign="FSC-1",
			repair_job=None,
			customer="CUST-1",
			items=[row],
		)
		with self.assertRaisesRegex(frappe.ValidationError, "project"):
			document_sync._validate_sales_document_scope(doc)

	def test_campaign_scope_rejects_mixed_campaign_and_single_job_parent(self):
		doc = frappe._dict(
			fleet_service_campaign="FSC-1",
			repair_job="RJ-1",
			customer="CUST-1",
			items=[self._complete_trace()],
		)
		with self.assertRaisesRegex(frappe.ValidationError, "cannot also have a parent Repair Job"):
			document_sync._validate_sales_document_scope(doc)

	def test_campaign_scope_rejects_forged_vehicle_trace(self):
		doc = self._campaign_sales_doc()
		doc.get("items")[0].customer_vehicle = "VEH-FORGED"
		with (
			patch.object(
				document_sync,
				"_resolve_campaign_component_authority",
				return_value=self._authoritative_trace(),
			),
			self.assertRaisesRegex(frappe.ValidationError, "customer_vehicle"),
		):
			document_sync._validate_campaign_component_authority(doc)

	def test_campaign_scope_rejects_forged_service_trace(self):
		doc = self._campaign_sales_doc()
		doc.get("items")[0].repair_job_service = "RJS-FORGED"
		with (
			patch.object(
				document_sync,
				"_resolve_campaign_component_authority",
				return_value=self._authoritative_trace(),
			),
			self.assertRaisesRegex(frappe.ValidationError, "repair_job_service"),
		):
			document_sync._validate_campaign_component_authority(doc)

	def test_campaign_scope_rejects_forged_project_trace(self):
		doc = self._campaign_sales_doc()
		doc.get("items")[0].project = "PROJ-FORGED"
		with (
			patch.object(
				document_sync,
				"_resolve_campaign_component_authority",
				return_value=self._authoritative_trace(),
			),
			self.assertRaisesRegex(frappe.ValidationError, "project"),
		):
			document_sync._validate_campaign_component_authority(doc)

	def test_campaign_scope_rejects_nonblank_parent_project(self):
		doc = self._campaign_sales_doc()
		doc.project = "PROJ-1"
		with self.assertRaisesRegex(frappe.ValidationError, "parent Project"):
			document_sync._validate_sales_document_scope(doc)

	def test_campaign_scope_rejects_nonblank_parent_repair_source(self):
		for fieldname, value in (("repair_job", "RJ-1"), ("repair_job_service", "RJS-1")):
			with self.subTest(fieldname=fieldname):
				doc = self._campaign_sales_doc()
				doc[fieldname] = value
				with self.assertRaisesRegex(frappe.ValidationError, "parent Repair Job"):
					document_sync._validate_sales_document_scope(doc)

	def test_manual_campaign_invoice_rejects_submitted_sales_order_overlap(self):
		doc = self._campaign_sales_doc("Sales Invoice")
		with (
			patch.object(
				document_sync,
				"_resolve_campaign_component_authority",
				return_value=self._authoritative_trace(),
			),
			patch.object(
				document_sync,
				"_submitted_component_document",
				side_effect=lambda _row, parent_doctype, _item_doctype, **_kwargs: (
					frappe._dict(parent="SO-1", item="SOI-1") if parent_doctype == "Sales Order" else None
				),
			),
			self.assertRaisesRegex(frappe.ValidationError, "submitted Sales Order SO-1"),
		):
			document_sync._validate_campaign_component_authority(doc)

	def test_campaign_sales_order_ignores_its_own_authoritative_order_link(self):
		doc = self._campaign_sales_doc()
		doc.name = "SO-1"
		authority = self._authoritative_trace()
		authority.sales_order = "SO-1"
		authority.sales_order_item = "SOI-1"
		with (
			patch.object(document_sync, "_resolve_campaign_component_authority", return_value=authority),
			patch.object(document_sync, "_submitted_component_document", return_value=None),
			patch.object(document_sync.frappe.db, "get_value", return_value=1),
		):
			document_sync._validate_campaign_component_authority(doc)

	def test_submitted_component_lookup_ignores_other_repair_job_service(self):
		row = frappe._dict(
			repair_component_doctype="Repair Job Service Part",
			repair_component_row="PART-1",
			repair_job_service="RJS-2",
		)
		other_service_item = frappe._dict(
			name="SOI-1",
			parent="SO-1",
			repair_job_service="RJS-1",
		)

		def get_all(_doctype, filters, **_kwargs):
			self.assertEqual(filters["repair_job_service"], row.repair_job_service)
			return (
				[other_service_item]
				if other_service_item.repair_job_service == filters["repair_job_service"]
				else []
			)

		with patch.object(document_sync.frappe, "get_all", side_effect=get_all):
			self.assertIsNone(
				document_sync._submitted_component_document(
					row,
					"Sales Order",
					"Sales Order Item",
				)
			)

	def test_submitted_component_lookup_still_detects_same_repair_job_service(self):
		row = frappe._dict(
			repair_component_doctype="Repair Job Service Part",
			repair_component_row="PART-1",
			repair_job_service="RJS-1",
		)
		same_service_item = frappe._dict(
			name="SOI-1",
			parent="SO-1",
			repair_job_service="RJS-1",
		)

		with (
			patch.object(document_sync.frappe, "get_all", return_value=[same_service_item]),
			patch.object(document_sync.frappe.db, "get_value", return_value=1),
		):
			result = document_sync._submitted_component_document(
				row,
				"Sales Order",
				"Sales Order Item",
			)

		self.assertEqual((result.parent, result.item), ("SO-1", "SOI-1"))

	def test_component_link_guard_ignores_duplicate_ref_from_other_repair_job_service(self):
		rows = [
			frappe._dict(
				repair_job="RJ-1",
				repair_job_service=service,
				repair_component_doctype="Repair Job Service Part",
				repair_component_row="PART-1",
			)
			for service in ("RJS-1", "RJS-2")
		]
		doc = frappe._dict(items=rows, name="SO-1")

		with (
			patch.object(document_sync.frappe.db, "exists", return_value=True),
			patch.object(
				document_sync.frappe.db,
				"get_value",
				return_value=frappe._dict(repair_job="RJ-1", sales_order=None),
			),
		):
			document_sync._validate_component_links(doc, "Sales Order", "sales_order")

	def test_campaign_sales_order_maps_only_explicit_available_components(self):
		target = _Target("Sales Order")
		campaign = frappe._dict(name="FSC-1", customer="CUST-1", campaign_end="2026-09-30", status="Ongoing")
		job_1 = frappe._dict(name="RJ-1", customer="CUST-1", customer_vehicle="VEH-1", project="PROJ-1")
		job_2 = frappe._dict(name="RJ-2", customer="CUST-1", customer_vehicle="VEH-2", project="PROJ-2")
		service_1 = frappe._dict(name="RJS-1", service_name="Brakes")
		service_2 = frappe._dict(name="RJS-2", service_name="Battery")
		component_1 = frappe._dict(row_doctype="Repair Job Service Part", name="PART-1")
		component_2 = frappe._dict(row_doctype="Repair Job Service Part", name="PART-2")

		with (
			patch.object(component_mapping, "_get_campaign", return_value=campaign) as get_campaign,
			patch.object(
				component_mapping,
				"_iter_campaign_components",
				return_value=[
					(job_1, service_1, component_1),
					(job_2, service_2, component_2),
				],
			),
			patch.object(component_mapping, "_get_target_doc", return_value=target),
			patch.object(component_mapping, "_validate_campaign_component_refs"),
			patch.object(component_mapping, "_component_invoice_state", return_value="Unbilled"),
			patch.object(component_mapping, "_component_sales_order_state", return_value="Available"),
			patch.object(
				component_mapping,
				"_sales_order_item",
				side_effect=lambda job, _service, component: {
					"repair_job": job.name,
					"repair_component_row": component.name,
				},
			),
			patch.object(
				component_mapping,
				"_get_settings",
				return_value=frappe._dict(company="Company", selling_price_list="Standard Selling"),
			),
		):
			result = component_mapping.map_campaign_sales_order(
				"FSC-1",
				component_refs=[{"doctype": "Repair Job Service Part", "name": "PART-2"}],
			)

		self.assertIs(result, target)
		get_campaign.assert_called_once_with("FSC-1", permission="write")
		self.assertEqual(target.fleet_service_campaign, "FSC-1")
		self.assertIsNone(target.repair_job)
		self.assertEqual(target.delivery_date, frappe.utils.getdate("2026-09-30"))
		self.assertEqual(
			target.items,
			[{"repair_job": "RJ-2", "repair_component_row": "PART-2"}],
		)

	def test_direct_campaign_invoice_rejects_component_committed_to_submitted_order(self):
		component = frappe._dict(
			billable=1,
			sales_invoice=None,
			sales_order="SO-1",
			sales_order_item="SOI-1",
		)
		with (
			patch.object(component_mapping, "_component_invoice_state", return_value="Unbilled"),
			patch.object(component_mapping, "_accepted_sales_order_item", return_value=("SO-1", "SOI-1")),
		):
			self.assertEqual(component_mapping._campaign_invoice_state(component), "Ordered")

	def test_campaign_selector_combines_jobs_and_preselects_only_available_components(self):
		campaign = frappe._dict(name="FSC-1", customer="CUST-1")
		jobs = [
			frappe._dict(name="RJ-1", customer_vehicle="VEH-1", registration_number="REG-1"),
			frappe._dict(name="RJ-2", customer_vehicle="VEH-2", registration_number="REG-2"),
		]
		services = [
			frappe._dict(name="RJS-1", service_name="Brakes"),
			frappe._dict(name="RJS-2", service_name="Battery"),
		]
		components = [
			frappe._dict(
				row_doctype="Repair Job Service Part",
				name="PART-1",
				component_type="Part",
				service_description="Pads",
				item_code="ITEM-1",
				invoice_quantity=1,
				invoice_rate=10,
				invoice_amount=10,
				billable=1,
				sales_invoice=None,
				sales_order=None,
				sales_order_item=None,
			),
			frappe._dict(
				row_doctype="Repair Job Service Labour",
				name="LAB-1",
				component_type="Labour",
				service_description="Install",
				item_code="LABOUR",
				invoice_quantity=2,
				invoice_rate=20,
				invoice_amount=40,
				billable=1,
				sales_invoice="SI-1",
				sales_order=None,
				sales_order_item=None,
			),
		]
		with (
			patch.object(component_mapping, "_get_campaign", return_value=campaign),
			patch.object(
				component_mapping,
				"_iter_campaign_components",
				return_value=[
					(jobs[0], services[0], components[0]),
					(jobs[1], services[1], components[1]),
				],
			),
			patch.object(component_mapping, "_sales_order_component_history", return_value={}),
			patch.object(component_mapping.frappe.db, "get_value", return_value=1),
		):
			result = component_mapping.get_campaign_sales_order_components("FSC-1")

		self.assertEqual({row["repair_job"] for row in result["components"]}, {"RJ-1", "RJ-2"})
		self.assertTrue(result["components"][0]["selectable"])
		self.assertFalse(result["components"][1]["selectable"])
		self.assertEqual(result["counts"]["Available"], 1)
		self.assertEqual(result["counts"]["Invoiced"], 1)

	def test_sales_order_to_invoice_propagates_campaign_and_item_traces(self):
		invoice_item = _Row(so_detail="SOI-1")
		invoice = frappe._dict(repair_job="STALE", fleet_service_campaign=None, items=[invoice_item])
		order_item = _Row(
			name="SOI-1",
			repair_job="RJ-2",
			customer_vehicle="VEH-2",
			repair_job_service="RJS-2",
			repair_component_doctype="Repair Job Service Part",
			repair_component_row="PART-2",
			repair_service_line="PART-2",
		)
		order = frappe._dict(
			repair_job=None,
			fleet_service_campaign="FSC-1",
			items=[order_item],
		)
		with (
			patch(
				"erpnext.selling.doctype.sales_order.sales_order.make_sales_invoice",
				return_value=invoice,
			),
			patch.object(sales_order_mapping.frappe, "get_doc", return_value=order),
		):
			result = sales_order_mapping.make_sales_invoice("SO-1")

		self.assertEqual(result.fleet_service_campaign, "FSC-1")
		self.assertIsNone(result.repair_job)
		self.assertEqual(invoice_item["repair_job"], "RJ-2")
		self.assertEqual(invoice_item["repair_component_row"], "PART-2")
