"""Desk desktop visibility for Auto Service Management.

Ensures an App-type Desktop Icon exists so the module card appears on the
Frappe Desk desktop alongside Accounting, Selling, etc.  The Workshop
Management workspace is automatically linked as a child icon by Frappe's
``create_desktop_icons_from_workspace`` logic.
"""

import frappe


def _ensure_workspace_app_field():
	"""Set the ``app`` field on the Workspace if it is NULL.

	Required for Frappe v16 desk routing — without it, the workspace
	doesn't appear in any app's workspace list and the SPA 404s.
	"""
	frappe.db.set_value(
		"Workspace",
		"Workshop Management",
		"app",
		"auto_service_management",
		update_modified=False,
	)


def _ensure_workspace_sidebar():
	"""Create the Workspace Sidebar entry if it does not exist.

	Frappe v16's desk loads workspace route resolution from Workspace
	Sidebar records. Without it, clicking the app icon gives a 404.
	"""
	sidebar_name = "Workshop Management"
	if frappe.db.exists("Workspace Sidebar", sidebar_name):
		return

	frappe.get_doc(
		{
			"doctype": "Workspace Sidebar",
			"name": sidebar_name,
			"title": sidebar_name,
			"app": "auto_service_management",
			"standard": 1,
		}
	).insert(ignore_permissions=True, ignore_if_duplicate=True)

	# Add the sidebar item linking to the workspace
	existing_item = frappe.db.exists(
		"Workspace Sidebar Item",
		{"parent": sidebar_name, "link_to": "Workshop Management"},
	)
	if not existing_item:
		frappe.get_doc(
			{
				"doctype": "Workspace Sidebar Item",
				"parent": sidebar_name,
				"parenttype": "Workspace Sidebar",
				"parentfield": "items",
				"label": "Workshop Management",
				"link_type": "Workspace",
				"link_to": "Workshop Management",
				"type": "Link",
				"idx": 0,
			}
		).insert(ignore_permissions=True)


def create_app_desktop_icon():
	"""Create the App-type Desktop Icon if it does not already exist.

	Called from ``after_install``, ``after_migrate``, and ``before_tests``
	/hooks so fresh installs, existing deployments, and test runs all get
	the icon automatically.
	"""
	app_name = "auto_service_management"
	app_title = "Auto Service Management"

	# Skip if an App-type icon already exists for this app
	if frappe.db.exists("Desktop Icon", {"icon_type": "App", "app": app_name}):
		return

	icon = frappe.new_doc("Desktop Icon")
	icon.label = app_title
	icon.icon_type = "App"
	icon.link_type = "External"
	icon.app = app_name
	icon.link = "/app/workshop-management"
	icon.standard = 1
	icon.idx = 0
	icon.insert(ignore_if_duplicate=True)

	frappe.clear_cache()


def setup_desktop():
	"""Run all desktop setup steps: icon, workspace app field, sidebar.

	Called from ``before_tests`` hook.
	"""
	create_app_desktop_icon()
	_ensure_workspace_app_field()
	_ensure_workspace_sidebar()


def ensure_permission():
	"""Permission check for the ``add_to_apps_screen`` hook.

	Any non-Guest user may see the module card.  Role-specific access is
	enforced at the Workspace and DocType levels.
	"""
	return frappe.session.user != "Guest"
