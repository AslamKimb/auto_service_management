# Copyright (c) 2026, Aslam Kimbugwe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class WorkshopBay(Document):
	def validate(self):
		if self.status == "Under Maintenance" and self.occupied_count() > 0:
			frappe.throw("Cannot set bay to Under Maintenance while jobs are assigned to it.")

	def occupied_count(self):
		"""Count active repair jobs assigned to this bay."""
		return frappe.db.count(
			"Repair Job",
			{
				"workshop_bay": self.name,
				"job_status": ("in", ["Checked In", "In Progress", "Under Diagnosis"]),
			},
		)
