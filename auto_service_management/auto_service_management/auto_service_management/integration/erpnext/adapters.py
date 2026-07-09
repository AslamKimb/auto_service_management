# Copyright (c) 2026, Aslam Kimbugwe and contributors
# For license information, please see license.txt

"""
ERPNext Integration Adapters

All ERPNext internal API calls live here. The Repair Job controller
and other app code must call these functions instead of directly
invoking ERPNext internals. This keeps version-upgrade risk contained.
"""

import frappe
from frappe import _

from auto_service_management.auto_service_management.doctype.repair_job_service.repair_job_service import (
	EXCLUDED_COMPONENT_STATUSES,
	STOCK_COMPONENT_TYPES,
	iter_repair_job_components,
	set_component_values,
)


def get_settings():
	"""Return Auto Service Settings as a dict."""
	return frappe.get_single("Auto Service Settings")


def _make_doc(values):
	"""Small seam for adapter tests to mock ERPNext document creation."""
	return frappe.get_doc(values)


def _component_trace_fields(repair_job, service, line):
	return {
		"repair_job": repair_job.name,
		"customer_vehicle": repair_job.customer_vehicle,
		"repair_job_service": service.name,
		"repair_component_doctype": line.row_doctype,
		"repair_component_row": line.name,
		"repair_service_line": line.legacy_repair_service_line or line.name,
	}


def _component_description(service, line):
	service_name = service.service_name or service.name
	description = line.service_description or line.item_code or line.name
	return f"{service_name}: {description}"


def _eligible_components(
	repair_job,
	*,
	statuses=None,
	component_types=None,
	billable_only=False,
):
	return list(
		iter_repair_job_components(
			repair_job.name,
			statuses=statuses,
			component_types=component_types,
			billable_only=billable_only,
			include_excluded=False,
		)
	)


# ---------------------------------------------------------------------------
# Project
# ---------------------------------------------------------------------------


def create_project_for_repair_job(repair_job):
	"""Create an ERPNext Project linked to a Repair Job.

	Called idempotently on Check-In. Returns the Project name.
	"""
	if repair_job.project:
		return repair_job.project

	settings = get_settings()
	project = _make_doc(
		{
			"doctype": "Project",
			"project_name": f"RJ-{repair_job.name}",
			"customer": repair_job.customer,
			"expected_start_date": frappe.utils.today(),
			"expected_end_date": repair_job.promised_date,
			"company": settings.company,
			"status": "Working",
		}
	)
	project.insert(ignore_permissions=True)
	frappe.db.set_value(
		"Repair Job",
		repair_job.name,
		{"project": project.name},
	)
	return project.name


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------


def create_tasks_from_template(project_name, repair_job):
	"""Generate Tasks from the default Project Template.

	Each Task is linked to the Project, Repair Job, and Customer Vehicle.
	Returns a list of Task names.
	"""
	settings = get_settings()
	template_name = getattr(settings, "default_project_template", None)
	if not template_name:
		return []

	tasks = []
	template = frappe.get_doc("Project Template", template_name)
	for row in template.tasks:
		task = _make_doc(
			{
				"doctype": "Task",
				"project": project_name,
				"task_name": f"{repair_job.name} - {row.task_template}",
				"description": row.description,
				"status": "Open",
			}
		)
		task.insert(ignore_permissions=True)
		tasks.append(task.name)

	return tasks


# ---------------------------------------------------------------------------
# Pricing
# ---------------------------------------------------------------------------


def get_item_price(item_code, price_list=None):
	"""Fetch the selling price for an item from ERPNext price lists."""
	settings = get_settings()
	pl = price_list or settings.selling_price_list or settings.price_list

	result = frappe.get_all(
		"Item Price",
		filters={"item_code": item_code, "price_list": pl},
		fields=["price_list_rate"],
		limit_page_length=1,
	)
	if result:
		return result[0].price_list_rate
	return 0


# ---------------------------------------------------------------------------
# Quotation
# ---------------------------------------------------------------------------


def create_quotation(repair_job):
	"""Create a Quotation from approved service components."""
	settings = get_settings()
	items = []
	eligible_lines = []
	for service, line in _eligible_components(
		repair_job,
		statuses={"Approved", "Completed"},
		billable_only=True,
	):
		items.append(
			{
				"item_code": line.item_code,
				"item_name": line.service_description,
				"description": _component_description(service, line),
				"qty": line.quantity,
				"uom": line.uom,
				"rate": line.rate,
				"amount": line.amount,
				"project": repair_job.project,
				**_component_trace_fields(repair_job, service, line),
			}
		)
		eligible_lines.append(line)

	if not items:
		frappe.throw(_("No approved service components to quote."))

	quotation = _make_doc(
		{
			"doctype": "Quotation",
			"quotation_to": "Customer",
			"party_name": repair_job.customer,
			"company": settings.company,
			"selling_price_list": settings.selling_price_list or settings.price_list,
			"items": items,
		}
	)
	quotation.insert(ignore_permissions=True)
	frappe.db.set_value("Repair Job", repair_job.name, {"quotation": quotation.name})
	for line in eligible_lines:
		set_component_values(line, {"quotation": quotation.name})
	return quotation.name


# ---------------------------------------------------------------------------
# Sales Order
# ---------------------------------------------------------------------------


def create_sales_order(repair_job):
	"""Create a Sales Order from the linked Quotation."""
	if not repair_job.quotation:
		frappe.throw(_("Create a Quotation before generating a Sales Order."))

	settings = get_settings()
	quotation = frappe.get_doc("Quotation", repair_job.quotation)

	so = _make_doc(
		{
			"doctype": "Sales Order",
			"customer": repair_job.customer,
			"company": settings.company,
			"selling_price_list": settings.selling_price_list or settings.price_list,
			"items": quotation.items,
			"po_no": repair_job.name,
			"project": repair_job.project,
		}
	)
	so.insert(ignore_permissions=True)
	frappe.db.set_value("Repair Job", repair_job.name, {"sales_order": so.name})
	for service, line in _eligible_components(
		repair_job,
		statuses={"Approved", "Completed"},
		billable_only=True,
	):
		set_component_values(line, {"sales_order": so.name})
	return so.name


# ---------------------------------------------------------------------------
# Material Request
# ---------------------------------------------------------------------------


def create_material_request(repair_job):
	"""Create a Material Request for approved Part and Consumable components."""
	settings = get_settings()
	items = []
	eligible_lines = []
	for service, line in _eligible_components(
		repair_job,
		statuses={"Approved", "Completed"},
		component_types=STOCK_COMPONENT_TYPES,
	):
		if not line.item_code:
			continue
		if line.stock_request_status == "Requested":
			frappe.throw(_("Material Request already exists for component {0}.").format(line.service_description))
		if line.status in EXCLUDED_COMPONENT_STATUSES:
			continue
		items.append(
			{
				"item_code": line.item_code,
				"qty": line.quantity,
				"uom": line.uom,
				"warehouse": line.warehouse or getattr(settings, "source_warehouse", None),
				"schedule_date": frappe.utils.today(),
				"description": _component_description(service, line),
				**_component_trace_fields(repair_job, service, line),
			}
		)
		eligible_lines.append(line)

	if not items:
		frappe.throw(_("No approved Part or Consumable components to request."))

	mr = _make_doc(
		{
			"doctype": "Material Request",
			"material_request_type": "Material Issue",
			"company": settings.company,
			"items": items,
		}
	)
	mr.insert(ignore_permissions=True)

	for line in eligible_lines:
		set_component_values(
			line,
			{
				"requested_qty": line.quantity,
				"material_request": mr.name,
				"stock_request_status": "Requested",
			},
		)

	return mr.name


# ---------------------------------------------------------------------------
# Sales Invoice
# ---------------------------------------------------------------------------


def create_sales_invoice(repair_job):
	"""Create a Sales Invoice from completed, billable service components.

	The invoice does NOT use update_stock since parts are already issued.
	"""
	settings = get_settings()
	items = []
	eligible_lines = []
	for service, line in _eligible_components(
		repair_job,
		statuses={"Completed"},
		billable_only=True,
	):
		if line.sales_invoice:
			frappe.throw(_("Service component {0} has already been invoiced.").format(line.service_description))
		items.append(
			{
				"item_code": line.item_code,
				"item_name": line.service_description,
				"description": _component_description(service, line),
				"qty": line.quantity,
				"uom": line.uom,
				"rate": line.rate,
				"amount": line.amount,
				"project": repair_job.project,
				**_component_trace_fields(repair_job, service, line),
			}
		)
		eligible_lines.append(line)

	if not items:
		frappe.throw(_("No completed billable service components to invoice."))

	si = _make_doc(
		{
			"doctype": "Sales Invoice",
			"customer": repair_job.customer,
			"company": settings.company,
			"selling_price_list": settings.selling_price_list or settings.price_list,
			"items": items,
			"update_stock": 0,
			"is_pos": 0,
			"project": repair_job.project,
		}
	)
	si.insert(ignore_permissions=True)
	frappe.db.set_value("Repair Job", repair_job.name, {"sales_invoice": si.name})
	for line in eligible_lines:
		set_component_values(line, {"sales_invoice": si.name})
	return si.name


# ---------------------------------------------------------------------------
# Stock Entry (Material Issue)
# ---------------------------------------------------------------------------


def create_stock_entry_for_material_issue(repair_job):
	"""Create a Stock Entry (Material Issue) for requested stock components."""
	settings = get_settings()
	items = []
	eligible_lines = []
	for service, line in _eligible_components(
		repair_job,
		statuses={"Approved", "Completed"},
		component_types=STOCK_COMPONENT_TYPES,
	):
		if line.item_code and line.stock_request_status == "Requested":
			items.append(
				{
					"item_code": line.item_code,
					"qty": line.quantity,
					"uom": line.uom,
					"s_warehouse": line.warehouse or getattr(settings, "source_warehouse", None),
					"description": _component_description(service, line),
					**_component_trace_fields(repair_job, service, line),
				}
			)
			eligible_lines.append(line)

	if not items:
		frappe.throw(_("No requested Part or Consumable components to issue."))

	se = _make_doc(
		{
			"doctype": "Stock Entry",
			"stock_entry_type": "Material Issue",
			"company": settings.company,
			"items": items,
		}
	)
	se.insert(ignore_permissions=True)

	for line in eligible_lines:
		set_component_values(
			line,
			{
				"issued_qty": line.quantity,
				"stock_entry": se.name,
				"stock_request_status": "Fully Issued",
			},
		)

	return se.name


# ---------------------------------------------------------------------------
# Timesheet Hooks
# ---------------------------------------------------------------------------


def sync_timesheet_actuals(doc, method=None):
	"""Sync submitted Timesheet Detail hours back to service components."""
	component_refs = {
		(row.repair_component_doctype, row.repair_component_row)
		for row in doc.get("time_logs", [])
		if getattr(row, "repair_component_doctype", None) and getattr(row, "repair_component_row", None)
	}
	for component_doctype, component_row in component_refs:
		sync_timesheet_actuals_for_component(component_doctype, component_row)

	line_names = {
		row.repair_service_line
		for row in doc.get("time_logs", [])
		if getattr(row, "repair_service_line", None)
	}
	for line_name in line_names - {row_name for _doctype, row_name in component_refs}:
		sync_timesheet_actuals_for_line(line_name)


def sync_timesheet_actuals_for_component(component_doctype, component_row):
	details = frappe.get_all(
		"Timesheet Detail",
		filters={"repair_component_doctype": component_doctype, "repair_component_row": component_row},
		fields=["name", "parent", "hours", "billing_hours"],
		limit_page_length=0,
	)
	total_hours = 0
	last_timesheet = None
	last_detail = None
	for detail in details:
		if frappe.db.get_value("Timesheet", detail.parent, "docstatus") != 1:
			continue
		total_hours += detail.billing_hours or detail.hours or 0
		last_timesheet = detail.parent
		last_detail = detail.name

	frappe.db.set_value(
		component_doctype,
		component_row,
		{
			"actual_hours": total_hours,
			"timesheet": last_timesheet,
			"timesheet_detail": last_detail,
		},
		update_modified=False,
	)


def sync_timesheet_actuals_for_line(line_name):
	details = frappe.get_all(
		"Timesheet Detail",
		filters={"repair_service_line": line_name},
		fields=["name", "parent", "hours", "billing_hours"],
		limit_page_length=0,
	)
	total_hours = 0
	last_timesheet = None
	last_detail = None
	for detail in details:
		if frappe.db.get_value("Timesheet", detail.parent, "docstatus") != 1:
			continue
		total_hours += detail.billing_hours or detail.hours or 0
		last_timesheet = detail.parent
		last_detail = detail.name

	frappe.db.set_value(
		"Repair Service Line",
		line_name,
		{
			"actual_hours": total_hours,
			"timesheet": last_timesheet,
			"timesheet_detail": last_detail,
		},
		update_modified=False,
	)


# ---------------------------------------------------------------------------
# Invoice Hook (called from doc_events)
# ---------------------------------------------------------------------------


def on_invoice_submit(doc, method):
	"""Update linked Repair Job when Sales Invoice is submitted."""
	repair_job_name = frappe.db.get_value("Repair Job", {"sales_invoice": doc.name}, "name")
	if repair_job_name:
		repair_job = frappe.get_doc("Repair Job", repair_job_name)
		repair_job.payment_status = "Unpaid"
		if repair_job.job_status == "Ready for Invoice":
			repair_job.job_status = "Invoiced"
		repair_job.save(ignore_permissions=True)
