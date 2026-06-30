# Copyright (c) 2026, Aslam Kimbugwe and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class FleetServiceCampaign(Document):
	def validate(self):
		self.validate_unique_jobs()
		self.validate_job_customers()

	def on_update(self):
		self.sync_job_links()

	def on_trash(self):
		self.sync_job_links(clear_all=True)

	def validate_unique_jobs(self):
		seen = set()
		for row in self.fleet_jobs or []:
			if not row.repair_job:
				continue
			if row.repair_job in seen:
				frappe.throw(f"Repair Job {row.repair_job} appears more than once in this campaign.")
			seen.add(row.repair_job)

	def validate_job_customers(self):
		for row in self.fleet_jobs or []:
			if not row.repair_job:
				continue
			job_customer = frappe.db.get_value("Repair Job", row.repair_job, "customer")
			if job_customer != self.customer:
				frappe.throw(
					_("Repair Job {0} belongs to customer {1}, not {2}.").format(
						row.repair_job,
						job_customer,
						self.customer,
					)
				)

	def sync_job_links(self, clear_all=False):
		linked_jobs = set(
			frappe.get_all(
				"Repair Job",
				filters={"fleet_service_campaign": self.name},
				pluck="name",
			)
		)
		selected_jobs = set()
		if not clear_all:
			selected_jobs = {row.repair_job for row in self.fleet_jobs or [] if row.repair_job}

		for repair_job in linked_jobs - selected_jobs:
			frappe.db.set_value(
				"Repair Job",
				repair_job,
				"fleet_service_campaign",
				None,
			)
		for repair_job in selected_jobs:
			frappe.db.set_value(
				"Repair Job",
				repair_job,
				"fleet_service_campaign",
				self.name,
			)
