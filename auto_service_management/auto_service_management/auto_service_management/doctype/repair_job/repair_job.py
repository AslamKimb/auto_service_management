# Copyright (c) 2026, Aslam Kimbugwe and contributors
# For license information, please see license.txt

from datetime import datetime

import frappe
from auto_service_management.auto_service_management.doctype.repair_job_service.repair_job_service import (
	EXCLUDED_SERVICE_STATUSES,
	STOCK_COMPONENT_TYPES,
	component_has_downstream,
	get_repair_job_services,
	get_service_components,
	iter_repair_job_components,
)
from frappe import _
from frappe.model.document import Document

# ---------------------------------------------------------------------------
# State machine - spec-aligned workflow
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
	"Invoiced": ["Ready for Invoice", "Gate Pass Issued"],
	"Gate Pass Issued": ["Closed", "Closed - Diagnosis Only"],
	"Closed": [],
	"Closed - Diagnosis Only": [],
	"Cancelled": [],
}


@frappe.whitelist(methods=["POST"])
def make_sales_invoice(source_name: str, target_doc: str | None = None):
	from auto_service_management.auto_service_management.integration.erpnext.component_mapping import (
		map_sales_invoice,
	)

	return map_sales_invoice(source_name, target_doc=target_doc)


@frappe.whitelist(methods=["POST"])
def make_material_request(source_name: str, target_doc: str | None = None):
	from auto_service_management.auto_service_management.integration.erpnext.component_mapping import (
		map_material_request,
	)

	return map_material_request(source_name, target_doc=target_doc)


class RepairJob(Document):
	def before_validate(self):
		self.sync_customer_and_vehicle()
		self.resolve_primary_related_documents()

	def validate(self):
		self.validate_intake_requirements()
		self.validate_primary_related_documents()
		self.validate_status_transition()
		self.calculate_totals()
		self.set_currency_from_settings()
		self.fetch_vehicle_details()

	def validate_intake_requirements(self):
		if self.odometer_in is None:
			frappe.throw(_("Odometer In (km) is required before creating a Repair Job."))
		if not self.customer_concern or not str(self.customer_concern).strip():
			frappe.throw(_("Reason for visit is required before creating a Repair Job."))
		if not self.customer_vehicle:
			frappe.throw(_("Customer Vehicle is required before creating a Repair Job."))
		if not self.customer:
			frappe.throw(_("Customer is required before creating a Repair Job."))

	def sync_customer_and_vehicle(self):
		if not self.customer_vehicle:
			return
		vehicle_customer = frappe.db.get_value("Customer Vehicle", self.customer_vehicle, "customer")
		if not vehicle_customer:
			return
		if not self.customer:
			self.customer = vehicle_customer
		elif self.customer != vehicle_customer:
			frappe.throw(
				_("Selected Customer Vehicle does not belong to customer {0}.").format(self.customer)
			)

	def resolve_primary_related_documents(self):
		if self.is_new():
			return
		for fieldname, doctype in (
			("walkaround_inspection", "Walkaround Inspection"),
			("diagnosis_report", "Diagnosis Report"),
			("customer_authorization", "Customer Authorization"),
			("quality_check", "Quality Check"),
			("road_test_report", "Road Test Report"),
			("gate_pass", "Gate Pass"),
		):
			if getattr(self, fieldname, None):
				continue
			linked_name = frappe.db.get_value(doctype, {"repair_job": self.name}, "name")
			if linked_name:
				setattr(self, fieldname, linked_name)

	def validate_primary_related_documents(self):
		for fieldname, doctype, matching_field in (
			("walkaround_inspection", "Walkaround Inspection", "customer_vehicle"),
			("diagnosis_report", "Diagnosis Report", "customer_vehicle"),
			("customer_authorization", "Customer Authorization", "customer"),
			("quality_check", "Quality Check", "customer_vehicle"),
			("road_test_report", "Road Test Report", "customer_vehicle"),
			("gate_pass", "Gate Pass", "customer_vehicle"),
		):
			linked_name = getattr(self, fieldname, None)
			if not linked_name:
				continue
			linked_row = frappe.db.get_value(
				doctype, linked_name, ["repair_job", matching_field], as_dict=True
			)
			if not linked_row:
				frappe.throw(_("{0} {1} does not exist.").format(doctype, linked_name))
			if linked_row.repair_job and not self.is_new() and linked_row.repair_job != self.name:
				frappe.throw(_("{0} {1} is linked to a different Repair Job.").format(doctype, linked_name))
			expected_value = getattr(self, matching_field, None)
			if (
				expected_value
				and linked_row.get(matching_field)
				and linked_row.get(matching_field) != expected_value
			):
				frappe.throw(
					_("{0} {1} does not match this Repair Job's {2}.").format(
						doctype, linked_name, frappe.unscrub(matching_field)
					)
				)

	def before_save(self):
		if self.is_new():
			return
		if self.has_value_changed("job_status"):
			self.log_state_change()

	# ------------------------------------------------------------------ #
	#  Status workflow                                                    #
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
	#  Financials                                                        #
	# ------------------------------------------------------------------ #

	def calculate_totals(self):
		total = 0
		if not self.is_new():
			for service in self._get_services():
				if service.status not in EXCLUDED_SERVICE_STATUSES:
					total += service.total_amount or 0
		self.total_amount = total

	def get_labour_summary(self):
		"""Return structured labour summary grouped by technician."""
		lines = []
		total_hours = 0
		total_amount = 0
		for service, line in self._get_service_components(component_types={"Labour"}):
			entry = {
				"technician": line.assigned_to,
				"service": service.service_name,
				"description": line.service_description,
				"hours": line.hours or 0,
				"amount": line.billing_amount or 0,
			}
			lines.append(entry)
			total_hours += entry["hours"]
			total_amount += entry["amount"]
		return {"lines": lines, "total_hours": total_hours, "total_amount": total_amount}

	def get_service_groups(self, service_statuses=None):
		"""Return service/component rows for print formats and summaries."""
		statuses = set(service_statuses or [])
		groups = []
		for service in self._get_services():
			if statuses and service.status not in statuses:
				continue
			groups.append(
				{
					"name": service.name,
					"service_name": service.service_name,
					"status": service.status,
					"total_amount": service.total_amount,
					"components": list(get_service_components(service)),
				}
			)
		return groups

	def set_currency_from_settings(self):
		if not self.currency:
			settings = frappe.get_single("Auto Service Settings")
			if settings and settings.default_currency:
				self.currency = settings.default_currency

	# ------------------------------------------------------------------ #
	#  Vehicle                                                           #
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
	#  Actions - whitelisted workflow methods                            #
	# ------------------------------------------------------------------ #

	def _require_write_permission(self):
		self.check_permission("write")

	@frappe.whitelist()
	def check_in(self):
		"""Check in the vehicle. Creates the ERPNext Project on first check-in."""
		self._require_write_permission()
		self._transition_to("Checked In")
		self.save()
		self._ensure_project()
		self._write_log("check_in")

	@frappe.whitelist()
	def start_diagnosis(self):
		self._require_write_permission()
		self._require_primary_document("walkaround_inspection", "Walkaround Inspection")
		self._transition_to("Diagnosis")
		self.save()
		self._write_log("start_diagnosis")

	@frappe.whitelist()
	def prepare_estimate(self):
		self._require_write_permission()
		self._require_primary_document("diagnosis_report", "Diagnosis Report")
		self._transition_to("Estimate Prepared")
		self._normalize_pending_services()
		self.save()
		self._write_log("estimate_prepared")

	@frappe.whitelist()
	def complete_diagnosis(self):
		self._require_write_permission()
		self._require_primary_document("diagnosis_report", "Diagnosis Report")
		if self.job_status != "Estimate Prepared":
			self._transition_to("Estimate Prepared")
			self._normalize_pending_services()
			self.save()
		self._write_log("complete_diagnosis")

	@frappe.whitelist()
	def request_authorization(self):
		self._require_write_permission()
		self._require_primary_document("diagnosis_report", "Diagnosis Report")
		if self.job_status == "Diagnosis":
			self._transition_to("Estimate Prepared")
			self._normalize_pending_services()
			self.save()
			self._write_log("estimate_prepared")
		self._transition_to("Waiting for Customer Approval")
		self._normalize_pending_services()
		self.save()
		self._write_log("request_authorization")

	@frappe.whitelist()
	def authorize(self):
		self._require_write_permission()
		self._require_approved_authorization()
		self._approve_remaining_pending_services()
		if not self._has_service_status({"Approved", "Completed"}):
			frappe.throw(_("At least one Repair Job Service must be approved before starting repair work."))
		self._transition_to("Approved")
		self.save()
		self._write_log("authorized")

	@frappe.whitelist(methods=["POST"])
	def approve_service_lines(self, line_names: list | str | None = None):
		self._require_write_permission()
		names = self._coerce_line_names(line_names)
		self._apply_service_status(
			"Approved",
			names,
			{"Pending Approval", "Rejected", "Deferred", "Approved"},
			"service_lines_approved",
		)

	@frappe.whitelist(methods=["POST"])
	def reject_service_lines(self, line_names: list | str | None = None):
		self._require_write_permission()
		names = self._coerce_line_names(line_names)
		self._apply_service_status(
			"Rejected",
			names,
			{"Pending Approval", "Approved", "Rejected", "Deferred"},
			"service_lines_rejected",
		)

	@frappe.whitelist(methods=["POST"])
	def defer_service_lines(self, line_names: list | str | None = None):
		self._require_write_permission()
		names = self._coerce_line_names(line_names)
		self._apply_service_status(
			"Deferred",
			names,
			{"Pending Approval", "Approved", "Deferred"},
			"service_lines_deferred",
		)

	@frappe.whitelist()
	def start_work(self):
		"""Begin repair work. Requires authorization."""
		self._require_write_permission()
		self._require_approved_authorization()
		if not self._has_service_status({"Approved", "Completed"}):
			frappe.throw(_("At least one approved Repair Job Service is required before starting work."))
		self._transition_to("In Repair")
		self.save()
		self._write_log("start_work")

	@frappe.whitelist(methods=["POST"])
	def complete_service_lines(self, line_names: list | str | None = None):
		self._require_write_permission()
		names = self._coerce_line_names(line_names)
		self._apply_service_status(
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
		self._require_passed_quality_check()
		self._require_passed_road_test_if_needed()
		self._transition_to("Ready for Invoice")
		self.save()
		self._sync_invoice_state()
		self._write_log("pass_qc")

	@frappe.whitelist()
	def mark_ready_for_invoice(self):
		self._require_write_permission()
		if not self._has_service_status({"Completed"}):
			frappe.throw(_("At least one completed Repair Job Service is required before invoicing."))
		self._transition_to("Ready for Invoice")
		self.save()
		self._sync_invoice_state()
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
		self._require_issued_gate_pass()
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
		self._require_issued_gate_pass()
		if self._has_service_status({"Pending Approval", "Approved", "In Progress"}):
			frappe.throw(
				_(
					"Diagnosis-only closure requires all repair recommendations to be rejected, deferred, cancelled, or completed."
				)
			)
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

	@frappe.whitelist()
	def create_service(self, service_name=None, repair_service_template=None):
		self._require_write_permission()
		service = frappe.get_doc(
			{
				"doctype": "Repair Job Service",
				"repair_job": self.name,
				"customer": self.customer,
				"customer_vehicle": self.customer_vehicle,
				"diagnosis_report": self.diagnosis_report,
				"repair_service_template": repair_service_template,
				"service_name": service_name or _("New Repair Service"),
				"currency": self.currency,
			}
		)
		service.insert(ignore_permissions=True)
		self.reload()
		return service.name

	# ------------------------------------------------------------------ #
	#  ERPNext integration triggers                                      #
	# ------------------------------------------------------------------ #

	@frappe.whitelist()
	def create_quotation(self):
		"""Generate a Quotation from approved service components."""
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

	@frappe.whitelist(methods=["POST"])
	def create_material_request(self):
		"""Create and save a draft Material Request for compatibility callers."""
		self._require_write_permission()

		from auto_service_management.auto_service_management.integration.erpnext.adapters import (
			create_material_request,
		)

		return create_material_request(self)

	@frappe.whitelist()
	def create_stock_entry(self):
		"""Create Stock Entry (Material Issue) for requested stock components."""
		self._require_write_permission()
		from auto_service_management.auto_service_management.integration.erpnext.adapters import (
			create_stock_entry_for_material_issue,
		)

		se_name = create_stock_entry_for_material_issue(self)
		self.reload()
		return se_name

	@frappe.whitelist(methods=["POST"])
	def create_sales_invoice(self):
		"""Create and save a draft Sales Invoice for compatibility callers."""
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
		from auto_service_management.auto_service_management.integration.erpnext.document_sync import (
			validate_job_invoices_for_gate_pass,
		)

		invoices = validate_job_invoices_for_gate_pass(self.name)
		primary_invoice = self.sales_invoice if self.sales_invoice in invoices else invoices[0]
		gp = frappe.get_doc(
			{
				"doctype": "Gate Pass",
				"repair_job": self.name,
				"customer_vehicle": self.customer_vehicle,
				"sales_invoice": primary_invoice,
				"recipient_name": frappe.db.get_value("Customer", self.customer, "customer_name") or "",
			}
		)
		gp.insert(ignore_permissions=True)
		self.reload()
		return gp.name

	# ------------------------------------------------------------------ #
	#  Reporting helpers                                                 #
	# ------------------------------------------------------------------ #

	def get_shortage_report(self):
		"""Return stock components where issued_qty < quantity."""
		shortages = []
		for service, line in self._get_service_components(component_types=STOCK_COMPONENT_TYPES):
			issued = line.issued_qty or 0
			needed = line.quantity or 0
			if needed > 0 and issued < needed:
				shortages.append(
					{
						"line_name": line.name,
						"service": service.service_name,
						"description": line.service_description,
						"item_code": line.item_code,
						"requested_qty": line.requested_qty or 0,
						"issued_qty": issued,
						"needed_qty": needed,
						"shortage_qty": needed - issued,
					}
				)
		return shortages

	# ------------------------------------------------------------------ #
	#  Internal helpers                                                  #
	# ------------------------------------------------------------------ #

	def _transition_to(self, target_status):
		self.job_status = target_status

	def _require_primary_document(self, fieldname, label):
		self.resolve_primary_related_documents()
		if not getattr(self, fieldname, None):
			frappe.throw(_("{0} must be linked to this Repair Job before continuing.").format(label))

	def _require_approved_authorization(self):
		self._require_primary_document("customer_authorization", "Customer Authorization")
		authorization = frappe.get_doc("Customer Authorization", self.customer_authorization)
		if authorization.status != "Approved":
			frappe.throw(_("Customer Authorization must be approved before continuing."))

	def _require_passed_quality_check(self):
		self._require_primary_document("quality_check", "Quality Check")
		quality_check = frappe.get_doc("Quality Check", self.quality_check)
		if quality_check.status != "Passed":
			frappe.throw(_("Quality Check must be in Passed status before continuing."))

	def _require_passed_road_test_if_needed(self):
		if not self.diagnosis_report:
			return
		road_test_required = frappe.db.get_value(
			"Diagnosis Report", self.diagnosis_report, "road_test_required"
		)
		if not road_test_required:
			return
		self._require_primary_document("road_test_report", "Road Test Report")
		road_test = frappe.get_doc("Road Test Report", self.road_test_report)
		if road_test.status != "Passed":
			frappe.throw(_("Road Test Report must be in Passed status before continuing."))

	def _require_issued_gate_pass(self):
		self._require_primary_document("gate_pass", "Gate Pass")
		gate_pass = frappe.get_doc("Gate Pass", self.gate_pass)
		if gate_pass.status not in {"Issued", "Used"}:
			frappe.throw(_("Gate Pass must be issued before closing the Repair Job."))

	def _coerce_line_names(self, line_names):
		if not line_names:
			return None
		if isinstance(line_names, str):
			try:
				parsed = frappe.parse_json(line_names)
			except Exception:
				parsed = [line_names]
			line_names = parsed if isinstance(parsed, (list, tuple, set)) else [parsed]
		return {str(name) for name in line_names if name}

	def _get_services(self):
		return get_repair_job_services(self.name)

	def _get_service_components(
		self,
		*,
		service_statuses=None,
		component_types=None,
		billable_only=False,
		include_excluded=False,
	):
		return list(
			iter_repair_job_components(
				self.name,
				service_statuses=service_statuses,
				component_types=component_types,
				billable_only=billable_only,
				include_excluded=include_excluded,
			)
		)

	def _has_service_status(self, statuses):
		statuses = set(statuses)
		return any(service.status in statuses for service in self._get_services())

	def _normalize_pending_services(self):
		for service in self._get_services():
			if service.status in (None, "", "Pending", "Draft"):
				service.status = "Pending Approval"
				service.save(ignore_permissions=True)

	def _approve_remaining_pending_services(self):
		for service in self._get_services():
			if service.status == "Pending Approval":
				service.status = "Approved"
				service.save(ignore_permissions=True)

	def _apply_service_status(self, target_status, line_names, allowed_current_statuses, event_type):
		service_names = self._resolve_service_names(line_names)
		if line_names and not service_names:
			frappe.throw(_("No Repair Job Service matches the selected records."))
		updated = []
		for service in self._get_services():
			if service_names and service.name not in service_names:
				continue
			if service.status not in allowed_current_statuses:
				continue
			if target_status in EXCLUDED_SERVICE_STATUSES and any(
				component_has_downstream(component) for component in get_service_components(service)
			):
				frappe.throw(
					_(
						"Repair Job Service {0} has linked ERPNext records. Cancel or reverse those records before changing it to {1}."
					).format(service.service_name or service.name, target_status)
				)
			old_status = service.status
			service.status = target_status
			service.save(ignore_permissions=True)
			updated.append(f"{service.service_name or service.name}:{old_status}->{target_status}")

		if not updated:
			frappe.throw(_("No eligible Repair Job Services were updated."))

		self.reload()
		self._write_log(event_type, new_value="\n".join(updated))

	def _resolve_service_names(self, names):
		if not names:
			return set()
		service_names = {service.name for service in self._get_services() if service.name in names}
		for service in self._get_services():
			if any(component.name in names for component in get_service_components(service)):
				service_names.add(service.name)
		return service_names

	def _sync_invoice_state(self):
		from auto_service_management.auto_service_management.integration.erpnext.document_sync import (
			sync_repair_job_invoice_state,
		)

		sync_repair_job_invoice_state(self.name)
		self.reload()

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
		for service, line in self._get_service_components(
			service_statuses={"Completed"}, include_excluded=True
		):
			if line.service_type == "Labour":
				services.append(f"{service.service_name}: {line.service_description or ''}")
			elif line.service_type in STOCK_COMPONENT_TYPES:
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
