from __future__ import annotations

from collections.abc import Iterable

import frappe
from frappe import _
from frappe.utils import flt

from auto_service_management.auto_service_management.doctype.repair_job_service.repair_job_service import (
	get_repair_job_services,
	get_service_components,
	iter_repair_job_components,
)

REPAIR_JOB_SERVICE_FIELDS = (
	"repair_job",
	"repair_job_service",
	"service_name",
	"workshop_bay",
	"total_amount",
	"payment_status",
	"is_completed",
)
REPAIR_JOB_INVOICE_FIELDS = (
	"repair_job",
	"sales_invoice",
	"customer",
	"job_status",
	"posting_date",
	"closed_on",
	"grand_total",
	"paid_amount",
	"outstanding_amount",
	"payment_status",
)
REPAIR_JOB_SALES_ORDER_FIELDS = (
	"repair_job",
	"sales_order",
	"transaction_date",
	"delivery_date",
	"status",
	"docstatus",
	"grand_total",
	"per_billed",
	"billing_status",
)
REPAIR_JOB_PAYMENT_FIELDS = (
	"repair_job",
	"payment_entry",
	"reference_invoice",
	"posting_date",
	"allocated_amount",
)


TERMINAL_JOB_STATUSES = {"Closed", "Cancelled"}
CANONICAL_JOB_STATUSES = {
	"Draft",
	"Assessment",
	"Awaiting Approval",
	"In Repair",
	"Quality Check",
	"Billing",
	"Ready for Release",
	"Closed",
	"Cancelled",
}


def sync_repair_job_compatibility_views(repair_job):
	repair_job = _resolve_doc(repair_job, "Repair Job")
	if repair_job.is_new() or not repair_job.name:
		return repair_job
	if getattr(repair_job.flags, "skip_compatibility_sync", False):
		return repair_job

	repair_job.set(
		"repair_job_services",
		[
			{field: row.get(field) for field in REPAIR_JOB_SERVICE_FIELDS}
			for row in build_repair_job_service_rows(repair_job.name)
		],
	)
	repair_job.set(
		"sales_invoices",
		[
			{field: row.get(field) for field in REPAIR_JOB_INVOICE_FIELDS}
			for row in build_repair_job_invoice_rows(repair_job.name)
		],
	)
	repair_job.set(
		"payment_entries",
		[
			{field: row.get(field) for field in REPAIR_JOB_PAYMENT_FIELDS}
			for row in build_repair_job_payment_rows(repair_job.name)
		],
	)

	repair_job.scope_revision = max(
		int(getattr(repair_job, "scope_revision", 0) or 0),
		len(repair_job.get("repair_job_services") or []),
	)
	repair_job.payment_total = flt(sum(flt(row.get("allocated_amount")) for row in repair_job.get("payment_entries") or []))
	repair_job.closure_type = _derive_closure_type(repair_job)
	repair_job.payment_status = _derive_payment_status(
		sum(flt(row.get("grand_total")) for row in repair_job.get("sales_invoices") or []),
		repair_job.payment_total,
	)
	repair_job.set(
		"sales_orders",
		[
			{field: row.get(field) for field in REPAIR_JOB_SALES_ORDER_FIELDS}
			for row in build_repair_job_sales_order_rows(repair_job.name)
		],
	)
	# Keep the singular field as a derived compatibility pointer for older
	# callers: prefer the newest submitted order, otherwise newest draft.
	if repair_job.get("sales_orders"):
		ordered = sorted(
			repair_job.get("sales_orders") or [],
			key=lambda row: (int(row.get("docstatus") or 0) == 1, row.get("transaction_date") or "", row.get("sales_order") or ""),
			reverse=True,
		)
		repair_job.sales_order = ordered[0].get("sales_order")
	else:
		repair_job.sales_order = None
	return repair_job


def sync_repair_job_related_tables(repair_job_name: str):
	if not repair_job_name or not frappe.db.exists("Repair Job", repair_job_name):
		return
	job = frappe.get_doc("Repair Job", repair_job_name)
	sync_repair_job_compatibility_views(job)
	job.flags.skip_compatibility_sync = True
	job.flags.ignore_links = True
	job.save(ignore_permissions=True)


def recompute_repair_job_state(repair_job_name: str):
	if not repair_job_name or not frappe.db.exists("Repair Job", repair_job_name):
		return None
	job = frappe.get_doc("Repair Job", repair_job_name)
	if getattr(job.flags, "skip_compatibility_sync", False):
		return job
	target = _derive_repair_job_status(job)
	if target == "Closed":
		gate_pass = _get_linked_doc(job.name, "Gate Pass")
		if gate_pass and gate_pass.status == "Used" and job.docstatus == 0:
			job._finalize_closure(ignore_permissions=True)
		return job
	if not target or target == job.job_status:
		return job
	job.job_status = target
	if getattr(job, "meta", None) and job.meta.has_field("workflow_state"):
		job.workflow_state = target
	job.flags.skip_status_validation = True
	job.flags.ignore_links = True
	job.save(ignore_permissions=True)
	return job


def bump_repair_job_scope_revision(repair_job_name: str):
	if not repair_job_name or not frappe.db.exists("Repair Job", repair_job_name):
		return
	current = int(frappe.db.get_value("Repair Job", repair_job_name, "scope_revision") or 0)
	frappe.db.set_value("Repair Job", repair_job_name, "scope_revision", current + 1, update_modified=False)


def invalidate_repair_job_authorizations(repair_job_name: str):
	if not repair_job_name or not frappe.db.exists("Repair Job", repair_job_name):
		return
	approvals = frappe.get_all(
		"Customer Authorization",
		filters={"repair_job": repair_job_name, "docstatus": 1},
		fields=["name", "scope_revision", "scope_total_amount"],
		limit_page_length=0,
	)
	current_scope_revision = int(frappe.db.get_value("Repair Job", repair_job_name, "scope_revision") or 0)
	current_total_amount = flt(frappe.db.get_value("Repair Job", repair_job_name, "total_amount") or 0)
	for auth in approvals:
		if int(auth.scope_revision or 0) == current_scope_revision and flt(auth.scope_total_amount) == current_total_amount:
			continue
		frappe.db.set_value("Customer Authorization", auth.name, "docstatus", 2, update_modified=False)


def sync_repair_job_service_summary(service):
	service = _resolve_doc(service, "Repair Job Service")
	if getattr(service.flags, "skip_compatibility_sync", False):
		return service

	invoices = _service_invoice_rows(service)
	payment_total = _service_payment_total(service, invoices)
	service.invoice_total = flt(sum(flt(row.get("invoice_amount")) for row in invoices))
	service.payment_total = flt(payment_total)
	service.outstanding_amount = flt(max(service.invoice_total - service.payment_total, 0))
	service.payment_status = _derive_payment_status(service.invoice_total, service.payment_total)
	return service


def sync_quality_check_road_tests(quality_check):
	quality_check = _resolve_doc(quality_check, "Quality Check")
	if getattr(quality_check.flags, "skip_compatibility_sync", False):
		return quality_check

	quality_check.set(
		"road_tests",
		[
			{
				"quality_check": quality_check.name,
				"repair_job": quality_check.repair_job,
				"customer_vehicle": quality_check.customer_vehicle,
				"test_date": row.get("test_date"),
				"tested_by": row.get("tested_by"),
				"odometer_start": row.get("odometer_start"),
				"odometer_end": row.get("odometer_end"),
				"duration_minutes": row.get("duration_minutes"),
				"route": row.get("route"),
				"braking_ok": row.get("braking_ok"),
				"steering_ok": row.get("steering_ok"),
				"engine_performance_ok": row.get("engine_performance_ok"),
				"transmission_ok": row.get("transmission_ok"),
				"no_warning_lights": row.get("no_warning_lights"),
				"test_notes": row.get("test_notes"),
			}
			for row in build_quality_check_road_test_rows(quality_check)
		],
	)
	return quality_check


def sync_quality_check_road_tests_for_repair_job(repair_job_name: str):
	if not repair_job_name:
		return
	quality_check_name = frappe.db.get_value("Quality Check", {"repair_job": repair_job_name}, "name")
	if not quality_check_name:
		return
	quality_check = frappe.get_doc("Quality Check", quality_check_name)
	quality_check.flags.skip_compatibility_sync = True
	sync_quality_check_road_tests(quality_check)
	quality_check.save(ignore_permissions=True)


def sync_customer_authorization_snapshot(authorization):
	authorization = _resolve_doc(authorization, "Customer Authorization")
	if getattr(authorization.flags, "skip_compatibility_sync", False):
		return authorization

	if not authorization.repair_job:
		return authorization
	if getattr(authorization, "docstatus", 0) == 1 and authorization.scope_revision and authorization.scope_total_amount:
		return authorization

	authorization.scope_revision = int(_get_job_field(authorization.repair_job, "scope_revision") or 0)
	authorization.scope_total_amount = flt(_get_job_field(authorization.repair_job, "total_amount"))
	return authorization


def build_repair_job_service_rows(repair_job_name: str) -> list[dict]:
	service_rows = []
	services = get_repair_job_services(repair_job_name)
	for service in services:
		service_rows.append(
			{
				"repair_job": repair_job_name,
				"repair_job_service": service.name,
				"service_name": service.service_name,
				"workshop_bay": getattr(service, "workshop_bay", None),
				"total_amount": service.total_amount,
				"payment_status": _service_payment_status(service),
				"is_completed": int(bool(getattr(service, "is_completed", False))),
			}
		)
	return service_rows


def build_repair_job_invoice_rows(repair_job_name: str) -> list[dict]:
	rows = []
	job = frappe.get_doc("Repair Job", repair_job_name)
	for invoice_name in _legacy_invoice_names(repair_job_name):
		if not frappe.db.exists("Sales Invoice", invoice_name):
			continue
		invoice = frappe.get_doc("Sales Invoice", invoice_name)
		rows.append(
			{
				"repair_job": repair_job_name,
				"sales_invoice": invoice.name,
				"customer": job.customer,
				"job_status": job.job_status,
				"posting_date": invoice.posting_date,
				"closed_on": job.closed_on,
				"grand_total": flt(invoice.get("rounded_total") or invoice.grand_total),
				"paid_amount": flt(max(flt(invoice.get("rounded_total") or invoice.grand_total) - flt(getattr(invoice, "outstanding_amount", 0)), 0)),
				"outstanding_amount": flt(getattr(invoice, "outstanding_amount", 0)),
				"payment_status": _derive_payment_status(
					flt(invoice.get("rounded_total") or invoice.grand_total),
					flt(max(flt(invoice.get("rounded_total") or invoice.grand_total) - flt(getattr(invoice, "outstanding_amount", 0)), 0)),
				),
			}
		)
	return rows


def build_repair_job_sales_order_rows(repair_job_name: str) -> list[dict]:
	orders = frappe.get_all(
		"Sales Order",
		filters={"repair_job": repair_job_name},
		fields=["name", "transaction_date", "delivery_date", "status", "docstatus", "grand_total", "per_billed"],
		order_by="creation asc",
		limit_page_length=0,
	)
	rows = []
	for order in orders:
		if order.docstatus == 2:
			billing_status = "Cancelled"
		elif flt(order.per_billed) >= 100:
			billing_status = "Fully Billed"
		elif flt(order.per_billed) > 0:
			billing_status = "Partly Billed"
		else:
			billing_status = "Not Billed"
		rows.append(
			{
				"repair_job": repair_job_name,
				"sales_order": order.name,
				"transaction_date": order.transaction_date,
				"delivery_date": order.delivery_date,
				"status": order.status or {0: "Draft", 1: "Submitted", 2: "Cancelled"}.get(order.docstatus, "Draft"),
				"docstatus": order.docstatus,
				"grand_total": flt(order.grand_total),
				"per_billed": flt(order.per_billed),
				"billing_status": billing_status,
			}
		)
	return rows


def build_repair_job_payment_rows(repair_job_name: str) -> list[dict]:
	rows = []
	invoice_names = _legacy_invoice_names(repair_job_name)
	if not invoice_names:
		return rows

	refs = frappe.get_all(
		"Payment Entry Reference",
		filters={
			"reference_doctype": "Sales Invoice",
			"reference_name": ["in", invoice_names],
		},
		fields=["parent", "reference_name", "allocated_amount"],
		order_by="creation asc, idx asc",
	)
	for ref in refs:
		payment_entry = frappe.db.get_value("Payment Entry", ref.parent, ["posting_date", "docstatus"], as_dict=True)
		if not payment_entry or payment_entry.docstatus != 1:
			continue
		rows.append(
			{
				"repair_job": repair_job_name,
				"payment_entry": ref.parent,
				"reference_invoice": ref.reference_name,
				"posting_date": payment_entry.posting_date,
				"allocated_amount": flt(ref.allocated_amount),
			}
		)
	return rows


def build_quality_check_road_test_rows(quality_check) -> list[dict]:
	quality_check = _resolve_doc(quality_check, "Quality Check")
	if quality_check.get("road_tests"):
		return [
			build_quality_check_road_test_row(quality_check.name, row, quality_check.repair_job, quality_check.customer_vehicle)
			for row in quality_check.get("road_tests") or []
		]
	return []


def build_quality_check_road_test_row(quality_check_name: str, road_test, repair_job: str, customer_vehicle: str) -> dict:
	return {
		"quality_check": quality_check_name,
		"repair_job": getattr(road_test, "repair_job", None) or repair_job,
		"customer_vehicle": getattr(road_test, "customer_vehicle", None) or customer_vehicle,
		"test_date": getattr(road_test, "test_date", None),
		"tested_by": getattr(road_test, "tested_by", None),
		"odometer_start": getattr(road_test, "odometer_start", None),
		"odometer_end": getattr(road_test, "odometer_end", None),
		"duration_minutes": getattr(road_test, "duration_minutes", None),
		"route": getattr(road_test, "route", None),
		"braking_ok": getattr(road_test, "braking_ok", None),
		"steering_ok": getattr(road_test, "steering_ok", None),
		"engine_performance_ok": getattr(road_test, "engine_performance_ok", None),
		"transmission_ok": getattr(road_test, "transmission_ok", None),
		"no_warning_lights": getattr(road_test, "no_warning_lights", None),
		"test_notes": getattr(road_test, "test_notes", None),
	}


def build_repair_job_service_workshop_bay_rows(repair_job_name: str) -> tuple[list[dict], list[dict]]:
	rows = []
	exceptions = []
	bay_name = _get_enabled_job_workshop_bay(repair_job_name)
	for service in get_repair_job_services(repair_job_name):
		if getattr(service, "workshop_bay", None):
			continue
		if getattr(service, "docstatus", 0) == 2:
			continue
		if bay_name:
			rows.append(
				{
					"repair_job": repair_job_name,
					"repair_job_service": service.name,
					"workshop_bay": bay_name,
				}
			)
			continue
		exceptions.append(
				{
					"repair_job": repair_job_name,
					"repair_job_service": service.name,
					"docstatus": getattr(service, "docstatus", 0),
					"reason": "Repair Job has no enabled Workshop Bay",
				}
		)
	return rows, exceptions


def _legacy_invoice_names(repair_job_name: str) -> list[str]:
	invoices = {
		component.sales_invoice
		for _service, component in iter_repair_job_components(
			repair_job_name,
			include_excluded=True,
		)
		if component.sales_invoice
	}
	return sorted(invoices)


def _service_invoice_rows(service) -> list[dict]:
	rows = []
	for component in get_service_components(service):
		if not component.sales_invoice:
			continue
		if not frappe.db.exists("Sales Invoice", component.sales_invoice):
			continue
		invoice = frappe.get_doc("Sales Invoice", component.sales_invoice)
		rows.append(
			{
				"invoice_amount": flt(component.invoice_amount),
				"invoice_docstatus": invoice.docstatus,
				"sales_invoice": invoice.name,
			}
		)
	return rows


def _service_payment_total(service, invoice_rows: Iterable[dict]) -> float:
	invoice_names = [row.get("sales_invoice") for row in invoice_rows if row.get("sales_invoice")]
	if not invoice_names:
		return 0
	refs = frappe.get_all(
		"Payment Entry Reference",
		filters={"reference_doctype": "Sales Invoice", "reference_name": ["in", invoice_names]},
		fields=["parent", "allocated_amount"],
	)
	total = 0
	for ref in refs:
		payment_entry = frappe.db.get_value("Payment Entry", ref.parent, "docstatus")
		if payment_entry == 1:
			total += flt(ref.allocated_amount)
	return total


def _service_payment_status(service) -> str:
	invoice_total = 0
	payment_total = 0
	for component in get_service_components(service):
		if component.sales_invoice and frappe.db.exists("Sales Invoice", component.sales_invoice):
			invoice_total += flt(component.invoice_amount)
	payment_total = _service_payment_total(service, _service_invoice_rows(service))
	return _derive_payment_status(invoice_total, payment_total)


def _derive_payment_status(invoice_total: float, payment_total: float) -> str:
	if invoice_total <= 0:
		return "Not Invoiced"
	if payment_total <= 0:
		return "Unpaid"
	if payment_total < invoice_total:
		return "Partially Paid"
	return "Paid"


def _derive_repair_job_status(job):
	current = getattr(job, "job_status", None) or "Draft"
	if current in TERMINAL_JOB_STATUSES:
		return current

	gate_pass = _get_linked_doc(job.name, "Gate Pass")
	if gate_pass and getattr(gate_pass, "status", None) == "Used":
		return "Closed"
	if gate_pass and getattr(gate_pass, "status", None) == "Issued":
		return "Ready for Release"

	quality_check = _get_linked_doc(job.name, "Quality Check")
	if quality_check:
		qc_status = getattr(quality_check, "status", None)
		if qc_status in {"Failed", "Rework"}:
			return "In Repair"
		if qc_status == "Passed":
			return "Billing"
		return "Quality Check"

	authorization = _get_linked_doc(job.name, "Customer Authorization")
	if authorization:
		if getattr(authorization, "docstatus", 0) == 1:
			return "In Repair"
		return "Awaiting Approval"

	diagnosis = _get_linked_doc(job.name, "Diagnosis Report")
	if diagnosis:
		if getattr(diagnosis, "docstatus", 0) != 1:
			return "Assessment"
		if _has_any_service_rows(job.name):
			return "Awaiting Approval"
		return "Billing"

	if _get_linked_doc(job.name, "Walkaround Inspection"):
		return "Assessment"
	if getattr(job, "project", None):
		return "Assessment"

	if current in CANONICAL_JOB_STATUSES:
		return current
	return "Draft"


def _derive_closure_type(repair_job) -> str | None:
	if repair_job.get("closure_type"):
		return repair_job.closure_type
	if repair_job.get("job_status") == "Closed":
		return "Diagnosis Only"
	return None


def _get_job_field(repair_job_name: str, fieldname: str):
	if not repair_job_name or not frappe.db.exists("Repair Job", repair_job_name):
		return None
	return frappe.db.get_value("Repair Job", repair_job_name, fieldname)


def _get_linked_doc(repair_job_name: str, doctype: str):
	filters = {"repair_job": repair_job_name}
	if doctype == "Gate Pass" and _db_has_column("Gate Pass", "purpose"):
		filters["purpose"] = "Final Release"
	name = frappe.db.get_value(doctype, filters, "name")
	if not name:
		return None
	return frappe.get_doc(doctype, name)


def _has_work_started(repair_job_name: str) -> bool:
	return _get_job_field(repair_job_name, "job_status") in {
		"In Repair",
		"Quality Check",
		"Billing",
		"Ready for Release",
		"Closed",
	}


def _has_any_service_rows(repair_job_name: str) -> bool:
	return bool(get_repair_job_services(repair_job_name))


def _has_any_billable_invoice(repair_job_name: str) -> bool:
	for service in get_repair_job_services(repair_job_name):
		if getattr(service, "docstatus", 0) == 2:
			continue
		for component in get_service_components(service):
			if component.billable and component.sales_invoice:
				return True
	return False


def _all_billable_components_submitted(repair_job_name: str) -> bool:
	components = [
		component
		for _service, component in iter_repair_job_components(
			repair_job_name,
			billable_only=True,
		)
	]
	if not components:
		return False
	return all(
		component.sales_invoice
		and frappe.db.get_value("Sales Invoice", component.sales_invoice, "docstatus") == 1
		for component in components
	)


def _get_enabled_job_workshop_bay(repair_job_name: str):
	bay_name = _get_job_field(repair_job_name, "workshop_bay")
	if not bay_name or not frappe.db.exists("Workshop Bay", bay_name):
		return None
	if frappe.db.get_value("Workshop Bay", bay_name, "status") == "Under Maintenance":
		return None
	return bay_name


def _resolve_doc(doc_or_name, doctype: str):
	if isinstance(doc_or_name, str):
		return frappe.get_doc(doctype, doc_or_name)
	return doc_or_name


def _db_has_column(doctype, fieldname):
	has_column = getattr(frappe.db, "has_column", None)
	return bool(has_column and has_column(doctype, fieldname))
