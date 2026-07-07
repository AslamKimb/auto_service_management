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
	"Checked In": ["Walkaround Inspection", "Cancelled"],
	"Walkaround Inspection": ["Diagnosis", "Cancelled"],
	"Diagnosis": ["Estimate Prepared", "Ready for Invoice", "Cancelled"],
	"Estimate Prepared": ["Waiting for Customer Approval", "Approved", "Ready for Invoice", "Cancelled"],
	"Waiting for Customer Approval": ["Approved", "Ready for Invoice", "Cancelled"],
	"Approved": ["In Repair", "Cancelled"],
	"In Repair": ["Quality Check", "Cancelled"],
	"Quality Check": ["In Repair", "Ready for Invoice", "Cancelled"],
	"Ready for Invoice": ["Invoiced", "Cancelled"],
	"Invoiced": ["Gate Pass Issued"],
	"Gate Pass Issued": ["Closed", "Closed - Diagnosis Only"],
	"Closed": [],
	"Closed - Diagnosis Only": [],
	"Cancelled": [],
}


class RepairJob(Document):
	def validate(self):
		self.validate_intake_requirements()
		self.validate_status_transition()
		self.calculate_totals()
		self.set_currency_from_settings()
		self.fetch_vehicle_details()

	def validate_intake_requirements(self):
		if self.odometer_in is None:
			frappe.throw(_("Odometer In (km) is required before creating a Repair Job."))
		if not self.customer_concern or not str(self.customer_concern).strip():
			frappe.throw(_("Reason for visit is required before creating a Repair Job."))

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
		labour_hours = 0
		labour_amount = 0
		for line in self.service_lines or []:
			line.calculate_amount()
			total += line.amount or 0
			if line.service_type == "Labour":
				labour_hours += line.quantity or 0
				labour_amount += line.amount or 0
		self.total_amount = total
		self.labour_total_hours = labour_hours
		self.labour_total_amount = labour_amount

	def get_labour_summary(self):
		"""Return structured labour summary grouped by technician."""
		lines = []
		total_hours = 0
		total_amount = 0
		for line in self.service_lines or []:
			if line.service_type != "Labour":
				continue
			entry = {
				"technician": line.assigned_to,
				"description": line.service_description,
				"hours": line.quantity or 0,
				"amount": line.amount or 0,
			}
			lines.append(entry)
			total_hours += entry["hours"]
			total_amount += entry["amount"]
		return {"lines": lines, "total_hours": total_hours, "total_amount": total_amount}

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
		self._transition_to("Diagnosis")
		self.save()
		self._write_log("start_diagnosis")

	@frappe.whitelist()
	def prepare_estimate(self):
		self._require_write_permission()
		self._transition_to("Estimate Prepared")
		self._normalize_pending_approval_lines()
		self.save()
		self._write_log("estimate_prepared")

	@frappe.whitelist()
	def complete_diagnosis(self):
		self._require_write_permission()
		if self.job_status != "Estimate Prepared":
			self._transition_to("Estimate Prepared")
			self._normalize_pending_approval_lines()
			self.save()
		self._write_log("complete_diagnosis")

	@frappe.whitelist()
	def request_authorization(self):
		self._require_write_permission()
		if self.job_status == "Diagnosis":
			self._transition_to("Estimate Prepared")
			self._normalize_pending_approval_lines()
			self.save()
			self._write_log("estimate_prepared")
		self._transition_to("Waiting for Customer Approval")
		self._normalize_pending_approval_lines()
		self.save()
		self._write_log("request_authorization")

	@frappe.whitelist()
	def authorize(self):
		self._require_write_permission()
		self._approve_remaining_pending_lines()
		if not any(line.status == "Approved" for line in self.service_lines or []):
			frappe.throw(_("At least one service line must be approved before starting repair work."))
		self._transition_to("Approved")
		self.customer_authorized = 1
		self.authorization_date = datetime.now()
		self.authorized_by = frappe.session.user
		self.save()
		self._write_log("authorized")

	@frappe.whitelist()
	def approve_service_lines(self, line_names: list | str | None = None):
		self._require_write_permission()
		names = self._coerce_line_names(line_names)
		self._apply_service_line_status(
			"Approved",
			names,
			{"Pending Approval", "Rejected", "Approved"},
			"service_lines_approved",
		)

	@frappe.whitelist()
	def reject_service_lines(self, line_names: list | str | None = None):
		self._require_write_permission()
		names = self._coerce_line_names(line_names)
		self._apply_service_line_status(
			"Rejected",
			names,
			{"Pending Approval", "Approved", "Rejected"},
			"service_lines_rejected",
		)

	@frappe.whitelist()
	def start_work(self):
		"""Begin repair work. Requires authorization."""
		self._require_write_permission()
		if not self.customer_authorized:
			frappe.throw(_("Customer authorization is required before starting work."))
		if not any(line.status == "Approved" for line in self.service_lines or []):
			frappe.throw(_("At least one approved service line is required before starting work."))
		self._transition_to("In Repair")
		self.save()
		self._write_log("start_work")

	@frappe.whitelist()
	def complete_service_lines(self, line_names: list | str | None = None):
		self._require_write_permission()
		names = self._coerce_line_names(line_names)
		self._apply_service_line_status(
			"Completed",
			names,
			{"Approved", "Completed"},
			"service_lines_completed",
		)

	@frappe.whitelist()
	def hold_for_qc(self):
		self._require_write_permission()
		self._transition_to("Quality Check")
		self.save()
		self._write_log("hold_for_qc")

	@frappe.whitelist()
	def pass_qc(self):
		self._require_write_permission()
		self.quality_check_passed = 1
		self._transition_to("Ready for Invoice")
		self.save()
		self._write_log("pass_qc")

	@frappe.whitelist()
	def mark_ready_for_invoice(self):
		self._require_write_permission()
		if not any(line.status == "Completed" for line in self.service_lines or []):
			frappe.throw(_("At least one completed service line is required before invoicing."))
		self._transition_to("Ready for Invoice")
		self.save()
		self._write_log("ready_for_invoice")

	@frappe.whitelist()
	def release(self):
		self._require_write_permission()
		self._transition_to("Gate Pass Issued")
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
	def close_as_diagnosis_only(self):
		self._require_write_permission()
		if any(line.status in {"Pending Approval", "Approved"} for line in self.service_lines or []):
			frappe.throw(_("Diagnosis-only closure requires all repair recommendations to be rejected, cancelled, or completed."))
		self._transition_to("Closed - Diagnosis Only")
		self.closed_on = datetime.now()
		self.closed_by = frappe.session.user
		self.save()
		self._update_vehicle_after_closure()
		self._create_service_history()
		self._write_log("closed_diagnosis_only")

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
		"""Create Material Request for Parts lines. Blocks duplicate requests."""
		self._require_write_permission()
		# Guard: block if any eligible Parts line already has an active MR
		for line in self.service_lines or []:
			if (
				line.service_type == "Parts"
				and line.item_code
				and line.status in ("Approved", "Completed")
				and line.stock_request_status == "Requested"
			):
				frappe.throw(
					_(
						"Material Request already exists for line '{0}' (status: Requested). "
						"Cancel the existing request before creating a new one."
					).format(line.service_description or line.name)
				)

		from auto_service_management.auto_service_management.integration.erpnext.adapters import (
			create_material_request,
		)

		mr_name = create_material_request(self)
		return mr_name

	@frappe.whitelist()
	def create_stock_entry(self):
		"""Create Stock Entry (Material Issue) for requested Parts lines."""
		self._require_write_permission()
		from auto_service_management.auto_service_management.integration.erpnext.adapters import (
			create_stock_entry_for_material_issue,
		)

		se_name = create_stock_entry_for_material_issue(self)
		self.reload()
		return se_name

	@frappe.whitelist()
	def create_sales_invoice(self):
		"""Create Sales Invoice. Blocks double-billing."""
		self._require_write_permission()
		# Guard: prevent double-billing
		if self.sales_invoice:
			frappe.throw(
				_(
					"Sales Invoice '{0}' already exists for this Repair Job. "
					"Cannot create a duplicate invoice."
				).format(self.sales_invoice)
			)

		from auto_service_management.auto_service_management.integration.erpnext.adapters import (
			create_sales_invoice,
		)

		si_name = create_sales_invoice(self)
		self.reload()
		if self.job_status != "Invoiced":
			self._transition_to("Invoiced")
			self.save()
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
	#  Reporting helpers                                                   #
	# ------------------------------------------------------------------ #

	def get_shortage_report(self):
		"""Return Parts lines where issued_qty < quantity (shortage)."""
		shortages = []
		for line in self.service_lines or []:
			if line.service_type != "Parts":
				continue
			issued = line.issued_qty or 0
			needed = line.quantity or 0
			if needed > 0 and issued < needed:
				shortages.append({
					"line_name": line.name,
					"description": line.service_description,
					"item_code": line.item_code,
					"requested_qty": line.requested_qty or 0,
					"issued_qty": issued,
					"needed_qty": needed,
					"shortage_qty": needed - issued,
				})
		return shortages

	# ------------------------------------------------------------------ #
	#  Internal helpers                                                    #
	# ------------------------------------------------------------------ #

	def _transition_to(self, target_status):
		self.job_status = target_status

	def _coerce_line_names(self, line_names):
		if not line_names:
			return None
		if isinstance(line_names, str):
			line_names = frappe.parse_json(line_names)
		return {str(name) for name in line_names if name}

	def _normalize_pending_approval_lines(self):
		for line in self.service_lines or []:
			if line.status in (None, "", "Pending"):
				line.status = "Pending Approval"

	def _approve_remaining_pending_lines(self):
		for line in self.service_lines or []:
			if line.status == "Pending Approval":
				line.status = "Approved"

	def _apply_service_line_status(self, target_status, line_names, allowed_current_statuses, event_type):
		updated = []
		for line in self.service_lines or []:
			if line_names and line.name not in line_names:
				continue
			if line.status not in allowed_current_statuses:
				continue
			old_status = line.status
			line.status = target_status
			updated.append(f"{line.service_description or line.name}:{old_status}->{target_status}")

		if not updated:
			frappe.throw(_("No eligible service lines were updated."))

		self.save()
		self._write_log(event_type, new_value="\n".join(updated))

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
