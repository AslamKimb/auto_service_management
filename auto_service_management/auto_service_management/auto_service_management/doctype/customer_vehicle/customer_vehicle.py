# Copyright (c) 2026, Aslam Kimbugwe and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime


def _throw(code: str, message: str):
	frappe.local.response["error_code"] = code
	frappe.throw(message)


def normalize_vin_chassis_number(value: str | None) -> str | None:
	"""Return the canonical comparison value for a VIN/chassis identifier.

	VINs are case-insensitive identifiers.  Removing incidental whitespace keeps
	imports and desk entry from creating two records for the same identifier,
	while returning ``None`` preserves the intended multiple-blank semantics.
	"""
	normalized = "".join(str(value or "").split()).upper()
	return normalized or None


class CustomerVehicle(Document):
	def after_insert(self):
		if self.customer:
			from auto_service_management.auto_service_management.doctype.customer_vehicle_customer_association.customer_vehicle_customer_association import (
				create_initial_association,
			)

			create_initial_association(self.name, self.customer, source_name=self.name)

	def validate(self):
		old = self.get_doc_before_save()
		if old and old.customer != self.customer and not getattr(self.flags, "allow_customer_association_update", False):
			frappe.throw(_("Use the customer association action to change a vehicle's current customer."))
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


@frappe.whitelist(methods=["GET"])
def get_customer_vehicle_association_history(customer_vehicle: str) -> dict:
	"""Return a permission-scoped, chronological customer association timeline."""
	if not customer_vehicle:
		_throw("VALIDATION_FAILED", _("Customer Vehicle is required."))
	vehicle = frappe.get_doc("Customer Vehicle", customer_vehicle)
	vehicle.check_permission("read")
	rows = frappe.get_all(
		"Customer Vehicle Customer Association",
		filters={"customer_vehicle": vehicle.name},
		fields=["name", "customer_vehicle", "customer", "valid_from", "valid_to", "source_doctype", "source_name"],
		order_by="valid_from asc, creation asc",
		limit_page_length=0,
	)
	return {"customer_vehicle": vehicle.name, "history": rows}


@frappe.whitelist(methods=["POST"])
def associate_customer(
	customer_vehicle: str,
	customer: str,
	expected_version: str | None = None,
	idempotency_key: str | None = None,
	source_doctype: str = "Repair Job",
	source_name: str | None = None,
) -> dict:
	"""Associate a vehicle to a customer through one audited, idempotent action."""
	from auto_service_management.auto_service_management.doctype.customer_vehicle_customer_association.customer_vehicle_customer_association import (
		associate_vehicle_customer,
	)

	return associate_vehicle_customer(
		customer_vehicle=customer_vehicle,
		customer=customer,
		expected_version=expected_version,
		idempotency_key=idempotency_key,
		source_doctype=source_doctype,
		source_name=source_name,
	)
