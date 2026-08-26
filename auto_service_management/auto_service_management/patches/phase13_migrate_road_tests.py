from __future__ import annotations

import json

import frappe
from frappe.model.naming import set_new_name

from auto_service_management.auto_service_management.workflow_compatibility import (
	build_quality_check_road_test_row,
)

ROAD_TEST_FIELDS = [
	"name",
	"repair_job",
	"customer_vehicle",
	"test_date",
	"tested_by",
	"odometer_start",
	"odometer_end",
	"duration_minutes",
	"route",
	"braking_ok",
	"steering_ok",
	"engine_performance_ok",
	"transmission_ok",
	"no_warning_lights",
	"test_notes",
	"owner",
	"creation",
	"modified",
	"modified_by",
]


def execute():
	_migrate_road_tests()


def _migrate_road_tests():
	if not frappe.db.table_exists("Road Test Report"):
		return
	if not frappe.db.table_exists("Quality Check"):
		return
	if not frappe.db.table_exists("Quality Check Road Test"):
		return

	for report_row in frappe.get_all(
		"Road Test Report",
		fields=ROAD_TEST_FIELDS,
		order_by="creation asc, name asc",
		limit_page_length=0,
	):
		road_test = frappe.get_doc("Road Test Report", report_row.name)
		quality_check_name = _ensure_quality_check(road_test)
		row = build_quality_check_road_test_row(
			quality_check_name, road_test, road_test.repair_job, road_test.customer_vehicle
		)
		if _quality_check_road_test_exists(row):
			continue
		_insert_quality_check_road_test(row, road_test)


def _ensure_quality_check(road_test):
	quality_check_name = frappe.db.get_value("Quality Check", {"repair_job": road_test.repair_job}, "name")
	if quality_check_name:
		return quality_check_name

	quality_check = frappe.get_doc(
		{
			"doctype": "Quality Check",
			"repair_job": road_test.repair_job,
			"customer_vehicle": road_test.customer_vehicle,
			"qc_date": road_test.test_date,
			"checked_by": road_test.tested_by,
			"status": "Pending",
		}
	)
	set_new_name(quality_check)
	_insert_quality_check(quality_check, road_test)
	frappe.db.set_value(
		"Repair Job", road_test.repair_job, "quality_check", quality_check.name, update_modified=False
	)
	return quality_check.name


def _insert_quality_check(quality_check, road_test):
	columns = (
		"name",
		"repair_job",
		"customer_vehicle",
		"qc_date",
		"checked_by",
		"status",
		"docstatus",
		"owner",
		"creation",
		"modified",
		"modified_by",
	)
	values = {
		"name": quality_check.name,
		"repair_job": quality_check.repair_job,
		"customer_vehicle": quality_check.customer_vehicle,
		"qc_date": quality_check.qc_date,
		"checked_by": quality_check.checked_by,
		"status": quality_check.status or "Pending",
		"docstatus": 0,
		"owner": road_test.owner or frappe.session.user,
		"creation": road_test.creation,
		"modified": road_test.modified,
		"modified_by": road_test.modified_by or road_test.owner or frappe.session.user,
	}
	_insert_row("Quality Check", columns, values)


def _quality_check_road_test_exists(row: dict) -> bool:
	return bool(
		frappe.db.exists(
			"Quality Check Road Test",
			{
				"quality_check": row["quality_check"],
				"repair_job": row["repair_job"],
				"customer_vehicle": row["customer_vehicle"],
				"test_date": row["test_date"],
				"tested_by": row["tested_by"],
				"odometer_start": row["odometer_start"],
				"odometer_end": row["odometer_end"],
				"duration_minutes": row["duration_minutes"],
				"route": row["route"],
				"braking_ok": row["braking_ok"],
				"steering_ok": row["steering_ok"],
				"engine_performance_ok": row["engine_performance_ok"],
				"transmission_ok": row["transmission_ok"],
				"no_warning_lights": row["no_warning_lights"],
				"test_notes": row["test_notes"],
			},
		)
	)


def _insert_quality_check_road_test(row: dict, road_test):
	columns = (
		"name",
		"parent",
		"parenttype",
		"parentfield",
		"idx",
		"docstatus",
		"quality_check",
		"repair_job",
		"customer_vehicle",
		"test_date",
		"tested_by",
		"odometer_start",
		"odometer_end",
		"duration_minutes",
		"route",
		"braking_ok",
		"steering_ok",
		"engine_performance_ok",
		"transmission_ok",
		"no_warning_lights",
		"test_notes",
		"owner",
		"creation",
		"modified",
		"modified_by",
	)
	values = {
		"name": frappe.generate_hash(length=10),
		"parent": row["quality_check"],
		"parenttype": "Quality Check",
		"parentfield": "road_tests",
		"idx": _next_road_test_idx(row["quality_check"]),
		"docstatus": 0,
		"quality_check": row["quality_check"],
		"repair_job": row["repair_job"],
		"customer_vehicle": row["customer_vehicle"],
		"test_date": row["test_date"],
		"tested_by": row["tested_by"],
		"odometer_start": row["odometer_start"],
		"odometer_end": row["odometer_end"],
		"duration_minutes": row["duration_minutes"],
		"route": row["route"],
		"braking_ok": row["braking_ok"],
		"steering_ok": row["steering_ok"],
		"engine_performance_ok": row["engine_performance_ok"],
		"transmission_ok": row["transmission_ok"],
		"no_warning_lights": row["no_warning_lights"],
		"test_notes": row["test_notes"],
		"owner": road_test.owner or frappe.session.user,
		"creation": road_test.creation,
		"modified": road_test.modified,
		"modified_by": road_test.modified_by or road_test.owner or frappe.session.user,
	}
	_insert_row("Quality Check Road Test", columns, values)


def _next_road_test_idx(quality_check_name: str) -> int:
	current = frappe.db.count(
		"Quality Check Road Test", {"parent": quality_check_name, "parentfield": "road_tests"}
	)
	return int(current or 0) + 1


def _insert_row(doctype: str, columns: tuple[str, ...], values: dict):
	table_name = f"tab{doctype}"
	placeholder_sql = ", ".join(["%s"] * len(columns))
	column_sql = ", ".join(f"`{column}`" for column in columns)
	frappe.db.sql(
		f"INSERT INTO `{table_name}` ({column_sql}) VALUES ({placeholder_sql})",
		[values[column] for column in columns],
	)
