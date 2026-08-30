# Copyright (c) 2026, Aslam Kimbugwe and contributors
# For license information, please see license.txt

import json
from datetime import datetime

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, now_datetime

from auto_service_management.auto_service_management.doctype.repair_job_service.repair_job_service import (
	STOCK_COMPONENT_TYPES,
	component_has_downstream,
	get_repair_job_services,
	get_service_components,
	iter_repair_job_components,
)
from auto_service_management.auto_service_management.settings_cache import (
	get_settings as _get_cached_settings,
)
from auto_service_management.auto_service_management.workflow_compatibility import (
	sync_repair_job_compatibility_views,
)


def _get_settings():
	return _get_cached_settings(frappe_module=frappe)


def _throw(code: str, message: str):
	frappe.local.response["error_code"] = code
	frappe.throw(message)


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
def make_sales_order(
	source_name: str,
	target_doc: str | None = None,
	component_refs=None,
):
	from auto_service_management.auto_service_management.integration.erpnext.component_mapping import (
		map_sales_order,
	)

	args = getattr(frappe.flags, "args", None) or {}
	return map_sales_order(
		source_name,
		target_doc=target_doc,
		component_refs=component_refs or args.get("component_refs"),
	)


@frappe.whitelist(methods=["POST"])
def make_material_request(
	source_name: str,
	target_doc: str | None = None,
	component_refs=None,
	material_request_type: str | None = None,
):
	from auto_service_management.auto_service_management.integration.erpnext.component_mapping import (
		map_material_request,
	)

	args = getattr(frappe.flags, "args", None) or {}
	return map_material_request(
		source_name,
		target_doc=target_doc,
		component_refs=component_refs or args.get("component_refs"),
		material_request_type=material_request_type or args.get("material_request_type"),
	)


@frappe.whitelist(methods=["GET"])
def get_sales_order_summary(repair_job_name: str) -> dict:
	job = frappe.get_doc("Repair Job", repair_job_name)
	job.check_permission("read")
	orders = frappe.get_all(
		"Sales Order",
		filters={"repair_job": repair_job_name},
		fields=[
			"name",
			"docstatus",
			"status",
			"transaction_date",
			"delivery_date",
			"grand_total",
			"per_billed",
		],
		order_by="creation desc",
		limit_page_length=0,
	)
	return {"count": len(orders), "sales_orders": orders}


@frappe.whitelist(methods=["GET"])
def get_company_contacts(
	doctype: str | None = None,
	txt: str | None = None,
	searchfield: str | None = None,
	start: int = 0,
	page_len: int = 20,
	filters=None,
	reference_doctype: str | None = None,
	ignore_user_permissions=False,
	customer: str | None = None,
	query: str | None = None,
	**kwargs,
) -> list:
	"""Return readable Contacts linked to the selected Company Customer.

	Frappe's Link search invokes custom query methods with the standard
	``doctype, txt, searchfield, start, page_len, filters`` positional contract.
	"""
	if isinstance(filters, str):
		filters = frappe.parse_json(filters)
	filters = filters or {}
	customer = customer or filters.get("customer") or kwargs.get("customer")
	if not customer:
		return []
	customer_doc = frappe.get_doc("Customer", customer)
	customer_doc.check_permission("read")
	if customer_doc.customer_type != "Company":
		return []
	frappe.has_permission("Contact", "read", throw=True)
	contact_names = frappe.get_all(
		"Dynamic Link",
		filters={"parenttype": "Contact", "link_doctype": "Customer", "link_name": customer},
		pluck="parent",
		limit_page_length=0,
	)
	if not contact_names:
		return []
	contacts = frappe.get_list(
		"Contact",
		filters={"name": ["in", contact_names]},
		fields=["name", "first_name", "last_name", "phone", "mobile_no", "email_id"],
		limit_page_length=0,
	)
	needle = str(txt or query or "").strip().lower()
	if needle:
		contacts = [
			row
			for row in contacts
			if needle in " ".join(str(row.get(field) or "") for field in ("name", "first_name", "last_name", "phone", "mobile_no", "email_id")).lower()
		]
	contacts = contacts[int(start or 0) : int(start or 0) + int(page_len or 20)]
	if kwargs.get("as_dict"):
		return contacts

	# Frappe's validate_link_and_fetch path compares custom-query rows with
	# ``row[0]``.  Keep dict rows for callers explicitly requesting as_dict,
	# but return standard Link-search tuples for the default path.
	return [
		(
			row["name"],
			" ".join(filter(None, (row.get("first_name"), row.get("last_name")))) or row["name"],
			" | ".join(filter(None, (row.get("email_id"), row.get("phone"), row.get("mobile_no")))),
		)
		for row in contacts
	]


@frappe.whitelist(methods=["POST"])
def create_company_contact(
	customer: str,
	first_name: str,
	middle_name: str | None = None,
	last_name: str | None = None,
	salutation: str | None = None,
	gender: str | None = None,
	designation: str | None = None,
	department: str | None = None,
	email_id: str | None = None,
	phone: str | None = None,
	mobile_no: str | None = None,
) -> dict:
	"""Create a Contact and attach it to one Company Customer."""
	if not str(first_name or "").strip():
		frappe.throw(_("First Name is required."))
	customer_doc = frappe.get_doc("Customer", customer)
	customer_doc.check_permission("read")
	if customer_doc.customer_type != "Company":
		frappe.throw(_("Company contacts can only be added for Company Customers."))
	frappe.has_permission("Contact", "create", throw=True)

	contact = frappe.get_doc({"doctype": "Contact"})
	contact_meta = frappe.get_meta("Contact")
	for fieldname, value in {
		"first_name": first_name,
		"middle_name": middle_name,
		"last_name": last_name,
		"salutation": salutation,
		"gender": gender,
		"designation": designation,
		"department": department,
		"email_id": email_id,
		"phone": phone,
		"mobile_no": mobile_no,
	}.items():
		if value and contact_meta.has_field(fieldname):
			setattr(contact, fieldname, str(value).strip())
	if not contact_meta.has_field("links"):
		frappe.throw(_("Contact cannot be linked to a Customer on this site."))
	contact.append("links", {"link_doctype": "Customer", "link_name": customer})
	contact.insert()
	return {
		"name": contact.name,
		"label": " ".join(value for value in (contact.first_name, contact.middle_name, contact.last_name) if value).strip(),
		"customer": customer,
	}


@frappe.whitelist(methods=["GET"])
def get_quotation_summary(repair_job_name: str) -> dict:
	"""Read-only legacy view retained for historical Quotation documents."""
	job = frappe.get_doc("Repair Job", repair_job_name)
	job.check_permission("read")
	quotations = frappe.get_all(
		"Quotation",
		filters={"repair_job": repair_job_name},
		fields=["name", "docstatus", "status", "transaction_date", "valid_till", "grand_total"],
		order_by="creation desc",
		limit_page_length=0,
	)
	return {"count": len(quotations), "quotations": quotations}


@frappe.whitelist(methods=["GET"])
def can_create_final_release_gate_pass(repair_job_name: str) -> bool:
	if not repair_job_name:
		return False
	job = frappe.get_doc("Repair Job", repair_job_name)
	job.check_permission("read")
	if job.gate_pass or any(row.sales_invoice for row in job.get("sales_invoices") or []):
		return True
	policy = _get_settings().get("gate_pass_payment_policy")
	return policy in {"Payment Not Required", "No Payment Required"}


class RepairJob(Document):
	def onload(self):
		"""Rebuild derived child tables when a persisted Repair Job is opened."""
		if self.is_new() or not self.name:
			return
		sync_repair_job_compatibility_views(self)

	def before_validate(self):
		self.sync_customer_and_vehicle()
		self.resolve_primary_related_documents()
		sync_repair_job_compatibility_views(self)

	def validate(self):
		self.validate_intake_requirements()
		self.validate_company_contact(require_check_in=False)
		self.validate_fleet_service_campaign()
		self.validate_customer_lpo()
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

	def validate_company_contact(self, *, require_check_in=False):
		"""Validate the per-visit Contact without changing the Customer master."""
		if not self.customer:
			return
		customer_type = frappe.db.get_value("Customer", self.customer, "customer_type")
		if customer_type == "Individual":
			if self.contact_person:
				_throw("VALIDATION_FAILED", _("Individual customers cannot have a company contact."))
			return
		if customer_type != "Company":
			return
		if require_check_in and not self.contact_person:
			_throw("COMPANY_CONTACT_REQUIRED", _("Select a Company Contact / Responsible Person before Check In."))
		if not self.contact_person:
			return
		contact = frappe.get_doc("Contact", self.contact_person)
		contact.check_permission("read")
		if not frappe.db.exists(
			"Dynamic Link",
			{"parent": contact.name, "parenttype": "Contact", "link_doctype": "Customer", "link_name": self.customer},
		):
			_throw("CONTACT_NOT_LINKED", _("Contact {0} is not linked to Customer {1}.").format(self.contact_person, self.customer))

	def capture_contact_snapshot(self):
		"""Capture the selected Contact once, at Check In."""
		if self.contact_person_name_snapshot or not self.contact_person:
			return
		contact = frappe.get_doc("Contact", self.contact_person)
		self.contact_person_name_snapshot = " ".join(
			value for value in (contact.first_name, contact.last_name) if value
		).strip()
		self.contact_person_phone_snapshot = contact.phone
		self.contact_person_mobile_snapshot = contact.mobile_no
		self.contact_person_email_snapshot = contact.email_id
		self.contact_person_captured_at = now_datetime()

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
		old = self.get_doc_before_save()
		if old and old.job_status != "Draft" and self.contact_person != old.contact_person:
			_throw("VALIDATION_FAILED", _("The company contact is read-only after Check In."))
		if self.has_value_changed("job_status"):
			self.log_state_change()

	def on_update(self):
		self.sync_fleet_campaign_membership()

	def validate_fleet_service_campaign(self):
		previous_campaign = self._previous_fleet_service_campaign()
		current_campaign = self.fleet_service_campaign
		if previous_campaign == current_campaign:
			if current_campaign:
				self._validate_campaign_customer(frappe.get_doc("Fleet Service Campaign", current_campaign))
			return

		if previous_campaign:
			frappe.get_doc("Fleet Service Campaign", previous_campaign).check_permission("write")
		if not current_campaign:
			return

		campaign = frappe.get_doc("Fleet Service Campaign", current_campaign)
		campaign.check_permission("write")
		campaign.require_active_job_link_status()
		self._validate_campaign_customer(campaign)
		if self.customer_lpo and campaign.get("customer_lpo") and self.customer_lpo != campaign.customer_lpo:
			frappe.throw(_("Repair Job Customer LPO must match Fleet Service Campaign Customer LPO."))

	def validate_customer_lpo(self):
		if not self.customer_lpo:
			return
		lpo = frappe.db.get_value(
			"Customer LPO",
			self.customer_lpo,
			["customer", "docstatus", "fleet_service_campaign"],
			as_dict=True,
		)
		if not lpo:
			frappe.throw(_("Customer LPO {0} does not exist.").format(self.customer_lpo))
		if lpo.customer != self.customer:
			frappe.throw(
				_("Customer LPO {0} customer does not match this Repair Job.").format(self.customer_lpo)
			)
		if lpo.docstatus != 1:
			frappe.throw(
				_("Customer LPO {0} must be submitted before linking a Repair Job.").format(self.customer_lpo)
			)
		if lpo.fleet_service_campaign and self.fleet_service_campaign != lpo.fleet_service_campaign:
			frappe.throw(
				_("Repair Job Fleet Service Campaign must match Customer LPO {0}.").format(self.customer_lpo)
			)

	def sync_fleet_campaign_membership(self):
		if getattr(self.flags, "skip_fleet_campaign_sync", False):
			return
		previous_campaign = self._previous_fleet_service_campaign()
		current_campaign = self.fleet_service_campaign
		if previous_campaign == current_campaign:
			return
		if previous_campaign:
			self._update_campaign_membership(previous_campaign, include=False)
		if current_campaign:
			self._update_campaign_membership(current_campaign, include=True)

	def _previous_fleet_service_campaign(self):
		old_doc = self.get_doc_before_save()
		return old_doc.fleet_service_campaign if old_doc else None

	def _validate_campaign_customer(self, campaign):
		if campaign.customer != self.customer:
			frappe.throw(
				_("Fleet Service Campaign {0} belongs to customer {1}, not {2}.").format(
					campaign.name,
					campaign.customer,
					self.customer,
				)
			)

	def _update_campaign_membership(self, campaign_name, *, include):
		campaign = frappe.get_doc("Fleet Service Campaign", campaign_name)
		campaign.check_permission("write")
		matching_rows = [row for row in campaign.get("fleet_jobs") or [] if row.repair_job == self.name]
		changed = False
		if include and not matching_rows:
			campaign.append("fleet_jobs", {"repair_job": self.name})
			changed = True
		elif include and len(matching_rows) > 1:
			for duplicate in matching_rows[1:]:
				campaign.remove(duplicate)
			changed = True
		elif not include and matching_rows:
			for row in matching_rows:
				campaign.remove(row)
			changed = True
		if not changed:
			return
		campaign.flags.skip_job_link_sync = True
		campaign.save()

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
		return frappe.render_template(
			template,
			{
				"doc": self,
				"frappe": frappe,
				"related_docs": related_docs,
				"operations": operations,
				"road_tests": road_tests,
				"linked_display_status": linked_display_status,
			},
		)

	def set_currency_from_settings(self):
		if not self.currency:
			settings = _get_settings()
			if settings and settings.default_currency:
				self.currency = settings.default_currency

	# ------------------------------------------------------------------ #
	#  Vehicle                                                           #
	# ------------------------------------------------------------------ #

	def fetch_vehicle_details(self):
		if self.customer_vehicle and not self.registration_number:
			vehicle = frappe.get_doc("Customer Vehicle", self.customer_vehicle)
			self.registration_number = vehicle.registration_number
			model_name = (
				(frappe.db.get_value("Vehicle Model", vehicle.model, "model_name") if vehicle.model else "")
				or vehicle.model
				or ""
			)
			parts = [
				vehicle.make or "",
				model_name,
				str(vehicle.year_of_manufacture or ""),
			]
			self.vehicle_details = " ".join(parts).strip()

	def capture_job_card_snapshot(self):
		"""Capture the linked customer and vehicle identity once at check-in."""
		if self.job_card_snapshot or not self.customer or not self.customer_vehicle:
			return
		from auto_service_management.auto_service_management.printing import build_job_card_snapshot

		self.job_card_snapshot = json.dumps(
			build_job_card_snapshot(self.customer, self.customer_vehicle),
			default=str,
			sort_keys=True,
		)

	# ------------------------------------------------------------------ #
	#  Actions - whitelisted workflow methods                            #
	# ------------------------------------------------------------------ #

	def _require_write_permission(self):
		self.check_permission("write")

	def _require_create_permission(self, doctype: str):
		frappe.has_permission(doctype, "create", throw=True)

	def _require_manager_override_permission(self):
		roles = set(frappe.get_roles(frappe.session.user))
		if not roles.intersection({"Workshop Manager", "Auto Service Admin", "System Manager"}):
			frappe.throw(_("Only a Workshop Manager can manually override Repair Job status."))

	@frappe.whitelist(methods=["POST"])
	def check_in(
		self,
		confirm_customer_association=False,
		expected_version=None,
		idempotency_key=None,
		contact_person=None,
	):
		"""Check in the vehicle. Creates the ERPNext Project on first check-in."""
		self._require_write_permission()
		self.reload()
		if expected_version and str(self.modified) != str(expected_version):
			_throw("STALE_REQUEST", _("Repair Job changed. Refresh and try again."))
		if contact_person is not None:
			self.contact_person = contact_person
		if self.job_status == "Assessment":
			return {"status": "already_checked_in", "repair_job": self.name}
		self.validate_intake_requirements()
		self.validate_company_contact(require_check_in=True)
		vehicle_customer = frappe.db.get_value("Customer Vehicle", self.customer_vehicle, "customer")
		association = None
		if vehicle_customer != self.customer:
			if not cint(confirm_customer_association):
				_throw(
					"CONFIRMATION_REQUIRED",
					_("Confirm that this vehicle is being serviced for Customer {0}.").format(self.customer),
				)
			from auto_service_management.auto_service_management.doctype.customer_vehicle_customer_association.customer_vehicle_customer_association import (
				associate_vehicle_customer,
			)

			association = associate_vehicle_customer(
				customer_vehicle=self.customer_vehicle,
				customer=self.customer,
				expected_version=None,
				idempotency_key=idempotency_key or f"repair-job-check-in:{self.name}",
				source_doctype="Repair Job",
				source_name=self.name,
			)
		self.capture_contact_snapshot()
		self.capture_job_card_snapshot()
		self._transition_to("Assessment")
		self.save()
		self._ensure_project()
		self._write_log("check_in")
		return {"status": "checked_in", "repair_job": self.name, "association": association}

	@frappe.whitelist(methods=["POST"])
	def start_diagnosis(self):
		self._require_write_permission()
		self.reload()
		self._transition_to("Assessment")
		self.save()
		self._write_log("start_diagnosis")

	@frappe.whitelist(methods=["POST"])
	def prepare_estimate(self):
		self._require_write_permission()
		self.reload()
		self._transition_to("Awaiting Approval")
		self.save()
		self._write_log("estimate_prepared")

	@frappe.whitelist(methods=["POST"])
	def complete_diagnosis(self):
		self._require_write_permission()
		# Desk actions may be invoked from a stale form snapshot after an
		# optional evidence row or compatibility mirror has been saved. Reload
		# before applying the transition so Frappe's optimistic timestamp check
		# protects the current document rather than rejecting a valid action.
		self.reload()
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
		self.reload()
		if self.job_status != "Awaiting Approval":
			self._transition_to("Awaiting Approval")
			self.save()
		self._write_log("request_authorization")
		return

	@frappe.whitelist(methods=["POST"])
	def authorize(self):
		self._require_write_permission()
		self.reload()
		# Authorization evidence is optional and may arrive late. Do not let an
		# approval action regress a job that has already advanced past repair.
		if self.job_status not in {"Assessment", "Awaiting Approval"}:
			return self.name
		self._transition_to("In Repair")
		self.save()
		self._write_log("authorized")

	@frappe.whitelist(methods=["POST"])
	def start_work(self):
		"""Begin repair work without requiring an authorization document."""
		self._require_write_permission()
		self.reload()
		self._transition_to("In Repair")
		self.save()
		self._write_log("start_work")

	@frappe.whitelist(methods=["POST"])
	def hold_for_qc(self):
		self._require_write_permission()
		self.reload()
		self._transition_to("Quality Check")
		self.save()
		self._write_log("hold_for_qc")

	@frappe.whitelist(methods=["POST"])
	def pass_qc(self):
		self._require_write_permission()
		self.reload()
		self._transition_to("Billing")
		self.save()
		self._sync_invoice_state()
		self._write_log("pass_qc")

	@frappe.whitelist(methods=["POST"])
	def return_to_repair(self):
		"""Explicitly return a job from Quality Check to In Repair."""
		self._require_write_permission()
		self.reload()
		if self.job_status != "Quality Check":
			frappe.throw(_("Repair Job must be in Quality Check before returning to repair."))
		self._transition_to("In Repair")
		self.save()
		self._write_log("return_to_repair")

	@frappe.whitelist(methods=["POST"])
	def mark_ready_for_invoice(self):
		self._require_write_permission()
		self.reload()
		if not self._get_services():
			frappe.throw(_("At least one Repair Job Service is required before invoicing."))
		self._transition_to("Billing")
		self.save()
		self._sync_invoice_state()
		self._write_log("ready_for_invoice")

	@frappe.whitelist(methods=["POST"])
	def release(self):
		self._require_write_permission()
		self.reload()
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
		self.reload()
		self._finalize_closure()
		self._write_log("closed")

	@frappe.whitelist(methods=["POST"])
	def close_as_diagnosis_only(self):
		self._require_write_permission()
		self.reload()
		self.closure_type = "Diagnosis Only"
		self._finalize_closure()
		self._write_log("closed_diagnosis_only")

	@frappe.whitelist(methods=["POST"])
	def cancel(self):
		self._require_write_permission()
		self.reload()
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
		self._require_create_permission("Repair Job Service")
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
	def create_sales_order(self, component_refs=None, service_names=None):
		self._require_write_permission()
		from auto_service_management.auto_service_management.integration.erpnext.adapters import (
			create_sales_order,
		)

		args = getattr(frappe.flags, "args", None) or {}
		so_name = create_sales_order(
			self,
			component_refs=component_refs or args.get("component_refs"),
			service_names=service_names or args.get("service_names"),
		)
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
		self._require_create_permission("Gate Pass")
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


def _db_has_column(doctype, fieldname):
	has_column = getattr(frappe.db, "has_column", None)
	return bool(has_column and has_column(doctype, fieldname))
