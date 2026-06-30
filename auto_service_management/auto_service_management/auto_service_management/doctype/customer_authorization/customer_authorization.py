# Copyright (c) 2026, Aslam Kimbugwe and contributors
# For license information, please see license.txt

from datetime import datetime

import frappe
from frappe import _
from frappe.model.document import Document


class CustomerAuthorization(Document):
	def validate(self):
		self.validate_repair_job_state()
		self.validate_amount()
		self.check_expiry()

	def _require_write_permission(self):
		self.check_permission("write")

	def validate_repair_job_state(self):
		"""Authorization is needed before work can begin."""
		if self.repair_job:
			status = frappe.db.get_value("Repair Job", self.repair_job, "job_status")
			if status not in ("Diagnosed", "Awaiting Authorization"):
				frappe.throw(
					_(
						"Customer Authorization can only be created when the Repair Job "
						"is in 'Diagnosed' or 'Awaiting Authorization' state. Current: {0}"
					).format(status)
				)

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
		# Update Repair Job authorization state
		if self.repair_job:
			frappe.db.set_value(
				"Repair Job",
				self.repair_job,
				{
					"customer_authorized": 1,
					"authorization_date": self.authorization_date,
					"authorized_by": self.authorized_by_user,
				},
			)

	@frappe.whitelist()
	def reject(self):
		"""Reject the authorization."""
		self._require_write_permission()
		if self.status != "Pending":
			frappe.throw(_("Only pending authorizations can be rejected."))
		self.status = "Rejected"
		self.save()
