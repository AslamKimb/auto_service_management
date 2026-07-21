from __future__ import annotations

import frappe
from frappe import _


DEFAULT_LABOUR_ITEM = "ASM-WORKSHOP-LABOUR"


def execute():
	if not frappe.db.table_exists("Repair Job Service Labour"):
		return

	settings = frappe.get_single("Auto Service Settings")
	labour_item = _ensure_labour_item(settings.default_labour_item)
	if settings.default_labour_item != labour_item:
		frappe.db.set_single_value("Auto Service Settings", "default_labour_item", labour_item)

	for row in frappe.get_all(
		"Repair Job Service Labour",
		filters={"item_code": ["is", "not set"]},
		pluck="name",
	):
		frappe.db.set_value(
			"Repair Job Service Labour",
			row,
			"item_code",
			labour_item,
			update_modified=False,
		)

	_repair_draft_invoice_items()

	from auto_service_management.auto_service_management.workflow_compatibility import (
		sync_repair_job_related_tables,
	)

	for job_name in frappe.get_all("Repair Job", pluck="name"):
		sync_repair_job_related_tables(job_name)


def _ensure_labour_item(item_code):
	if item_code and _is_valid_labour_item(item_code):
		return item_code

	if frappe.db.exists("Item", DEFAULT_LABOUR_ITEM):
		if not _is_valid_labour_item(DEFAULT_LABOUR_ITEM):
			frappe.throw(
				_("Item {0} exists but is not a valid Labour Service Item.").format(DEFAULT_LABOUR_ITEM)
			)
		return DEFAULT_LABOUR_ITEM

	_ensure_labour_references()

	item = frappe.get_doc(
		{
			"doctype": "Item",
			"item_code": DEFAULT_LABOUR_ITEM,
			"item_name": "Workshop Labour",
			"item_group": "Services",
			"stock_uom": "Hour",
			"is_stock_item": 0,
			"is_sales_item": 1,
			"is_purchase_item": 0,
		}
	)
	item.insert(ignore_permissions=True)

	price_list = frappe.db.get_single_value("Auto Service Settings", "selling_price_list") or frappe.db.get_single_value(
		"Auto Service Settings", "price_list"
	)
	rate = frappe.db.get_single_value("Auto Service Settings", "default_labour_rate")
	if price_list and rate and not frappe.db.exists(
		"Item Price", {"item_code": item.name, "price_list": price_list}
	):
		frappe.get_doc(
			{
				"doctype": "Item Price",
				"item_code": item.name,
				"price_list": price_list,
				"price_list_rate": rate,
				"uom": "Hour",
			}
		).insert(ignore_permissions=True)

	return item.name


def _ensure_labour_references():
	if not frappe.db.exists("UOM", "Hour"):
		frappe.get_doc({"doctype": "UOM", "uom_name": "Hour"}).insert(ignore_permissions=True)

	if frappe.db.exists("Item Group", "Services"):
		return

	parent = "All Item Groups"
	if not frappe.db.exists("Item Group", parent):
		parent = frappe.db.get_value("Item Group", {"is_group": 1}, "name")
	if not parent:
		frappe.throw(_("An Item Group is required before creating the default Labour Service Item."))
	frappe.get_doc(
		{
			"doctype": "Item Group",
			"item_group_name": "Services",
			"parent_item_group": parent,
			"is_group": 0,
		}
	).insert(ignore_permissions=True)


def _is_valid_labour_item(item_code):
	item = frappe.db.get_value(
		"Item",
		item_code,
		["disabled", "is_stock_item", "is_sales_item", "stock_uom"],
		as_dict=True,
	)
	return bool(item and not item.disabled and not item.is_stock_item and item.is_sales_item and item.stock_uom == "Hour")


def _repair_draft_invoice_items():
	rows = frappe.get_all(
		"Sales Invoice Item",
		filters={
			"repair_component_doctype": "Repair Job Service Labour",
			"item_code": ["is", "not set"],
		},
		pluck="parent",
	)
	for invoice_name in set(rows):
		if frappe.db.get_value("Sales Invoice", invoice_name, "docstatus") != 0:
			continue
		invoice = frappe.get_doc("Sales Invoice", invoice_name)
		changed = False
		for item in invoice.items:
			if item.item_code or item.repair_component_doctype != "Repair Job Service Labour":
				continue
			labour_item = frappe.db.get_value(
				"Repair Job Service Labour", item.repair_component_row, "item_code"
			)
			if labour_item:
				item.item_code = labour_item
				changed = True
		if changed:
			invoice.run_method("set_missing_values")
			invoice.run_method("calculate_taxes_and_totals")
			invoice.save(ignore_permissions=True)
