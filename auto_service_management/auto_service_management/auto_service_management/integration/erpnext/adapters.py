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


def get_settings():
	"""Return Auto Service Settings as a dict."""
	return frappe.get_single("Auto Service Settings")


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
	project = frappe.get_doc(
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
		task = frappe.get_doc(
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
	"""Create a Quotation from approved service lines.

	Returns the Quotation name.
	"""
	settings = get_settings()
	items = []
	for line in repair_job.service_lines:
		if line.status in ("Approved", "Completed"):
			items.append(
				{
					"item_code": line.item_code,
					"item_name": line.service_description,
					"qty": line.quantity,
					"rate": line.rate,
					"amount": line.amount,
				}
			)

	if not items:
		frappe.throw(_("No approved service lines to quote."))

	quotation = frappe.get_doc(
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
	return quotation.name


# ---------------------------------------------------------------------------
# Sales Order
# ---------------------------------------------------------------------------


def create_sales_order(repair_job):
	"""Create a Sales Order from the linked Quotation.

	Returns the Sales Order name.
	"""
	if not repair_job.quotation:
		frappe.throw(_("Create a Quotation before generating a Sales Order."))

	settings = get_settings()
	quotation = frappe.get_doc("Quotation", repair_job.quotation)

	so = frappe.get_doc(
		{
			"doctype": "Sales Order",
			"customer": repair_job.customer,
			"company": settings.company,
			"selling_price_list": settings.selling_price_list or settings.price_list,
			"items": quotation.items,
			"po_no": repair_job.name,
		}
	)
	so.insert(ignore_permissions=True)
	frappe.db.set_value("Repair Job", repair_job.name, {"sales_order": so.name})
	return so.name


# ---------------------------------------------------------------------------
# Material Request
# ---------------------------------------------------------------------------


def create_material_request(repair_job):
	"""Create a Material Request for parts needed by this Repair Job.

	Returns the Material Request name.
	"""
	settings = get_settings()
	items = []
	for line in repair_job.service_lines:
		if line.service_type == "Parts" and line.item_code:
			items.append(
				{
					"item_code": line.item_code,
					"qty": line.quantity,
					"warehouse": getattr(settings, "source_warehouse", None),
					"schedule_date": frappe.utils.today(),
				}
			)

	if not items:
		frappe.throw(_("No parts service lines to request."))

	mr = frappe.get_doc(
		{
			"doctype": "Material Request",
			"material_request_type": "Material Issue",
			"company": settings.company,
			"items": items,
		}
	)
	mr.insert(ignore_permissions=True)
	return mr.name


# ---------------------------------------------------------------------------
# Sales Invoice
# ---------------------------------------------------------------------------


def create_sales_invoice(repair_job):
	"""Create a Sales Invoice from finalized service lines.

	The invoice does NOT use update_stock since parts are already issued.
	Returns the Sales Invoice name.
	"""
	settings = get_settings()
	items = []
	for line in repair_job.service_lines:
		if line.status in ("Completed",) and line.item_code:
			items.append(
				{
					"item_code": line.item_code,
					"item_name": line.service_description,
					"qty": line.quantity,
					"rate": line.rate,
					"amount": line.amount,
				}
			)
		elif line.service_type == "Labour" and line.status == "Completed":
			items.append(
				{
					"item_name": line.service_description,
					"qty": line.quantity,
					"rate": line.rate,
					"amount": line.amount,
				}
			)

	if not items:
		frappe.throw(_("No completed service lines to invoice."))

	si = frappe.get_doc(
		{
			"doctype": "Sales Invoice",
			"customer": repair_job.customer,
			"company": settings.company,
			"selling_price_list": settings.selling_price_list or settings.price_list,
			"items": items,
			"update_stock": 0,
			"is_pos": 0,
		}
	)
	si.insert(ignore_permissions=True)
	frappe.db.set_value("Repair Job", repair_job.name, {"sales_invoice": si.name})
	return si.name


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
