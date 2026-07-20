# Copyright (c) 2026, Aslam Kimbugwe and contributors
# For license information, please see license.txt

from __future__ import annotations

from dataclasses import dataclass

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

INVOICEABLE_SERVICE_STATUSES = frozenset({"Approved", "Completed"})
EXCLUDED_SERVICE_STATUSES = frozenset({"Rejected", "Cancelled", "Canceled"})
STOCK_COMPONENT_TYPES = {"Part", "Consumable"}
STATUS_ALIASES = {
	"Parts": "Part",
}

COMPONENT_TABLES = (
	{
		"fieldname": "parts",
		"doctype": "Repair Job Service Part",
		"component_type": "Part",
		"template_fieldname": "parts",
	},
	{
		"fieldname": "labour",
		"doctype": "Repair Job Service Labour",
		"component_type": "Labour",
		"template_fieldname": "labour",
	},
	{
		"fieldname": "consumables",
		"doctype": "Repair Job Service Consumable",
		"component_type": "Consumable",
		"template_fieldname": "consumables",
	},
)
COMPONENT_TABLE_BY_TYPE = {row["component_type"]: row for row in COMPONENT_TABLES}


@frappe.whitelist(methods=["POST"])
def make_sales_invoice(source_name: str, target_doc: str | None = None):
	service = frappe.get_doc("Repair Job Service", source_name)
	service.check_permission("read")
	from auto_service_management.auto_service_management.integration.erpnext.component_mapping import (
		map_sales_invoice,
	)

	return map_sales_invoice(service.repair_job, target_doc=target_doc, service_names={service.name})


@frappe.whitelist(methods=["POST"])
def make_material_request(source_name: str, target_doc: str | None = None):
	service = frappe.get_doc("Repair Job Service", source_name)
	service.check_permission("read")
	from auto_service_management.auto_service_management.integration.erpnext.component_mapping import (
		map_material_request,
	)

	return map_material_request(service.repair_job, target_doc=target_doc, service_names={service.name})


@dataclass(frozen=True)
class ServiceComponent:
	service: Document
	row: Document
	table_fieldname: str
	component_type: str

	@property
	def row_doctype(self):
		return self.row.doctype

	@property
	def name(self):
		return self.row.name

	@property
	def service_type(self):
		return self.component_type

	@property
	def service_description(self):
		return getattr(self.row, "description", None) or getattr(self.row, "item_code", None) or self.row.name

	@property
	def quantity(self):
		if self.component_type == "Labour":
			return getattr(self.row, "hours", None) or getattr(self.row, "estimated_hours", None) or 1
		return getattr(self.row, "quantity", None) or 0

	@property
	def invoice_quantity(self):
		if self.component_type == "Labour":
			return getattr(self.row, "billing_hours", None) or 0
		return getattr(self.row, "quantity", None) or 0

	@property
	def invoice_rate(self):
		if self.component_type == "Labour":
			return getattr(self.row, "billing_rate", None) or 0
		return getattr(self.row, "rate", None) or 0

	@property
	def rate(self):
		return self.invoice_rate

	@property
	def invoice_amount(self):
		if self.component_type == "Labour":
			return getattr(self.row, "billing_amount", None) or 0
		return getattr(self.row, "amount", None) or 0

	@property
	def amount(self):
		return self.invoice_amount

	def __getattr__(self, fieldname):
		return getattr(self.row, fieldname)


class RepairJobService(Document):
	def before_validate(self):
		self.sync_from_repair_job()
		self.sync_component_context()

	def validate(self):
		if not self.repair_job:
			frappe.throw(_("Repair Job is required before saving a Repair Job Service."))
		if not self.workshop_bay:
			frappe.throw(_("Workshop Bay is required for a Repair Job Service."))
		self.validate_diagnosis_report()
		self.calculate_totals()
		from auto_service_management.auto_service_management.workflow_compatibility import (
			sync_repair_job_service_summary,
		)

		sync_repair_job_service_summary(self)

	def on_update(self):
		from auto_service_management.auto_service_management.workflow_compatibility import (
			recompute_repair_job_state,
			sync_repair_job_related_tables,
			sync_repair_job_service_summary,
		)

		sync_repair_job_service_summary(self)
		sync_repair_job_related_tables(self.repair_job)
		recompute_repair_job_state(self.repair_job)
		sync_repair_job_total(self.repair_job)

	def after_delete(self):
		from auto_service_management.auto_service_management.workflow_compatibility import (
			sync_repair_job_related_tables,
		)

		sync_repair_job_related_tables(self.repair_job)
		sync_repair_job_total(self.repair_job)

	def on_trash(self):
		for component in get_service_components(self):
			if component_has_downstream(component):
				frappe.throw(
					_("Cancel linked ERPNext documents before deleting service component {0}.").format(
						component.service_description
					)
				)

	def sync_from_repair_job(self):
		if not self.repair_job:
			return
		job = frappe.db.get_value(
			"Repair Job",
			self.repair_job,
			["customer", "customer_vehicle", "diagnosis_report", "currency"],
			as_dict=True,
		)
		if not job:
			frappe.throw(_("Repair Job {0} does not exist.").format(self.repair_job))

		self.customer = job.customer
		self.customer_vehicle = job.customer_vehicle
		self.currency = job.currency
		if not self.diagnosis_report:
			self.diagnosis_report = job.diagnosis_report

	def validate_diagnosis_report(self):
		if not self.diagnosis_report:
			return
		diagnosis = frappe.db.get_value(
			"Diagnosis Report",
			self.diagnosis_report,
			["repair_job", "customer_vehicle"],
			as_dict=True,
		)
		if not diagnosis:
			frappe.throw(_("Diagnosis Report {0} does not exist.").format(self.diagnosis_report))
		if diagnosis.repair_job and diagnosis.repair_job != self.repair_job:
			frappe.throw(_("Diagnosis Report is linked to a different Repair Job."))
		if diagnosis.customer_vehicle and diagnosis.customer_vehicle != self.customer_vehicle:
			frappe.throw(_("Diagnosis Report vehicle does not match this service."))

	def has_components(self):
		return any(self.get(row["fieldname"]) for row in COMPONENT_TABLES)

	def sync_component_context(self):
		for component in get_service_components(self):
			row = component.row
			row.repair_job = self.repair_job
			row.repair_job_service = self.name
			row.customer_vehicle = self.customer_vehicle
			row.currency = self.currency
			if row.billable is None:
				row.billable = 1
			if component.component_type == "Labour":
				if row.billable:
					if not getattr(row, "billing_hours", None):
						row.billing_hours = getattr(row, "hours", None) or 0
				else:
					row.billing_hours = 0
				if row.billable and not getattr(row, "billing_rate", None):
					settings = frappe.get_single("Auto Service Settings")
					if settings.default_labour_rate:
						row.billing_rate = settings.default_labour_rate
						if not row.currency and settings.default_currency:
							row.currency = settings.default_currency
			calculate_component_amount(row, component.component_type)

	def calculate_totals(self):
		total = 0
		cost_total = 0
		for component in get_service_components(self):
			calculate_component_amount(component.row, component.component_type)
			if component.component_type == "Labour":
				cost_total += component.costing_amount or 0
				if component.billable:
					total += component.billing_amount or 0
			else:
				cost_total += component.cost_amount or 0
				if component.billable:
					total += component.amount or 0

		self.total_amount = flt(total, self.precision("total_amount"))
		self.cost_total = flt(cost_total, self.precision("cost_total"))
		self.gross_margin = flt(self.total_amount - self.cost_total, self.precision("gross_margin"))
		self.margin_percentage = flt(
			(self.gross_margin / self.total_amount * 100) if self.total_amount else 0,
			self.precision("margin_percentage"),
		)

class RepairJobServiceComponent(Document):
	component_type = None

	def validate(self):
		if self.billable is None:
			self.billable = 1
		calculate_component_amount(self, self.component_type)


def _component_quantity(row, component_type):
	if component_type == "Labour":
		return getattr(row, "hours", None) or getattr(row, "estimated_hours", None) or 1
	return getattr(row, "quantity", None) or 0


def calculate_component_amount(row, component_type):
	if component_type == "Labour":
		hours = getattr(row, "hours", None) or 0
		billing_hours = getattr(row, "billing_hours", None) or 0
		billing_rate = getattr(row, "billing_rate", None) or 0
		costing_rate = getattr(row, "costing_rate", None) or 0
		row.billing_amount = billing_hours * billing_rate
		row.costing_amount = hours * costing_rate
		return

	# Parts and consumables use stock-style pricing.
	quantity = _component_quantity(row, component_type)
	gross_amount = quantity * (row.rate or 0)
	row.discount_amount = gross_amount * (row.discount_percentage or 0) / 100
	row.amount = gross_amount - (row.discount_amount or 0)
	row.cost_amount = quantity * (row.cost_rate or 0)
	row.margin_amount = (row.amount or 0) - (row.cost_amount or 0)
	row.margin_percentage = (row.margin_amount / row.amount * 100) if row.amount else 0


def _normalize_service_type(service_type):
	return STATUS_ALIASES.get(service_type, service_type)


def _component_signature(row, component_type):
	return (
		component_type,
		getattr(row, "description", None),
		getattr(row, "item_code", None),
		getattr(row, "assigned_to", None),
		getattr(row, "activity_type", None),
		getattr(row, "task", None),
		getattr(row, "quantity", None),
		getattr(row, "hours", None),
		getattr(row, "estimated_hours", None),
		getattr(row, "billing_hours", None),
		getattr(row, "billing_rate", None),
		getattr(row, "costing_rate", None),
		getattr(row, "billable", None),
		getattr(row, "rate", None),
		getattr(row, "discount_percentage", None),
		getattr(row, "cost_rate", None),
		getattr(row, "consumption_basis", None),
	)


def _copy_template_component_row(target_row, source_row):
	for fieldname in (
		"description",
		"item_code",
		"assigned_to",
		"activity_type",
		"task",
		"quantity",
		"hours",
		"estimated_hours",
		"billing_hours",
		"billing_rate",
		"costing_rate",
		"billable",
		"rate",
		"discount_percentage",
		"cost_rate",
		"consumption_basis",
		"legacy_repair_service_line",
	):
		value = getattr(source_row, fieldname, None)
		if value is not None:
			setattr(target_row, fieldname, value)


def component_has_downstream(component):
	row = component.row if isinstance(component, ServiceComponent) else component
	return any(
		getattr(row, fieldname, None)
		for fieldname in (
			"material_request",
			"material_request_item",
			"stock_entry",
			"stock_entry_detail",
			"timesheet",
			"timesheet_detail",
			"sales_invoice",
			"sales_invoice_item",
		)
	)


def get_service_components(service, component_types=None):
	component_types = set(component_types or [])
	for definition in COMPONENT_TABLES:
		component_type = definition["component_type"]
		if component_types and component_type not in component_types:
			continue
		for row in service.get(definition["fieldname"]) or []:
			yield ServiceComponent(
				service=service,
				row=row,
				table_fieldname=definition["fieldname"],
				component_type=component_type,
			)


def get_repair_job_services(repair_job_name):
	if not repair_job_name:
		return []
	if not frappe.db.table_exists("Repair Job Service"):
		return []
	service_names = frappe.get_all(
		"Repair Job Service",
		filters={"repair_job": repair_job_name},
		pluck="name",
		order_by="creation asc",
	)
	return [frappe.get_doc("Repair Job Service", name) for name in service_names]


def iter_repair_job_components(
	repair_job_name,
	*,
	service_statuses=None,
	component_types=None,
	billable_only=False,
	include_excluded=False,
	service_names=None,
):
	component_types = {
		_normalize_service_type(component_type) for component_type in set(component_types or [])
	}
	service_statuses = {str(status) for status in service_statuses} if service_statuses is not None else None
	service_names = set(service_names or [])
	for service in get_repair_job_services(repair_job_name):
		if service_names and service.name not in service_names:
			continue
		if not include_excluded and getattr(service, "docstatus", 0) == 2:
			continue
		if service_statuses is not None and getattr(service, "status", None) not in service_statuses:
			continue
		for component in get_service_components(service, component_types=component_types):
			if billable_only and not component.billable:
				continue
			yield service, component


def set_component_values(component, values, update_modified=False):
	row = component.row if isinstance(component, ServiceComponent) else component
	frappe.db.set_value(row.doctype, row.name, values, update_modified=update_modified)


def sync_repair_job_total(repair_job_name):
	if not repair_job_name or not frappe.db.exists("Repair Job", repair_job_name):
		return
	total = 0
	for service in get_repair_job_services(repair_job_name):
		if getattr(service, "docstatus", 0) != 2:
			total += service.total_amount or 0
	frappe.db.set_value("Repair Job", repair_job_name, "total_amount", total, update_modified=False)
