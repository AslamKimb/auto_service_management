# Copyright (c) 2026, Aslam Kimbugwe and contributors
# For license information, please see license.txt

import frappe
from auto_service_management.auto_service_management.workflow_compatibility import (
	recompute_repair_job_state,
	sync_customer_authorization_snapshot,
)
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class CustomerAuthorization(Document):
	def validate(self):
		self.sync_with_repair_job()
		self.validate_repair_job_state()
		self.validate_unique_for_repair_job()
		self.validate_amount()
		self.check_expiry()
		sync_customer_authorization_snapshot(self)

	def on_update(self):
		self.sync_primary_link()
		sync_customer_authorization_snapshot(self)
		recompute_repair_job_state(self.repair_job)

	def sync_with_repair_job(self):
		if not self.repair_job:
			return
		job = frappe.get_doc("Repair Job", self.repair_job)
		if not self.customer:
			self.customer = job.customer
		elif self.customer != job.customer:
			frappe.throw(_("Customer Authorization customer must match the linked Repair Job customer."))
		if not self.currency and job.currency:
			self.currency = job.currency

	def _require_write_permission(self):
		self.check_permission("write")

	def validate_repair_job_state(self):
		"""Keep authorization evidence optional at every Repair Job status."""
		return

	def validate_unique_for_repair_job(self):
		if not self.repair_job:
			return
		existing = frappe.db.exists(
			"Customer Authorization",
			{"repair_job": self.repair_job, "name": ["!=", self.name or ""]},
		)
		if existing:
			frappe.throw(_("Only one Customer Authorization may be linked to a Repair Job."))

	def validate_amount(self):
		"""Approved amount must cover the full job scope."""
		if self.approved_amount and self.approved_amount <= 0:
			frappe.throw(_("Approved amount must be greater than zero."))
		if self.repair_job:
			job_total = frappe.db.get_value("Repair Job", self.repair_job, "total_amount") or 0
			if self.approved_amount and float(self.approved_amount) < float(job_total):
				frappe.throw(_("Approved amount must cover the full Repair Job amount."))

	def check_expiry(self):
		"""Block submitting an expired authorization."""
		if self.expiry_date and getattr(self, "docstatus", 0) == 1:
			if getdate(self.expiry_date) < getdate(frappe.utils.today()):
				frappe.throw(_("Approved authorization has expired."))

	@frappe.whitelist(methods=["POST"])
	def approve(self):
		"""Approve the authorization and update linked Repair Job."""
		self._require_write_permission()
		if getattr(self, "docstatus", 0) != 1:
			self.save()
			self.submit()
		if self.repair_job:
			job = frappe.get_doc("Repair Job", self.repair_job)
			if job.customer_authorization != self.name:
				frappe.db.set_value(
					"Repair Job", self.repair_job, "customer_authorization", self.name, update_modified=False
				)
			job.reload()
			if job.job_status in {"Assessment", "Awaiting Approval"}:
				job.authorize()
		recompute_repair_job_state(self.repair_job)

	@frappe.whitelist(methods=["POST"])
	def reject(self):
		"""Reject the authorization."""
		self._require_write_permission()
		if not self.authorization_notes:
			frappe.throw(_("A rejection reason must be provided in Notes."))
		if getattr(self, "docstatus", 0) != 1:
			frappe.throw(_("Submit the authorization before rejecting it."))
		self.cancel()
		recompute_repair_job_state(self.repair_job)

	def sync_primary_link(self):
		if not self.repair_job:
			return
		if frappe.db.get_value("Repair Job", self.repair_job, "customer_authorization") != self.name:
			frappe.db.set_value(
				"Repair Job", self.repair_job, "customer_authorization", self.name, update_modified=False
			)
