# Copyright (c) 2026, Aslam Kimbugwe and contributors
# For license information, please see license.txt

from frappe.model.document import Document

SERVICE_TYPE_ALIASES = {
	"Parts": "Part",
	"Subcontract": "Subcontracted Service",
}


class RepairServiceLine(Document):
	def validate(self):
		self.normalize_component()
		self.calculate_amount()

	def normalize_component(self):
		self.service_type = SERVICE_TYPE_ALIASES.get(self.service_type, self.service_type)
		if self.quantity is None:
			self.quantity = 1
		if self.billable is None:
			self.billable = 1
		if self.service_type == "Labour" and not self.estimated_hours:
			self.estimated_hours = self.quantity

	def calculate_amount(self):
		gross_amount = (self.quantity or 0) * (self.rate or 0)
		self.discount_amount = gross_amount * (self.discount_percentage or 0) / 100
		self.amount = gross_amount - (self.discount_amount or 0)
		self.cost_amount = (self.quantity or 0) * (self.cost_rate or 0)
		self.margin_amount = (self.amount or 0) - (self.cost_amount or 0)
		self.margin_percentage = (self.margin_amount / self.amount * 100) if self.amount else 0
