# Copyright (c) 2026, Aslam Kimbugwe and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


def normalize_vin_chassis_number(value: str | None) -> str | None:
	"""Return the canonical comparison value for a VIN/chassis identifier.

	VINs are case-insensitive identifiers.  Removing incidental whitespace keeps
	imports and desk entry from creating two records for the same identifier,
	while returning ``None`` preserves the intended multiple-blank semantics.
	"""
	normalized = "".join(str(value or "").split()).upper()
	return normalized or None


class CustomerVehicle(Document):
	def validate(self):
		self.validate_make_and_model()
		self.validate_engine_model()
		self.validate_unique_vehicle()

	def validate_make_and_model(self):
		if not self.model:
			return
		if not self.make:
			frappe.throw(_("Make is required when Model is set."))

		model_make = frappe.db.get_value("Vehicle Model", self.model, "vehicle_make")
		if not model_make:
			frappe.throw(_("Vehicle Model {0} does not exist.").format(self.model))
		if model_make != self.make:
			frappe.throw(
				_("Vehicle Model {0} belongs to {1}, not {2}.").format(self.model, model_make, self.make)
			)

	def validate_engine_model(self):
		if self.engine_model and not frappe.db.exists("Vehicle Engine", self.engine_model):
			frappe.throw(_("Vehicle Engine {0} does not exist.").format(self.engine_model))

	def validate_unique_vehicle(self):
		"""Normalize and reject duplicate nonblank VIN/chassis identifiers."""
		self.vin_chassis_number = normalize_vin_chassis_number(self.vin_chassis_number)
		if self.vin_chassis_number:
			existing = frappe.db.exists(
				"Customer Vehicle",
				{"vin_chassis_number": self.vin_chassis_number, "name": ("!=", self.name)},
			)
			if existing:
				frappe.throw(
					_("Another Customer Vehicle with VIN / Chassis Number {0} already exists ({1}).").format(
						self.vin_chassis_number, existing
					)
				)

	def show_unique_validation_message(self, error):
		"""Turn the database race winner into a domain-specific validation error."""
		if "vin_chassis_number" in str(error):
			frappe.throw(
				_("VIN / Chassis Number {0} already belongs to another Customer Vehicle.").format(
					self.vin_chassis_number
				)
			)
		super().show_unique_validation_message(error)
