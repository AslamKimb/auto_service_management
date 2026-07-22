from __future__ import annotations

import frappe


def execute():
	"""Remove broad custom grants that shadow the DocType's standard permissions."""
	doctypes = frappe.get_all(
		"DocType",
		filters={"module": "Auto Service Management", "istable": 0},
		pluck="name",
		limit_page_length=0,
	)
	for name in frappe.get_all(
		"Custom DocPerm",
		filters={"parent": ["in", doctypes], "role": "System Manager"},
		pluck="name",
		limit_page_length=0,
	):
		frappe.delete_doc("Custom DocPerm", name, force=True, ignore_permissions=True)
	frappe.clear_cache()
