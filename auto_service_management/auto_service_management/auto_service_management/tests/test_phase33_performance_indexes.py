from __future__ import annotations

import unittest
from unittest.mock import patch

import frappe

from auto_service_management.auto_service_management.integration.erpnext import document_sync
from auto_service_management.patches.phase33_performance_indexes import INDEXES, execute


class TestPhase33PerformanceIndexes(unittest.TestCase):
	def test_billable_invoice_statuses_are_loaded_in_one_batch(self):
		components = [
			frappe._dict({"sales_invoice": "SINV-1"}),
			frappe._dict({"sales_invoice": "SINV-2"}),
		]
		with (
			patch.object(
				document_sync,
				"iter_repair_job_components",
				return_value=[(None, component) for component in components],
			),
			patch.object(
				document_sync.frappe,
				"get_all",
				return_value=[
					frappe._dict({"name": "SINV-1", "docstatus": 1}),
					frappe._dict({"name": "SINV-2", "docstatus": 1}),
				],
			) as get_all,
		):
			self.assertTrue(document_sync._all_billable_components_submitted("RJ-1"))

		get_all.assert_called_once_with(
			"Sales Invoice",
			filters={"name": ["in", ["SINV-1", "SINV-2"]]},
			fields=["name", "docstatus"],
			limit_page_length=2,
		)

	def test_index_contract_is_explicit_and_deterministic(self):
		self.assertEqual(
			INDEXES,
			(
				("Repair Job", ("customer", "creation"), "repair_job_customer_creation_idx"),
				("Repair Job", ("job_status", "creation"), "repair_job_status_creation_idx"),
				(
					"Repair Job Service",
					("repair_job", "docstatus", "creation"),
					"repair_job_service_job_docstatus_creation_idx",
				),
				("Sales Invoice", ("repair_job", "docstatus"), "sales_invoice_repair_job_docstatus_idx"),
				("Sales Invoice", ("customer_lpo", "docstatus"), "sales_invoice_customer_lpo_docstatus_idx"),
				(
					"Sales Invoice Item",
					("repair_component_doctype", "repair_component_row"),
					"sales_invoice_item_component_trace_idx",
				),
				(
					"Sales Order Item",
					("repair_component_doctype", "repair_component_row"),
					"sales_order_item_component_trace_idx",
				),
				(
					"Material Request Item",
					("repair_component_doctype", "repair_component_row"),
					"material_request_item_component_trace_idx",
				),
				(
					"Sales Invoice Item",
					("repair_job", "repair_job_service"),
					"sales_invoice_item_job_service_idx",
				),
				(
					"Sales Order Item",
					("repair_job", "repair_job_service"),
					"sales_order_item_job_service_idx",
				),
				(
					"Material Request Item",
					("repair_job", "repair_job_service"),
					"material_request_item_job_service_idx",
				),
				("Repair Job Service Part", ("sales_order",), "repair_part_sales_order_idx"),
				("Repair Job Service Part", ("sales_invoice",), "repair_part_sales_invoice_idx"),
				("Repair Job Service Part", ("material_request",), "repair_part_material_request_idx"),
				("Repair Job Service Labour", ("sales_order",), "repair_labour_sales_order_idx"),
				("Repair Job Service Labour", ("sales_invoice",), "repair_labour_sales_invoice_idx"),
				("Repair Job Service Consumable", ("sales_order",), "repair_consumable_sales_order_idx"),
				("Repair Job Service Consumable", ("sales_invoice",), "repair_consumable_sales_invoice_idx"),
				(
					"Repair Job Service Consumable",
					("material_request",),
					"repair_consumable_material_request_idx",
				),
			),
		)

	def test_missing_optional_fields_are_skipped(self):
		class Meta:
			def has_field(self, fieldname):
				return fieldname not in {"repair_job", "customer_lpo"}

		with (
			patch(
				"auto_service_management.patches.phase33_performance_indexes.frappe.get_meta",
				return_value=Meta(),
			),
			patch(
				"auto_service_management.patches.phase33_performance_indexes.frappe.db.add_index"
			) as add_index,
		):
			execute()

		self.assertEqual(add_index.call_count, 13)
		self.assertEqual(add_index.call_args_list[0].args, ("Repair Job", ["customer", "creation"]))
