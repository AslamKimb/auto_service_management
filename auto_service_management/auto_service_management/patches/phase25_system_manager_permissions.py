from __future__ import annotations

import frappe

ERP_NEXT_DOCTYPES = (
	"Customer",
	"Vehicle",
	"Item",
	"Project",
	"Task",
	"Timesheet",
	"Quotation",
	"Sales Order",
	"Material Request",
	"Stock Entry",
	"Sales Invoice",
	"Payment Entry",
)
ACTION_PERMISSION_FIELDS = (
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
)
PERMISSION_FIELDS = (*ACTION_PERMISSION_FIELDS, "if_owner")


def execute():
	for doctype in _app_doctypes():
		_ensure_full_system_manager_permission(doctype, standard=True)
		if frappe.db.exists("Custom DocPerm", {"parent": doctype}):
			_ensure_full_system_manager_permission(doctype, standard=False)
	for doctype in ERP_NEXT_DOCTYPES:
		_ensure_standard_custom_permissions(doctype)
		_ensure_full_system_manager_permission(doctype, standard=False)
	frappe.clear_cache()


def all_doctypes():
	return (*_app_doctypes(), *ERP_NEXT_DOCTYPES)


def _app_doctypes():
	return frappe.get_all(
		"DocType",
		filters={"module": "Auto Service Management", "istable": 0},
		pluck="name",
		limit_page_length=0,
	)


def _ensure_standard_custom_permissions(doctype):
	existing = {
		(row.role, row.permlevel)
		for row in frappe.get_all(
			"Custom DocPerm",
			filters={"parent": doctype},
			fields=["role", "permlevel"],
			limit_page_length=0,
		)
	}
	for row in frappe.get_all(
		"DocPerm",
		filters={"parent": doctype},
		fields=["role", "permlevel", *PERMISSION_FIELDS],
		limit_page_length=0,
	):
		if (row.role, row.permlevel) not in existing:
			frappe.get_doc(
				{
					"doctype": "Custom DocPerm",
					"parent": doctype,
					**{field: row.get(field) for field in ("role", "permlevel", *PERMISSION_FIELDS)},
				}
			).insert(ignore_permissions=True)


def _ensure_full_system_manager_permission(doctype, *, standard):
	doctype_name = "DocPerm" if standard else "Custom DocPerm"
	name = frappe.db.get_value(
		doctype_name,
		{"parent": doctype, "role": "System Manager", "permlevel": 0},
		"name",
	)
	applicable_fields = _applicable_action_fields(doctype)
	values = {field: int(field in applicable_fields) for field in ACTION_PERMISSION_FIELDS}
	values["if_owner"] = 0
	if name:
		frappe.db.set_value(doctype_name, name, values, update_modified=False)
	else:
		frappe.get_doc(
			{
				"doctype": doctype_name,
				"parent": doctype,
				"role": "System Manager",
				"permlevel": 0,
				**values,
			}
		).insert(ignore_permissions=True)
	frappe.clear_cache(doctype=doctype)


def _applicable_action_fields(doctype):
	meta = frappe.get_meta(doctype)
	fields = set(ACTION_PERMISSION_FIELDS)
	if not meta.is_submittable:
		fields.difference_update({"submit", "cancel", "amend"})
	if not meta.allow_import:
		fields.discard("import")
	return fields
