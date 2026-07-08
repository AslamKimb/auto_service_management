# Copyright (c) 2026, Aslam Kimbugwe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class RoadTestReport(Document):
	def validate(self):
		self.sync_with_repair_job()
		self.validate_unique_for_repair_job()
		if self.odometer_start and self.odometer_end:
			if self.odometer_end < self.odometer_start:
				frappe.throw("End odometer cannot be less than start odometer.")

	def on_update(self):
		self.sync_primary_link()

	def sync_with_repair_job(self):
		if not self.repair_job:
			return

		job = frappe.get_doc("Repair Job", self.repair_job)
		if not self.customer_vehicle:
			self.customer_vehicle = job.customer_vehicle
		elif self.customer_vehicle != job.customer_vehicle:
			frappe.throw("Road Test Report vehicle must match the linked Repair Job vehicle.")

		if self.odometer_start is None and job.odometer_in is not None:
			self.odometer_start = job.odometer_in

	def validate_unique_for_repair_job(self):
		if not self.repair_job:
			return

		existing = frappe.db.get_value(
			"Road Test Report",
			{"repair_job": self.repair_job, "name": ["!=", self.name or ""]},
			"name",
		)
		if existing:
			frappe.throw(f"Repair Job {self.repair_job} already has Road Test Report {existing}.")

	def sync_primary_link(self):
		if not self.repair_job or not frappe.db.exists("Repair Job", self.repair_job):
			return

		job = frappe.get_doc("Repair Job", self.repair_job)
		if job.road_test_report == self.name:
			return

		job.road_test_report = self.name
		if self.odometer_end is not None:
			job.odometer_out = self.odometer_end
		job.save(ignore_permissions=True)
