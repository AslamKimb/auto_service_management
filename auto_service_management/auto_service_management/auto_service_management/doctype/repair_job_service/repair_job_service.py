# Copyright (c) 2026, Aslam Kimbugwe and contributors
# For license information, please see license.txt

from __future__ import annotations

from dataclasses import dataclass

import frappe
from frappe import _
from frappe.model.document import Document

STOCK_COMPONENT_TYPES = {"Part", "Consumable"}
STATUS_ALIASES = {
	"Parts": "Part",
	"Subcontract": "Subcontracted Service",
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
	{
		"fieldname": "subcontracted_services",
		"doctype": "Repair Job Service Subcontracted Service",
		"component_type": "Subcontracted Service",
		"template_fieldname": "subcontracted_services",
	},
)
COMPONENT_TABLE_BY_TYPE = {row["component_type"]: row for row in COMPONENT_TABLES}


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
			return getattr(self.row, "actual_hours", None) or getattr(self.row, "estimated_hours", None) or 1
		if self.component_type == "Subcontracted Service":
			return 1
		return getattr(self.row, "quantity", None) or 0

	def __getattr__(self, fieldname):
		return getattr(self.row, fieldname)


class RepairJobService(Document):
	def before_validate(self):
		self.sync_from_repair_job()
		if self.repair_service_template and not self.has_components():
			self.load_template_components()
		self.sync_component_context()

	def validate(self):
		self.validate_diagnosis_report()
		self.calculate_totals()
		self.derive_status_from_components()

	def on_update(self):
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

	def load_template_components(self):
		template = frappe.get_doc("Repair Service Template", self.repair_service_template)
		if not self.service_name:
			self.service_name = template.service_name or template.template_name
		if not self.description:
			self.description = template.description
		if template.default_billable is not None:
			self.billable = template.default_billable

		for definition in COMPONENT_TABLES:
			for template_row in template.get(definition["template_fieldname"]) or []:
				self.append(
					definition["fieldname"],
					_template_row_to_service_row(template_row, definition["component_type"]),
				)

	def sync_component_context(self):
		for component in get_service_components(self):
			row = component.row
			row.repair_job = self.repair_job
			row.repair_job_service = self.name
			row.customer_vehicle = self.customer_vehicle
			row.currency = self.currency
			if row.billable is None:
				row.billable = 1
			calculate_component_amount(row, component.component_type)

	def calculate_totals(self):
		total = 0
		cost_total = 0
		for component in get_service_components(self):
			calculate_component_amount(component.row, component.component_type)
			if not component.billable:
				continue
			total += component.amount or 0
			cost_total += component.cost_amount or 0

		self.total_amount = total
		self.cost_total = cost_total
		self.gross_margin = total - cost_total
		self.margin_percentage = (self.gross_margin / total * 100) if total else 0

	def derive_status_from_components(self):
		if self.status in {"Rejected", "Deferred", "Cancelled"}:
			return
		if self.status in {None, "", "Draft"}:
			self.status = "Pending Approval"


class RepairJobServiceComponent(Document):
	component_type = None

	def validate(self):
		if self.billable is None:
			self.billable = 1
		calculate_component_amount(self, self.component_type)


def _template_row_to_service_row(template_row, component_type):
	values = {
		"description": template_row.description,
		"item_code": getattr(template_row, "item_code", None),
		"rate": getattr(template_row, "rate", None),
		"cost_rate": getattr(template_row, "cost_rate", None),
		"billable": getattr(template_row, "billable", 1),
	}
	if component_type in STOCK_COMPONENT_TYPES:
		values.update(
			{
				"quantity": getattr(template_row, "quantity", None) or 1,
				"uom": getattr(template_row, "uom", None),
				"warehouse": getattr(template_row, "warehouse", None),
			}
		)
	if component_type == "Consumable":
		values["consumption_basis"] = getattr(template_row, "consumption_basis", None)
	if component_type == "Labour":
		values.update(
			{
				"activity_type": getattr(template_row, "activity_type", None),
				"estimated_hours": getattr(template_row, "estimated_hours", None) or 1,
			}
		)
	if component_type == "Subcontracted Service":
		values.update(
			{
				"supplier": getattr(template_row, "supplier", None),
				"expected_return_date": getattr(template_row, "expected_return_date", None),
			}
		)
	return values


def _component_quantity(row, component_type):
	if component_type == "Labour":
		return getattr(row, "actual_hours", None) or getattr(row, "estimated_hours", None) or 1
	if component_type == "Subcontracted Service":
		return 1
	return getattr(row, "quantity", None) or 0


def calculate_component_amount(row, component_type):
	quantity = _component_quantity(row, component_type)
	gross_amount = quantity * (row.rate or 0)
	row.discount_amount = gross_amount * (row.discount_percentage or 0) / 100
	row.amount = gross_amount - (row.discount_amount or 0)
	row.cost_amount = quantity * (row.cost_rate or 0)
	row.margin_amount = (row.amount or 0) - (row.cost_amount or 0)
	row.margin_percentage = (row.margin_amount / row.amount * 100) if row.amount else 0


def _normalize_service_type(service_type):
	return STATUS_ALIASES.get(service_type, service_type)


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
	component_types=None,
	billable_only=False,
	include_excluded=False,
):
	component_types = {_normalize_service_type(component_type) for component_type in set(component_types or [])}
	for service in get_repair_job_services(repair_job_name):
		if not include_excluded and service.status in {"Rejected", "Deferred", "Cancelled"}:
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
		if service.status not in {"Rejected", "Deferred", "Cancelled"}:
			total += service.total_amount or 0
	frappe.db.set_value("Repair Job", repair_job_name, "total_amount", total, update_modified=False)
