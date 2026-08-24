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


class CustomerLPO(Document):
	def validate(self):
		self.validate_dates()
		self.validate_unique_lpo_number()
		self.validate_vehicle_rows()
		self.validate_customer_vehicle_ownership()
		self.validate_repair_job_ownership()
		self.validate_campaign_ownership()
		self.validate_allocated_ceilings()
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
		for row in self.vehicle_rows or []:
			if not row.customer_vehicle:
				continue
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
		if self.get_effective_expiry_date() and self.get_effective_expiry_date() < getdate(as_of or today()):
			return "Expired"
		if self.get_effective_authorized_amount() <= 0:
			return "Exhausted"
		return "Active"


def _to_decimal(value) -> Decimal:
	try:
		return Decimal(str(value or 0))
	except (InvalidOperation, TypeError, ValueError):
		frappe.throw(_("Amount must be a valid number."))
		return Decimal("0")
