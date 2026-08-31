# Copyright (c) 2026, Aslam Kimbugwe and contributors
# For license information, please see license.txt

from __future__ import annotations

from dataclasses import dataclass

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, now_datetime

from auto_service_management.auto_service_management.settings_cache import (
	get_settings as _get_cached_settings,
)


def _get_settings():
	return _get_cached_settings(frappe_module=frappe)


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


def item_maintains_stock(item_code):
	return bool(item_code and cint(frappe.db.get_value("Item", item_code, "is_stock_item")))


@frappe.whitelist(methods=["POST"])
def make_sales_invoice(
	source_name: str,
	target_doc: str | None = None,
	component_refs=None,
):
	service = frappe.get_doc("Repair Job Service", source_name)
	service.check_permission("read")
	from auto_service_management.auto_service_management.integration.erpnext.component_mapping import (
		map_sales_invoice,
	)

	args = getattr(frappe.flags, "args", None) or {}
	return map_sales_invoice(
		service.repair_job,
		target_doc=target_doc,
		service_names={service.name},
		component_refs=component_refs or args.get("component_refs"),
	)


@frappe.whitelist(methods=["POST"])
def make_sales_order(
	source_name: str,
	target_doc: str | None = None,
	component_refs=None,
):
	service = frappe.get_doc("Repair Job Service", source_name)
	service.check_permission("read")
	from auto_service_management.auto_service_management.integration.erpnext.component_mapping import (
		map_sales_order,
	)

	args = getattr(frappe.flags, "args", None) or {}
	return map_sales_order(
		service.repair_job,
		target_doc=target_doc,
		service_names={service.name},
		component_refs=component_refs or args.get("component_refs"),
	)


@frappe.whitelist(methods=["POST"])
def make_material_request(
	source_name: str,
	target_doc: str | None = None,
	component_refs=None,
	material_request_type: str | None = None,
):
	service = frappe.get_doc("Repair Job Service", source_name)
	service.check_permission("read")
	from auto_service_management.auto_service_management.integration.erpnext.component_mapping import (
		map_material_request,
	)

	args = getattr(frappe.flags, "args", None) or {}
	return map_material_request(
		service.repair_job,
		target_doc=target_doc,
		service_names={service.name},
		component_refs=component_refs or args.get("component_refs"),
		material_request_type=material_request_type or args.get("material_request_type"),
	)


@frappe.whitelist(methods=["POST"])
def make_repair_job_service(source_name: str, target_doc: str | None = None, repair_job: str | None = None):
	"""Map an active template to an unsaved Repair Job Service with current prices."""
	template = frappe.get_doc("Repair Job Service Template", source_name)
	template.check_permission("read")
	if not getattr(template, "is_active", 1):
		frappe.throw(_("Only active Repair Job Service Templates can be applied."))
	frappe.has_permission("Repair Job Service", "create", throw=True)
	service = _coerce_target_doc(target_doc, "Repair Job Service")
	repair_job = repair_job or service.repair_job
	if repair_job:
		job = frappe.get_doc("Repair Job", repair_job)
		job.check_permission("read")
		vehicle = frappe.db.get_value(
			"Customer Vehicle", getattr(job, "customer_vehicle", None), ["make", "model"], as_dict=True
		)
		if not _template_is_compatible(
			template, getattr(vehicle, "make", None), getattr(vehicle, "model", None)
		):
			frappe.throw(_("This service template is not compatible with the Repair Job vehicle."))
		service.repair_job = job.name
		service.customer = getattr(job, "customer", None)
		service.customer_vehicle = getattr(job, "customer_vehicle", None)
		service.diagnosis_report = getattr(job, "diagnosis_report", None)
		service.currency = getattr(job, "currency", None)
	else:
		service.repair_job = None
	service.repair_job_service_template = template.name
	service.service_name = template.service_name
	service.description = template.description
	service.billable = template.default_billable
	for definition in COMPONENT_TABLES:
		for source_row in template.get(definition["template_fieldname"]) or []:
			row = service.append(definition["fieldname"], {})
			_copy_template_component_row(row, source_row)
			_snapshot_current_component_values(row, definition["component_type"])
	return service


@frappe.whitelist(methods=["POST"])
def make_repair_job_service_template(source_name: str, target_doc: str | None = None):
	"""Map a service's reusable definition to an unsaved current-model template."""
	service = frappe.get_doc("Repair Job Service", source_name)
	service.check_permission("read")
	frappe.has_permission("Repair Job Service Template", "create", throw=True)
	template = _coerce_target_doc(target_doc, "Repair Job Service Template")
	template.template_name = template.template_name or service.service_name
	template.service_name = service.service_name
	template.description = service.description
	template.default_billable = service.billable
	vehicle_name = getattr(service, "customer_vehicle", None)
	if not vehicle_name and getattr(service, "repair_job", None):
		vehicle_name = frappe.db.get_value("Repair Job", service.repair_job, "customer_vehicle")
	if vehicle_name:
		vehicle = frappe.db.get_value("Customer Vehicle", vehicle_name, ["make", "model"], as_dict=True)
		template.vehicle_make = getattr(vehicle, "make", None)
		template.vehicle_model = getattr(vehicle, "model", None)
	for definition in COMPONENT_TABLES:
		for source_row in service.get(definition["fieldname"]) or []:
			row = template.append(definition["template_fieldname"], {})
			_copy_template_component_row(row, source_row)
	return template


@frappe.whitelist(methods=["GET"])
def get_compatible_repair_job_service_templates(repair_job: str):
	"""Return active global/make/model templates compatible with a Repair Job vehicle."""
	job = frappe.get_doc("Repair Job", repair_job)
	job.check_permission("read")
	frappe.has_permission("Repair Job Service Template", "read", throw=True)
	vehicle = (
		frappe.db.get_value("Customer Vehicle", job.customer_vehicle, ["make", "model"], as_dict=True)
		or frappe._dict()
	)
	templates = frappe.get_list(
		"Repair Job Service Template",
		filters={"is_active": 1},
		fields=["name", "template_name", "service_name", "vehicle_make", "vehicle_model"],
		order_by="template_name asc",
	)
	compatible = [
		template for template in templates if _template_is_compatible(template, vehicle.make, vehicle.model)
	]
	return sorted(
		compatible,
		key=lambda template: (
			0
			if template.vehicle_model == vehicle.model and vehicle.model
			else 1
			if template.vehicle_make
			else 2,
			template.template_name or template.service_name or template.name,
		),
	)


def _coerce_target_doc(target_doc, doctype):
	if not target_doc:
		return frappe.new_doc(doctype)
	if isinstance(target_doc, str):
		target_doc = frappe.parse_json(target_doc)
	if isinstance(target_doc, Document):
		return target_doc
	return frappe.get_doc(target_doc)


def _template_is_compatible(template, vehicle_make, vehicle_model):
	template_make = getattr(template, "vehicle_make", None)
	template_model = getattr(template, "vehicle_model", None)
	if template_make and template_make != vehicle_make:
		return False
	if template_model and template_model != vehicle_model:
		return False
	return True


def _snapshot_current_component_values(row, component_type):
	"""Keep templates price-free; a new service captures today's price/defaults."""
	settings = _get_settings()
	if component_type == "Labour":
		row.item_code = row.item_code or settings.default_labour_item
		row.hours = row.estimated_hours or 1
		row.billing_hours = row.hours if row.billable else 0
		if row.billable:
			from auto_service_management.auto_service_management.integration.erpnext.adapters import (
				get_item_price,
			)

			row.billing_rate = get_item_price(row.item_code) if row.item_code else 0
			row.billing_rate = row.billing_rate or settings.default_labour_rate or 0
		return
	if row.item_code:
		from auto_service_management.auto_service_management.integration.erpnext.adapters import (
			get_item_price,
		)

		row.rate = get_item_price(row.item_code)
		row.uom = row.uom or frappe.db.get_value("Item", row.item_code, "stock_uom")
	row.warehouse = row.warehouse or settings.default_warehouse


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
	@frappe.whitelist(methods=["POST"])
	def create_sales_order(self, component_refs=None):
		self.check_permission("write")
		from auto_service_management.auto_service_management.integration.erpnext.adapters import (
			create_sales_order,
		)

		return create_sales_order(
			frappe.get_doc("Repair Job", self.repair_job),
			service_names={self.name},
			component_refs=component_refs,
		)

	def materialize_template_components(self):
		"""Legacy compatibility no-op; new flows use explicit unsaved mappers."""
		return False

	def before_validate(self):
		self.sync_from_repair_job()
		self.sync_component_context()

	def validate(self):
		if not self.repair_job:
			frappe.throw(_("Repair Job is required before saving a Repair Job Service."))
		if not self.workshop_bay:
			frappe.throw(_("Workshop Bay is required for a Repair Job Service."))
		self.validate_diagnosis_report()
		self.validate_completion_change()
		self.calculate_totals()
		from auto_service_management.auto_service_management.workflow_compatibility import (
			sync_repair_job_service_summary,
		)

		sync_repair_job_service_summary(self)

	def validate_completion_change(self):
		was_completed = bool(self.get_db_value("is_completed")) if not self.is_new() else False
		if bool(self.is_completed) == was_completed:
			return
		roles = set(frappe.get_roles())
		if not roles.intersection({"Workshop Technician", "Workshop Manager"}):
			frappe.throw(_("Only a Workshop Technician or Workshop Manager can change service completion."))
		if self.is_completed:
			self.completed_on = now_datetime()
			self.completed_by = frappe.session.user
		else:
			if "Workshop Manager" not in roles:
				frappe.throw(_("Only a Workshop Manager can reopen a completed service."))
			self.completed_on = None
			self.completed_by = None

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
		frappe.publish_realtime("repair_job_services_updated", {"repair_job": self.repair_job})

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
				if not getattr(row, "item_code", None):
					settings = _get_settings()
					if settings.default_labour_item:
						row.item_code = settings.default_labour_item
				if row.billable:
					if not getattr(row, "billing_hours", None):
						row.billing_hours = getattr(row, "hours", None) or 0
				else:
					row.billing_hours = 0
				if row.billable and not getattr(row, "billing_rate", None):
					settings = _get_settings()
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
		_validate_component_item(self.component_type, self.item_code)
		calculate_component_amount(self, self.component_type)


def _validate_component_item(component_type, item_code):
	if component_type == "Labour":
		_validate_labour_item(item_code)
		return

	if component_type not in STOCK_COMPONENT_TYPES:
		return
	label = "Part" if component_type == "Part" else "Consumable"
	if not item_code:
		frappe.throw(_("A {0} Item is required for every {0} component.").format(label))
	item = frappe.db.get_value(
		"Item",
		item_code,
		["disabled", "is_stock_item"],
		as_dict=True,
	)
	if not item:
		frappe.throw(_("{0} Item {1} does not exist.").format(label, item_code))
	if not item.is_stock_item:
		frappe.throw(
			_("{0} Item {1} must have Maintain Stock enabled.").format(label, item_code)
		)


def _validate_labour_item(item_code):
	if not item_code:
		frappe.throw(_("A Labour Service Item is required for every Labour component."))

	item = frappe.db.get_value(
		"Item",
		item_code,
		["disabled", "is_stock_item", "is_sales_item", "stock_uom"],
		as_dict=True,
	)
	if not item:
		frappe.throw(_("Labour Service Item {0} does not exist.").format(item_code))
	if item.disabled or item.is_stock_item or not item.is_sales_item or item.stock_uom != "Hour":
		frappe.throw(
			_(
				"Labour Service Item {0} must be an enabled, non-stock sales Item with Hour as its UOM."
			).format(item_code)
		)


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


def _copy_template_component_row(target_row, source_row):
	"""Copy reusable scope only; prices and operational traces never enter templates."""
	for fieldname in ("description", "item_code", "billable"):
		value = getattr(source_row, fieldname, None)
		if value is not None:
			setattr(target_row, fieldname, value)
	if "Labour" in target_row.doctype:
		target_row.activity_type = getattr(source_row, "activity_type", None)
		target_row.estimated_hours = (
			getattr(source_row, "estimated_hours", None) or getattr(source_row, "hours", None) or 1
		)
		return
	target_row.quantity = getattr(source_row, "quantity", None) or 1
	target_row.uom = getattr(source_row, "uom", None)
	if "Part" in target_row.doctype:
		target_row.required_by = getattr(source_row, "required_by", None)
	if "Consumable" in target_row.doctype:
		target_row.consumption_basis = getattr(source_row, "consumption_basis", None)


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
			"sales_order",
			"sales_order_item",
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
	stock_only=False,
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
		if service_statuses is not None and not _status_filter_allows(service, service_statuses):
			continue
		for component in get_service_components(service, component_types=component_types):
			if stock_only and not item_maintains_stock(component.item_code):
				continue
			if billable_only and not component.billable:
				continue
			yield service, component


def set_component_values(component, values, update_modified=False):
	row = component.row if isinstance(component, ServiceComponent) else component
	frappe.db.set_value(row.doctype, row.name, values, update_modified=update_modified)


def _status_filter_allows(service, service_statuses):
	meta = getattr(service, "meta", None)
	if meta and not meta.has_field("status"):
		return True
	return getattr(service, "status", None) in service_statuses


def sync_repair_job_total(repair_job_name):
	if not repair_job_name or not frappe.db.exists("Repair Job", repair_job_name):
		return
	total = 0
	for service in get_repair_job_services(repair_job_name):
		if getattr(service, "docstatus", 0) != 2:
			total += service.total_amount or 0
	frappe.db.set_value("Repair Job", repair_job_name, "total_amount", total, update_modified=False)
