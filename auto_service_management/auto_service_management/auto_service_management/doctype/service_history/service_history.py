# Copyright (c) 2026, Aslam Kimbugwe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ServiceHistory(Document):
	def validate(self):
		"""Ensure idempotency: one Service History per Repair Job."""
		if self.repair_job:
			existing = frappe.db.exists(
				"Service History",
				{"repair_job": self.repair_job, "name": ("!=", self.name)},
			)
			if existing:
				frappe.throw(
					f"A Service History record already exists for Repair Job {self.repair_job} ({existing})."
				)
