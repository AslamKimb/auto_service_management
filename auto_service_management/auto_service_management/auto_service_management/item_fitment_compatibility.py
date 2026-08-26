# Copyright (c) 2026, Aslam Kimbugwe and contributors

"""Read-only item fitment lookup and Repair Job part snapshots.

Fitment is deliberately many-to-many: an Item remains the stock identity and
these helpers only rank the evidence attached to it for a vehicle context.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping

import frappe
from frappe import _
from frappe.utils import cint

FITMENT_FIELDS = [
	"name",
	"item",
	"vehicle_make",
	"vehicle_model",
	"vehicle_engine",
	"year_from",
	"year_to",
	"verification_status",
	"notes",
	"source",
]
WARNING_STATUSES = {"Broad Match", "Universal Match", "Provisional Match", "Mismatch", "No Fitment Data"}


def calculate_fitment_match(
	vehicle_make: str | None,
	vehicle_model: str | None,
	vehicle_engine: str | None,
	vehicle_year: int | str | None,
	fitments: Iterable[Mapping | object],
) -> dict:
	"""Return the strongest match snapshot for one vehicle context."""
	fitments = list(fitments or [])
	context = {
		"vehicle_make": vehicle_make,
		"vehicle_model": vehicle_model,
		"vehicle_engine": vehicle_engine,
		"vehicle_year": _year(vehicle_year),
	}
	if not any(context.values()):
		return _snapshot("Not Checked", None, context, warning_required=False)

	candidates = []
	for fitment in fitments or []:
		row = _as_dict(fitment)
		if not _candidate_matches(row, context):
			continue
		tier, score = _tier_and_score(row, context)
		verified = 1 if _normalise(row.get("verification_status")) == "verified" else 0
		candidates.append((score, verified, _specificity(row), tier, row))

	if not fitments:
		return _snapshot("No Fitment Data", None, context)
	if not candidates:
		return _snapshot("Mismatch", None, context)

	_, verified, _, tier, row = max(candidates, key=lambda value: value[:4])
	status = (
		"Exact Match"
		if tier == "exact" and verified
		else {
			"exact": "Provisional Match",
			"broad": "Broad Match",
			"universal": "Universal Match",
		}[tier]
	)
	return _snapshot(
		status,
		row.get("name"),
		context,
		verification_status=row.get("verification_status"),
		notes=row.get("notes"),
		source=row.get("source"),
	)


@frappe.whitelist(methods=["GET"])
def get_item_fitment_match(
	item_code: str,
	customer_vehicle: str | None = None,
	vehicle_make: str | None = None,
	vehicle_model: str | None = None,
	vehicle_engine: str | None = None,
	vehicle_year: int | str | None = None,
) -> dict:
	"""GET-only compatibility lookup for one Item and vehicle context."""
	_ensure_get_request()
	_ensure_read_permissions(customer_vehicle)
	if not item_code:
		frappe.throw(_("Item is required for a compatibility lookup."))
	context = _vehicle_context(customer_vehicle, vehicle_make, vehicle_model, vehicle_engine, vehicle_year)
	return calculate_fitment_match(**context, fitments=_get_fitments(item_code))


@frappe.whitelist(methods=["GET"])
def search_compatible_items(
	item_search: str | None = None,
	customer_vehicle: str | None = None,
	vehicle_make: str | None = None,
	vehicle_model: str | None = None,
	vehicle_engine: str | None = None,
	vehicle_year: int | str | None = None,
	limit: int | str = 20,
) -> list[dict]:
	"""GET-only bounded Item search with a compatibility snapshot per result."""
	_ensure_get_request()
	_ensure_read_permissions(customer_vehicle)
	context = _vehicle_context(customer_vehicle, vehicle_make, vehicle_model, vehicle_engine, vehicle_year)
	page_length = min(max(cint(limit) or 20, 1), 100)
	filters = {"disabled": 0}
	or_filters = None
	term = (item_search or "").strip()
	if term:
		like = f"%{term}%"
		or_filters = [
			["Item", "name", "like", like],
			["Item", "item_name", "like", like],
			["Item", "description", "like", like],
		]
	items = frappe.get_all(
		"Item",
		filters=filters,
		or_filters=or_filters,
		fields=["name", "item_name", "description"],
		limit_page_length=page_length,
	)
	results = []
	for item in items:
		match = calculate_fitment_match(**context, fitments=_get_fitments(item.name))
		results.append(
			{"item_code": item.name, "item_name": item.item_name, "description": item.description, **match}
		)
	results.sort(key=lambda row: (_status_rank(row["fitment_match_status"]), row["item_code"]))
	return results


def apply_fitment_snapshot(row, vehicle_context: Mapping | None = None):
	"""Recompute a child-row snapshot and enforce the approved warn-and-allow gate."""
	item_code = getattr(row, "item_code", None)
	if not item_code:
		_set(row, "fitment_match_status", "Not Checked")
		_set(row, "matched_fitment", None)
		return row
	if not _doctype_exists("Item Vehicle Fitment"):
		_set(row, "fitment_match_status", "Not Checked")
		_set(row, "matched_fitment", None)
		return row
	if vehicle_context is None:
		vehicle_context = _get_vehicle_context(getattr(row, "customer_vehicle", None))
	if not any(vehicle_context.values()):
		_set(row, "fitment_match_status", "Not Checked")
		_set(row, "matched_fitment", None)
		return row
	match = calculate_fitment_match(**vehicle_context, fitments=_get_fitments(item_code))
	_set(row, "fitment_match_status", match["fitment_match_status"])
	_set(row, "matched_fitment", match.get("matched_fitment"))
	if match["warning_required"] and not (getattr(row, "fitment_override_reason", None) or "").strip():
		frappe.throw(
			_("An override reason is required for a %(status)s part selection.")
			% {"status": match["fitment_match_status"]},
			title=_("Compatibility warning"),
		)
	return row


def _get_fitments(item_code: str) -> list:
	if not _doctype_exists("Item Vehicle Fitment"):
		return []
	return frappe.get_all(
		"Item Vehicle Fitment", filters={"item": item_code}, fields=FITMENT_FIELDS, limit_page_length=0
	)


def _vehicle_context(customer_vehicle, vehicle_make, vehicle_model, vehicle_engine, vehicle_year) -> dict:
	if customer_vehicle:
		vehicle = (
			frappe.db.get_value(
				"Customer Vehicle",
				customer_vehicle,
				["make", "model", "engine_model", "year_of_manufacture"],
				as_dict=True,
			)
			or {}
		)
		vehicle_make = vehicle.get("make") or vehicle_make
		vehicle_model = vehicle.get("model") or vehicle_model
		vehicle_engine = vehicle.get("engine_model") or vehicle_engine
		vehicle_year = vehicle.get("year_of_manufacture") or vehicle_year
	return {
		"vehicle_make": vehicle_make,
		"vehicle_model": vehicle_model,
		"vehicle_engine": vehicle_engine,
		"vehicle_year": vehicle_year,
	}


def _get_vehicle_context(customer_vehicle):
	return _vehicle_context(customer_vehicle, None, None, None, None)


def _ensure_get_request():
	request = getattr(frappe, "request", None)
	method = getattr(request, "method", None)
	if method and method.upper() != "GET":
		frappe.throw(
			_("Compatibility lookup is read-only and accepts GET requests only."), frappe.PermissionError
		)


def _ensure_read_permissions(customer_vehicle=None):
	if not frappe.has_permission("Item", "read") or not frappe.has_permission("Item Vehicle Fitment", "read"):
		frappe.throw(_("You do not have permission to read item compatibility."), frappe.PermissionError)
	if customer_vehicle and not frappe.has_permission("Customer Vehicle", "read", customer_vehicle):
		frappe.throw(_("You do not have permission to read this Customer Vehicle."), frappe.PermissionError)


def _candidate_matches(row, context):
	for key in ("vehicle_make", "vehicle_model", "vehicle_engine"):
		fitment_value = _normalise(row.get(key))
		context_value = _normalise(context[key])
		if fitment_value and fitment_value != context_value:
			return False
	year = context["vehicle_year"]
	if year is not None:
		from_year = _year(row.get("year_from"))
		to_year = _year(row.get("year_to"))
		if from_year is not None and year < from_year:
			return False
		if to_year is not None and year > to_year:
			return False
	return True


def _tier_and_score(row, context):
	make = _normalise(row.get("vehicle_make"))
	model = _normalise(row.get("vehicle_model"))
	engine = _normalise(row.get("vehicle_engine"))
	year = context["vehicle_year"]
	from_year = _year(row.get("year_from"))
	to_year = _year(row.get("year_to"))
	year_exact = year is not None and (from_year is not None or to_year is not None)
	if model and engine and year_exact:
		return "exact", 400
	if model and engine:
		return "broad", 320
	if model:
		return "broad", 260
	if make:
		return "broad", 180
	return "universal", 100


def _specificity(row):
	return sum(
		bool(_normalise(row.get(key))) for key in ("vehicle_make", "vehicle_model", "vehicle_engine")
	) + int(bool(row.get("year_from") or row.get("year_to")))


def _snapshot(status, matched_fitment, context, warning_required=None, **extra):
	return {
		"fitment_match_status": status,
		"matched_fitment": matched_fitment,
		"warning_required": status in WARNING_STATUSES if warning_required is None else warning_required,
		"vehicle_make": context.get("vehicle_make"),
		"vehicle_model": context.get("vehicle_model"),
		"vehicle_engine": context.get("vehicle_engine"),
		"vehicle_year": context.get("vehicle_year"),
		**extra,
	}


def _as_dict(value):
	if isinstance(value, Mapping):
		return dict(value)
	return {field: getattr(value, field, None) for field in FITMENT_FIELDS}


def _normalise(value):
	return str(value or "").strip().casefold()


def _year(value):
	try:
		return int(value) if value not in (None, "") else None
	except (TypeError, ValueError):
		return None


def _set(row, fieldname, value):
	if hasattr(row, "set"):
		row.set(fieldname, value)
	else:
		setattr(row, fieldname, value)


def _doctype_exists(doctype):
	try:
		return bool(frappe.db.exists("DocType", doctype))
	except Exception:
		return False


def _status_rank(status):
	return {
		"Exact Match": 0,
		"Provisional Match": 1,
		"Broad Match": 2,
		"Universal Match": 3,
		"No Fitment Data": 4,
		"Mismatch": 5,
		"Not Checked": 6,
	}.get(status, 99)
