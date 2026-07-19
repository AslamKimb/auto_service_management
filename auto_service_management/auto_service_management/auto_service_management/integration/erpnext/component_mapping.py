from __future__ import annotations

from collections.abc import Iterable

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, today

from auto_service_management.auto_service_management.doctype.repair_job_service.repair_job_service import (
	INVOICEABLE_SERVICE_STATUSES,
	STOCK_COMPONENT_TYPES,
	ServiceComponent,
	iter_repair_job_components,
)

MATERIAL_REQUEST_JOB_STATUSES = {
	"Approved",
	"In Repair",
	"Quality Check",
	"Ready for Invoice",
}


def map_sales_invoice(
	repair_job_name: str,
	*,
	target_doc: str | dict | None = None,
	service_names: Iterable[str] | None = None,
) -> Document:
	repair_job = _get_repair_job(repair_job_name)

	target = _get_target_doc("Sales Invoice", target_doc)
	_validate_target_job(target, repair_job)
	_validate_service_scope(
		repair_job.name,
		service_names,
		None,
		document_label=_("Sales Invoice"),
	)
	current_refs = _component_refs(target)
	components, reserved = _eligible_components(
		repair_job,
		service_statuses=None,
		billable_only=True,
		service_names=service_names,
		current_refs=current_refs,
		current_target_name=target.name if not target.is_new() else None,
		linked_doctype="Sales Invoice",
		linked_field="sales_invoice",
	)
	if not components:
		_throw_no_components(
			reserved,
			_("No billable Parts, Consumables, or Labour components are available on this Repair Job."),
		)
	if reserved:
		_show_reservation_notice(reserved)

	_settings = frappe.get_single("Auto Service Settings")
	_validate_company(target, _settings.company)
	_set_if_empty(target, "customer", repair_job.customer)
	_set_if_empty(target, "company", _settings.company)
	_set_if_empty(target, "selling_price_list", _settings.selling_price_list or _settings.price_list)
	target.currency = _settings.default_currency or target.get("currency")
	_set_if_empty(target, "project", repair_job.project)
	target.repair_job = repair_job.name
	target.update_stock = 0
	target.is_pos = 0

	mapped_items = [_sales_invoice_item(repair_job, service, component) for service, component in components]
	for item in mapped_items:
		target.append("items", item)

	target.run_method("set_missing_values")
	target.run_method("calculate_taxes_and_totals")
	return target


def map_material_request(
	repair_job_name: str,
	*,
	target_doc: str | dict | None = None,
	service_names: Iterable[str] | None = None,
) -> Document:
	repair_job = _get_repair_job(repair_job_name)
	if repair_job.job_status not in MATERIAL_REQUEST_JOB_STATUSES:
		frappe.throw(_("Repair Job must be Approved or in workshop execution before requesting materials."))

	target = _get_target_doc("Material Request", target_doc)
	_validate_target_job(target, repair_job)
	_validate_service_scope(
		repair_job.name,
		service_names,
		INVOICEABLE_SERVICE_STATUSES,
		document_label=_("Material Request"),
	)
	current_refs = _component_refs(target)
	components, _reserved = _eligible_components(
		repair_job,
		service_statuses=INVOICEABLE_SERVICE_STATUSES,
		component_types=STOCK_COMPONENT_TYPES,
		service_names=service_names,
		current_refs=current_refs,
		current_target_name=target.name if not target.is_new() else None,
		linked_doctype="Material Request",
		linked_field="material_request",
	)
	if not components:
		frappe.throw(_("No approved, unrequested Part or Consumable components are available."))

	settings = frappe.get_single("Auto Service Settings")
	_validate_company(target, settings.company)
	_set_if_empty(target, "company", settings.company)
	target.material_request_type = "Material Issue"
	target.repair_job = repair_job.name

	for service, component in components:
		target.append("items", _material_request_item(repair_job, service, component, settings))

	target.run_method("set_missing_values")
	return target


def _get_repair_job(name: str):
	repair_job = frappe.get_doc("Repair Job", name)
	repair_job.check_permission("read")
	return repair_job


def _get_target_doc(doctype: str, target_doc: str | dict | None):
	if isinstance(target_doc, str):
		target_doc = frappe.parse_json(target_doc)
	target = frappe.get_doc(target_doc) if target_doc else frappe.new_doc(doctype)
	if target.doctype != doctype:
		frappe.throw(_("Expected target document type {0}.").format(doctype))
	if target.docstatus != 0:
		frappe.throw(_("Items can only be mapped into a draft {0}.").format(doctype))
	if target.name and not target.is_new():
		target.check_permission("write")
	else:
		frappe.has_permission(doctype, "create", throw=True)
	return target


def _validate_target_job(target, repair_job):
	if target.get("repair_job") and target.repair_job != repair_job.name:
		frappe.throw(_("A target document can contain components from only one Repair Job."))
	if (
		target.doctype == "Sales Invoice"
		and target.get("customer")
		and target.customer != repair_job.customer
	):
		frappe.throw(_("Sales Invoice customer must match the Repair Job customer."))

	item_jobs = {row.repair_job for row in target.get("items") or [] if getattr(row, "repair_job", None)}
	if item_jobs - {repair_job.name}:
		frappe.throw(_("A target document can contain components from only one Repair Job."))


def _eligible_components(
	repair_job,
	*,
	service_statuses=None,
	current_refs,
	current_target_name,
	linked_doctype,
	linked_field,
	component_types=None,
	billable_only=False,
	service_names=None,
):
	eligible = []
	reserved = {}
	for service, component in iter_repair_job_components(
		repair_job.name,
		service_statuses=service_statuses,
		component_types=component_types,
		billable_only=billable_only,
		service_names=service_names,
	):
		ref = (component.row_doctype, component.name)
		if ref in current_refs:
			continue
		linked_name = _active_link_name(
			component,
			linked_doctype,
			linked_field,
			current_target_name=current_target_name,
		)
		if linked_name:
			reserved.setdefault(linked_name, []).append(component.service_description)
			continue
		eligible.append((service, component))
	return eligible, reserved


def _has_active_link(component, linked_doctype, linked_field, *, current_target_name=None):
	return bool(
		_active_link_name(
			component,
			linked_doctype,
			linked_field,
			current_target_name=current_target_name,
		)
	)


def _active_link_name(component, linked_doctype, linked_field, *, current_target_name=None):
	linked_name = getattr(component, linked_field, None)
	if not linked_name:
		return None
	if current_target_name and linked_name == current_target_name:
		return None
	docstatus = frappe.db.get_value(linked_doctype, linked_name, "docstatus")
	return linked_name if docstatus in {0, 1} else None


def _component_refs(target):
	return {
		(row.repair_component_doctype, row.repair_component_row)
		for row in target.get("items") or []
		if getattr(row, "repair_component_doctype", None) and getattr(row, "repair_component_row", None)
	}


def _sales_invoice_item(repair_job, service, component: ServiceComponent):
	qty = flt(component.invoice_quantity)
	if qty <= 0:
		frappe.throw(
			_("Service {0} component {1} requires a quantity greater than zero.").format(
				service.service_name or service.name,
				component.service_description,
			)
		)
	rate = flt(component.invoice_rate)
	item_code = component.item_code
	item_name = component.service_description or service.service_name or service.name
	uom = getattr(component, "uom", None)
	if not uom and item_code:
		uom = frappe.db.get_value("Item", item_code, "stock_uom")
	if not uom:
		uom = "Hour" if component.component_type == "Labour" else "Nos"
	if uom and not frappe.db.exists("UOM", uom):
		uom = frappe.db.get_value("UOM", {}, "name") or uom
	item = {
		"item_code": item_code,
		"item_name": item_name,
		"description": _component_description(service, component),
		"qty": qty,
		"uom": uom,
		"rate": rate,
		"project": repair_job.project,
		**_component_trace_fields(repair_job, service, component),
	}
	company_name = frappe.get_single("Auto Service Settings").company
	income_account = frappe.db.get_value(
		"Account",
		{"company": company_name, "root_type": "Income", "is_group": 0},
		"name",
	)
	if income_account:
		item["income_account"] = income_account
	if component.component_type in STOCK_COMPONENT_TYPES:
		item["discount_percentage"] = flt(component.discount_percentage)
	return item


def _material_request_item(repair_job, service, component: ServiceComponent, settings):
	if not component.item_code:
		frappe.throw(
			_("Stock component {0} requires an Item before requesting materials.").format(
				component.service_description
			)
		)
	quantity = flt(component.quantity)
	if quantity <= 0:
		frappe.throw(
			_("Stock component {0} requires a quantity greater than zero.").format(
				component.service_description
			)
		)
	warehouse = component.warehouse or settings.default_warehouse
	if not warehouse:
		frappe.throw(_("Stock component {0} requires a Warehouse.").format(component.service_description))
	return {
		"item_code": component.item_code,
		"qty": quantity,
		"uom": component.uom,
		"warehouse": warehouse,
		"schedule_date": today(),
		"description": _component_description(service, component),
		**_component_trace_fields(repair_job, service, component),
	}


def _component_trace_fields(repair_job, service, component):
	return {
		"repair_job": repair_job.name,
		"customer_vehicle": repair_job.customer_vehicle,
		"repair_job_service": service.name,
		"repair_component_doctype": component.row_doctype,
		"repair_component_row": component.name,
		"repair_service_line": component.legacy_repair_service_line or component.name,
	}


def _component_description(service, component):
	service_name = service.service_name or service.name
	description = component.service_description or component.item_code or component.name
	return f"{service_name}: {description}"


def _set_if_empty(doc, fieldname, value):
	if not doc.get(fieldname) and value:
		doc.set(fieldname, value)


def _validate_company(target, company):
	if target.get("company") and company and target.company != company:
		frappe.throw(_("Target company must match the Auto Service Settings company."))


def _validate_service_scope(
	repair_job_name: str,
	service_names: Iterable[str] | None,
	allowed_statuses: Iterable[str] | None,
	*,
	document_label: str,
) -> None:
	service_names = set(service_names or [])
	allowed_statuses = set(allowed_statuses or []) if allowed_statuses is not None else None
	if not service_names:
		return

	services = frappe.get_all(
		"Repair Job Service",
		filters={"name": ["in", sorted(service_names)]},
		fields=["name", "repair_job", "docstatus", "service_name"],
		limit_page_length=0,
	)
	services_by_name = {service.name: service for service in services}

	missing = sorted(service_names - set(services_by_name))
	if missing:
		frappe.throw(_("Repair Job Service {0} was not found.").format(", ".join(missing)))

	for service_name in sorted(service_names):
		service = services_by_name[service_name]
		if service.repair_job != repair_job_name:
			frappe.throw(
				_("Repair Job Service {0} does not belong to Repair Job {1}.").format(
					service_name,
					repair_job_name,
				)
			)
		# Service lifecycle status was removed; submission is handled by docstatus on the document itself.


def _throw_no_components(reserved, empty_message):
	if reserved:
		links = ", ".join(sorted(reserved))
		frappe.throw(
			_("All eligible components are already reserved by active Sales Invoice(s): {0}.").format(links)
		)
	frappe.throw(empty_message)


def _show_reservation_notice(reserved):
	details = ", ".join(
		_("{0} ({1} component(s))").format(invoice, len(components))
		for invoice, components in sorted(reserved.items())
	)
	frappe.msgprint(
		_("Some components were skipped because they are reserved by active Sales Invoice(s): {0}.").format(
			details
		),
		alert=True,
	)
