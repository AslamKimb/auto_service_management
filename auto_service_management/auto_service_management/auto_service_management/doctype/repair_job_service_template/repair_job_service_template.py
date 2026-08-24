# Copyright (c) 2026, Aslam Kimbugwe and contributors
# For license information, please see license.txt

from frappe import _
from frappe.model.document import Document


class RepairJobServiceTemplate(Document):
	def validate(self):
		if self.vehicle_model and not self.vehicle_make:
			from frappe import throw

			throw(_("Vehicle Make is required when Vehicle Model is set."))
		if self.vehicle_model:
			from frappe import db, throw

			model_make = db.get_value("Vehicle Model", self.vehicle_model, "vehicle_make")
			if model_make and model_make != self.vehicle_make:
				throw(_("Vehicle Model must belong to the selected Vehicle Make."))
