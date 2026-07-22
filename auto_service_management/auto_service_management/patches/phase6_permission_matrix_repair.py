from __future__ import annotations

import frappe

from auto_service_management.auto_service_management.user_defaults import (
	backfill_default_workspace_for_existing_users,
)

# All custom roles the app needs — created here because the exported Role
# fixtures only export *existing* roles, they never create new ones.
APP_ROLES = [
	"Workshop Manager",
	"Service Advisor",
	"Parts Interpreter",
	"Cashier",
	"Security Gate Officer",
	"Workshop Technician",
]


def execute():
	_ensure_app_roles()
	backfill_default_workspace_for_existing_users()
	ensure_cashier_sales_invoice_custom_docperm()
	ensure_service_advisor_customer_custom_docperm()


def _ensure_app_roles():
	"""Insert any missing custom roles so downstream patches can reference them."""
	for role_name in APP_ROLES:
		if not frappe.db.exists("Role", role_name):
			frappe.get_doc(
				{"doctype": "Role", "role_name": role_name, "desk_access": 1}
			).insert(ignore_permissions=True)
	frappe.clear_cache()


def ensure_cashier_sales_invoice_custom_docperm():
	values = {
		"parent": "Sales Invoice",
		"role": "Cashier",
		"permlevel": 0,
		"read": 1,
		"write": 0,
		"create": 0,
		"delete": 0,
		"submit": 0,
		"cancel": 0,
		"amend": 0,
		"report": 0,
		"export": 0,
		"import": 0,
		"share": 0,
		"print": 0,
		"email": 0,
		"if_owner": 0,
		"select": 0,
	}
	_ensure_custom_docperm(values, clear_doctype="Sales Invoice")


def ensure_service_advisor_customer_custom_docperm():
	values = {
		"parent": "Customer",
		"role": "Service Advisor",
		"permlevel": 0,
		"read": 1,
		"write": 0,
		"create": 0,
		"delete": 0,
		"submit": 0,
		"cancel": 0,
		"amend": 0,
		"report": 0,
		"export": 0,
		"import": 0,
		"share": 0,
		"print": 0,
		"email": 0,
		"if_owner": 0,
		"select": 1,
	}
	_ensure_custom_docperm(values, clear_doctype="Customer")


def _ensure_custom_docperm(values: dict[str, object], *, clear_doctype: str) -> None:
	existing = frappe.db.get_value(
		"Custom DocPerm",
		{
			"parent": values["parent"],
			"role": values["role"],
			"permlevel": values["permlevel"],
		},
		"name",
	)
	if existing:
		frappe.db.set_value("Custom DocPerm", existing, values, update_modified=False)
		frappe.clear_cache(doctype=clear_doctype)
		return

	frappe.get_doc({"doctype": "Custom DocPerm", **values}).insert(ignore_permissions=True)
	frappe.clear_cache(doctype=clear_doctype)
