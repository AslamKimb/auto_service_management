# Copyright (c) 2026, Aslam Kimbugwe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class WorkshopBay(Document):
	def validate(self):
		if self.status == "Under Maintenance" and self.occupied_count() > 0:
			frappe.throw("Cannot set bay to Under Maintenance while jobs are assigned to it.")
		if self.warehouse:
			warehouse = frappe.db.get_value(
				"Warehouse", self.warehouse, ["is_group", "company"], as_dict=True
			)
			company = frappe.db.get_single_value("Auto Service Settings", "company")
			if not warehouse or warehouse.is_group:
				frappe.throw("Workshop Bay warehouse must be a leaf warehouse.")
			if company and warehouse.company != company:
				frappe.throw("Workshop Bay warehouse must belong to the configured company.")

	def occupied_count(self):
		"""Count active repair jobs assigned to this bay."""
		return frappe.db.sql(
			"""SELECT COUNT(*) FROM `tabRepair Job Service` service
			JOIN `tabRepair Job` job ON job.name = service.repair_job
			WHERE service.workshop_bay = %s
			AND service.docstatus != 2
			AND job.job_status NOT IN ('Closed', 'Cancelled')""",
			self.name,
		)[0][0]
