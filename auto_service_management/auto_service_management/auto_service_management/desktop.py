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


def _ensure_workspace_type_field():
	"""Set the ``type`` field on the Workspace if it is NULL.

	Required for Frappe v16 — ``type`` is a required field on Workspace.
	"""
	frappe.db.set_value(
		"Workspace",
		"Workshop Management",
		"type",
		"Workspace",
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

	In Frappe v16, desk icons must use ``link_type = "Workspace Sidebar"``
	with ``link_to`` set to the workspace name — NOT ``link_type = "External"``.
	"""
	app_name = "auto_service_management"
	app_title = "Auto Service Management"
	workspace_name = "Workshop Management"

	# Clean up any stale External-type icon left from earlier code
	stale = frappe.db.exists(
		"Desktop Icon",
		{"icon_type": "App", "app": app_name, "link_type": "External"},
	)
	if stale:
		frappe.delete_doc("Desktop Icon", stale, ignore_permissions=True)

	# Skip if a correct Workspace-Sidebar-type icon already exists
	if frappe.db.exists(
		"Desktop Icon",
		{"icon_type": "App", "app": app_name, "link_type": "Workspace Sidebar"},
	):
		return

	icon = frappe.new_doc("Desktop Icon")
	icon.label = app_title
	icon.icon_type = "App"
	icon.link_type = "Workspace Sidebar"
	icon.link_to = workspace_name
	icon.app = app_name
	icon.standard = 1
	icon.idx = 0
	icon.insert(ignore_if_duplicate=True, ignore_links=True)

	frappe.clear_cache()


def setup_desktop():
	"""Run all desktop setup steps: icon, workspace fields, sidebar.

	Called from ``after_install``, ``after_migrate``, and ``before_tests``
	/hooks so fresh installs, existing deployments, and test runs all get
	the full desk setup automatically.

	Order matters: workspace fields and sidebar must exist before the
	Desktop Icon (which validates its link_to against Workspace Sidebar).
	"""
	_ensure_workspace_app_field()
	_ensure_workspace_type_field()
	_ensure_workspace_sidebar()
	create_app_desktop_icon()


def ensure_permission():
	"""Permission check for the ``add_to_apps_screen`` hook.

	Any non-Guest user may see the module card.  Role-specific access is
	enforced at the Workspace and DocType levels.
	"""
	return frappe.session.user != "Guest"
