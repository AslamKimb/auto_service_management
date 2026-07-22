# Copyright (c) 2026, Aslam Kimbugwe and contributors
# For license information, please see license.txt

from datetime import datetime

import frappe
from auto_service_management.auto_service_management.doctype.repair_job_service.repair_job_service import (
	STOCK_COMPONENT_TYPES,
	component_has_downstream,
	get_repair_job_services,
	get_service_components,
	iter_repair_job_components,
)
from auto_service_management.auto_service_management.workflow_compatibility import (
	sync_repair_job_compatibility_views,
)
from frappe import _
from frappe.model.document import Document

# ---------------------------------------------------------------------------
# State machine - spec-aligned workflow
# ---------------------------------------------------------------------------
VALID_TRANSITIONS = {
	"Draft": ["Assessment", "Cancelled"],
	"Assessment": ["Awaiting Approval", "Billing", "Cancelled"],
	"Awaiting Approval": ["In Repair", "Billing", "Cancelled"],
	"In Repair": ["Quality Check", "Billing", "Cancelled"],
	"Quality Check": ["In Repair", "Billing", "Cancelled"],
	"Billing": ["Ready for Release", "Awaiting Approval", "Cancelled"],
	"Ready for Release": ["Billing", "Closed", "Cancelled"],
	"Closed": [],
	"Cancelled": [],
}


@frappe.whitelist(methods=["POST"])
def make_sales_invoice(
	source_name: str,
	target_doc: str | None = None,
	component_refs=None,
):
	from auto_service_management.auto_service_management.integration.erpnext.component_mapping import (
		map_sales_invoice,
	)

	args = getattr(frappe.flags, "args", None) or {}
	return map_sales_invoice(
		source_name,
		target_doc=target_doc,
		component_refs=component_refs or args.get("component_refs"),
	)


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
		sync_repair_job_compatibility_views(self)

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
		if self.is_new() or getattr(self.flags, "skip_primary_related_resolution", False):
			return
		for fieldname, doctype in (
			("walkaround_inspection", "Walkaround Inspection"),
			("diagnosis_report", "Diagnosis Report"),
			("customer_authorization", "Customer Authorization"),
			("quality_check", "Quality Check"),
			("gate_pass", "Gate Pass"),
		):
			if getattr(self, fieldname, None):
				continue
			filters = {"repair_job": self.name}
			if doctype == "Gate Pass" and _db_has_column("Gate Pass", "purpose"):
				filters["purpose"] = "Final Release"
			linked_name = frappe.db.get_value(doctype, filters, "name")
			if linked_name:
				setattr(self, fieldname, linked_name)

	def validate_primary_related_documents(self):
		for fieldname, doctype, matching_field in (
			("walkaround_inspection", "Walkaround Inspection", "customer_vehicle"),
			("diagnosis_report", "Diagnosis Report", "customer_vehicle"),
			("customer_authorization", "Customer Authorization", "customer"),
			("quality_check", "Quality Check", "customer_vehicle"),
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
		if getattr(self.flags, "skip_status_validation", False):
			return
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
				if getattr(service, "docstatus", 0) != 2:
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
		groups = []
		for service in self._get_services():
			groups.append(
				{
					"name": service.name,
					"service_name": service.service_name,
					"status": {0: "Draft", 1: "Submitted", 2: "Cancelled"}.get(
						getattr(service, "docstatus", 0),
						"Draft",
					),
					"docstatus": getattr(service, "docstatus", 0),
					"docstatus_label": {0: "Draft", 1: "Submitted", 2: "Cancelled"}.get(
						getattr(service, "docstatus", 0),
						"Draft",
					),
					"payment_status": getattr(service, "payment_status", None),
					"total_amount": service.total_amount,
					"components": list(get_service_components(service)),
				}
			)
		return groups

	def render_repair_summary(self):
		related_docs = [
			("Walkaround Inspection", "walkaround_inspection", "Walkaround Inspection"),
			("Diagnosis Report", "diagnosis_report", "Diagnosis Report"),
			("Customer Authorization", "customer_authorization", "Customer Authorization"),
			("Quality Check", "quality_check", "Quality Check"),
			("Gate Pass", "gate_pass", "Gate Pass"),
			("Project", "project", "Project"),
			("Quotation", "quotation", "Quotation"),
			("Sales Order", "sales_order", "Sales Order"),
		]
		operations = {
			"tasks": frappe.get_all(
				"Task",
				filters={"project": self.project} if self.project else {"name": ["=", ""]},
				fields=["name", "status", "subject"],
				order_by="creation asc",
				limit_page_length=0,
			),
			"timesheets": frappe.get_all(
				"Timesheet",
				filters={"project": self.project} if self.project else {"name": ["=", ""]},
				fields=["name", "status", "employee", "total_hours"],
				order_by="creation asc",
				limit_page_length=0,
			),
			"material_requests": frappe.get_all(
				"Material Request",
				filters={"repair_job": self.name},
				fields=["name", "docstatus", "material_request_type", "transaction_date"],
				order_by="creation asc",
				limit_page_length=0,
			),
			"stock_entries": frappe.get_all(
				"Stock Entry",
				filters={"repair_job": self.name},
				fields=["name", "docstatus", "stock_entry_type", "posting_date"],
				order_by="creation asc",
				limit_page_length=0,
			),
			"logs": frappe.get_all(
				"Repair Job Log",
				filters={"repair_job": self.name},
				fields=["event_type", "performed_by", "event_timestamp", "old_value", "new_value"],
				order_by="creation asc",
				limit_page_length=0,
			),
			"service_history": frappe.get_all(
				"Service History",
				filters={"repair_job": self.name},
				fields=["name", "closure_date", "total_amount", "closed_by"],
				order_by="modified desc",
				limit_page_length=0,
			),
		}
		quality_check = frappe.get_doc("Quality Check", self.quality_check) if self.quality_check else None
		road_tests = list(quality_check.get("road_tests") or []) if quality_check else []
		def linked_display_status(doctype, linked_name):
			meta = frappe.get_meta(doctype)
			if meta.has_field("status"):
				status = frappe.db.get_value(doctype, linked_name, "status") or ""
				if status:
					return status
			docstatus = frappe.db.get_value(doctype, linked_name, "docstatus")
			return {2: "Cancelled", 1: "Submitted"}.get(docstatus, "Linked")

		template = """
<style>
.repair-summary { font-family: sans-serif; color: #111827; }
.repair-summary h2, .repair-summary h3 { margin: 0 0 8px; }
.repair-summary .section { margin: 0 0 16px; }
.repair-summary table { width: 100%; border-collapse: collapse; margin: 0 0 12px; }
.repair-summary th, .repair-summary td { border: 1px solid #d1d5db; padding: 5px 6px; vertical-align: top; }
.repair-summary th { background: #f3f4f6; text-align: left; }
.repair-summary .muted { color: #6b7280; }
.repair-summary .group { background: #f9fafb; font-weight: 700; }
</style>
<div class="repair-summary">
  <div class="section">
    <h2>Repair Summary {{ doc.name }}</h2>
    <table>
      <tr>
        <th>Customer</th><td>{{ doc.customer or "" }}</td>
        <th>Vehicle</th><td>{{ doc.customer_vehicle or "" }}</td>
      </tr>
      <tr>
        <th>Status</th><td>{{ doc.job_status or "" }}</td>
        <th>Payment</th><td>{{ doc.payment_status or "" }}</td>
      </tr>
      <tr>
        <th>Closed On</th><td>{{ frappe.utils.format_datetime(doc.closed_on) if doc.closed_on else "" }}</td>
        <th>Odometer</th><td>{{ doc.odometer_in or "" }} → {{ doc.odometer_out or "" }}</td>
      </tr>
    </table>
  </div>
  <div class="section">
    <h3>Related documents</h3>
    <table>
      <tr><th>Type</th><th>Document</th><th>Status</th></tr>
      {% for label, fieldname, doctype in related_docs %}
        {% set linked_name = doc.get(fieldname) %}
        {% if linked_name %}
          <tr><td>{{ label }}</td><td>{{ linked_name }}</td><td>{{ linked_display_status(doctype, linked_name) }}</td></tr>
        {% else %}
          <tr><td>{{ label }}</td><td class="muted">Not linked</td><td class="muted">—</td></tr>
        {% endif %}
      {% endfor %}
    </table>
  </div>
	<div class="section">
    <h3>Services</h3>
    {% for service in doc.get_service_groups() %}
      <table>
        <tr class="group"><td colspan="5">{{ service.service_name or service.name }} — {{ service.docstatus_label }}</td></tr>
        <tr><th>Type</th><th>Description</th><th>Qty</th><th>Amount</th><th>Billable</th></tr>
        {% for row in service.components %}
          <tr>
            <td>{{ row.service_type }}</td>
            <td>{{ row.service_description }}</td>
            <td>{{ row.quantity if row.service_type != "Labour" else row.billing_hours }}</td>
            <td>{{ row.amount if row.service_type != "Labour" else row.billing_amount }}</td>
            <td>{{ "Yes" if row.billable else "No" }}</td>
          </tr>
        {% endfor %}
      </table>
    {% endfor %}
  </div>
  <div class="section">
    <h3>Invoices and payments</h3>
    <table>
      <tr><th>Sales Invoices</th><th>Posted</th><th>Grand Total</th><th>Paid</th><th>Outstanding</th></tr>
      {% for row in doc.get("sales_invoices") or [] %}
        <tr>
          <td>{{ row.sales_invoice }}</td>
          <td>{{ row.posting_date or "" }}</td>
          <td>{{ row.grand_total or 0 }}</td>
          <td>{{ row.paid_amount or 0 }}</td>
          <td>{{ row.outstanding_amount or 0 }}</td>
        </tr>
      {% endfor %}
    </table>
    <table>
      <tr><th>Payment Entry</th><th>Invoice</th><th>Posted</th><th>Allocated</th></tr>
      {% for row in doc.get("payment_entries") or [] %}
        <tr>
          <td>{{ row.payment_entry }}</td>
          <td>{{ row.reference_invoice }}</td>
          <td>{{ row.posting_date or "" }}</td>
          <td>{{ row.allocated_amount or 0 }}</td>
        </tr>
      {% endfor %}
    </table>
  </div>
  <div class="section">
    <h3>Operational trail</h3>
    <table>
      <tr><th>Tasks</th><th>Timesheets</th><th>Material Requests</th><th>Stock Entries</th></tr>
      <tr>
        <td>{{ operations.tasks|length }}</td>
        <td>{{ operations.timesheets|length }}</td>
        <td>{{ operations.material_requests|length }}</td>
        <td>{{ operations.stock_entries|length }}</td>
      </tr>
    </table>
    <table>
      <tr><th>Event</th><th>By</th><th>When</th><th>From</th><th>To</th></tr>
      {% for row in operations.logs %}
        <tr>
          <td>{{ row.event_type }}</td>
          <td>{{ row.performed_by }}</td>
          <td>{{ row.event_timestamp }}</td>
          <td>{{ row.old_value or "" }}</td>
          <td>{{ row.new_value or "" }}</td>
        </tr>
      {% endfor %}
    </table>
    <table>
      <tr><th>Service History</th><th>Closed By</th><th>Closed On</th><th>Total</th></tr>
      {% for row in operations.service_history %}
        <tr>
          <td>{{ row.name }}</td>
          <td>{{ row.closed_by or "" }}</td>
          <td>{{ row.closure_date or "" }}</td>
          <td>{{ row.total_amount or 0 }}</td>
        </tr>
      {% endfor %}
    </table>
  </div>
  <div class="section">
    <h3>Road tests</h3>
    <table>
      <tr><th>Status</th><th>Tested By</th><th>Date</th><th>Route</th><th>Notes</th></tr>
      {% for row in road_tests %}
        <tr>
          <td>{{ row.status or "" }}</td>
          <td>{{ row.tested_by or "" }}</td>
          <td>{{ row.test_date or "" }}</td>
          <td>{{ row.route or "" }}</td>
          <td>{{ row.test_notes or "" }}</td>
        </tr>
      {% endfor %}
    </table>
  </div>
</div>
"""
		return frappe.render_template(template, {
			"doc": self,
			"frappe": frappe,
			"related_docs": related_docs,
			"operations": operations,
			"road_tests": road_tests,
			"linked_display_status": linked_display_status,
		})

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

	def _require_manager_override_permission(self):
		roles = set(frappe.get_roles(frappe.session.user))
		if not roles.intersection({"Workshop Manager", "Auto Service Admin", "System Manager"}):
			frappe.throw(_("Only a Workshop Manager can manually override Repair Job status."))

	@frappe.whitelist(methods=["POST"])
	def check_in(self):
		"""Check in the vehicle. Creates the ERPNext Project on first check-in."""
		self._require_write_permission()
		self._transition_to("Assessment")
		self.save()
		self._ensure_project()
		self._write_log("check_in")

	@frappe.whitelist(methods=["POST"])
	def start_diagnosis(self):
		self._require_write_permission()
		self._require_primary_document("walkaround_inspection", "Walkaround Inspection")
		self._transition_to("Assessment")
		self.save()
		self._write_log("start_diagnosis")

	@frappe.whitelist(methods=["POST"])
	def prepare_estimate(self):
		self._require_write_permission()
		self._require_submitted_diagnosis()
		self._transition_to("Awaiting Approval")
		self.save()
		self._write_log("estimate_prepared")

	@frappe.whitelist(methods=["POST"])
	def complete_diagnosis(self):
		self._require_write_permission()
		self._require_submitted_diagnosis()
		if self._get_services():
			target_status = "Awaiting Approval"
		else:
			target_status = "Billing"
		if self.job_status != target_status:
			self._transition_to(target_status)
			self.save()
		self._write_log("complete_diagnosis")

	@frappe.whitelist(methods=["POST"])
	def request_authorization(self):
		self._require_write_permission()
		self._require_submitted_diagnosis()
		if self.job_status != "Awaiting Approval":
			self._transition_to("Awaiting Approval")
			self.save()
		self._write_log("request_authorization")
		return

	@frappe.whitelist(methods=["POST"])
	def authorize(self):
		self._require_write_permission()
		self._require_approved_authorization()
		self.reload()
		self._transition_to("In Repair")
		self.save()
		self._write_log("authorized")

	@frappe.whitelist(methods=["POST"])
	def start_work(self):
		"""Begin repair work. Requires authorization."""
		self._require_write_permission()
		self._require_approved_authorization()
		self._transition_to("In Repair")
		self.save()
		self._write_log("start_work")

	@frappe.whitelist(methods=["POST"])
	def hold_for_qc(self):
		self._require_write_permission()
		self._transition_to("Quality Check")
		self.save()
		self._write_log("hold_for_qc")

	@frappe.whitelist(methods=["POST"])
	def pass_qc(self):
		self._require_write_permission()
		self._require_passed_quality_check()
		self._require_passed_road_test_if_needed()
		self._transition_to("Billing")
		self.save()
		self._sync_invoice_state()
		self._write_log("pass_qc")

	@frappe.whitelist(methods=["POST"])
	def mark_ready_for_invoice(self):
		self._require_write_permission()
		if not self._get_services():
			frappe.throw(_("At least one Repair Job Service is required before invoicing."))
		self._transition_to("Billing")
		self.save()
		self._sync_invoice_state()
		self._write_log("ready_for_invoice")

	@frappe.whitelist(methods=["POST"])
	def release(self):
		self._require_write_permission()
		self._sync_invoice_state()
		from auto_service_management.auto_service_management.integration.erpnext.document_sync import (
			validate_job_invoices_for_gate_pass,
		)

		validate_job_invoices_for_gate_pass(self.name)
		self._transition_to("Ready for Release")
		self.save()
		self._write_log("released")

	@frappe.whitelist(methods=["POST"])
	def close(self):
		"""Close the job. Creates Service History and updates vehicle."""
		self._require_write_permission()
		self._finalize_closure()
		self._write_log("closed")

	@frappe.whitelist(methods=["POST"])
	def close_as_diagnosis_only(self):
		self._require_write_permission()
		self.closure_type = "Diagnosis Only"
		self._finalize_closure()
		self._write_log("closed_diagnosis_only")

	@frappe.whitelist(methods=["POST"])
	def cancel(self):
		self._require_write_permission()
		self._transition_to("Cancelled")
		self.save()
		self._write_log("cancelled")

	@frappe.whitelist(methods=["POST"])
	def override_status(self, target_status, reason):
		self._require_manager_override_permission()
		target_status = str(target_status or "").strip()
		reason = str(reason or "").strip()
		if not reason:
			frappe.throw(_("Reason is required for a manual status override."))
		if target_status not in VALID_TRANSITIONS:
			frappe.throw(_("Unknown Repair Job status {0}.").format(target_status))
		if target_status in {"Closed", "Cancelled"}:
			frappe.throw(_("Use the Close or Cancel action for terminal statuses."))
		old_status = self.job_status or "Draft"
		self.job_status = target_status
		if self.meta.has_field("workflow_state"):
			self.workflow_state = target_status
		if old_status in {"Closed", "Cancelled"}:
			self.closed_on = None
			self.closed_by = None
			self.closure_type = None
			self.gate_pass = None
		self.flags.skip_status_validation = True
		self.flags.ignore_links = True
		self.flags.skip_primary_related_resolution = True
		self.save(ignore_permissions=True)
		self._write_override_audit(old_status, target_status, reason)
		self._write_log("manual_status_override", old_status, target_status)
		return self.name

	@frappe.whitelist(methods=["POST"])
	def create_service(self, service_name=None):
		self._require_write_permission()
		service = frappe.get_doc(
			{
				"doctype": "Repair Job Service",
				"repair_job": self.name,
				"customer": self.customer,
				"customer_vehicle": self.customer_vehicle,
				"diagnosis_report": self.diagnosis_report,
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

	@frappe.whitelist(methods=["POST"])
	def create_quotation(self):
		"""Generate a Quotation from approved service components."""
		self._require_write_permission()
		from auto_service_management.auto_service_management.integration.erpnext.adapters import (
			create_quotation,
		)

		quote_name = create_quotation(self)
		self.reload()
		return quote_name

	@frappe.whitelist(methods=["POST"])
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

	@frappe.whitelist(methods=["POST"])
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

	@frappe.whitelist(methods=["POST"])
	def create_gate_pass(self, purpose="Final Release"):
		"""Issue a Gate Pass for this Repair Job."""
		self._require_write_permission()
		purpose = purpose or "Final Release"
		from auto_service_management.auto_service_management.integration.erpnext.document_sync import (
			validate_job_invoices_for_gate_pass,
		)

		invoices = [] if purpose == "Road Test" else validate_job_invoices_for_gate_pass(self.name)
		primary_invoice = invoices[0] if invoices else None
		for row in self.get("sales_invoices") or []:
			if row.sales_invoice in invoices:
				primary_invoice = row.sales_invoice
				break
		gp = frappe.get_doc(
			{
				"doctype": "Gate Pass",
				"repair_job": self.name,
				"purpose": purpose,
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
		if self.meta.has_field("workflow_state"):
			self.workflow_state = target_status

	def _require_primary_document(self, fieldname, label):
		self.resolve_primary_related_documents()
		if not getattr(self, fieldname, None):
			frappe.throw(_("{0} must be linked to this Repair Job before continuing.").format(label))

	def _require_submitted_diagnosis(self):
		self.resolve_primary_related_documents()
		if not self.diagnosis_report:
			self.diagnosis_report = frappe.db.get_value(
				"Diagnosis Report", {"repair_job": self.name, "docstatus": ["!=", 2]}, "name"
			)
		if not self.diagnosis_report:
			frappe.throw(_("Diagnosis Report must be linked to this Repair Job before continuing."))
		if frappe.db.get_value("Diagnosis Report", self.diagnosis_report, "docstatus") != 1:
			frappe.throw(_("Diagnosis Report must be submitted before continuing."))

	def _require_approved_authorization(self):
		self._require_primary_document("customer_authorization", "Customer Authorization")
		authorization = frappe.get_doc("Customer Authorization", self.customer_authorization)
		if getattr(authorization, "docstatus", 0) != 1:
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
		self._require_primary_document("quality_check", "Quality Check")
		quality_check = frappe.get_doc("Quality Check", self.quality_check)
		road_tests = quality_check.get("road_tests") or []
		if not road_tests:
			frappe.throw(_("At least one road test must be recorded on the Quality Check before continuing."))
		if not any(_road_test_is_passed(road_test) for road_test in road_tests):
			frappe.throw(_("At least one recorded road test must pass before continuing."))

	def _require_issued_gate_pass(self):
		self._require_primary_document("gate_pass", "Gate Pass")
		gate_pass = frappe.get_doc("Gate Pass", self.gate_pass)
		if getattr(gate_pass, "purpose", "Final Release") != "Final Release":
			frappe.throw(_("Final Release Gate Pass is required before closing the Repair Job."))
		if gate_pass.status != "Used":
			frappe.throw(_("Gate Pass must be used before closing the Repair Job."))

	def _finalize_closure(self, ignore_permissions=False):
		self._require_issued_gate_pass()
		self._transition_to("Closed")
		self.closed_on = self.closed_on or datetime.now()
		self.closed_by = self.closed_by or frappe.session.user
		self.flags.ignore_permissions = ignore_permissions
		self.flags.ignore_links = True
		self.flags.skip_status_validation = True
		self.save(ignore_permissions=ignore_permissions)
		self._update_vehicle_after_closure()
		self._create_service_history()

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
		component_types=None,
		billable_only=False,
		include_excluded=False,
	):
		return list(
			iter_repair_job_components(
				self.name,
				component_types=component_types,
				billable_only=billable_only,
				include_excluded=include_excluded,
			)
		)

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

	def _write_override_audit(self, old_status, target_status, reason):
		override = frappe.get_doc(
			{
				"doctype": "Repair Job Override",
				"override_type": "Status Override",
				"repair_job": self.name,
				"previous_status": old_status,
				"target_status": target_status,
				"reason": reason,
				"override_by": frappe.session.user,
				"override_date": datetime.now(),
				"status": "Approved",
			}
		)
		override.insert(ignore_permissions=True)
		if getattr(override.meta, "is_submittable", False):
			override.submit()

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
			history = frappe.get_doc("Service History", existing)
		else:
			history = frappe.new_doc("Service History")

		services = []
		parts = []
		for service, line in self._get_service_components(include_excluded=True):
			if line.service_type == "Labour":
				services.append(f"{service.service_name}: {line.service_description or ''}")
			elif line.service_type in STOCK_COMPONENT_TYPES:
				parts.append(line.service_description or "")

		history.update(
			{
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
		)
		if history.is_new():
			history.insert(ignore_permissions=True)
		else:
			history.save(ignore_permissions=True)


def _road_test_is_passed(road_test):
	if getattr(road_test, "status", None) == "Passed":
		return True
	if getattr(road_test, "passed", None):
		return True
	if getattr(road_test, "road_test_passed", None):
		return True
	check_fields = (
		"braking_ok",
		"steering_ok",
		"engine_performance_ok",
		"transmission_ok",
		"no_warning_lights",
	)
	return all(bool(getattr(road_test, field, None)) for field in check_fields)


def _db_has_column(doctype, fieldname):
	has_column = getattr(frappe.db, "has_column", None)
	return bool(has_column and has_column(doctype, fieldname))
