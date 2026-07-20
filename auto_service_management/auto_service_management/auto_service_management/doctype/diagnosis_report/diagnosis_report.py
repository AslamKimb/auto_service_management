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

	def on_submit(self):
		self.sync_primary_link()
		self._recompute_repair_job()

	def on_cancel(self):
		self._recompute_repair_job()

	def _recompute_repair_job(self):
		if self.repair_job:
			from auto_service_management.auto_service_management.workflow_compatibility import (
				recompute_repair_job_state,
			)

			recompute_repair_job_state(self.repair_job)

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
			if status not in ("Assessment", "Awaiting Approval", "In Repair"):
				frappe.throw(
					f"Diagnosis Report requires the Repair Job to be in "
					f"'Assessment', 'Awaiting Approval', or 'In Repair' state. Current: {status}"
				)

	def validate_unique_for_repair_job(self):
		if not self.repair_job:
			return
		existing = frappe.db.sql(
			"""SELECT name FROM `tabDiagnosis Report`
			WHERE repair_job = %s AND name != %s AND docstatus != 2 LIMIT 1""",
			(self.repair_job, self.name or ""),
			as_dict=False,
		)
		if existing:
			existing = existing[0][0]
		if existing:
			frappe.throw("Only one Diagnosis Report may be linked to a Repair Job.")

	def sync_primary_link(self):
		if not self.repair_job:
			return
		if frappe.db.get_value("Repair Job", self.repair_job, "diagnosis_report") != self.name:
			frappe.db.set_value(
				"Repair Job", self.repair_job, "diagnosis_report", self.name, update_modified=False
			)
