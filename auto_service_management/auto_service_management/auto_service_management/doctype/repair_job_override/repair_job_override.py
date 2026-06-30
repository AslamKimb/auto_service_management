# Copyright (c) 2026, Aslam Kimbugwe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class RepairJobOverride(Document):
	def validate(self):
		if self.status == "Approved" and not self.override_by:
			frappe.throw("Override must specify who approved it.")

	def approve(self):
		self.status = "Approved"
		self.save()

	def reject(self):
		self.status = "Rejected"
		self.save()
