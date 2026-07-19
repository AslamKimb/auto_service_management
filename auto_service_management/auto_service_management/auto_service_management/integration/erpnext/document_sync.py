from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import flt

from auto_service_management.auto_service_management.doctype.repair_job_service.repair_job_service import (
	COMPONENT_TABLES,
	INVOICEABLE_SERVICE_STATUSES,
	iter_repair_job_components,
)
from auto_service_management.auto_service_management.workflow_compatibility import (
	recompute_repair_job_state,
	sync_repair_job_related_tables,
	_service_payment_total as _compat_service_payment_total,
)

ACTIVE_COMPONENT_DOCTYPES = {row["doctype"] for row in COMPONENT_TABLES}
TRACE_COMPONENT_DOCTYPES = ACTIVE_COMPONENT_DOCTYPES | {
	"Repair Job Service Subcontracted Service",
}
PROTECTED_JOB_STATUSES = {"Closed", "Cancelled"}


def validate_sales_invoice(doc, method=None):
	if not _has_repair_traces(doc):
		return
	job = _validate_single_repair_job(doc)
	if doc.customer != job.customer:
		frappe.throw(_("Sales Invoice customer must match Repair Job {0}.").format(job.name))
	if doc.get("company") and job.get("company") and doc.company != job.company:
		frappe.throw(_("Sales Invoice company must match Repair Job {0}.").format(job.name))
	doc.update_stock = 0
	_validate_component_links(doc, "Sales Invoice", "sales_invoice")
	_validate_component_quantities(doc, labour_uses_billing_hours=True)
	_validate_invoice_service_submission(doc)


def validate_material_request(doc, method=None):
	if not _has_repair_traces(doc):
		return
	_validate_single_repair_job(doc)
	if doc.material_request_type != "Material Issue":
		frappe.throw(_("Repair Job components require Material Request type Material Issue."))
	_validate_component_links(doc, "Material Request", "material_request")
	_validate_component_quantities(doc, stock_only=True)


def sync_sales_invoice(doc, method=None):
	if not _has_repair_traces(doc):
		return
	job_names = _repair_job_names(doc)
	_reconcile_component_links(
		doc,
		linked_field="sales_invoice",
		linked_item_field="sales_invoice_item",
	)
	for job_name in job_names:
		recompute_repair_job_state(job_name)
		sync_repair_job_related_tables(job_name)


def submit_sales_invoice(doc, method=None):
	if not _has_repair_traces(doc):
		return
	_validate_invoice_service_submission(doc)
	sync_sales_invoice(doc)
	for job_name in _repair_job_names(doc):
		recompute_repair_job_state(job_name)


def cancel_sales_invoice(doc, method=None):
	job_names = _repair_job_names(doc)
	for job_name in job_names:
		_assert_invoice_cancellation_allowed(job_name)
	_release_component_links(doc, "sales_invoice", "sales_invoice_item")
	for job_name in job_names:
		recompute_repair_job_state(job_name)


def trash_sales_invoice(doc, method=None):
	job_names = _repair_job_names(doc)
	_release_component_links(doc, "sales_invoice", "sales_invoice_item")
	for job_name in job_names:
		recompute_repair_job_state(job_name)
		sync_repair_job_related_tables(job_name)


def sync_payment_entry(doc, method=None):
	job_names = _payment_entry_job_names(doc)
	if not job_names:
		return
	after_commit = getattr(frappe.db, "after_commit", None)
	if after_commit and hasattr(after_commit, "add"):
		after_commit.add(lambda job_names=tuple(sorted(job_names)): _sync_payment_jobs(job_names))
		return
	_sync_payment_jobs(tuple(sorted(job_names)))


def _sync_payment_jobs(job_names):
	for job_name in job_names:
		sync_repair_job_related_tables(job_name)
		recompute_repair_job_state(job_name)


def _service_payment_total(service, invoice_rows):
	return _compat_service_payment_total(service, invoice_rows)


def sync_material_request(doc, method=None):
	if not _has_repair_traces(doc):
		return
	_reconcile_component_links(
		doc,
		linked_field="material_request",
		linked_item_field="material_request_item",
		extra_values=lambda row: {
			"requested_qty": flt(row.qty),
			"stock_request_status": "Requested",
		},
		release_values={"requested_qty": 0, "stock_request_status": "Not Requested"},
	)


def cancel_material_request(doc, method=None):
	_release_component_links(
		doc,
		"material_request",
		"material_request_item",
		extra_values={"requested_qty": 0, "stock_request_status": "Cancelled"},
	)


def trash_material_request(doc, method=None):
	_release_component_links(
		doc,
		"material_request",
		"material_request_item",
		extra_values={"requested_qty": 0, "stock_request_status": "Not Requested"},
	)


def validate_job_invoices_for_gate_pass(repair_job_name: str) -> list[str]:
	if not _all_billable_components_submitted(repair_job_name):
		frappe.throw(
			_(
				"Every billable component in an Approved or Completed Repair Job Service must be covered by a submitted Sales Invoice before issuing a Gate Pass."
			)
		)
	invoices = get_repair_job_sales_invoices(repair_job_name, submitted_only=True)
	if not invoices:
		frappe.throw(_("A submitted Sales Invoice is required before issuing a Gate Pass."))
	return invoices


def get_repair_job_sales_invoices(repair_job_name: str, *, submitted_only: bool = False) -> list[str]:
	job = frappe.get_doc("Repair Job", repair_job_name)
	invoices = {row.sales_invoice for row in (job.get("sales_invoices") or []) if row.sales_invoice}
	if submitted_only:
		invoices = {
			invoice for invoice in invoices if frappe.db.get_value("Sales Invoice", invoice, "docstatus") == 1
		}
	return sorted(invoices)


def sync_repair_job_invoice_state(repair_job_name: str):
	recompute_repair_job_state(repair_job_name)


def _all_billable_components_submitted(repair_job_name: str) -> bool:
	components = [
		component
		for _service, component in iter_repair_job_components(
			repair_job_name,
			service_statuses=INVOICEABLE_SERVICE_STATUSES,
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


def _validate_invoice_service_submission(doc):
	service_names = {
		row.repair_job_service
		for row in _trace_items(doc)
		if getattr(row, "repair_job_service", None)
	}
	if not service_names:
		return


def _validate_single_repair_job(doc):
	job_names = _repair_job_names(doc)
	if len(job_names) != 1:
		frappe.throw(_("A target document must contain components from exactly one Repair Job."))
	job_name = next(iter(job_names))
	if doc.get("repair_job") and doc.repair_job != job_name:
		frappe.throw(_("The parent Repair Job must match all component rows."))
	doc.repair_job = job_name
	return frappe.get_doc("Repair Job", job_name)


def _validate_component_links(doc, linked_doctype, linked_field):
	seen_refs = set()
	for row in _trace_items(doc):
		ref = (row.repair_component_doctype, row.repair_component_row)
		if ref in seen_refs:
			frappe.throw(_("Repair component {0} appears more than once.").format(row.repair_component_row))
		seen_refs.add(ref)
		if row.repair_component_doctype not in ACTIVE_COMPONENT_DOCTYPES:
			frappe.throw(_("Component type {0} is not active.").format(row.repair_component_doctype))
		if not frappe.db.exists(row.repair_component_doctype, row.repair_component_row):
			frappe.throw(_("Repair component {0} no longer exists.").format(row.repair_component_row))
		component = frappe.db.get_value(
			row.repair_component_doctype,
			row.repair_component_row,
			["repair_job", linked_field],
			as_dict=True,
		)
		if component.repair_job != row.repair_job:
			frappe.throw(_("Repair component trace does not match Repair Job {0}.").format(row.repair_job))
		linked_name = component.get(linked_field)
		if linked_name and linked_name != doc.name:
			docstatus = frappe.db.get_value(linked_doctype, linked_name, "docstatus")
			if docstatus in {0, 1}:
				frappe.throw(
					_("Repair component {0} is reserved by {1}.").format(
						row.repair_component_row, linked_name
					)
				)


def _validate_component_quantities(doc, *, labour_uses_billing_hours=False, stock_only=False):
	for row in _trace_items(doc):
		is_labour = row.repair_component_doctype == "Repair Job Service Labour"
		if stock_only and is_labour:
			frappe.throw(_("Material Requests cannot include Labour components."))
		quantity_field = "billing_hours" if labour_uses_billing_hours and is_labour else "quantity"
		expected_qty = flt(
			frappe.db.get_value(row.repair_component_doctype, row.repair_component_row, quantity_field)
		)
		if flt(row.qty) != expected_qty:
			frappe.throw(
				_("Quantity for repair component {0} must remain {1}.").format(
					row.repair_component_row,
					expected_qty,
				)
			)


def _reconcile_component_links(
	doc,
	*,
	linked_field,
	linked_item_field,
	extra_values=None,
	release_values=None,
):
	current = {(row.repair_component_doctype, row.repair_component_row): row for row in _trace_items(doc)}
	for component_doctype in TRACE_COMPONENT_DOCTYPES:
		if not _linked_field_exists(component_doctype, linked_field):
			continue
		for linked_row in frappe.get_all(
			component_doctype,
			filters={linked_field: doc.name},
			pluck="name",
		):
			if (component_doctype, linked_row) not in current:
				_clear_component_link(
					component_doctype,
					linked_row,
					linked_field,
					linked_item_field,
					extra_values=release_values,
				)
	for (component_doctype, component_row), target_row in current.items():
		values = {linked_field: doc.name, linked_item_field: target_row.name}
		if callable(extra_values):
			values.update(extra_values(target_row))
		elif extra_values:
			values.update(extra_values)
		frappe.db.set_value(component_doctype, component_row, values, update_modified=False)


def _release_component_links(doc, linked_field, linked_item_field, extra_values=None):
	for component_doctype in TRACE_COMPONENT_DOCTYPES:
		if not _linked_field_exists(component_doctype, linked_field):
			continue
		for component_row in frappe.get_all(
			component_doctype,
			filters={linked_field: doc.name},
			pluck="name",
		):
			_clear_component_link(
				component_doctype,
				component_row,
				linked_field,
				linked_item_field,
				extra_values=extra_values,
			)


def _clear_component_link(
	component_doctype,
	component_row,
	linked_field,
	linked_item_field,
	*,
	extra_values=None,
):
	values = {linked_field: None, linked_item_field: None}
	if extra_values:
		values.update(extra_values)
	frappe.db.set_value(component_doctype, component_row, values, update_modified=False)


def _linked_field_exists(component_doctype, linked_field):
	if not frappe.db.table_exists(component_doctype):
		return False
	return bool(frappe.get_meta(component_doctype).get_field(linked_field))


def _assert_invoice_cancellation_allowed(repair_job_name):
	job_status = frappe.db.get_value("Repair Job", repair_job_name, "job_status")
	if job_status in PROTECTED_JOB_STATUSES:
		frappe.throw(_("Sales Invoices cannot be cancelled after Gate Pass issuance or job closure."))
	issued_gate_pass = frappe.db.exists(
		"Gate Pass",
		{
			"repair_job": repair_job_name,
			"status": ["in", ["Issued", "Used"]],
		},
	)
	if issued_gate_pass:
		frappe.throw(_("Sales Invoices cannot be cancelled after Gate Pass issuance."))


def _repair_job_names(doc):
	job_names = {row.repair_job for row in _trace_items(doc) if getattr(row, "repair_job", None)}
	if doc.get("repair_job"):
		job_names.add(doc.repair_job)
	return job_names


def _payment_entry_job_names(doc):
	invoice_names = {
		row.reference_name
		for row in doc.get("references") or []
		if getattr(row, "reference_doctype", None) == "Sales Invoice" and getattr(row, "reference_name", None)
	}
	if not invoice_names:
		return set()
	job_names = set()
	for invoice_name in invoice_names:
		job_name = frappe.db.get_value("Sales Invoice", invoice_name, "repair_job")
		if job_name:
			job_names.add(job_name)
	return job_names


def _trace_items(doc):
	return [
		row
		for row in doc.get("items") or []
		if getattr(row, "repair_component_doctype", None) and getattr(row, "repair_component_row", None)
	]


def _has_repair_traces(doc):
	return bool(doc.get("repair_job") or _trace_items(doc))
