"""Audited, append-only customer intervals for a reusable Customer Vehicle."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_datetime, now_datetime


def _throw(code: str, message: str):
	frappe.local.response["error_code"] = code
	frappe.throw(message)


class CustomerVehicleCustomerAssociation(Document):
	def validate(self):
		if not self.is_new():
			_throw("VALIDATION_FAILED", _("Customer associations are append-only."))
		if not self.valid_from:
			self.valid_from = now_datetime()
		if self.valid_to and get_datetime(self.valid_to) < get_datetime(self.valid_from):
			_throw("VALIDATION_FAILED", _("Valid To cannot be earlier than Valid From."))

	def on_trash(self):
		_throw("VALIDATION_FAILED", _("Customer association history is append-only."))


def _check_permissions(customer_vehicle: str, customer: str):
	vehicle = frappe.get_doc("Customer Vehicle", customer_vehicle)
	vehicle.check_permission("write")
	if not frappe.db.exists("Customer", customer):
		_throw("VALIDATION_FAILED", _("Customer {0} does not exist.").format(customer))
	frappe.get_doc("Customer", customer).check_permission("read")
	return vehicle


def _existing_idempotent(idempotency_key: str | None):
	if not idempotency_key:
		return None
	return frappe.db.get_value(
		"Customer Vehicle Customer Association",
		{"idempotency_key": idempotency_key},
		["name", "customer_vehicle", "customer", "valid_from", "valid_to", "is_current"],
		as_dict=True,
	)


def create_initial_association(customer_vehicle: str, customer: str, source_name: str | None = None):
	if not customer or frappe.db.exists(
		"Customer Vehicle Customer Association",
		{"customer_vehicle": customer_vehicle},
	):
		return None
	row = frappe.new_doc("Customer Vehicle Customer Association")
	row.update(
		{
			"customer_vehicle": customer_vehicle,
			"customer": customer,
			"valid_from": frappe.db.get_value("Customer Vehicle", customer_vehicle, "creation") or now_datetime(),
			"source_doctype": "Customer Vehicle",
			"source_name": source_name or customer_vehicle,
			"is_current": 1,
		}
	)
	row.insert(ignore_permissions=True)
	return row


def associate_vehicle_customer(
	*,
	customer_vehicle: str,
	customer: str,
	expected_version: str | None = None,
	idempotency_key: str | None = None,
	source_doctype: str = "Repair Job",
	source_name: str | None = None,
) -> dict:
	if not customer_vehicle or not customer:
		_throw("VALIDATION_FAILED", _("Customer Vehicle and Customer are required."))
	vehicle = _check_permissions(customer_vehicle, customer)
	replay = _existing_idempotent(idempotency_key)
	if replay:
		if replay.customer_vehicle != customer_vehicle or replay.customer != customer:
			_throw("ACTIVE_CONFLICT", _("This idempotency key was already used for another association."))
		return {"status": "replayed", "association": replay, "customer_vehicle": customer_vehicle, "customer": customer}
	if expected_version and str(vehicle.modified) != str(expected_version):
		_throw("STALE_REQUEST", _("Customer Vehicle changed. Refresh and try again."))

	current = frappe.db.get_value(
		"Customer Vehicle Customer Association",
		{"customer_vehicle": customer_vehicle, "valid_to": ["is", "not set"]},
		["name", "customer", "valid_from"],
		as_dict=True,
		order_by="valid_from desc",
	)
	if not current and vehicle.customer:
		current = create_initial_association(vehicle.name, vehicle.customer, source_name=vehicle.name)
		if current:
			current = frappe._dict(name=current.name, customer=current.customer, valid_from=current.valid_from)
	if current and current.customer == customer:
		return {"status": "unchanged", "association": current, "customer_vehicle": customer_vehicle, "customer": customer}

	when = now_datetime()
	if current:
		if get_datetime(current.valid_from) > when:
			_throw("ACTIVE_CONFLICT", _("The current customer association has an invalid future start time."))
		frappe.db.set_value(
			"Customer Vehicle Customer Association",
			current.name,
			{"valid_to": when, "is_current": 0},
		)

	row = frappe.new_doc("Customer Vehicle Customer Association")
	row.update(
		{
			"customer_vehicle": customer_vehicle,
			"customer": customer,
			"valid_from": when,
			"source_doctype": source_doctype or "Repair Job",
			"source_name": source_name,
			"idempotency_key": idempotency_key,
			"is_current": 1,
		}
	)
	row.insert()
	vehicle.flags.allow_customer_association_update = True
	vehicle.customer = customer
	vehicle.save()
	return {"status": "associated", "association": row, "customer_vehicle": customer_vehicle, "customer": customer}
