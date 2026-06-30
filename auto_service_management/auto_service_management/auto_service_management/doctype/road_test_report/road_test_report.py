# Copyright (c) 2026, Aslam Kimbugwe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class RoadTestReport(Document):
	def validate(self):
		if self.odometer_start and self.odometer_end:
			if self.odometer_end < self.odometer_start:
				frappe.throw("End odometer cannot be less than start odometer.")
