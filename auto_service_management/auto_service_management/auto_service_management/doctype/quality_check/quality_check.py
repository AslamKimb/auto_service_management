# Copyright (c) 2026, Aslam Kimbugwe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class QualityCheck(Document):
	def validate(self):
		self.sync_with_repair_job()
		self.validate_repair_job_state()
		self.validate_unique_for_repair_job()

	def on_update(self):
		self.sync_primary_link()

	def validate_repair_job_state(self):
		if self.repair_job:
			status = frappe.db.get_value("Repair Job", self.repair_job, "job_status")
			if status not in ("In Repair", "Quality Check"):
				frappe.throw(
					f"Quality Check can only be created when the Repair Job "
					f"is in 'In Repair' or 'Quality Check' state. Current: {status}"
				)

	def sync_with_repair_job(self):
		if not self.repair_job:
			return

		job = frappe.get_doc("Repair Job", self.repair_job)
		if not self.customer_vehicle:
			self.customer_vehicle = job.customer_vehicle
		elif self.customer_vehicle != job.customer_vehicle:
			frappe.throw("Quality Check vehicle must match the linked Repair Job vehicle.")

	def validate_unique_for_repair_job(self):
		if not self.repair_job:
			return

		existing = frappe.db.get_value(
			"Quality Check",
			{"repair_job": self.repair_job, "name": ["!=", self.name or ""]},
			"name",
		)
		if existing:
			frappe.throw(f"Repair Job {self.repair_job} already has Quality Check {existing}.")

	def sync_primary_link(self):
		if not self.repair_job or not frappe.db.exists("Repair Job", self.repair_job):
			return

		job = frappe.get_doc("Repair Job", self.repair_job)
		if job.quality_check == self.name:
			return

		job.quality_check = self.name
		job.save(ignore_permissions=True)
