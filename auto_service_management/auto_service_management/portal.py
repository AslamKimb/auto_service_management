from __future__ import annotations

import frappe
from erpnext.controllers.website_list_for_contact import get_parents_for_user
from frappe import _
from frappe.utils import cint

REPAIR_JOB_LIFECYCLE = (
	"Draft",
	"Assessment",
	"Awaiting Approval",
	"In Repair",
	"Quality Check",
	"Billing",
	"Ready for Release",
	"Closed",
)


def _ensure_authenticated():
	if _session_user() == "Guest":
		raise frappe.PermissionError(_("Please sign in to view your repairs."))


def _session_user() -> str | None:
	session = getattr(frappe, "session", None)
	if isinstance(session, dict):
		return session.get("user")
	return getattr(session, "user", None)


def _customer_names() -> list[str]:
	_ensure_authenticated()
	return get_parents_for_user("Customer")


def get_portal_repair_jobs(page=1, page_length=20) -> dict:
	customers = _customer_names()
	page = max(cint(page), 1)
	page_length = min(max(cint(page_length), 1), 50)
	if not customers:
		return {"jobs": [], "page": page, "page_length": page_length, "total": 0, "has_next": False}

	filters = {"customer": ["in", customers]}
	total = frappe.db.count("Repair Job", filters)
	jobs = frappe.get_all(
		"Repair Job",
		filters=filters,
		fields=[
			"name",
			"customer_vehicle",
			"registration_number",
			"vehicle_details",
			"creation as intake_date",
			"job_status",
			"total_amount",
			"payment_status",
			"currency",
		],
		order_by="creation desc",
		start=(page - 1) * page_length,
		page_length=page_length,
	)
	return {
		"jobs": jobs,
		"page": page,
		"page_length": page_length,
		"total": total,
		"has_next": page * page_length < total,
	}


def get_portal_repair_job(name: str) -> dict:
	customers = _customer_names()
	if not customers or not frappe.db.exists(
		"Repair Job",
		{"name": name, "customer": ["in", customers]},
	):
		raise frappe.PermissionError(_("You are not permitted to view this repair."))

	job = frappe.get_doc("Repair Job", name)
	services = frappe.get_all(
		"Repair Job Service",
		filters={"repair_job": name, "docstatus": ["<", 2]},
		fields=["name", "service_name", "is_completed", "total_amount", "currency"],
		order_by="creation asc",
	)
	invoices = frappe.get_all(
		"Sales Invoice",
		filters={"repair_job": name, "docstatus": 1},
		fields=["name", "posting_date", "grand_total", "outstanding_amount", "status", "currency"],
		order_by="posting_date desc, creation desc",
	)
	payments = _submitted_payment_allocations(invoices)
	job_status = job.job_status
	current_index = (
		REPAIR_JOB_LIFECYCLE.index(job_status)
		if job_status in REPAIR_JOB_LIFECYCLE
		else -1
	)
	return {
		"job": frappe._dict(
			name=job.name,
			customer_vehicle=job.customer_vehicle,
			registration_number=job.registration_number,
			vehicle_details=job.vehicle_details,
			intake_date=job.creation,
			job_status=job_status,
			total_amount=job.total_amount,
			payment_status=job.payment_status,
			currency=job.currency,
		),
		"lifecycle": [
			{
				"label": stage,
				"complete": current_index >= index,
				"current": stage == job_status,
			}
			for index, stage in enumerate(REPAIR_JOB_LIFECYCLE)
		],
		"is_cancelled": job_status == "Cancelled",
		"services": services,
		"invoices": invoices,
		"payments": payments,
	}


def _submitted_payment_allocations(invoices) -> list[dict]:
	invoice_names = [invoice.name for invoice in invoices]
	if not invoice_names:
		return []
	references = frappe.get_all(
		"Payment Entry Reference",
		filters={
			"reference_doctype": "Sales Invoice",
			"reference_name": ["in", invoice_names],
			"docstatus": 1,
		},
		fields=["parent", "reference_name", "allocated_amount"],
		order_by="creation desc",
	)
	payment_names = sorted({reference.parent for reference in references})
	payment_dates = {
		payment.name: payment.posting_date
		for payment in frappe.get_all(
			"Payment Entry",
			filters={"name": ["in", payment_names], "docstatus": 1},
			fields=["name", "posting_date"],
			limit_page_length=0,
		)
	}
	return [
		{
			"payment_entry": reference.parent,
			"posting_date": payment_dates[reference.parent],
			"invoice": reference.reference_name,
			"allocated_amount": reference.allocated_amount,
		}
		for reference in references
		if reference.parent in payment_dates
	]
