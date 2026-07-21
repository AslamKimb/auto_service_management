from __future__ import annotations

import frappe


def execute():
	app_doctypes = frappe.get_all(
		"DocType",
		filters={"module": "Auto Service Management", "istable": 0},
		pluck="name",
		limit_page_length=0,
	)
	for doctype in app_doctypes:
		_ensure_docperm(doctype, "System Manager", read=1, write=1, create=1, delete=1, report=1, export=1, print=1)
	_ensure_custom_invoice_perm("Cashier", write=1, create=1, submit=1, cancel=1, amend=1, read=1, report=1, print=1)
	_ensure_custom_invoice_perm("Service Advisor", write=1, create=1, submit=1, read=1, report=1, print=1)
	frappe.clear_cache()


def _ensure_docperm(doctype, role, **values):
	if frappe.db.exists("Custom DocPerm", {"parent": doctype, "role": role, "permlevel": 0}):
		return
	frappe.get_doc(
		{
			"doctype": "Custom DocPerm",
			"parent": doctype,
			"role": role,
			"permlevel": 0,
			"delete": 0,
			"cancel": 0,
			"amend": 0,
			"share": 0,
			"select": 0,
			**values,
		}
	).insert(ignore_permissions=True)


def _ensure_custom_invoice_perm(role, **values):
	name = frappe.db.get_value(
		"Custom DocPerm", {"parent": "Sales Invoice", "role": role, "permlevel": 0}, "name"
	)
	values = {
		"parent": "Sales Invoice",
		"role": role,
		"permlevel": 0,
		"delete": 0,
		"cancel": 0,
		"amend": 0,
		"share": 0,
		"select": 0,
		**values,
	}
	if name:
		frappe.db.set_value("Custom DocPerm", name, values, update_modified=False)
	else:
		frappe.get_doc({"doctype": "Custom DocPerm", **values}).insert(ignore_permissions=True)
