from __future__ import annotations

import frappe
from frappe.permissions import copy_perms

PERMISSION_FIELDS = (
	"read",
	"write",
	"create",
	"delete",
	"submit",
	"cancel",
	"amend",
	"report",
	"export",
	"import",
	"share",
	"print",
	"email",
	"select",
	"if_owner",
)


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
			fields=["name", "role", "permlevel", *PERMISSION_FIELDS],
			limit_page_length=0,
		)
		if not custom_rows:
			continue
		standard_rows = {
			(row.role, row.permlevel): row
			for row in frappe.get_all(
				"DocPerm",
				filters={"parent": doctype},
				fields=["role", "permlevel", *PERMISSION_FIELDS],
				limit_page_length=0,
			)
		}
		for row in custom_rows:
			standard = standard_rows.get((row.role, row.permlevel))
			if standard and _permission_values(row) == _permission_values(standard):
				frappe.delete_doc("Custom DocPerm", row.name, force=True, ignore_permissions=True)
		copy_perms(doctype)
	frappe.clear_cache()


def _permission_values(row):
	return {field: int(row.get(field) or 0) for field in PERMISSION_FIELDS}
