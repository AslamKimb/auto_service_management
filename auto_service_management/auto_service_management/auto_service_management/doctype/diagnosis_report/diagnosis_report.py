# Copyright (c) 2026, Aslam Kimbugwe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class DiagnosisReport(Document):
	def validate(self):
		self.sync_with_repair_job()
		self.validate_repair_job_state()
		self.validate_unique_for_repair_job()

	def on_update(self):
		self.sync_primary_link()

	def sync_with_repair_job(self):
		if not self.repair_job:
			return
		job = frappe.get_doc("Repair Job", self.repair_job)
		if not self.customer_vehicle:
			self.customer_vehicle = job.customer_vehicle
		elif self.customer_vehicle != job.customer_vehicle:
			frappe.throw("Diagnosis Report vehicle must match the linked Repair Job vehicle.")
		if not self.customer_complaint and job.customer_concern:
			self.customer_complaint = job.customer_concern

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

	def validate_unique_for_repair_job(self):
		if not self.repair_job:
			return
		existing = frappe.db.exists(
			"Diagnosis Report",
			{"repair_job": self.repair_job, "name": ["!=", self.name or ""]},
		)
		if existing:
			frappe.throw("Only one Diagnosis Report may be linked to a Repair Job.")

	def sync_primary_link(self):
		if not self.repair_job:
			return
		if frappe.db.get_value("Repair Job", self.repair_job, "diagnosis_report") != self.name:
			frappe.db.set_value(
				"Repair Job", self.repair_job, "diagnosis_report", self.name, update_modified=False
			)
