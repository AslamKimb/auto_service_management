from __future__ import annotations

import frappe
from frappe.permissions import copy_perms


def execute():
	"""Ensure app-owned DocTypes don't lose standard access when custom perms exist."""
	doctypes = frappe.get_all(
		"DocType",
		filters={"module": "Auto Service Management", "istable": 0},
		pluck="name",
		limit_page_length=0,
	)
	for doctype in doctypes:
		custom_rows = frappe.get_all(
			"Custom DocPerm",
			filters={"parent": doctype},
			fields=["name", "role", "permlevel"],
			limit_page_length=0,
		)
		if not custom_rows:
			continue
		standard_roles = set(
			frappe.get_all("DocPerm", filters={"parent": doctype}, pluck="role", limit_page_length=0)
		)
		for row in custom_rows:
			if row.role in standard_roles:
				frappe.delete_doc("Custom DocPerm", row.name, force=True, ignore_permissions=True)
		copy_perms(doctype)
	frappe.clear_cache()
