# Copyright (c) 2026, Aslam Kimbugwe and contributors
# For license information, please see license.txt

from datetime import date
from decimal import Decimal, InvalidOperation

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, today

from auto_service_management.auto_service_management.doctype.customer_lpo_vehicle.customer_lpo_vehicle import (
	normalize_registration_number,
)


@frappe.whitelist(methods=["GET"])
def preview_vehicle_csv(lpo_name, csv_text=None, file_url=None, rows=None):
	from auto_service_management.auto_service_management.integration.customer_lpo_workflow import (
		preview_vehicle_csv as _preview_vehicle_csv,
	)

	return _preview_vehicle_csv(lpo_name, csv_text=csv_text, file_url=file_url, rows=rows)


@frappe.whitelist(methods=["POST"])
def import_vehicle_csv(lpo_name, csv_text=None, file_url=None, rows=None):
	from auto_service_management.auto_service_management.integration.customer_lpo_workflow import (
		import_vehicle_csv as _import_vehicle_csv,
	)

	return _import_vehicle_csv(lpo_name, csv_text=csv_text, file_url=file_url, rows=rows)


@frappe.whitelist(methods=["POST"])
def resolve_vehicle_rows(lpo_name, row_names=None, create_confirmed=False):
	from auto_service_management.auto_service_management.integration.customer_lpo_workflow import (
		resolve_vehicle_rows as _resolve_vehicle_rows,
	)

	return _resolve_vehicle_rows(lpo_name, row_names=row_names, create_confirmed=create_confirmed)


@frappe.whitelist(methods=["POST"])
def create_campaign_and_repair_jobs(lpo_name):
	from auto_service_management.auto_service_management.integration.customer_lpo_workflow import (
		create_campaign_and_repair_jobs as _create_campaign_and_repair_jobs,
	)

	return _create_campaign_and_repair_jobs(lpo_name)


@frappe.whitelist(methods=["GET"])
def get_lpo_summary(lpo_name):
	from auto_service_management.auto_service_management.integration.customer_lpo_workflow import (
		get_lpo_summary as _get_lpo_summary,
	)

	return _get_lpo_summary(lpo_name)


@frappe.whitelist(methods=["POST"])
def make_sales_order(lpo_name=None, target_doc=None, component_refs=None, source_name=None):
	from auto_service_management.auto_service_management.integration.customer_lpo_workflow import (
		make_sales_order as _make_sales_order,
	)

	return _make_sales_order(lpo_name or source_name, target_doc=target_doc, component_refs=component_refs)


@frappe.whitelist(methods=["POST"])
def make_sales_invoice(lpo_name=None, target_doc=None, component_refs=None, source_name=None):
	from auto_service_management.auto_service_management.integration.customer_lpo_workflow import (
		make_sales_invoice as _make_sales_invoice,
	)

	return _make_sales_invoice(lpo_name or source_name, target_doc=target_doc, component_refs=component_refs)


@frappe.whitelist(methods=["POST"])
def close_lpo(lpo_name):
	from auto_service_management.auto_service_management.integration.customer_lpo_workflow import (
		close_lpo as _close_lpo,
	)

	return _close_lpo(lpo_name)


class CustomerLPO(Document):
	def validate(self):
		self.validate_dates()
		self.validate_unique_lpo_number()
		self.validate_vehicle_rows()
		self.validate_customer_vehicle_ownership()
		self.validate_repair_job_ownership()
		self.validate_campaign_ownership()
		self.validate_row_removals()
		self.validate_allocated_ceilings()
		self.sync_calculated_totals()
		self.status = self.calculate_status()

	def before_submit(self):
		self.validate_submission_requirements()
		if self.get_effective_expiry_date() and self.get_effective_expiry_date() < getdate(today()):
			frappe.throw(_("An expired Customer LPO cannot be submitted."))
		self.status = self.calculate_status(submitted=True)

	def on_cancel(self):
		self.status = "Cancelled"

	def validate_submission_requirements(self):
		missing = [
			field
			for field in (
				"company",
				"customer",
				"lpo_number",
				"issue_date",
				"expiry_date",
				"currency",
				"ceiling_basis",
				"source_lpo",
			)
			if not self.get(field)
		]
		if missing:
			frappe.throw(_("Customer LPO cannot be submitted without: {0}.").format(", ".join(missing)))
		if not self.vehicle_rows:
			frappe.throw(_("At least one vehicle row is required before submitting a Customer LPO."))
		unresolved = [row.registration_number for row in self.vehicle_rows if not row.customer_vehicle]
		if unresolved:
			frappe.throw(
				_("Every vehicle row must resolve to a Customer Vehicle before submission: {0}.").format(
					", ".join(unresolved)
				)
			)
		if _to_decimal(self.authorized_amount) <= 0:
			frappe.throw(_("Authorized Amount must be greater than zero."))

	def validate_dates(self):
		if self.issue_date and self.expiry_date and getdate(self.expiry_date) < getdate(self.issue_date):
			frappe.throw(_("Expiry Date cannot be before Issue Date."))

	def validate_unique_lpo_number(self):
		if not self.company or not self.customer or not self.lpo_number:
			return
		filters = {
			"company": self.company,
			"customer": self.customer,
			"lpo_number": self.lpo_number.strip(),
		}
		if self.name:
			filters["name"] = ["!=", self.name]
		if frappe.db.exists("Customer LPO", filters):
			frappe.throw(
				_("Customer LPO number {0} already exists for this Company and Customer.").format(
					self.lpo_number
				)
			)

	def validate_vehicle_rows(self):
		seen = set()
		for row in self.vehicle_rows or []:
			normalized = normalize_registration_number(row.registration_number)
			if not normalized:
				frappe.throw(_("Every Customer LPO vehicle row requires a registration number."))
			if normalized in seen:
				frappe.throw(
					_("Registration number {0} appears more than once in this Customer LPO.").format(normalized)
				)
			seen.add(normalized)
			row.registration_number = normalized

	def validate_customer_vehicle_ownership(self):
		seen = set()
		for row in self.vehicle_rows or []:
			if not row.customer_vehicle:
				continue
			if row.customer_vehicle in seen:
				frappe.throw(_("Customer Vehicle {0} appears more than once on this Customer LPO.").format(row.customer_vehicle))
			seen.add(row.customer_vehicle)
			vehicle_customer = frappe.db.get_value("Customer Vehicle", row.customer_vehicle, "customer")
			if not vehicle_customer:
				frappe.throw(_("Customer Vehicle {0} does not exist.").format(row.customer_vehicle))
			if vehicle_customer != self.customer:
				frappe.throw(
					_("Customer Vehicle {0} belongs to {1}, not {2}.").format(
						row.customer_vehicle,
						vehicle_customer,
						self.customer,
					)
				)

	def validate_repair_job_ownership(self):
		for row in self.vehicle_rows or []:
			if not row.repair_job:
				continue
			job_customer = frappe.db.get_value("Repair Job", row.repair_job, "customer")
			if not job_customer:
				frappe.throw(_("Repair Job {0} does not exist.").format(row.repair_job))
			if job_customer != self.customer:
				frappe.throw(
					_("Repair Job {0} belongs to {1}, not {2}.").format(
						row.repair_job,
						job_customer,
						self.customer,
					)
				)
			job_vehicle = frappe.db.get_value("Repair Job", row.repair_job, "customer_vehicle")
			if row.customer_vehicle and job_vehicle and job_vehicle != row.customer_vehicle:
				frappe.throw(_("Repair Job {0} does not match Customer Vehicle {1}.").format(row.repair_job, row.customer_vehicle))
			job_lpo = frappe.db.get_value("Repair Job", row.repair_job, "customer_lpo")
			if job_lpo and job_lpo != self.name:
				frappe.throw(_("Repair Job {0} is already linked to Customer LPO {1}.").format(row.repair_job, job_lpo))

	def validate_campaign_ownership(self):
		if not self.fleet_service_campaign:
			return
		campaign_customer = frappe.db.get_value(
			"Fleet Service Campaign", self.fleet_service_campaign, "customer"
		)
		if not campaign_customer:
			frappe.throw(_("Fleet Service Campaign {0} does not exist.").format(self.fleet_service_campaign))
		if campaign_customer != self.customer:
			frappe.throw(
				_("Fleet Service Campaign {0} belongs to {1}, not {2}.").format(
					self.fleet_service_campaign,
					campaign_customer,
					self.customer,
				)
			)

	def validate_allocated_ceilings(self):
		total_allocated = Decimal("0")
		for row in self.vehicle_rows or []:
			allocated = _to_decimal(row.allocated_ceiling)
			if allocated < 0:
				frappe.throw(_("Allocated Ceiling cannot be negative."))
			total_allocated += allocated
		if total_allocated > self.get_effective_authorized_amount():
			frappe.throw(
				_("Vehicle allocations cannot exceed the effective authorized amount of {0}.").format(
					self.get_effective_authorized_amount()
				)
			)

	def validate_row_removals(self):
		old_doc = self.get_doc_before_save()
		if not old_doc:
			return
		current_names = {row.name for row in self.vehicle_rows or [] if row.name}
		for row in old_doc.vehicle_rows or []:
			if row.name and row.name not in current_names and row.repair_job:
				frappe.throw(
					_("Vehicle row {0} cannot be removed while Repair Job {1} is linked. Cancel the job instead.").format(
						row.registration_number, row.repair_job
					)
				)

	def get_effective_authorized_amount(self) -> Decimal:
		total = _to_decimal(self.authorized_amount)
		if not self.name:
			return total
		for amendment in frappe.get_all(
			"Customer LPO Amendment",
			filters={"customer_lpo": self.name, "docstatus": 1},
			fields=["amount_increase"],
		):
			total += _to_decimal(amendment.amount_increase)
		return total

	def get_effective_expiry_date(self) -> date | None:
		effective_expiry = getdate(self.expiry_date) if self.expiry_date else None
		if not effective_expiry or not self.name:
			return effective_expiry
		for amendment in frappe.get_all(
			"Customer LPO Amendment",
			filters={"customer_lpo": self.name, "docstatus": 1},
			fields=["replacement_expiry"],
		):
			replacement = getdate(amendment.replacement_expiry) if amendment.replacement_expiry else None
			if replacement and (not effective_expiry or replacement > effective_expiry):
				effective_expiry = replacement
		return effective_expiry

	def calculate_status(self, as_of=None, submitted=False) -> str:
		if self.docstatus == 2:
			return "Cancelled"
		if self.docstatus != 1 and not submitted:
			return "Draft"
		if self.status == "Completed":
			return "Completed"
		if self.get_effective_expiry_date() and self.get_effective_expiry_date() < getdate(as_of or today()):
			return "Expired"
		if self.get("effective_authorized_amount") and self.get("invoiced_amount") >= self.get("effective_authorized_amount"):
			return "Exhausted"
		if self.get_effective_authorized_amount() <= 0:
			return "Exhausted"
		return "Active"

	def sync_calculated_totals(self):
		if not self.name:
			return
		effective = self.get_effective_authorized_amount()
		invoiced = Decimal("0")
		if frappe.get_meta("Sales Invoice").has_field("customer_lpo"):
			for invoice in frappe.get_all(
				"Sales Invoice",
				filters={"customer_lpo": self.name, "docstatus": 1},
				fields=["net_total", "grand_total", "rounded_total", "disable_rounded_total"],
				limit_page_length=0,
			):
				if self.ceiling_basis == "Tax Exclusive":
					invoiced += _to_decimal(invoice.net_total)
				elif not invoice.disable_rounded_total:
					invoiced += _to_decimal(invoice.rounded_total)
				else:
					invoiced += _to_decimal(invoice.grand_total)
		self.effective_authorized_amount = effective
		self.invoiced_amount = invoiced
		self.remaining_amount = max(effective - invoiced, Decimal("0"))
		self.vehicle_count = len(self.vehicle_rows or [])
		self.completed_vehicle_count = sum(
			1
			for row in self.vehicle_rows or []
			if row.repair_job
			and frappe.db.get_value("Repair Job", row.repair_job, "job_status") in {"Closed", "Cancelled"}
		)


def _to_decimal(value) -> Decimal:
	try:
		return Decimal(str(value or 0))
	except (InvalidOperation, TypeError, ValueError):
		frappe.throw(_("Amount must be a valid number."))
		return Decimal("0")
