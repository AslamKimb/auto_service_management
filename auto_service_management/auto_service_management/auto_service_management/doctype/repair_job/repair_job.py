# Copyright (c) 2026, Aslam Kimbugwe and contributors
# For license information, please see license.txt

from datetime import datetime

import frappe
from frappe import _
from frappe.model.document import Document

# ---------------------------------------------------------------------------
# State machine — spec-aligned workflow
# ---------------------------------------------------------------------------
VALID_TRANSITIONS = {
	"Draft": ["Checked In", "Cancelled"],
	"Checked In": ["Under Diagnosis", "Cancelled"],
	"Under Diagnosis": ["Diagnosed", "Cancelled"],
	"Diagnosed": ["Awaiting Authorization", "Cancelled"],
	"Awaiting Authorization": ["Authorized", "Cancelled"],
	"Authorized": ["In Progress", "Cancelled"],
	"In Progress": ["QC Hold", "Cancelled"],
	"QC Hold": ["In Progress", "Ready for Release", "Cancelled"],
	"Ready for Release": ["Released", "Cancelled"],
	"Released": ["Closed"],
	"Closed": [],
	"Cancelled": [],
}


class RepairJob(Document):
	def validate(self):
		self.validate_status_transition()
		self.calculate_totals()
		self.set_currency_from_settings()
		self.fetch_vehicle_details()

	def before_save(self):
		if self.is_new():
			return
		if self.has_value_changed("job_status"):
			self.log_state_change()

	# ------------------------------------------------------------------ #
	#  Status workflow                                                     #
	# ------------------------------------------------------------------ #

	def validate_status_transition(self):
		"""Enforce server-side state machine."""
		if self.is_new():
			if not self.job_status:
				self.job_status = "Draft"
			return
		if not self.has_value_changed("job_status"):
			return
		old = self.get_doc_before_save()
		old_status = old.job_status if old else "Draft"
		allowed = VALID_TRANSITIONS.get(old_status, [])
		if self.job_status not in allowed:
			frappe.throw(_("Transition from {0} to {1} is not allowed.").format(old_status, self.job_status))

	def log_state_change(self):
		old = self.get_doc_before_save()
		old_status = old.job_status if old else "Draft"
		self._write_log("status_change", old_status, self.job_status)

	# ------------------------------------------------------------------ #
	#  Financials                                                         #
	# ------------------------------------------------------------------ #

	def calculate_totals(self):
		total = 0
		for line in self.service_lines or []:
			if line.service_type != "Parts":
				line.calculate_amount()
			total += line.amount or 0
		self.total_amount = total

	def set_currency_from_settings(self):
		if not self.currency:
			settings = frappe.get_single("Auto Service Settings")
			if settings and settings.default_currency:
				self.currency = settings.default_currency

	# ------------------------------------------------------------------ #
	#  Vehicle                                                            #
	# ------------------------------------------------------------------ #

	def fetch_vehicle_details(self):
		if self.customer_vehicle and not self.registration_number:
			vehicle = frappe.get_doc("Customer Vehicle", self.customer_vehicle)
			self.registration_number = vehicle.registration_number
			parts = [
				vehicle.make or "",
				vehicle.model or "",
				str(vehicle.year_of_manufacture or ""),
			]
			self.vehicle_details = " ".join(parts).strip()

	# ------------------------------------------------------------------ #
	#  Actions — whitelisted workflow methods                              #
	# ------------------------------------------------------------------ #

	def _require_write_permission(self):
		self.check_permission("write")

	@frappe.whitelist()
	def check_in(self):
		"""Check in the vehicle. Creates the ERPNext Project on first check-in."""
		self._require_write_permission()
		self._transition_to("Checked In")
		self.save()
		# Create Project idempotently
		self._ensure_project()
		self._write_log("check_in")

	@frappe.whitelist()
	def start_diagnosis(self):
		self._require_write_permission()
		self._transition_to("Under Diagnosis")
		self.save()
		self._write_log("start_diagnosis")

	@frappe.whitelist()
	def complete_diagnosis(self):
		self._require_write_permission()
		self._transition_to("Diagnosed")
		self.save()
		self._write_log("complete_diagnosis")

	@frappe.whitelist()
	def request_authorization(self):
		self._require_write_permission()
		self._transition_to("Awaiting Authorization")
		self.save()
		self._write_log("request_authorization")

	@frappe.whitelist()
	def authorize(self):
		self._require_write_permission()
		self._transition_to("Authorized")
		self.customer_authorized = 1
		self.authorization_date = datetime.now()
		self.authorized_by = frappe.session.user
		self.save()
		self._write_log("authorized")

	@frappe.whitelist()
	def start_work(self):
		"""Begin repair work. Requires authorization."""
		self._require_write_permission()
		if not self.customer_authorized:
			frappe.throw(_("Customer authorization is required before starting work."))
		self._transition_to("In Progress")
		self.save()
		self._write_log("start_work")

	@frappe.whitelist()
	def hold_for_qc(self):
		self._require_write_permission()
		self._transition_to("QC Hold")
		self.save()
		self._write_log("hold_for_qc")

	@frappe.whitelist()
	def pass_qc(self):
		self._require_write_permission()
		self.quality_check_passed = 1
		self._transition_to("Ready for Release")
		self.save()
		self._write_log("pass_qc")

	@frappe.whitelist()
	def release(self):
		self._require_write_permission()
		self._transition_to("Released")
		self.save()
		self._write_log("released")

	@frappe.whitelist()
	def close(self):
		"""Close the job. Creates Service History and updates vehicle."""
		self._require_write_permission()
		self._transition_to("Closed")
		self.closed_on = datetime.now()
		self.closed_by = frappe.session.user
		self.save()
		self._update_vehicle_after_closure()
		self._create_service_history()
		self._write_log("closed")

	@frappe.whitelist()
	def cancel(self):
		self._require_write_permission()
		self._transition_to("Cancelled")
		self.save()
		self._write_log("cancelled")

	# ------------------------------------------------------------------ #
	#  ERPNext integration triggers                                        #
	# ------------------------------------------------------------------ #

	@frappe.whitelist()
	def create_quotation(self):
		"""Generate a Quotation from approved service lines."""
		self._require_write_permission()
		from auto_service_management.auto_service_management.integration.erpnext.adapters import (
			create_quotation,
		)

		quote_name = create_quotation(self)
		self.reload()
		return quote_name

	@frappe.whitelist()
	def create_sales_order(self):
		self._require_write_permission()
		from auto_service_management.auto_service_management.integration.erpnext.adapters import (
			create_sales_order,
		)

		so_name = create_sales_order(self)
		self.reload()
		return so_name

	@frappe.whitelist()
	def create_material_request(self):
		self._require_write_permission()
		from auto_service_management.auto_service_management.integration.erpnext.adapters import (
			create_material_request,
		)

		mr_name = create_material_request(self)
		return mr_name

	@frappe.whitelist()
	def create_sales_invoice(self):
		self._require_write_permission()
		from auto_service_management.auto_service_management.integration.erpnext.adapters import (
			create_sales_invoice,
		)

		si_name = create_sales_invoice(self)
		self.reload()
		return si_name

	@frappe.whitelist()
	def create_gate_pass(self):
		"""Issue a Gate Pass for this Repair Job."""
		self._require_write_permission()
		if not self.sales_invoice:
			frappe.throw(_("Create a Sales Invoice before issuing a Gate Pass."))
		gp = frappe.get_doc(
			{
				"doctype": "Gate Pass",
				"repair_job": self.name,
				"customer_vehicle": self.customer_vehicle,
				"sales_invoice": self.sales_invoice,
				"recipient_name": frappe.db.get_value("Customer", self.customer, "customer_name") or "",
			}
		)
		gp.insert(ignore_permissions=True)
		self.reload()
		return gp.name

	# ------------------------------------------------------------------ #
	#  Internal helpers                                                    #
	# ------------------------------------------------------------------ #

	def _transition_to(self, target_status):
		self.job_status = target_status

	def _ensure_project(self):
		"""Create the ERPNext Project if one does not yet exist."""
		if self.project:
			return
		from auto_service_management.auto_service_management.integration.erpnext.adapters import (
			create_project_for_repair_job,
		)

		create_project_for_repair_job(self)
		self.reload()

	def _write_log(self, event_type, old_value=None, new_value=None):
		"""Create an immutable Repair Job Log entry."""
		frappe.get_doc(
			{
				"doctype": "Repair Job Log",
				"repair_job": self.name,
				"event_type": event_type,
				"performed_by": frappe.session.user,
				"event_timestamp": datetime.now(),
				"old_value": str(old_value) if old_value else None,
				"new_value": str(new_value) if new_value else None,
			}
		).insert(ignore_permissions=True)

	def _update_vehicle_after_closure(self):
		"""Update Customer Vehicle odometer and last service date on closure."""
		if self.customer_vehicle:
			update_fields = {"last_service_date": frappe.utils.today()}
			if self.odometer_out:
				update_fields["current_odometer"] = self.odometer_out
			frappe.db.set_value("Customer Vehicle", self.customer_vehicle, update_fields)

	def _create_service_history(self):
		"""Create an idempotent Service History snapshot."""
		existing = frappe.db.exists("Service History", {"repair_job": self.name})
		if existing:
			return

		services = []
		parts = []
		for line in self.service_lines or []:
			if line.service_type == "Labour":
				services.append(line.service_description or "")
			elif line.service_type == "Parts":
				parts.append(line.service_description or "")

		frappe.get_doc(
			{
				"doctype": "Service History",
				"repair_job": self.name,
				"customer_vehicle": self.customer_vehicle,
				"closure_date": frappe.utils.today(),
				"closed_by": frappe.session.user,
				"total_amount": self.total_amount,
				"currency": self.currency,
				"odometer_at_closure": self.odometer_out,
				"services_performed": "\n".join(services),
				"parts_replaced": "\n".join(parts),
			}
		).insert(ignore_permissions=True)
