# Copyright (c) 2026, Aslam Kimbugwe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from auto_service_management.auto_service_management.workflow_compatibility import (
	recompute_repair_job_state,
	sync_quality_check_road_tests,
)


class QualityCheck(Document):
	def validate(self):
		self.sync_with_repair_job()
		self.validate_repair_job_state()
		self.validate_unique_for_repair_job()
		sync_quality_check_road_tests(self)

	def on_update(self):
		self.sync_primary_link()
		sync_quality_check_road_tests(self)
		recompute_repair_job_state(self.repair_job)

	def validate_repair_job_state(self):
		"""Keep QC and road-test evidence optional at every Repair Job status."""
		return

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
			{"repair_job": self.repair_job, "docstatus": ["<", 2], "name": ["!=", self.name or ""]},
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
