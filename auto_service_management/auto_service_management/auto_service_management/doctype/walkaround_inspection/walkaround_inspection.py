# Copyright (c) 2026, Aslam Kimbugwe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class WalkaroundInspection(Document):
	def validate(self):
		self.validate_repair_job_link()

	def after_insert(self):
		self.advance_repair_job()

	def validate_repair_job_link(self):
		"""Ensure linked Repair Job is in an appropriate state."""
		if self.repair_job:
			job = frappe.get_doc("Repair Job", self.repair_job)
			if job.job_status not in ("Checked In", "Walkaround Inspection"):
				frappe.throw(
					f"Walkaround Inspection can only be created for Repair Jobs "
					f"in 'Checked In' or 'Walkaround Inspection' state. Current: {job.job_status}"
				)

	def advance_repair_job(self):
		if not self.repair_job:
			return
		job = frappe.get_doc("Repair Job", self.repair_job)
		if job.job_status == "Checked In":
			job.job_status = "Walkaround Inspection"
			job.save(ignore_permissions=True)
