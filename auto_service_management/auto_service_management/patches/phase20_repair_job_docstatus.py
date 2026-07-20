from __future__ import annotations

import frappe


def execute():
	if not frappe.db.table_exists("Repair Job") or not frappe.db.has_column("Repair Job", "docstatus"):
		return
	frappe.db.sql("UPDATE `tabRepair Job` SET docstatus = 0 WHERE docstatus IN (1, 2)")
