from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import flt

from auto_service_management.auto_service_management.doctype.repair_job_service.repair_job_service import (
	COMPONENT_TABLES,
	iter_repair_job_components,
)
from auto_service_management.auto_service_management.integration.erpnext.component_mapping import (
	is_material_request_active,
)
from auto_service_management.auto_service_management.settings_cache import (
	get_settings as _get_cached_settings,
)
from auto_service_management.auto_service_management.workflow_compatibility import (
	_service_payment_total as _compat_service_payment_total,
)
from auto_service_management.auto_service_management.workflow_compatibility import (
	sync_repair_job_related_tables,
)

ACTIVE_COMPONENT_DOCTYPES = {row["doctype"] for row in COMPONENT_TABLES}
TRACE_COMPONENT_DOCTYPES = ACTIVE_COMPONENT_DOCTYPES | {
	"Repair Job Service Subcontracted Service",
}
PROTECTED_JOB_STATUSES = {"Closed", "Cancelled"}
CAMPAIGN_SALES_ITEM_TRACE_FIELDS = (
	"repair_job",
	"customer_vehicle",
	"repair_job_service",
	"repair_component_doctype",
	"repair_component_row",
	"project",
)


def _get_settings():
	return _get_cached_settings(frappe_module=frappe)


def validate_sales_invoice(doc, method=None):
	from auto_service_management.auto_service_management.integration.customer_lpo_workflow import (
		validate_lpo_sales_document,
	)

	validate_lpo_sales_document(doc)
	if not _has_repair_traces(doc):
		return
	jobs = _validate_sales_document_scope(doc)
	for job in jobs:
		if doc.customer != job.customer:
			frappe.throw(_("Sales Invoice customer must match Repair Job {0}.").format(job.name))
		if doc.get("company") and job.get("company") and doc.company != job.company:
			frappe.throw(_("Sales Invoice company must match Repair Job {0}.").format(job.name))
	doc.update_stock = 0
	_validate_component_links(doc, "Sales Invoice", "sales_invoice")
	_validate_component_quantities(doc, labour_uses_billing_hours=True)
	_validate_invoice_service_submission(doc)


def validate_sales_order(doc, method=None):
	from auto_service_management.auto_service_management.integration.customer_lpo_workflow import (
		validate_lpo_sales_document,
	)

	validate_lpo_sales_document(doc)
	if not _has_repair_traces(doc):
		return
	if not doc.get("select_print_heading") and frappe.db.exists("Print Heading", "Proforma Invoice"):
		doc.select_print_heading = "Proforma Invoice"
	jobs = _validate_sales_document_scope(doc)
	for job in jobs:
		if doc.customer != job.customer:
			frappe.throw(_("Sales Order customer must match Repair Job {0}.").format(job.name))
		if doc.get("company") and job.get("company") and doc.company != job.company:
			frappe.throw(_("Sales Order company must match Repair Job {0}.").format(job.name))
	_validate_component_links(doc, "Sales Order", "sales_order")
	_validate_component_quantities(doc, labour_uses_billing_hours=True)
	if getattr(doc, "docstatus", 0) == 1:
		_validate_sales_order_submission(doc)


def sync_sales_order(doc, method=None):
	from auto_service_management.auto_service_management.integration.customer_lpo_workflow import (
		sync_lpo_from_sales_document,
	)

	sync_lpo_from_sales_document(doc)
	if not _has_repair_traces(doc):
		return
	job_names = _repair_job_names(doc)
	if getattr(doc, "docstatus", 0) == 1:
		_reconcile_component_links(doc, linked_field="sales_order", linked_item_field="sales_order_item")
	for job_name in job_names:
		sync_repair_job_related_tables(job_name)
	_notify_repair_job_related_tables(job_names)


def submit_sales_order(doc, method=None):
	validate_sales_order(doc, method)
	sync_sales_order(doc, method)


def cancel_sales_order(doc, method=None):
	from auto_service_management.auto_service_management.integration.customer_lpo_workflow import (
		sync_lpo_from_sales_document,
	)

	sync_lpo_from_sales_document(doc)
	job_names = _repair_job_names(doc)
	_release_component_links(doc, "sales_order", "sales_order_item")
	for job_name in job_names:
		sync_repair_job_related_tables(job_name)
	_notify_repair_job_related_tables(job_names)


def trash_sales_order(doc, method=None):
	cancel_sales_order(doc, method)


def validate_material_request(doc, method=None):
	if not _has_repair_traces(doc):
		return
	_validate_single_repair_job(doc)
	_validate_component_links(doc, "Material Request", "material_request")
	_validate_component_quantities(doc, stock_only=True)


def sync_sales_invoice(doc, method=None):
	from auto_service_management.auto_service_management.integration.customer_lpo_workflow import (
		sync_lpo_from_sales_document,
	)

	sync_lpo_from_sales_document(doc)
	if not _has_repair_traces(doc):
		return
	job_names = _repair_job_names(doc)
	_reconcile_component_links(
		doc,
		linked_field="sales_invoice",
		linked_item_field="sales_invoice_item",
	)
	for job_name in job_names:
		sync_repair_job_related_tables(job_name)
	_notify_repair_job_related_tables(job_names)


def submit_sales_invoice(doc, method=None):
	from auto_service_management.auto_service_management.integration.customer_lpo_workflow import (
		validate_lpo_invoice_ceiling,
		validate_lpo_sales_document,
	)

	if doc.get("customer_lpo"):
		# Serialize LPO invoice submissions so two concurrent submissions cannot
		# both pass the remaining-ceiling check against the same snapshot.
		frappe.db.sql(
			"SELECT name FROM `tabCustomer LPO` WHERE name = %s FOR UPDATE",
			doc.customer_lpo,
		)
	validate_lpo_sales_document(doc)
	validate_lpo_invoice_ceiling(doc)
	if not _has_repair_traces(doc):
		return
	_validate_invoice_service_submission(doc)
	sync_sales_invoice(doc)


def cancel_sales_invoice(doc, method=None):
	from auto_service_management.auto_service_management.integration.customer_lpo_workflow import (
		sync_lpo_from_sales_document,
	)

	sync_lpo_from_sales_document(doc)
	job_names = _repair_job_names(doc)
	for job_name in job_names:
		_assert_invoice_cancellation_allowed(job_name)
	_release_component_links(doc, "sales_invoice", "sales_invoice_item")
	for job_name in job_names:
		sync_repair_job_related_tables(job_name)
	_notify_repair_job_related_tables(job_names)


def trash_sales_invoice(doc, method=None):
	job_names = _repair_job_names(doc)
	_release_component_links(doc, "sales_invoice", "sales_invoice_item")
	for job_name in job_names:
		sync_repair_job_related_tables(job_name)
	_notify_repair_job_related_tables(job_names)


def sync_payment_entry(doc, method=None):
	job_names = _payment_entry_job_names(doc)
	if not job_names:
		return
	_sync_payment_jobs(tuple(sorted(job_names)))
	_notify_repair_job_related_tables(job_names)


def _sync_payment_jobs(job_names):
	for job_name in job_names:
		sync_repair_job_related_tables(job_name)


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
	settings = _get_settings()
	policy = settings.get("gate_pass_payment_policy") or "Full Payment Required"
	invoices = get_repair_job_sales_invoices(repair_job_name)
	_missing_invoices = [invoice for invoice in invoices if not frappe.db.exists("Sales Invoice", invoice)]
	if _missing_invoices:
		frappe.throw(
			_("Linked Sales Invoice {0} no longer exists. Refresh Repair Job billing links.").format(
				", ".join(_missing_invoices)
			)
		)
	invoices = [
		invoice for invoice in invoices if frappe.db.get_value("Sales Invoice", invoice, "docstatus") == 1
	]
	if policy in {"Payment Not Required", "No Payment Required"}:
		return invoices
	if not invoices:
		frappe.throw(_("A submitted Sales Invoice is required before issuing a Gate Pass."))
	if not _all_billable_components_submitted(repair_job_name):
		frappe.throw(
			_(
				"Every billable component must be covered by a submitted Sales Invoice before issuing a Gate Pass."
			)
		)
	rows = [
		frappe.db.get_value(
			"Sales Invoice",
			invoice,
			["grand_total", "rounded_total", "outstanding_amount"],
			as_dict=True,
		)
		for invoice in invoices
	]
	unpaid = []
	total = paid = 0
	for invoice, row in zip(invoices, rows, strict=False):
		if not row:
			frappe.throw(
				_("Linked Sales Invoice {0} no longer exists. Refresh Repair Job billing links.").format(
					invoice
				)
			)
		payable = flt(row.rounded_total or row.grand_total)
		outstanding = flt(row.outstanding_amount)
		total += payable
		paid += max(payable - outstanding, 0)
		if outstanding > 0.0001:
			unpaid.append(f"{invoice} ({outstanding:g} outstanding)")
	if policy == "Full Payment Required" and unpaid:
		frappe.throw(_("Full payment is required before issuing a Gate Pass: {0}.").format(", ".join(unpaid)))
	if policy == "Partial Payment Allowed" and paid <= 0:
		frappe.throw(_("At least partial payment is required before issuing a Gate Pass."))
	return invoices


def get_repair_job_sales_invoices(repair_job_name: str, *, submitted_only: bool = False) -> list[str]:
	job = frappe.get_doc("Repair Job", repair_job_name)
	invoices = {row.sales_invoice for row in (job.get("sales_invoices") or []) if row.sales_invoice}
	invoices.update(
		frappe.get_all(
			"Sales Invoice",
			filters={"repair_job": repair_job_name},
			pluck="name",
			limit_page_length=0,
		)
	)
	if submitted_only:
		invoices = {
			invoice for invoice in invoices if frappe.db.get_value("Sales Invoice", invoice, "docstatus") == 1
		}
	return sorted(invoices)


def has_active_repair_job_invoice(repair_job_name: str) -> bool:
	return bool(
		frappe.db.exists("Sales Invoice", {"repair_job": repair_job_name, "docstatus": ["<", 2]})
		or frappe.db.sql(
			"""
			SELECT 1 FROM `tabSales Invoice Item`
			WHERE repair_job = %s AND parenttype = 'Sales Invoice'
			AND docstatus < 2 LIMIT 1
			""",
			repair_job_name,
		)
	)


def sync_repair_job_invoice_state(repair_job_name: str):
	sync_repair_job_related_tables(repair_job_name)


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
	invoice_names = sorted({component.sales_invoice for component in components if component.sales_invoice})
	invoice_statuses = {
		row.name: row.docstatus
		for row in frappe.get_all(
			"Sales Invoice",
			filters={"name": ["in", invoice_names]},
			fields=["name", "docstatus"],
			limit_page_length=len(invoice_names),
		)
	}
	return all(
		component.sales_invoice and invoice_statuses.get(component.sales_invoice) == 1
		for component in components
	)


def _validate_invoice_service_submission(doc):
	if getattr(doc, "docstatus", 0) == 0:
		return
	service_names = {
		row.repair_job_service for row in _trace_items(doc) if getattr(row, "repair_job_service", None)
	}
	if not service_names:
		return
	services = frappe.get_all(
		"Repair Job Service",
		filters={"name": ["in", sorted(service_names)]},
		fields=["name", "service_name", "docstatus"],
		limit_page_length=0,
	)
	services_by_name = {service.name: service for service in services}
	missing = sorted(service_names - set(services_by_name))
	if missing:
		frappe.throw(_("Repair Job Service {0} was not found.").format(", ".join(missing)))
	invalid = [service.service_name or service.name for service in services if service.docstatus == 2]
	if invalid:
		frappe.throw(
			_("Cancelled Repair Job Services cannot be submitted in a Sales Invoice: {0}.").format(
				", ".join(sorted(invalid))
			)
		)


def _validate_sales_order_submission(doc):
	for row in _trace_items(doc):
		component = frappe.db.get_value(
			row.repair_component_doctype,
			row.repair_component_row,
			["sales_order", "sales_invoice"],
			as_dict=True,
		)
		if not component:
			continue
		linked_order = component.get("sales_order")
		if (
			linked_order
			and linked_order != doc.name
			and frappe.db.get_value("Sales Order", linked_order, "docstatus") == 1
		):
			frappe.throw(
				_("Repair component {0} is already owned by submitted Sales Order {1}.").format(
					row.repair_component_row, linked_order
				)
			)
		linked_invoice = component.get("sales_invoice")
		if linked_invoice and frappe.db.get_value("Sales Invoice", linked_invoice, "docstatus") == 1:
			frappe.throw(
				_("Repair component {0} is already invoiced in Sales Invoice {1}.").format(
					row.repair_component_row, linked_invoice
				)
			)
		conflict = frappe.db.sql(
			"""
			SELECT soi.parent
			FROM `tabSales Order Item` soi
			INNER JOIN `tabSales Order` so ON so.name = soi.parent
			WHERE so.docstatus = 1
			AND soi.repair_component_doctype = %s
			AND soi.repair_component_row = %s
			AND soi.parent <> %s
			LIMIT 1
			""",
			(row.repair_component_doctype, row.repair_component_row, doc.name),
		)
		if conflict:
			frappe.throw(
				_("Repair component {0} is already owned by submitted Sales Order {1}.").format(
					row.repair_component_row, conflict[0][0]
				)
			)


def _validate_single_repair_job(doc):
	job_names = _repair_job_names(doc)
	if len(job_names) != 1:
		frappe.throw(_("A target document must contain components from exactly one Repair Job."))
	job_name = next(iter(job_names))
	if doc.get("repair_job") and doc.repair_job != job_name:
		frappe.throw(_("The parent Repair Job must match all component rows."))
	doc.repair_job = job_name
	return frappe.get_doc("Repair Job", job_name)


def _validate_sales_document_scope(doc):
	"""Return the Repair Jobs represented by a single-job or campaign sales document."""
	campaign_name = doc.get("fleet_service_campaign")
	if not campaign_name:
		return [_validate_single_repair_job(doc)]

	if doc.get("repair_job"):
		frappe.throw(_("A campaign sales document cannot also have a parent Repair Job."))
	if doc.get("repair_job_service"):
		frappe.throw(_("A campaign sales document cannot have a parent Repair Job Service source."))
	if doc.get("project"):
		frappe.throw(_("A campaign sales document cannot have a parent Project."))

	_validate_campaign_item_traces(doc)
	_validate_campaign_component_authority(doc)
	job_names = {row.repair_job for row in _trace_items(doc) if getattr(row, "repair_job", None)}
	if not job_names:
		frappe.throw(_("A campaign sales document must contain Repair Job component rows."))

	campaign = frappe.get_doc("Fleet Service Campaign", campaign_name)
	if doc.get("customer") and doc.customer != campaign.customer:
		frappe.throw(
			_("Sales document customer must match Fleet Service Campaign {0}.").format(campaign.name)
		)

	jobs = []
	for job_name in sorted(job_names):
		job = frappe.get_doc("Repair Job", job_name)
		if job.get("fleet_service_campaign") != campaign.name:
			frappe.throw(
				_("Repair Job {0} does not belong to Fleet Service Campaign {1}.").format(
					job.name,
					campaign.name,
				)
			)
		if job.customer != campaign.customer:
			frappe.throw(
				_("Repair Job {0} customer does not match Fleet Service Campaign {1}.").format(
					job.name,
					campaign.name,
				)
			)
		jobs.append(job)

	doc.repair_job = None
	if hasattr(doc, "repair_job_service"):
		doc.repair_job_service = None
	return jobs


def _validate_campaign_item_traces(doc):
	items = doc.get("items") or []
	if not items:
		frappe.throw(_("A campaign sales document must contain Repair Job component rows."))
	for index, row in enumerate(items, start=1):
		missing = [
			fieldname for fieldname in CAMPAIGN_SALES_ITEM_TRACE_FIELDS if not getattr(row, fieldname, None)
		]
		if missing:
			frappe.throw(
				_("Sales document item {0} is missing campaign trace fields: {1}.").format(
					getattr(row, "idx", None) or index,
					", ".join(missing),
				)
			)


def _validate_campaign_component_authority(doc):
	for index, row in enumerate(doc.get("items") or [], start=1):
		authority = _resolve_campaign_component_authority(row)
		for fieldname in CAMPAIGN_SALES_ITEM_TRACE_FIELDS:
			if getattr(row, fieldname, None) != authority.get(fieldname):
				frappe.throw(
					_("Sales document item {0} has an invalid authoritative {1} trace.").format(
						getattr(row, "idx", None) or index,
						fieldname,
					)
				)

		invoice = _submitted_component_document(
			row,
			"Sales Invoice",
			"Sales Invoice Item",
			exclude_parent=doc.get("name"),
		)
		if not invoice and authority.sales_invoice:
			if frappe.db.get_value("Sales Invoice", authority.sales_invoice, "docstatus") == 1:
				invoice = frappe._dict(
					parent=authority.sales_invoice,
					item=authority.sales_invoice_item,
				)
		if invoice:
			frappe.throw(
				_("Repair component {0} is already invoiced in submitted Sales Invoice {1}.").format(
					row.repair_component_row,
					invoice.parent,
				)
			)

		order = _submitted_component_document(
			row,
			"Sales Order",
			"Sales Order Item",
			exclude_parent=doc.get("name") if doc.get("doctype") == "Sales Order" else None,
		)
		if not order and authority.sales_order:
			if frappe.db.get_value("Sales Order", authority.sales_order, "docstatus") == 1:
				order = frappe._dict(parent=authority.sales_order, item=authority.sales_order_item)
		if not order:
			continue
		if doc.get("doctype") == "Sales Invoice":
			is_native_order_invoice = (
				getattr(row, "sales_order", None) == order.parent
				and getattr(row, "so_detail", None) == order.item
			)
			if is_native_order_invoice:
				continue
		frappe.throw(
			_("Repair component {0} is already committed to submitted Sales Order {1}.").format(
				row.repair_component_row,
				order.parent,
			)
		)


def _resolve_campaign_component_authority(row):
	component_doctype = row.repair_component_doctype
	component_name = row.repair_component_row
	if component_doctype not in ACTIVE_COMPONENT_DOCTYPES:
		frappe.throw(_("Component type {0} is not active.").format(component_doctype))
	component = frappe.db.get_value(
		component_doctype,
		component_name,
		[
			"name",
			"repair_job",
			"repair_job_service",
			"customer_vehicle",
			"sales_order",
			"sales_order_item",
			"sales_invoice",
			"sales_invoice_item",
		],
		as_dict=True,
	)
	if not component:
		frappe.throw(_("Repair component {0} no longer exists.").format(component_name))
	service = frappe.db.get_value(
		"Repair Job Service",
		component.repair_job_service,
		["name", "repair_job", "customer_vehicle"],
		as_dict=True,
	)
	if not service:
		frappe.throw(_("Repair Job Service {0} no longer exists.").format(component.repair_job_service))
	job = frappe.db.get_value(
		"Repair Job",
		service.repair_job,
		["name", "customer_vehicle", "project"],
		as_dict=True,
	)
	if not job:
		frappe.throw(_("Repair Job {0} no longer exists.").format(service.repair_job))
	if component.repair_job != job.name or component.customer_vehicle != job.customer_vehicle:
		frappe.throw(_("Repair component {0} has inconsistent Repair Job context.").format(component.name))
	if service.customer_vehicle != job.customer_vehicle:
		frappe.throw(_("Repair Job Service {0} has inconsistent vehicle context.").format(service.name))
	return frappe._dict(
		repair_job=job.name,
		customer_vehicle=job.customer_vehicle,
		repair_job_service=service.name,
		repair_component_doctype=component_doctype,
		repair_component_row=component.name,
		project=job.project,
		sales_order=component.sales_order,
		sales_order_item=component.sales_order_item,
		sales_invoice=component.sales_invoice,
		sales_invoice_item=component.sales_invoice_item,
	)


def _submitted_component_document(
	row,
	parent_doctype,
	item_doctype,
	*,
	exclude_parent=None,
):
	items = frappe.get_all(
		item_doctype,
		filters={
			"repair_component_doctype": row.repair_component_doctype,
			"repair_component_row": row.repair_component_row,
		},
		fields=["name", "parent"],
		limit_page_length=0,
	)
	for item in items:
		if exclude_parent and item.parent == exclude_parent:
			continue
		if frappe.db.get_value(parent_doctype, item.parent, "docstatus") == 1:
			return frappe._dict(parent=item.parent, item=item.name)
	return None


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
			is_active = (
				is_material_request_active(linked_name)
				if linked_doctype == "Material Request"
				else frappe.db.get_value(linked_doctype, linked_name, "docstatus") in {0, 1}
			)
			if is_active:
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
			"purpose": "Final Release",
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
			continue
		for row in frappe.get_all(
			"Sales Invoice Item",
			filters={"parent": invoice_name, "repair_job": ["is", "set"]},
			pluck="repair_job",
			limit_page_length=0,
		):
			job_names.add(row)
	return job_names


def _notify_repair_job_related_tables(job_names):
	job_names = tuple(sorted(job_names or []))
	if not job_names:
		return

	def publish():
		for job_name in job_names:
			frappe.publish_realtime(
				"repair_job_related_tables_updated",
				{"repair_job": job_name},
				doctype="Repair Job",
				docname=job_name,
			)

	after_commit = getattr(frappe.db, "after_commit", None)
	if after_commit and hasattr(after_commit, "add"):
		after_commit.add(publish)
	else:
		publish()


def _trace_items(doc):
	return [
		row
		for row in doc.get("items") or []
		if getattr(row, "repair_component_doctype", None) and getattr(row, "repair_component_row", None)
	]


def _has_repair_traces(doc):
	return bool(doc.get("repair_job") or doc.get("fleet_service_campaign") or _trace_items(doc))
