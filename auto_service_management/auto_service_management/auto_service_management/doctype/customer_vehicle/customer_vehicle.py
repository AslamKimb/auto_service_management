# Copyright (c) 2026, Aslam Kimbugwe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class CustomerVehicle(Document):
	def validate(self):
		self.validate_unique_vehicle()

	def validate_unique_vehicle(self):
		"""Ensure no duplicate registration across the system."""
		if self.vin_chassis_number:
			existing = frappe.db.exists(
				"Customer Vehicle",
				{"vin_chassis_number": self.vin_chassis_number, "name": ("!=", self.name)},
			)
			if existing:
				frappe.throw(
					f"Another Customer Vehicle with VIN {self.vin_chassis_number} already exists ({existing})"
				)
