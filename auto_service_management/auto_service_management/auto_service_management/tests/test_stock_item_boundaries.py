from pathlib import Path
from unittest.mock import patch

import frappe
from frappe.tests import UnitTestCase

from auto_service_management.auto_service_management.doctype.repair_job_service import repair_job_service
from auto_service_management.auto_service_management.doctype.repair_job_service_consumable.repair_job_service_consumable import (
	RepairJobServiceConsumable,
)
from auto_service_management.auto_service_management.doctype.repair_job_service_part.repair_job_service_part import (
	RepairJobServicePart,
)
from auto_service_management.auto_service_management.doctype.repair_job_service_labour.repair_job_service_labour import (
	RepairJobServiceLabour,
)
from auto_service_management.auto_service_management.doctype.repair_job_service.repair_job_service import (
	ServiceComponent,
)
from auto_service_management.auto_service_management.integration.erpnext import (
	component_mapping,
	document_sync,
)


SERVICE_JS = Path(__file__).parents[1] / "doctype" / "repair_job_service" / "repair_job_service.js"


def _component(doctype, name, item_code, component_type):
	service = frappe._dict(name="RJS-1", docstatus=0, service_name="Brake service")
	row = frappe._dict(
		doctype=doctype,
		name=name,
		item_code=item_code,
		billable=1,
		quantity=1,
		rate=1,
		discount_percentage=0,
		cost_rate=0,
		hours=1,
		billing_hours=1,
		billing_rate=1,
		costing_rate=0,
	)
	return service, ServiceComponent(service, row, component_type.lower() + "s", component_type)


class TestStockItemBoundaries(UnitTestCase):
	def test_repair_job_service_filters_each_child_table_by_maintain_stock(self):
		source = SERVICE_JS.read_text(encoding="utf-8")

		self.assertIn("frm.set_query('item_code', 'parts'", source)
		self.assertIn("frm.set_query('item_code', 'consumables'", source)
		self.assertIn("filters: { disabled: 0, is_stock_item: 1 }", source)
		self.assertIn("filters: { disabled: 0, is_stock_item: 0, is_sales_item: 1, stock_uom: 'Hour' }", source)

	def test_part_rejects_non_stock_item(self):
		part = RepairJobServicePart(
			{
				"doctype": "Repair Job Service Part",
				"item_code": "LABOUR-ITEM",
				"quantity": 1,
				"rate": 0,
				"billable": 1,
			}
		)
		with (
			patch(
			"auto_service_management.auto_service_management.item_fitment_compatibility.apply_fitment_snapshot"
			),
			patch.object(
				repair_job_service.frappe.db,
				"get_value",
				return_value=frappe._dict(
					disabled=0,
					is_stock_item=0,
					is_sales_item=1,
					stock_uom="Hour",
				),
			),
		):
			with self.assertRaises(frappe.ValidationError):
				part.validate()

	def test_consumable_rejects_non_stock_item(self):
		consumable = RepairJobServiceConsumable(
			{
				"doctype": "Repair Job Service Consumable",
				"item_code": "LABOUR-ITEM",
				"quantity": 1,
				"rate": 0,
				"billable": 1,
			}
		)
		with patch.object(
			repair_job_service.frappe.db,
			"get_value",
			return_value=frappe._dict(
				disabled=0,
				is_stock_item=0,
				is_sales_item=1,
				stock_uom="Hour",
			),
		):
			with self.assertRaises(frappe.ValidationError):
				consumable.validate()

	def test_labour_rejects_stock_item(self):
		labour = RepairJobServiceLabour(
			{
				"doctype": "Repair Job Service Labour",
				"item_code": "STOCK-ITEM",
				"hours": 1,
				"billing_hours": 1,
				"billing_rate": 1,
				"costing_rate": 0,
				"billable": 1,
			}
		)
		with patch.object(
			repair_job_service.frappe.db,
			"get_value",
			return_value=frappe._dict(
				disabled=0,
				is_stock_item=1,
				is_sales_item=1,
				stock_uom="Nos",
			),
		):
			with self.assertRaises(frappe.ValidationError):
				labour.validate()

	def test_stock_only_component_iteration_excludes_non_stock_items(self):
		stock = _component("Repair Job Service Part", "PART-1", "STOCK-ITEM", "Part")
		non_stock = _component("Repair Job Service Consumable", "CON-1", "LABOUR-ITEM", "Consumable")

		with (
			patch.object(repair_job_service, "get_repair_job_services", return_value=[stock[0]]),
			patch.object(
				repair_job_service.frappe.db,
				"get_value",
				side_effect=lambda doctype, name, fieldname, *args, **kwargs: {
					"STOCK-ITEM": 1,
					"LABOUR-ITEM": 0,
				}.get(name),
			),
			patch.object(
				repair_job_service,
				"get_service_components",
				return_value=[stock[1], non_stock[1]],
			),
		):
			components = list(
				repair_job_service.iter_repair_job_components(
					"RJ-1",
					component_types={"Part", "Consumable"},
					stock_only=True,
				)
			)

		self.assertEqual([component.name for _, component in components], ["PART-1"])

	def test_material_request_mapping_requests_stock_only_components(self):
		target = frappe._dict(doctype="Material Request", name=None, docstatus=0, items=[])
		target.is_new = lambda: True
		target.set = lambda fieldname, value: target.update({fieldname: value})
		target.append = lambda fieldname, value: target[fieldname].append(value)
		target.run_method = lambda method: None

		with (
			patch.object(component_mapping, "_get_repair_job", return_value=frappe._dict(name="RJ-1")),
			patch.object(component_mapping, "_get_target_doc", return_value=target),
			patch.object(component_mapping, "_validate_target_job"),
			patch.object(component_mapping, "_validate_service_scope"),
			patch.object(component_mapping, "_validate_requested_component_refs"),
			patch.object(component_mapping, "_eligible_components", return_value=([], {})) as eligible,
			patch.object(component_mapping, "_get_settings", return_value=frappe._dict(company="COMPANY-1")),
			patch.object(component_mapping, "get_material_request_types", return_value=["Material Issue"]),
		):
			with self.assertRaises(frappe.ValidationError):
				component_mapping.map_material_request("RJ-1")

		self.assertTrue(eligible.call_args.kwargs["stock_only"])

	def test_material_request_validation_rejects_traced_non_stock_item(self):
		line = frappe._dict(
			repair_component_doctype="Repair Job Service Part",
			repair_component_row="PART-1",
			qty=1,
		)
		with (
			patch.object(document_sync, "_trace_items", return_value=[line]),
			patch.object(document_sync, "item_maintains_stock", return_value=False, create=True),
			patch.object(document_sync.frappe.db, "get_value", return_value=1),
		):
			with self.assertRaises(frappe.ValidationError):
				document_sync._validate_component_quantities(frappe._dict(items=[line]), stock_only=True)
