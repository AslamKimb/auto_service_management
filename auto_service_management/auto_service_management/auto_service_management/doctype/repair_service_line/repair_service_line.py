# Copyright (c) 2026, Aslam Kimbugwe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class RepairServiceLine(Document):
	def validate(self):
		self.calculate_amount()

	def calculate_amount(self):
		self.amount = (self.quantity or 0) * (self.rate or 0)
