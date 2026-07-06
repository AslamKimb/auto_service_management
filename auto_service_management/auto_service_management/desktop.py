"""Desk desktop visibility for Auto Service Management.

Ensures an App-type Desktop Icon exists so the module card appears on the
Frappe Desk desktop alongside Accounting, Selling, etc.  The Workshop
Management workspace is automatically linked as a child icon by Frappe's
``create_desktop_icons_from_workspace`` logic.
"""

import frappe


def create_app_desktop_icon():
	"""Create the App-type Desktop Icon if it does not already exist.

	Called from ``after_install`` and ``after_migrate`` hooks so both fresh
	installs and existing deployments get the icon automatically.
	"""
	app_name = "auto_service_management"
	app_title = "Auto Service Management"
	workspace_name = "Workshop Management"

	# Skip if an App-type icon already exists for this app
	existing = frappe.db.exists("Desktop Icon", {"icon_type": "App", "app": app_name})
	if existing:
		# Ensure link_type and link_to are correct even for existing icons
		frappe.db.set_value("Desktop Icon", existing, {
			"link_type": "Workspace Sidebar",
			"link_to": workspace_name,
			"link": "/app/workshop-management",
		})
		frappe.clear_cache()
		return

	icon = frappe.new_doc("Desktop Icon")
	icon.label = app_title
	icon.icon_type = "App"
	icon.link_type = "Workspace Sidebar"
	icon.link_to = workspace_name
	icon.app = app_name
	icon.link = "/app/workshop-management"
	icon.standard = 1
	icon.idx = 0
	icon.insert(ignore_if_duplicate=True)

	frappe.clear_cache()


def ensure_permission():
	"""Permission check for the ``add_to_apps_screen`` hook.

	Any non-Guest user may see the module card.  Role-specific access is
	enforced at the Workspace and DocType levels.
	"""
	return frappe.session.user != "Guest"
