from __future__ import annotations

import frappe

from auto_service_management.auto_service_management.custom_fields import ensure_trace_custom_fields
from auto_service_management.auto_service_management.doctype.repair_job_service.repair_job_service import (
	COMPONENT_TABLE_BY_TYPE,
)
from auto_service_management.auto_service_management.doctype.repair_service_line.repair_service_line import (
	SERVICE_TYPE_ALIASES,
)


def execute():
	ensure_trace_custom_fields()
	_migrate_live_service_components()
	_migrate_template_components()


def _migrate_live_service_components():
	if not frappe.db.table_exists("Repair Service Line"):
		return
	if not frappe.db.table_exists("Repair Job Service"):
		return
	generic_lines = frappe.get_all(
		"Repair Service Line",
		filters={"parenttype": "Repair Job Service", "parentfield": ["!=", "legacy_components"]},
		fields=["name", "parent", "idx", "service_type"],
		order_by="parent asc, idx asc",
		limit_page_length=0,
	)
	for line in generic_lines:
		line_doc = frappe.get_doc("Repair Service Line", line.name)
		component_type = SERVICE_TYPE_ALIASES.get(line_doc.service_type, line_doc.service_type)
		if component_type == "Other":
			component_type = "Subcontracted Service"
		definition = COMPONENT_TABLE_BY_TYPE.get(component_type)
		if not definition:
			continue
		if frappe.db.exists(definition["doctype"], {"legacy_repair_service_line": line_doc.name}):
			_mark_legacy_line(line_doc)
			continue

		service = frappe.get_doc("Repair Job Service", line.parent)
		service.append(definition["fieldname"], _legacy_line_to_component_row(line_doc, component_type))
		service.save(ignore_permissions=True)
		_mark_legacy_line(line_doc)


def _migrate_template_components():
	if not frappe.db.table_exists("Repair Service Template Component"):
		return
	if not frappe.db.table_exists("Repair Service Template"):
		return

	template_components = frappe.get_all(
		"Repair Service Template Component",
		filters={"parenttype": "Repair Service Template", "parentfield": ["!=", "legacy_components"]},
		fields=["name", "parent", "idx", "service_type"],
		order_by="parent asc, idx asc",
		limit_page_length=0,
	)
	for row in template_components:
		component_doc = frappe.get_doc("Repair Service Template Component", row.name)
		component_type = SERVICE_TYPE_ALIASES.get(component_doc.service_type, component_doc.service_type)
		if component_type == "Other":
			component_type = "Subcontracted Service"
		fieldname = _template_fieldname(component_type)
		if not fieldname:
			continue

		template = frappe.get_doc("Repair Service Template", row.parent)
		template.append(fieldname, _legacy_template_component_to_row(component_doc, component_type))
		template.save(ignore_permissions=True)
		_mark_legacy_template_component(component_doc)


def _legacy_line_to_component_row(line_doc, component_type):
	row = {
		"repair_job": line_doc.repair_job,
		"repair_job_service": line_doc.repair_job_service or line_doc.parent,
		"customer_vehicle": line_doc.customer_vehicle,
		"description": line_doc.service_description or line_doc.name,
		"status": line_doc.status or "Pending Approval",
		"billable": line_doc.billable if line_doc.billable is not None else 1,
		"currency": line_doc.currency,
		"item_code": line_doc.item_code,
		"rate": line_doc.rate,
		"amount": line_doc.amount,
		"discount_percentage": line_doc.discount_percentage,
		"discount_amount": line_doc.discount_amount,
		"tax_amount": line_doc.tax_amount,
		"cost_rate": line_doc.cost_rate,
		"cost_amount": line_doc.cost_amount,
		"margin_amount": line_doc.margin_amount,
		"margin_percentage": line_doc.margin_percentage,
		"quotation": line_doc.quotation,
		"quotation_item": line_doc.quotation_item,
		"sales_order": line_doc.sales_order,
		"sales_order_item": line_doc.sales_order_item,
		"sales_invoice": line_doc.sales_invoice,
		"sales_invoice_item": line_doc.sales_invoice_item,
		"legacy_repair_service_line": line_doc.name,
	}
	if component_type in {"Part", "Consumable"}:
		row.update(
			{
				"quantity": line_doc.quantity,
				"uom": line_doc.uom,
				"warehouse": line_doc.warehouse,
				"requested_qty": line_doc.requested_qty,
				"issued_qty": line_doc.issued_qty,
				"stock_request_status": line_doc.stock_request_status,
				"material_request": line_doc.material_request,
				"material_request_item": line_doc.material_request_item,
				"stock_entry": line_doc.stock_entry,
				"stock_entry_detail": line_doc.stock_entry_detail,
			}
		)
	if component_type == "Labour":
		row.update(
			{
				"assigned_to": line_doc.assigned_to,
				"activity_type": line_doc.activity_type,
				"task": line_doc.task,
				"estimated_hours": line_doc.estimated_hours or line_doc.quantity,
				"actual_hours": line_doc.actual_hours,
				"timesheet": line_doc.timesheet,
				"timesheet_detail": line_doc.timesheet_detail,
			}
		)
	if component_type == "Subcontracted Service":
		row.update({"supplier": getattr(line_doc, "supplier", None)})
	return row


def _legacy_template_component_to_row(component_doc, component_type):
	row = {
		"description": component_doc.service_description or component_doc.name,
		"item_code": component_doc.item_code,
		"rate": component_doc.rate,
		"cost_rate": component_doc.cost_rate,
		"billable": component_doc.billable if component_doc.billable is not None else 1,
	}
	if component_type in {"Part", "Consumable"}:
		row.update(
			{
				"quantity": component_doc.quantity,
				"uom": component_doc.uom,
				"warehouse": component_doc.warehouse,
			}
		)
	if component_type == "Labour":
		row["estimated_hours"] = component_doc.estimated_hours or component_doc.quantity or 1
	if component_type == "Subcontracted Service":
		row["supplier"] = getattr(component_doc, "supplier", None)
	return row


def _template_fieldname(component_type):
	return {
		"Part": "parts",
		"Labour": "labour",
		"Consumable": "consumables",
		"Subcontracted Service": "subcontracted_services",
	}.get(component_type)


def _mark_legacy_line(line_doc):
	frappe.db.set_value(
		"Repair Service Line",
		line_doc.name,
		{"parentfield": "legacy_components"},
		update_modified=False,
	)


def _mark_legacy_template_component(component_doc):
	frappe.db.set_value(
		"Repair Service Template Component",
		component_doc.name,
		{"parentfield": "legacy_components"},
		update_modified=False,
	)
