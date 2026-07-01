# Copyright (c) 2026, Aslam Kimbugwe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class DiagnosisReport(Document):
	def validate(self):
		self.validate_repair_job_state()

	def validate_repair_job_state(self):
		"""Diagnosis can only happen after check-in."""
		if self.repair_job:
			status = frappe.db.get_value("Repair Job", self.repair_job, "job_status")
			if status not in (
				"Walkaround Inspection",
				"Diagnosis",
				"Estimate Prepared",
				"Waiting for Customer Approval",
				"Approved",
			):
				frappe.throw(
					f"Diagnosis Report requires the Repair Job to be in "
					f"'Walkaround Inspection', 'Diagnosis', 'Estimate Prepared', "
					f"'Waiting for Customer Approval', or 'Approved' state. Current: {status}"
				)
