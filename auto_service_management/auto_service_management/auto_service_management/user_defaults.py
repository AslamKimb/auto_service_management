from __future__ import annotations

import frappe

WORKSHOP_DEFAULT_WORKSPACE = "Workshop Management"
WORKSHOP_DESK_ROLES = {
	"Service Advisor",
	"Workshop Manager",
	"Parts Interpreter",
	"Cashier",
	"Security Gate Officer",
	"Workshop Technician",
}


def assign_default_workspace(doc, method=None):
	"""Assign the workshop workspace when a qualifying user has no explicit default."""
	if not _should_assign_default_workspace(doc.default_workspace, _roles_from_user_doc(doc)):
		return

	doc.default_workspace = WORKSHOP_DEFAULT_WORKSPACE


def backfill_default_workspace_for_existing_users():
	"""Backfill the workshop workspace for qualifying users with a blank default."""
	for user in frappe.get_all("User", fields=["name", "default_workspace"], limit_page_length=0):
		if not _should_assign_default_workspace(user.default_workspace, frappe.get_roles(user.name)):
			continue

		frappe.db.set_value(
			"User",
			user.name,
			"default_workspace",
			WORKSHOP_DEFAULT_WORKSPACE,
			update_modified=False,
		)


def _roles_from_user_doc(doc) -> set[str]:
	return {row.role for row in (doc.roles or []) if getattr(row, "role", None)}


def _should_assign_default_workspace(current_default_workspace, roles) -> bool:
	return not (current_default_workspace or "").strip() and bool(WORKSHOP_DESK_ROLES.intersection(roles))
