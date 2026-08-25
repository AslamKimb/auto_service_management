# Copyright (c) 2026, Aslam Kimbugwe and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class ItemVehicleFitment(Document):
	def validate(self):
		self.validate_make_and_model()
		self.validate_year_range()
		self.validate_unique_fitment()

	def validate_make_and_model(self):
		if not self.vehicle_model:
			return
		if not self.vehicle_make:
			frappe.throw(_("Vehicle Make is required when Vehicle Model is set."))

		model_make = frappe.db.get_value("Vehicle Model", self.vehicle_model, "vehicle_make")
		if not model_make:
			frappe.throw(_("Vehicle Model {0} does not exist.").format(self.vehicle_model))
		if model_make != self.vehicle_make:
			frappe.throw(
				_("Vehicle Model {0} belongs to {1}, not {2}.").format(
					self.vehicle_model, model_make, self.vehicle_make
				)
			)

	def validate_year_range(self):
		if self.year_from and self.year_to and self.year_from > self.year_to:
			frappe.throw(_("Year From cannot be later than Year To."))

	def validate_unique_fitment(self):
		filters = {
			"item": self.item,
			"vehicle_make": self.vehicle_make or "",
			"vehicle_model": self.vehicle_model or "",
			"vehicle_engine": self.vehicle_engine or "",
			"year_from": self.year_from or 0,
			"year_to": self.year_to or 0,
		}
		if not self.is_new():
			filters["name"] = ("!=", self.name)

		existing = frappe.db.exists("Item Vehicle Fitment", filters)
		if existing:
			frappe.throw(
				_("This item already has the same vehicle fitment ({0}).").format(existing)
			)
