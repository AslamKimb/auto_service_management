"""Reconcile legacy identifiers before relying on Phase 33 uniqueness keys."""

from __future__ import annotations

import frappe

from auto_service_management.auto_service_management.doctype.customer_lpo.customer_lpo import (
	build_lpo_uniqueness_key,
	normalize_lpo_number,
)
from auto_service_management.auto_service_management.doctype.customer_vehicle.customer_vehicle import (
	normalize_vin_chassis_number,
)


def execute() -> None:
	"""Normalize existing identifiers and backfill scoped LPO keys idempotently."""
	_reconcile_customer_vehicles()
	_reconcile_customer_lpos()


def validate_legacy_identifier_safety() -> None:
	"""Fail before schema sync if canonicalization would collide with legacy data.

	This hook is intentionally read-only.  Frappe executes ``before_migrate`` before
	DocType schema changes, so a legacy collision cannot make creation of a new
	unique index fail halfway through migration.  The write/backfill pass remains
	owned by :func:`execute` in ``after_migrate``.
	"""
	_reconcile_customer_vehicles(write=False)
	_reconcile_customer_lpos(write=False)


def _reconcile_customer_vehicles(*, write: bool = True) -> None:
	if not frappe.db.exists("DocType", "Customer Vehicle"):
		return
	if not frappe.db.has_column("Customer Vehicle", "vin_chassis_number"):
		return
	seen: dict[str, str] = {}
	for row in frappe.get_all(
		"Customer Vehicle",
		fields=["name", "vin_chassis_number"],
		limit_page_length=0,
		order_by="creation asc, name asc",
	):
		canonical = normalize_vin_chassis_number(row.vin_chassis_number)
		if canonical:
			previous = seen.get(canonical)
			if previous and previous != row.name:
				frappe.throw(
					frappe._(
						"Cannot normalize VIN / Chassis Number {0}: Customer Vehicles {1} and {2} conflict."
					).format(canonical, previous, row.name)
				)
			seen[canonical] = row.name
		if write and row.vin_chassis_number != canonical:
			frappe.db.set_value(
				"Customer Vehicle", row.name, "vin_chassis_number", canonical, update_modified=False
			)


def _reconcile_customer_lpos(*, write: bool = True) -> None:
	if not frappe.db.exists("DocType", "Customer LPO"):
		return
	if not all(
		frappe.db.has_column("Customer LPO", fieldname) for fieldname in ("company", "customer", "lpo_number")
	):
		return
	has_key_column = frappe.db.has_column("Customer LPO", "lpo_uniqueness_key")
	seen: dict[str, str] = {}
	fields = ["name", "company", "customer", "lpo_number"]
	if has_key_column:
		fields.append("lpo_uniqueness_key")
	for row in frappe.get_all(
		"Customer LPO",
		fields=fields,
		limit_page_length=0,
		order_by="creation asc, name asc",
	):
		number = normalize_lpo_number(row.lpo_number)
		key = build_lpo_uniqueness_key(row.company, row.customer, number)
		if key:
			previous = seen.get(key)
			if previous and previous != row.name:
				frappe.throw(
					frappe._(
						"Cannot normalize Customer LPO {0}: records {1} and {2} conflict for the same Company, Customer, and LPO number."
					).format(number, previous, row.name)
				)
			seen[key] = row.name
		if write and (row.lpo_number != number or (has_key_column and row.lpo_uniqueness_key != key)):
			frappe.db.set_value(
				"Customer LPO",
				row.name,
				{"lpo_number": number, **({"lpo_uniqueness_key": key} if has_key_column else {})},
				update_modified=False,
			)
