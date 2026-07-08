# Copyright (c) 2026, Aslam Kimbugwe and contributors
# For license information, please see license.txt

from datetime import datetime

import frappe
from frappe import _
from frappe.model.document import Document


class CustomerAuthorization(Document):
	def validate(self):
		self.sync_with_repair_job()
		self.validate_repair_job_state()
		self.validate_unique_for_repair_job()
		self.validate_amount()
		self.check_expiry()

	def on_update(self):
		self.sync_primary_link()

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
		"""Authorization is needed before work can begin."""
		if self.repair_job:
			status = frappe.db.get_value("Repair Job", self.repair_job, "job_status")
			if status not in ("Estimate Prepared", "Waiting for Customer Approval", "Approved"):
				frappe.throw(
					_(
						"Customer Authorization can only be created when the Repair Job "
						"is in 'Estimate Prepared', 'Waiting for Customer Approval', or 'Approved' state. Current: {0}"
					).format(status)
				)

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
		"""Approved amount must be positive."""
		if self.approved_amount and self.approved_amount <= 0:
			frappe.throw(_("Approved amount must be greater than zero."))

	def check_expiry(self):
		"""Warn if authorization is expired."""
		if self.expiry_date and self.status == "Approved":
			from frappe.utils import getdate

			if getdate(self.expiry_date) < getdate(frappe.utils.today()):
				frappe.msgprint(
					_("Warning: This authorization has expired on {0}.").format(self.expiry_date),
					alert=True,
				)

	@frappe.whitelist()
	def approve(self):
		"""Approve the authorization and update linked Repair Job."""
		self._require_write_permission()
		if self.status != "Pending":
			frappe.throw(_("Only pending authorizations can be approved."))
		self.status = "Approved"
		self.save()
		if self.repair_job:
			job = frappe.get_doc("Repair Job", self.repair_job)
			if job.customer_authorization != self.name:
				frappe.db.set_value(
					"Repair Job", self.repair_job, "customer_authorization", self.name, update_modified=False
				)
				job.reload()
			job.authorize()

	@frappe.whitelist()
	def reject(self):
		"""Reject the authorization."""
		self._require_write_permission()
		if self.status != "Pending":
			frappe.throw(_("Only pending authorizations can be rejected."))
		self.status = "Rejected"
		self.save()

	def sync_primary_link(self):
		if not self.repair_job:
			return
		if frappe.db.get_value("Repair Job", self.repair_job, "customer_authorization") != self.name:
			frappe.db.set_value(
				"Repair Job", self.repair_job, "customer_authorization", self.name, update_modified=False
			)
