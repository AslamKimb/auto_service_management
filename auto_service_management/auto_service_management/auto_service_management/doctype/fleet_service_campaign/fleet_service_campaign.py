# Copyright (c) 2026, Aslam Kimbugwe and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from auto_service_management.auto_service_management.integration.erpnext.component_mapping import (
	map_campaign_sales_invoice,
	map_campaign_sales_order,
)

ACTIVE_JOB_LINK_STATUSES = {"Draft", "Ongoing"}


@frappe.whitelist(methods=["POST"])
def make_repair_job(source_name: str, target_doc: str | dict | None = None) -> Document:
	"""Return an unsaved Repair Job linked to an active fleet campaign."""
	campaign = frappe.get_doc("Fleet Service Campaign", source_name)
	campaign.check_permission("write")
	campaign.require_active_job_link_status()
	frappe.has_permission("Repair Job", "create", throw=True)

	if isinstance(target_doc, str):
		target_doc = frappe.parse_json(target_doc)
	target = frappe.get_doc(target_doc) if target_doc else frappe.new_doc("Repair Job")
	if target.doctype != "Repair Job":
		frappe.throw(_("Expected target document type Repair Job."))
	if target.get("docstatus") not in {None, 0}:
		frappe.throw(_("A Repair Job can only be created as a draft."))
	if target.get("customer") and target.customer != campaign.customer:
		frappe.throw(_("Target customer must match the Fleet Service Campaign customer."))
	if target.get("fleet_service_campaign") and target.fleet_service_campaign != campaign.name:
		frappe.throw(_("Target Repair Job is already linked to another Fleet Service Campaign."))

	target.customer = campaign.customer
	target.fleet_service_campaign = campaign.name
	return target


@frappe.whitelist(methods=["POST"])
def make_sales_order(
	source_name: str,
	target_doc: str | dict | None = None,
	component_refs: list[dict] | str | None = None,
) -> Document:
	"""Return an unsaved consolidated Sales Order for selected campaign components."""
	args = getattr(frappe.flags, "args", None) or {}
	return map_campaign_sales_order(
		source_name,
		target_doc=target_doc,
		component_refs=component_refs or args.get("component_refs"),
	)


@frappe.whitelist(methods=["POST"])
def make_sales_invoice(
	source_name: str,
	target_doc: str | dict | None = None,
	component_refs: list[dict] | str | None = None,
) -> Document:
	"""Return an unsaved direct Sales Invoice for selected campaign components."""
	args = getattr(frappe.flags, "args", None) or {}
	return map_campaign_sales_invoice(
		source_name,
		target_doc=target_doc,
		component_refs=component_refs or args.get("component_refs"),
	)


@frappe.whitelist(methods=["GET"])
def get_campaign_sales_document_summary(campaign_name: str) -> dict:
	"""Return live, permission-scoped campaign Sales Order and Invoice rows."""
	campaign = frappe.get_doc("Fleet Service Campaign", campaign_name)
	campaign.check_permission("read")
	filters = {"fleet_service_campaign": campaign.name}
	return {
		"sales_orders": _get_sales_document_rows(
			"Sales Order",
			filters,
			[
				"name",
				"transaction_date",
				"delivery_date",
				"status",
				"docstatus",
				"grand_total",
				"per_billed",
				"currency",
			],
			"transaction_date desc, creation desc",
		),
		"sales_invoices": _get_sales_document_rows(
			"Sales Invoice",
			filters,
			[
				"name",
				"posting_date",
				"status",
				"docstatus",
				"grand_total",
				"outstanding_amount",
				"currency",
			],
			"posting_date desc, creation desc",
		),
	}


def _get_sales_document_rows(doctype, filters, fields, order_by):
	if not frappe.has_permission(doctype, "read"):
		return []
	return frappe.get_list(
		doctype,
		filters=filters,
		fields=fields,
		order_by=order_by,
		limit_page_length=0,
	)


class FleetServiceCampaign(Document):
	def validate(self):
		self.validate_unique_jobs()
		self.validate_job_customers()
		self.validate_job_link_changes()
		self.validate_customer_lpo()

	def on_update(self):
		if getattr(self.flags, "skip_job_link_sync", False):
			return
		self.sync_job_links()

	def on_trash(self):
		self.sync_job_links(clear_all=True)

	def validate_unique_jobs(self):
		seen = set()
		for row in self.fleet_jobs or []:
			if not row.repair_job:
				continue
			if row.repair_job in seen:
				frappe.throw(f"Repair Job {row.repair_job} appears more than once in this campaign.")
			seen.add(row.repair_job)

	def validate_job_customers(self):
		for row in self.fleet_jobs or []:
			if not row.repair_job:
				continue
			job = frappe.db.get_value(
				"Repair Job",
				row.repair_job,
				["customer", "fleet_service_campaign"],
				as_dict=True,
			)
			if not job:
				frappe.throw(_("Repair Job {0} does not exist.").format(row.repair_job))
			if job.customer != self.customer:
				frappe.throw(
					_("Repair Job {0} belongs to customer {1}, not {2}.").format(
						row.repair_job,
						job.customer,
						self.customer,
					)
				)
			if self.customer_lpo:
				job_lpo = job.get("customer_lpo")
				if job_lpo and job_lpo != self.customer_lpo:
					frappe.throw(
						_("Repair Job {0} is linked to Customer LPO {1}, not {2}.").format(
							row.repair_job, job_lpo, self.customer_lpo
						)
					)
			if job.fleet_service_campaign and job.fleet_service_campaign != self.name:
				frappe.throw(
					_("Repair Job {0} is already linked to Fleet Service Campaign {1}.").format(
						row.repair_job,
						job.fleet_service_campaign,
					)
				)

	def require_active_job_link_status(self):
		if (self.status or "Draft") not in ACTIVE_JOB_LINK_STATUSES:
			frappe.throw(_("Repair Jobs can only be added to Draft or Ongoing Fleet Service Campaigns."))

	def validate_job_link_changes(self):
		old_doc = self.get_doc_before_save()
		old_jobs = _job_names(old_doc.get("fleet_jobs") if old_doc else [])
		new_jobs = _job_names(self.fleet_jobs)
		changed_jobs = old_jobs.symmetric_difference(new_jobs)
		if not changed_jobs:
			return
		self.require_active_job_link_status()
		for repair_job in sorted(changed_jobs):
			frappe.get_doc("Repair Job", repair_job).check_permission("write")

	def validate_customer_lpo(self):
		if not self.customer_lpo:
			return
		lpo = frappe.db.get_value("Customer LPO", self.customer_lpo, ["customer", "docstatus"], as_dict=True)
		if not lpo:
			frappe.throw(_("Customer LPO {0} does not exist.").format(self.customer_lpo))
		if lpo.customer != self.customer:
			frappe.throw(
				_("Customer LPO {0} customer does not match this campaign.").format(self.customer_lpo)
			)

	def sync_job_links(self, clear_all=False):
		linked_jobs = set(
			frappe.get_all(
				"Repair Job",
				filters={"fleet_service_campaign": self.name},
				pluck="name",
			)
		)
		selected_jobs = set()
		if not clear_all:
			selected_jobs = {row.repair_job for row in self.fleet_jobs or [] if row.repair_job}

		for repair_job in sorted(linked_jobs - selected_jobs):
			self._set_repair_job_campaign(repair_job, None)
		for repair_job in sorted(selected_jobs):
			self._set_repair_job_campaign(repair_job, self.name)

	def _set_repair_job_campaign(self, repair_job_name, campaign_name):
		repair_job = frappe.get_doc("Repair Job", repair_job_name)
		if repair_job.fleet_service_campaign == campaign_name:
			return
		if (
			campaign_name
			and repair_job.fleet_service_campaign
			and repair_job.fleet_service_campaign != campaign_name
		):
			frappe.throw(
				_("Repair Job {0} is already linked to Fleet Service Campaign {1}.").format(
					repair_job.name,
					repair_job.fleet_service_campaign,
				)
			)
		repair_job.check_permission("write")
		repair_job.fleet_service_campaign = campaign_name
		repair_job.flags.skip_fleet_campaign_sync = True
		repair_job.save()


def _job_names(rows) -> set[str]:
	return {row.repair_job for row in rows or [] if row.repair_job}
