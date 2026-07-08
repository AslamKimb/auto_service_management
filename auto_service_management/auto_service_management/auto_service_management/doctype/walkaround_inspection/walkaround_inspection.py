# Copyright (c) 2026, Aslam Kimbugwe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class WalkaroundInspection(Document):
	def validate(self):
		self.sync_with_repair_job()
		self.validate_repair_job_link()
		self.validate_unique_for_repair_job()

	def after_insert(self):
		self.sync_primary_link()
		self.advance_repair_job()

	def on_update(self):
		self.sync_primary_link()

	def sync_with_repair_job(self):
		if not self.repair_job:
			return
		job = frappe.get_doc("Repair Job", self.repair_job)
		if not self.customer_vehicle:
			self.customer_vehicle = job.customer_vehicle
		elif self.customer_vehicle != job.customer_vehicle:
			frappe.throw("Walkaround Inspection vehicle must match the linked Repair Job vehicle.")

	def validate_repair_job_link(self):
		"""Ensure linked Repair Job is in an appropriate state."""
		if self.repair_job:
			job = frappe.get_doc("Repair Job", self.repair_job)
			if job.job_status not in ("Checked In", "Walkaround Inspection"):
				frappe.throw(
					f"Walkaround Inspection can only be created for Repair Jobs "
					f"in 'Checked In' or 'Walkaround Inspection' state. Current: {job.job_status}"
				)

	def validate_unique_for_repair_job(self):
		if not self.repair_job:
			return
		existing = frappe.db.exists(
			"Walkaround Inspection",
			{"repair_job": self.repair_job, "name": ["!=", self.name or ""]},
		)
		if existing:
			frappe.throw("Only one Walkaround Inspection may be linked to a Repair Job.")

	def advance_repair_job(self):
		if not self.repair_job:
			return
		job = frappe.get_doc("Repair Job", self.repair_job)
		if job.job_status == "Checked In":
			job.job_status = "Walkaround Inspection"
			job.save(ignore_permissions=True)

	def sync_primary_link(self):
		if not self.repair_job:
			return
		if frappe.db.get_value("Repair Job", self.repair_job, "walkaround_inspection") != self.name:
			frappe.db.set_value(
				"Repair Job", self.repair_job, "walkaround_inspection", self.name, update_modified=False
			)
