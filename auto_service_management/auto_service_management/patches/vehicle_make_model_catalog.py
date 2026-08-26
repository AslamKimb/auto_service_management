from __future__ import annotations

import frappe

from auto_service_management.vehicle_catalog import DEFAULT_VEHICLE_CATALOG


def execute():
	_migrate_existing_vehicles()
	_seed_catalog()


def _migrate_existing_vehicles():
	for row in frappe.get_all("Customer Vehicle", fields=["name", "make", "model"]):
		make_name, model_name = _resolve_legacy_values(row.make, row.model)
		if not make_name and not model_name:
			continue

		if make_name:
			make_name = _ensure_make(make_name)
		if model_name:
			model_name = _ensure_model(make_name, model_name)

		values = {}
		if row.make != make_name:
			values["make"] = make_name
		if row.model != model_name:
			values["model"] = model_name
		if values:
			frappe.db.set_value("Customer Vehicle", row.name, values, update_modified=False)


def _resolve_legacy_values(make_value, model_value):
	make_name = _clean(make_value)
	model_value = _clean(model_value)

	if model_value and frappe.db.exists("Vehicle Model", model_value):
		model_make, model_name = frappe.db.get_value(
			"Vehicle Model", model_value, ["vehicle_make", "model_name"]
		)
		if not make_name:
			return model_make, model_name
		if make_name == model_make:
			return make_name, model_name
		model_value = model_name
	if make_name and model_value.casefold().startswith(f"{make_name} - ".casefold()):
		model_value = model_value[len(make_name) + 3 :]

	if model_value and not make_name:
		make_name = "Unspecified"
	return make_name, model_value


def _seed_catalog():
	for make_name, model_names in DEFAULT_VEHICLE_CATALOG.items():
		make_name = _ensure_make(make_name)
		for model_name in model_names:
			_ensure_model(make_name, model_name)


def _ensure_make(make_name):
	make_name = _clean(make_name)
	if not make_name:
		return ""

	existing = frappe.db.exists("Vehicle Make", {"make_name": make_name})
	if existing:
		return existing

	return (
		frappe.get_doc({"doctype": "Vehicle Make", "make_name": make_name})
		.insert(ignore_permissions=True)
		.name
	)


def _ensure_model(make_name, model_name):
	model_name = _clean(model_name)
	if not model_name:
		return ""
	if frappe.db.exists("Vehicle Model", model_name):
		existing_make, friendly_name = frappe.db.get_value(
			"Vehicle Model", model_name, ["vehicle_make", "model_name"]
		)
		if existing_make == make_name:
			model_name = friendly_name

	existing = frappe.db.exists("Vehicle Model", {"vehicle_make": make_name, "model_name": model_name})
	if existing:
		return existing

	return (
		frappe.get_doc(
			{
				"doctype": "Vehicle Model",
				"vehicle_make": make_name,
				"model_name": model_name,
			}
		)
		.insert(ignore_permissions=True)
		.name
	)


def _clean(value):
	return str(value or "").strip()
