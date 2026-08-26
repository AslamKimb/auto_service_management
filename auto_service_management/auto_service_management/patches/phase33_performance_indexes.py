"""Idempotent indexes for the DMS lookup paths measured in Phase 33."""

from __future__ import annotations

import frappe

INDEXES: tuple[tuple[str, tuple[str, ...], str], ...] = (
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
	("Sales Invoice Item", ("repair_job", "repair_job_service"), "sales_invoice_item_job_service_idx"),
	("Sales Order Item", ("repair_job", "repair_job_service"), "sales_order_item_job_service_idx"),
	("Material Request Item", ("repair_job", "repair_job_service"), "material_request_item_job_service_idx"),
	("Repair Job Service Part", ("sales_order",), "repair_part_sales_order_idx"),
	("Repair Job Service Part", ("sales_invoice",), "repair_part_sales_invoice_idx"),
	("Repair Job Service Part", ("material_request",), "repair_part_material_request_idx"),
	("Repair Job Service Labour", ("sales_order",), "repair_labour_sales_order_idx"),
	("Repair Job Service Labour", ("sales_invoice",), "repair_labour_sales_invoice_idx"),
	("Repair Job Service Consumable", ("sales_order",), "repair_consumable_sales_order_idx"),
	("Repair Job Service Consumable", ("sales_invoice",), "repair_consumable_sales_invoice_idx"),
	("Repair Job Service Consumable", ("material_request",), "repair_consumable_material_request_idx"),
)
STANDARD_COLUMNS = frozenset({"name", "creation", "modified", "modified_by", "owner", "docstatus", "idx"})


def execute() -> None:
	"""Create measured indexes when their fields exist on the current site."""
	for doctype, fields, index_name in INDEXES:
		meta = frappe.get_meta(doctype)
		if all(fieldname in STANDARD_COLUMNS or meta.has_field(fieldname) for fieldname in fields):
			frappe.db.add_index(doctype, list(fields), index_name=index_name)
