# Copyright (c) 2026, Aslam Kimbugwe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class QualityCheck(Document):
	def validate(self):
		self.validate_repair_job_state()

	def validate_repair_job_state(self):
		if self.repair_job:
			status = frappe.db.get_value("Repair Job", self.repair_job, "job_status")
			if status not in ("In Progress", "QC Hold"):
				frappe.throw(
					f"Quality Check can only be created when the Repair Job "
					f"is in 'In Progress' or 'QC Hold' state. Current: {status}"
				)
