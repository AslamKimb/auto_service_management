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
	_migrate_legacy_repair_job_service_lines()


def _migrate_legacy_repair_job_service_lines():
	if not frappe.db.table_exists("Repair Service Line"):
		return
	if not frappe.db.table_exists("Repair Job Service"):
		return

	legacy_lines = frappe.get_all(
		"Repair Service Line",
		filters={"parenttype": "Repair Job"},
		fields=["name", "parent", "idx", "service_type", "service_description", "status"],
		order_by="parent asc, idx asc",
		limit_page_length=0,
	)
	for line in legacy_lines:
		line_doc = frappe.get_doc("Repair Service Line", line.name)
		job = frappe.db.get_value(
			"Repair Job",
			line.parent,
			["name", "customer", "customer_vehicle", "diagnosis_report", "currency"],
			as_dict=True,
		)
		if not job:
			continue

		service = frappe.get_doc(
			{
				"doctype": "Repair Job Service",
				"repair_job": job.name,
				"customer": job.customer,
				"customer_vehicle": job.customer_vehicle,
				"diagnosis_report": job.diagnosis_report,
				"service_name": line.service_description or line.name,
				"status": line.status or "Pending Approval",
				"billable": 1,
				"currency": job.currency,
			}
		)
		service.insert(ignore_permissions=True)

		_append_typed_component_from_legacy_line(service, line_doc, job)

		frappe.db.set_value(
			"Repair Service Line",
			line.name,
			{
				"parent": service.name,
				"parenttype": "Repair Job Service",
				"parentfield": "legacy_components",
				"repair_job": job.name,
				"repair_job_service": service.name,
				"customer_vehicle": job.customer_vehicle,
				"currency": job.currency,
				"service_type": SERVICE_TYPE_ALIASES.get(line.service_type, line.service_type),
				"billable": 1,
			},
			update_modified=False,
		)
		service.reload()
		service.save(ignore_permissions=True)


def _append_typed_component_from_legacy_line(service, line_doc, job):
	component_type = SERVICE_TYPE_ALIASES.get(line_doc.service_type, line_doc.service_type)
	if component_type == "Other":
		component_type = "Subcontracted Service"
	definition = COMPONENT_TABLE_BY_TYPE.get(component_type)
	if not definition:
		return

	row = {
		"repair_job": job.name,
		"repair_job_service": service.name,
		"customer_vehicle": job.customer_vehicle,
		"description": line_doc.service_description or line_doc.name,
		"status": line_doc.status or "Pending Approval",
		"billable": line_doc.billable if line_doc.billable is not None else 1,
		"currency": job.currency,
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
	service.append(definition["fieldname"], row)
