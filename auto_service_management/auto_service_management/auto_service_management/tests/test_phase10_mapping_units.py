from unittest.mock import patch

import frappe
from frappe.tests import UnitTestCase

from auto_service_management.auto_service_management.doctype.repair_job_service.repair_job_service import (
	ServiceComponent,
)
from auto_service_management.auto_service_management.integration.erpnext import (
	component_mapping,
	document_sync,
)


class TestPhase10MappingUnits(UnitTestCase):
	def test_labour_invoice_item_uses_billing_fields(self):
		job = frappe._dict(name="RJ-1", customer_vehicle="VEH-1", project="PROJ-1")
		service = frappe._dict(name="RJS-1", service_name="Brake service")
		row = frappe._dict(
			doctype="Repair Job Service Labour",
			name="LAB-1",
			description="Brake labour",
			item_code="LABOUR-ITEM",
			hours=4,
			billing_hours=2.5,
			billing_rate=60000,
			billing_amount=150000,
			legacy_repair_service_line=None,
		)
		component = ServiceComponent(service, row, "labour", "Labour")

		with patch.object(component_mapping.frappe.db, "get_value", return_value="Hour"):
			item = component_mapping._sales_invoice_item(job, service, component)

		self.assertEqual(item["qty"], 2.5)
		self.assertEqual(item["rate"], 60000)
		self.assertEqual(item["uom"], "Hour")

	def test_itemless_labour_maps_as_description_row(self):
		job = frappe._dict(name="RJ-1", customer_vehicle="VEH-1", project="PROJ-1")
		service = frappe._dict(name="RJS-1", service_name="Brake service")
		row = frappe._dict(
			doctype="Repair Job Service Labour",
			name="LAB-1",
			description="Brake labour",
			item_code=None,
			billing_hours=2.5,
			billing_rate=60000,
			billing_amount=150000,
			legacy_repair_service_line=None,
		)
		component = ServiceComponent(service, row, "labour", "Labour")

		item = component_mapping._sales_invoice_item(job, service, component)

		self.assertIsNone(item["item_code"])
		self.assertEqual(item["item_name"], "Brake labour")
		self.assertEqual(item["qty"], 2.5)
		self.assertEqual(item["uom"], "Hour")
		self.assertEqual(item["rate"], 60000)

	def test_itemless_stock_component_uses_nos_uom(self):
		job = frappe._dict(name="RJ-1", customer_vehicle="VEH-1", project="PROJ-1")
		service = frappe._dict(name="RJS-1", service_name="Cleaning service")
		row = frappe._dict(
			doctype="Repair Job Service Consumable",
			name="CON-1",
			description="Cleaning material",
			item_code=None,
			quantity=1,
			rate=10000,
			discount_percentage=0,
			legacy_repair_service_line=None,
		)
		component = ServiceComponent(service, row, "consumables", "Consumable")

		item = component_mapping._sales_invoice_item(job, service, component)

		self.assertIsNone(item["item_code"])
		self.assertEqual(item["item_name"], "Cleaning material")
		self.assertEqual(item["uom"], "Nos")

	def test_current_target_is_not_treated_as_another_draft(self):
		component = frappe._dict(sales_invoice="SINV-DRAFT-1")

		self.assertFalse(
			component_mapping._has_active_link(
				component,
				"Sales Invoice",
				"sales_invoice",
				current_target_name="SINV-DRAFT-1",
			)
		)

	def test_material_request_item_removal_resets_request_trace(self):
		doc = frappe._dict(name="MAT-MR-1", items=[])

		def get_all(doctype, **kwargs):
			if doctype == "Repair Job Service Part":
				return ["PART-1"]
			return []

		with (
			patch.object(document_sync.frappe.db, "table_exists", return_value=True),
			patch.object(document_sync.frappe, "get_all", side_effect=get_all),
			patch.object(document_sync.frappe.db, "set_value") as set_value,
		):
			document_sync._reconcile_component_links(
				doc,
				linked_field="material_request",
				linked_item_field="material_request_item",
				release_values={"requested_qty": 0, "stock_request_status": "Not Requested"},
			)

		set_value.assert_any_call(
			"Repair Job Service Part",
			"PART-1",
			{
				"material_request": None,
				"material_request_item": None,
				"requested_qty": 0,
				"stock_request_status": "Not Requested",
			},
			update_modified=False,
		)

	def test_material_request_sync_skips_component_doctypes_without_trace_field(self):
		doc = frappe._dict(
			name="MAT-MR-2",
			items=[
				frappe._dict(
					name="MRI-1",
					repair_component_doctype="Repair Job Service Part",
					repair_component_row="PART-1",
					qty=1,
				)
			],
		)
		meta_by_doctype = {
			"Repair Job Service Part": frappe._dict(get_field=lambda field: field == "material_request"),
			"Repair Job Service Labour": frappe._dict(get_field=lambda field: False),
			"Repair Job Service Consumable": frappe._dict(
				get_field=lambda field: field == "material_request"
			),
			"Repair Job Service Subcontracted Service": frappe._dict(get_field=lambda field: False),
		}

		def get_all(doctype, **kwargs):
			if doctype in {"Repair Job Service Part", "Repair Job Service Consumable"}:
				return []
			raise AssertionError(f"unexpected get_all call for {doctype}")

		with (
			patch.object(document_sync.frappe.db, "table_exists", return_value=True),
			patch.object(
				document_sync.frappe, "get_meta", side_effect=lambda doctype: meta_by_doctype[doctype]
			),
			patch.object(document_sync.frappe, "get_all", side_effect=get_all),
			patch.object(document_sync.frappe.db, "set_value") as set_value,
		):
			document_sync.sync_material_request(doc)

		set_value.assert_any_call(
			"Repair Job Service Part",
			"PART-1",
			{
				"material_request": "MAT-MR-2",
				"material_request_item": "MRI-1",
				"requested_qty": 1.0,
				"stock_request_status": "Requested",
			},
			update_modified=False,
		)

	def test_invoice_completeness_requires_every_component_to_be_submitted(self):
		components = [
			(frappe._dict(), frappe._dict(sales_invoice="SINV-1")),
			(frappe._dict(), frappe._dict(sales_invoice=None)),
		]
		with (
			patch.object(document_sync, "iter_repair_job_components", return_value=components),
			patch.object(document_sync.frappe.db, "get_value", return_value=1),
		):
			self.assertFalse(document_sync._all_billable_components_submitted("RJ-1"))
			document_sync.iter_repair_job_components.assert_called_once_with(
				"RJ-1",
				service_statuses={"Approved", "Completed"},
				billable_only=True,
			)

		components[1][1].sales_invoice = "SINV-2"
		with (
			patch.object(document_sync, "iter_repair_job_components", return_value=components),
			patch.object(document_sync.frappe.db, "get_value", return_value=1),
		):
			self.assertTrue(document_sync._all_billable_components_submitted("RJ-1"))

	def test_labour_invoice_item_preserves_zero_billing_rate(self):
		job = frappe._dict(name="RJ-1", customer_vehicle="VEH-1", project="PROJ-1")
		service = frappe._dict(name="RJS-1", service_name="Brake service")
		row = frappe._dict(
			doctype="Repair Job Service Labour",
			name="LAB-1",
			description="Brake labour",
			item_code="LABOUR-ITEM",
			billing_hours=2.5,
			billing_rate=0,
			legacy_repair_service_line=None,
		)
		component = ServiceComponent(service, row, "labour", "Labour")

		item = component_mapping._sales_invoice_item(job, service, component)

		self.assertEqual(item["rate"], 0)
